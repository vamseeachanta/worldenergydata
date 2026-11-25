# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas==3.1.1", "numpy==2.4.6", "matplotlib==3.11.2", "pillow==13.0.0"]
# ///
"""Rebuild Part 6 of Life of a Gulf of America well from two BSEE archives."""
import argparse
import csv
import io
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import xml.etree.ElementTree as ET

import pandas as pd


ROOT = Path(__file__).resolve().parent
BORE = "BoreholeRawData.zip"
EOR = "eWellEORRawData.zip"
REPRODUCTION_SHA256 = "bdf7afa8f21860bc9815be205f32f50fc5b52205bcc3440cfea5ae439a74c86d"
AS_OF = pd.Timestamp("2026-11-23")
R4 = ["0 to 200 m", "201 to 400 m", "401 to 800 m", "801 to 1,000 m", "Deeper than 1,000 m"]
SERIES = ["Under 100 m", "100 to under 500 m", "500 to under 1,500 m", "1,500 m and deeper"]
NO_DEPTH, ALL = "No depth", "All depths"
CODES = ["PA", "TA", "COM", "Other"]
YEARS = range(2005, 2026)
FIG3_YEARS = range(1960, 2026)
# Annual EOR points in the comparison series. Its lines are trailing means.
FIG4_PA = dict(enumerate((766, 673, 846, 917, 968, 798, 583, 633, 475, 687,
                          417, 391, 302, 219, 302, 400, 624, 310, 573), start=2007))
BORE_COLS = ["API_WELL_NUMBER", "REGION_CODE", "WELL_SPUD_DATE", "BOREHOLE_STAT_DT",
             "BOREHOLE_STAT_CD", "WATER_DEPTH"]
EOR_COLS = ["API_WELL_NUMBER", "EOR_OPERATION_CD", "BOREHOLE_STAT_CD", "BOREHOLE_STAT_DT"]
CSV_HEADLINES = {
    "status_by_band.csv": ["wells", *CODES, *(code + "_pct" for code in CODES)],
    "ta_by_band.csv": ["ta_count", "q25_years", "median_years", "q75_years", "ta_ge_10_years", "ta_since_2023"],
    "pa_pace_by_band.csv": ["pa_2021_2025", "pa_2016_2025", "pa_per_year_2021_2025",
                            "pa_per_year_2016_2025", "ta_backlog_years_2021_2025",
                            "ta_backlog_years_2016_2025", "ta_plus_com",
                            "ta_plus_com_years_2021_2025", "ta_plus_com_years_2016_2025"],
}


def check_hash(name, expected, actual):
    if actual != expected:
        raise ValueError(f"{name}: expected SHA-256 {expected}, got {actual}")


def verified_members(data_dir):
    """Authenticate both ZIPs, then return the verified bytes of the two tables."""
    sources = json.loads((ROOT / "source_pins.json").read_bytes())["sources"]
    pins = {entry["name"]: entry for entry in sources}
    if len(sources) != 2 or set(pins) != {BORE, EOR}:
        raise ValueError("Expected one pin for each of the borehole and EOR archives")
    archives = {}
    for name in (BORE, EOR):
        pin = pins[name]
        with (data_dir / name).open("rb") as stream:
            payload = stream.read(pin["bytes"])
            digest = hashlib.sha256(payload)
            size = len(payload)
            # Include extra bytes in the reported digest even for an oversized download.
            while extra := stream.read(1024 * 1024):
                digest.update(extra)
                size += len(extra)
        check_hash(name, pin["sha256"], digest.hexdigest())
        if size != pin["bytes"]:
            raise ValueError(f"{name}: expected {pin['bytes']} bytes, got {size}")
        archives[name] = payload
    members = {}
    for name, payload in archives.items():
        member = pins[name]["member"]
        with ZipFile(io.BytesIO(payload)) as archive:
            data = archive.read(member["name"])
        check_hash(member["name"], member["sha256"], hashlib.sha256(data).hexdigest())
        members[name] = data
    return members


def read_table(payload, columns):
    return pd.read_csv(io.BytesIO(payload), dtype=str, encoding="latin1", usecols=columns,
                       keep_default_na=False, na_values=[""])


@dataclass
class Audit:
    lines: list = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)

    def check(self, name, passed, detail=""):
        self.lines.append(f"{'PASS' if passed else 'FAIL'} | {name} | {detail}")

    def keep(self, name, frame, mask):
        if mask.isna().any() or not mask.index.equals(frame.index):
            raise ValueError(f"Unclassified rows: {name}")
        kept = frame.loc[mask]
        dropped = (~mask).sum()
        self.check(name, len(frame) == len(kept) + dropped,
                   f"read {len(frame)} = kept {len(kept)} + dropped {dropped}")
        return kept


def select_wells(raw, audit):
    b = audit.keep("Gulf boreholes (REGION_CODE = G)", raw, raw.REGION_CODE.eq("G")).copy()
    if not b.API_WELL_NUMBER.str.fullmatch(r"[0-9]{10,}", na=False).all():
        raise ValueError("Invalid Gulf API")
    b["well"] = b.API_WELL_NUMBER.str[:10]
    b["spud"] = pd.to_datetime(b.WELL_SPUD_DATE, format="%m/%d/%Y")
    b["status_date"] = pd.to_datetime(b.BOREHOLE_STAT_DT, format="%m/%d/%Y")
    b["depth_ft"] = pd.to_numeric(b.WATER_DEPTH, errors="raise")
    if b.depth_ft.lt(0).any() or b.status_date.gt(AS_OF).any():
        raise ValueError("Negative depth or status effective after the file date")
    b["noncancelled"] = b.BOREHOLE_STAT_CD.ne("CNL")
    flags = b.groupby("well").agg(non_cancelled=("noncancelled", "any"), spuds=("spud", "count"))
    survivors = audit.keep("wells with a non-CNL bore", flags, flags.non_cancelled)
    eligible = audit.keep("remaining wells with any dated spud", survivors, survivors.spuds.gt(0))
    b = audit.keep("bores of eligible Gulf wells", b, b.well.isin(eligible.index)).copy()
    audit.diagnostics.update(gulf_wells=len(flags), all_cnl=int((~flags.non_cancelled).sum()),
                             unspudded=int(survivors.spuds.eq(0).sum()))
    latest = b.groupby("well").status_date.transform("max")
    if latest.isna().any():
        raise ValueError("An eligible well has no dated borehole status")
    candidates = audit.keep("bores on latest dated status per eligible well", b, b.status_date.eq(latest))
    w = audit.keep("stable last source row per tied latest date", candidates,
                   ~candidates.well.duplicated(keep="last")).copy()
    audit.check("one winning bore per eligible API10",
                w.well.is_unique and set(w.well) == set(eligible.index), f"{len(w)} wells")
    w["status"] = w.BOREHOLE_STAT_CD.where(w.BOREHOLE_STAT_CD.isin(CODES[:3]), "Other")
    w["depth_m"] = w.depth_ft.where(w.depth_ft.gt(0)) * 0.3048
    first = candidates.drop_duplicates("well", keep="first")
    first_counts = first.BOREHOLE_STAT_CD.where(first.BOREHOLE_STAT_CD.isin(CODES[:3]), "Other").value_counts()
    earliest = b.sort_values("spud", kind="stable").drop_duplicates("well").set_index("well")
    alternate_band = assign_bands(w.well.map(earliest.depth_ft) * 0.3048, "series")
    audit.diagnostics.update(
        first_tie_status_counts={key: int(first_counts.get(key, 0)) for key in CODES},
        changed_bands_earliest_spud=int(alternate_band.ne(assign_bands(w.depth_m, "series")).sum()),
        tied_wells=int(candidates.groupby("well").size().gt(1).sum()),
        tied_status_conflicts=int(candidates.groupby("well").BOREHOLE_STAT_CD.nunique(dropna=False).gt(1).sum()),
        tied_depth_conflicts=int(candidates.groupby("well").depth_ft.nunique(dropna=False).gt(1).sum()),
        missing_winning_depth=int(w.depth_ft.isna().sum()), zero_winning_depth=int(w.depth_ft.eq(0).sum()))
    return w[["well", "status", "status_date", "depth_m"]]


def assign_bands(depth_m, scheme):
    if scheme == "r4":
        limits, labels, right = [0, 200, 400, 800, 1000, float("inf")], R4, True
    elif scheme == "series":
        limits, labels, right = [0, 100, 500, 1500, float("inf")], SERIES, False
    else:
        raise ValueError(f"Unknown band scheme: {scheme}")
    bins = pd.cut(depth_m.where(depth_m.gt(0)), limits, labels=labels, right=right)
    return bins.cat.add_categories([NO_DEPTH]).fillna(NO_DEPTH).astype("str")


def ratio(stock, rate):
    return stock / rate if rate else None


def summarize(wells, events, scheme, audit):
    bands = R4 if scheme == "r4" else SERIES
    w = wells.assign(band=assign_bands(wells.depth_m, scheme), year=wells.status_date.dt.year)
    w["age"] = (AS_OF - w.status_date).dt.days / 365.25
    e = events.merge(w[["well", "band"]], on="well", how="left", validate="many_to_one")
    if e.band.isna().any():
        raise ValueError("Abandonment report has no eligible API10")
    status, ages, pace = [], [], []
    for band in [*bands, NO_DEPTH, ALL]:
        prefix = f"{scheme} / {band}"
        rows = w if band == ALL else audit.keep(prefix + " stock", w, w.band.eq(band))
        counts = rows.status.value_counts().reindex(CODES, fill_value=0).to_dict()
        s = {"band": band, "wells": len(rows), **counts}
        for code, count in counts.items():
            s[code + "_pct"] = ratio(100 * count, len(rows))
        audit.check(prefix + " statuses sum to wells", sum(counts.values()) == len(rows),
                    f"statuses {sum(counts.values())}, wells {len(rows)}")
        ta = audit.keep(prefix + " current TA", rows, rows.status.eq("TA"))
        pa = audit.keep(prefix + " current PA", rows, rows.status.eq("PA"))
        in_period = audit.keep(prefix + " current PA effective in 2005–2025", pa, pa.year.between(2005, 2025))
        by_year = in_period.year.value_counts().reindex(YEARS, fill_value=0)
        recent = audit.keep(prefix + " current PA effective in 2021–2025", in_period, in_period.year.ge(2021))
        decade = audit.keep(prefix + " current PA effective in 2016–2025", in_period, in_period.year.ge(2016))
        rate5, rate10 = len(recent) / 5, len(decade) / 10
        q = ta.age.quantile([.25, .5, .75], interpolation="linear")
        older = audit.keep(prefix + " current TA age >=10 years", ta, ta.age.ge(10))
        entered = audit.keep(prefix + " current TA entered since 2023", ta, ta.year.ge(2023))
        ages.append(dict(band=band, ta_count=len(ta), q25_years=q[.25], median_years=q[.5],
                         q75_years=q[.75], ta_ge_10_years=len(older), ta_since_2023=len(entered)))
        both = len(ta) + counts["COM"]
        stock_pace = dict(pa_2021_2025=len(recent), pa_2016_2025=len(decade),
                          pa_per_year_2021_2025=rate5, pa_per_year_2016_2025=rate10,
                          ta_backlog_years_2021_2025=ratio(len(ta), rate5),
                          ta_backlog_years_2016_2025=ratio(len(ta), rate10),
                          ta_plus_com=both, ta_plus_com_years_2021_2025=ratio(both, rate5),
                          ta_plus_com_years_2016_2025=ratio(both, rate10))
        band_events = e if band == ALL else audit.keep(prefix + " EOR events", e, e.band.eq(band))
        period_events = audit.keep(prefix + " EOR well/year/status events in 2005–2025",
                                   band_events, band_events.year.between(2005, 2025))
        event_counts = pd.crosstab(period_events.year, period_events.status).reindex(
            index=YEARS, columns=["PA", "TA"], fill_value=0)
        metrics = {}
        for code in ("PA", "TA"):
            series = event_counts[code].loc[2007:]
            for n in (3, 5):
                metrics[f"eor_{code.lower()}_mean_{n}yr"] = series.rolling(n).mean().reindex(YEARS)
            for start, end in [(2007, 2015), (2016, 2025), (2023, 2025)]:
                stock_pace[f"mean_eor_{code.lower()}_{start}_{end}"] = series.loc[start:end].mean()
        audit.check(prefix + " year bins conserve PA wells and EOR events",
                    by_year.sum() == len(in_period) and event_counts.to_numpy().sum() == len(period_events),
                    f"{len(in_period)} current PA wells and {len(period_events)} EOR events across 21 years")
        for year in YEARS:
            pace.append(dict(band=band, year=year, pa_wells=int(by_year[year]), **stock_pace,
                             eor_pa_wells=int(event_counts.at[year, "PA"]),
                             eor_ta_wells=int(event_counts.at[year, "TA"]),
                             **{name: values.at[year] for name, values in metrics.items()}))
        audit.check(prefix + " annual PA counts reconcile to both pace windows",
                    by_year.loc[2021:2025].sum() == len(recent) and by_year.loc[2016:2025].sum() == len(decade),
                    f"2021–2025 {len(recent)}, 2016–2025 {len(decade)}")
        for start in (1990, 2000, 2010, 2020):
            cohort = audit.keep(prefix + f" PA in {start}s through file date", pa,
                                pa.year.between(start, start + 9))
            s[f"pa_in_{start}s"] = len(cohort)
        status.append(s)
    s, t, p = map(pd.DataFrame, [status, ages, pace])
    for start in (1990, 2000, 2010, 2020):
        col = f"pa_in_{start}s"
        s[col + "_pct_of_gulf"] = 100 * s[col] / s[col].iloc[-1]
    for factor, label in ((.95, "minus"), (1.05, "plus")):
        moved = assign_bands(w.depth_m * factor, scheme)
        ct = pd.crosstab(moved, w.status).reindex(index=[*bands, NO_DEPTH], columns=CODES, fill_value=0)
        for code in ["PA", "TA"]:
            s[f"{code}_depth_{label}_5pct"] = [*ct[code], int(w.status.eq(code).sum())]
            s[f"{code}_change_{label}_pct"] = (
                (s[f"{code}_depth_{label}_5pct"] - s[code]) * 100 / s[code].where(s[code].gt(0)))
        audit.check(f"{scheme} {label} 5% depth perturbation conserves wells",
                    ct.to_numpy().sum() == len(w), f"reclassified {ct.to_numpy().sum()} of {len(w)}")
    for col in ["wells", *CODES]:
        audit.check(f"{scheme} bands plus no depth sum to all-depth {col}",
                    s[col].iloc[:-1].sum() == s[col].iloc[-1], f"total {s[col].iloc[-1]}")
    audit.check(f"{scheme} separate no-depth row", s.at[len(bands), "wells"] == w.depth_m.isna().sum(),
                f"{w.depth_m.isna().sum()} wells, {s.at[len(bands), 'PA']} PA")
    audit.check(f"{scheme} TA age table reconciles to status counts",
                t.ta_count.equals(s.TA), f"{t.ta_count.iloc[-1]} TA all depths")
    for year, period in p.groupby("year"):
        cols = ["pa_wells", "eor_pa_wells", "eor_ta_wells"]
        audit.check(f"{scheme} annual PA stock and EOR event totals {year}",
                    period[cols].iloc[:-1].sum().equals(period[cols].iloc[-1]),
                    f"PA {period.pa_wells.iloc[-1]}, EOR PA {period.eor_pa_wells.iloc[-1]}, EOR TA {period.eor_ta_wells.iloc[-1]}")
    return s, t, p


def reproduction(tables, audit, events):
    """Recalculate the earlier tabulations at the precision of each reference value."""
    status, ages, annual = tables
    s, t = status.set_index("band"), ages.set_index("band")
    p = annual.loc[annual.year.eq(2025)].set_index("band")
    rows = []

    def compare(source, band, metric, published, computed, decimals=0):
        printed = None if pd.isna(computed) else round(float(computed), decimals)
        diff = None if printed is None else round(printed - published, decimals)
        rows.append(dict(source=source, band=band, metric=metric, r4_value=published,
                         computed_value=printed, difference=diff, computed_unrounded=computed,
                         published_decimals=decimals,
                         disposition="match" if diff == 0 else "unexplained",
                         explanation="" if diff == 0 else "No verified rule difference establishes the cause."))

    for key, value in [("gulf_wells", 38291), ("all_cnl", 762), ("unspudded", 16)]:
        compare("Appendices A–B", ALL, key, value, audit.diagnostics[key])
    for col, value in zip(["wells", *CODES], [37513, 30684, 2896, 3579, 354]):
        compare("§2", ALL, col, value, s.at[ALL, col])
    # Figure 2 accessible text preserves more precision than the labels inside its bars.
    fig2 = [(34015, 84.0, 7.6, 7.6), (834, 62.9, 18.8, 17.4), (622, 74.4, 7.4, 17.7),
            (346, 54.0, 7.2, 35.3), (1633, 53.5, 4.7, 37.2)]
    for band, values in zip(R4, fig2, strict=True):
        for col, value in zip(["wells", "PA_pct", "TA_pct", "COM_pct"], values, strict=True):
            compare("Figure 2", band, col, value, s.at[band, col], int(col.endswith("_pct")))
    for band, col, expected in [(R4[0], "PA", 28574), (R4[-1], "COM", 608),
                                (NO_DEPTH, "wells", 63), (NO_DEPTH, "PA", 61)]:
        compare("§2, Figures 2–3, §4", band, col, expected, s.at[band, col])
    table1 = [
        (2592, 13.2, 1703, 391.8, 6.6, 7.2), (157, 11.7, 90, 2.2, 71.4, 12.2),
        (46, 10.6, 24, 16.8, 2.7, 3.7), (25, 12.0, 14, 4.8, 5.2, 4.0),
        (76, 2.9, 17, 26.6, 2.9, 2.4), (2896, 13.1, 1848, 442.2, 6.5, 6.9)]
    cols = ["ta_count", "median_years", "ta_ge_10_years", "pa_per_year_2021_2025",
            "ta_backlog_years_2021_2025", "ta_backlog_years_2016_2025"]
    for band, expected in zip([*R4, ALL], table1, strict=True):
        for col, value in zip(cols, expected, strict=True):
            actual = (t if col in t else p).at[band, col]
            compare("Table 1", band, col, value, actual, int(isinstance(value, float)))
    compare("§4", R4[-1], "ta_since_2023", 48, t.at[R4[-1], "ta_since_2023"])
    compare("§4", R4[1], "pa_2021_2025", 11, p.at[R4[1], "pa_2021_2025"])
    for band, values in [(R4[0], (5184, 13.2, 14.4)), (R4[-1], (684, 25.7, 21.3))]:
        for col, value in zip(["ta_plus_com", "ta_plus_com_years_2021_2025",
                               "ta_plus_com_years_2016_2025"], values, strict=True):
            compare("§4 hypothesis", band, col, value, p.at[band, col], int(isinstance(value, float)))
    for start, expected in zip([1990, 2000, 2010, 2020], [1.9, 3.7, 5.7, 6.9], strict=True):
        key = f"pa_in_{start}s_pct_of_gulf"
        compare("§3 borehole pace", R4[-1], key, expected, s.at[R4[-1], key], 1)
    counts = annual.set_index(["band", "year"])
    gulf = counts.loc[ALL]
    for year, expected in [(2009, 882), (2010, 976), (2011, 1000), (2020, 213)]:
        compare("§3 borehole pace", ALL, f"pa_{year}", expected, gulf.at[year, "pa_wells"])
    recent = gulf.loc[2021:2025, "pa_wells"]
    compare("§3 borehole pace", ALL, "recent PA minimum", 300, recent.min())
    compare("§3 borehole pace", ALL, "recent PA maximum", 626, recent.max())
    compare("§4", R4[1], "pa_2020", 52, counts.at[(R4[1], 2020), "pa_wells"])
    for band, code, value, digits in [(R4[0], "PA", .26, 2), ("Deeper than 200 m", "PA", 9.5, 1),
                                       ("Deeper than 200 m", "TA", 28, 0)]:
        loc = [R4[0]] if band == R4[0] else R4[1:]
        change = s.loc[loc, [f"{code}_change_minus_pct", f"{code}_change_plus_pct"]].abs().max().max()
        compare("Appendix C", band, f"max_abs_{code}_change_pct", value, change, digits)
    for band, start, end, pa, ta in [
        (ALL, 2007, 2015, 739.9, 741.9), (ALL, 2016, 2025, 422.5, 276.3),
        (ALL, 2023, 2025, 502.3, 320.7), (R4[0], 2023, 2025, 459.0, 271.7),
        (R4[1], 2023, 2025, 1.3, 12.0), (R4[-1], 2023, 2025, 24.7, 24.7)]:
        for col, expected in [("eor_pa_wells", pa), ("eor_ta_wells", ta)]:
            avg = counts.loc[band].loc[start:end, col].mean()
            compare("§3 EOR", band, f"{col}_annual_mean_{start}_{end}", expected, avg, 1)
    for window in (3, 5):
        for band in [ALL, R4[2]]:
            delta = counts.loc[band].loc[2007:, "eor_pa_wells"] - counts.loc[band].loc[2007:, "eor_ta_wells"]
            lead = delta.rolling(window).mean().gt(0)
            if band == ALL:
                compare("Appendix C", band, f"years_PA_above_TA_{window}yr_mean_2016_2025",
                        10, lead.loc[2016:2025].sum())
            else:
                compare("§3 EOR window sensitivity", band, f"PA_unbroken_lead_start_{window}yr_mean",
                        2022 if window == 3 else 2017, int(lead.index[~lead].max()) + 1)
    recent_events = audit.keep("EOR dated 2007–2025 for Figure 4 caption", events, events.year.between(2007, 2025))
    both = recent_events.groupby(["well", "year"]).size().eq(2).sum()
    compare("Figure 4", ALL, "well_years_reaching_both_PA_TA_2007_2025", 1458, both)
    compare("Figure 4", ALL, "other_status_reports_2007_2025", 2246, audit.diagnostics["eor_other_2007_2025"])
    for period, expected in [("2005", 45.2), ("2006", 84.4), ("2007", 96.5), ("2010_2025", 98.2)]:
        matched, total = audit.diagnostics["eor_coverage_" + period]
        compare("Appendix B", ALL, f"EOR_confirmed_same_year_PA_pct_{period}", expected, matched * 100 / total, 1)
        if period == "2010_2025":
            compare("Appendix B", ALL, "matched_PA_2010_2025", 8527, matched)
            compare("Appendix B", ALL, "current_PA_2010_2025", 8687, total)
    return pd.DataFrame(rows)


def write_table(output, name, frame):
    frame.to_csv(output / name, index=False, lineterminator="\n")


def figure3_table(wells, pace):
    """Use saved pa_wells for its whole period and the same source wells for earlier bars."""
    from charts import DEPTH_LABELS, NO_DEPTH_LABEL

    pa = wells.loc[wells.status.eq("PA")]
    bands = [*SERIES, NO_DEPTH]
    history = pd.crosstab(pa.status_date.dt.year, assign_bands(pa.depth_m, "series")).reindex(
        index=FIG3_YEARS, columns=bands, fill_value=0)
    recent = pace.pivot(index="year", columns="band", values="pa_wells").sort_index()
    if list(recent.index) != list(YEARS) or set(recent) != {*bands, ALL}:
        raise ValueError("Unexpected years or bands in the pace CSV")
    if not recent[bands].equals(history.loc[YEARS]) or not recent[ALL].equals(recent[bands].sum(axis=1)):
        raise ValueError("Annual pa_wells in the pace CSV disagree with the source well counts")
    plotted = pd.concat([history.loc[:YEARS.start - 1], recent[bands]]).rename_axis("year")
    plotted.columns = [*DEPTH_LABELS, NO_DEPTH_LABEL]
    if not plotted[NO_DEPTH_LABEL].any():
        plotted = plotted.drop(columns=NO_DEPTH_LABEL)
    return plotted


def check_figure3(plotted, wells, events, audit):
    """Independently reconcile CSV stacks, stock wells and the published EOR PA dots."""
    pa = wells.loc[wells.status.eq("PA")]
    stock = pa.groupby(pa.status_date.dt.year).well.agg(set)
    reports = events.loc[events.status.eq("PA")].groupby("year").well.agg(set)
    for year, total in plotted.sum(axis=1).items():
        stock_wells = stock.get(year, set())
        matches = total == len(stock_wells)
        detail = f"band sum {total}, all-depth latest-status PA {len(stock_wells)}"
        if year in FIG4_PA:
            eor_wells = reports.get(year, set())
            stock_only = len(stock_wells - eor_wells)
            eor_only = len(eor_wells - stock_wells)
            delta = total - FIG4_PA[year]
            matches = matches and len(eor_wells) == FIG4_PA[year] and delta == stock_only - eor_only
            detail += (f"; r4 Figure 4 EOR PA {FIG4_PA[year]}, Figure 3 minus Figure 4 {delta:+d}; "
                       f"latest-status PA only {stock_only}, EOR reached PA only {eor_only} for this well/year")
        else:
            detail += "; r4 Figure 4 outside coverage (2007 to 2025)"
        audit.check(f"Figure 3 annual PA conservation {year}", matches, detail)


def headline_index(output):
    """Read the delivered tables back so every value can be located by a unique key."""
    entries = []
    for name, fields in CSV_HEADLINES.items():
        with (output / name).open(encoding="utf-8", newline="") as stream:
            records = list(csv.DictReader(stream))
        for row in records:
            key = {"band": row.pop("band")}
            if "year" in row:
                key["year"] = int(row.pop("year"))
                entries.append({"table": name, "filter": key.copy(), "field": "pa_wells",
                                "value": int(row["pa_wells"])})
                if key["year"] != 2025:
                    continue  # Window metrics repeat on yearly records; index them only once.
            for field_name in fields:
                value = row[field_name]
                entries.append({"table": name, "filter": key.copy(), "field": field_name,
                                "value": json.loads(value) if value else None})
    return {"as_of": str(AS_OF.date()), "headlines": entries}


def validate_saved(output, audit):
    from PIL import Image

    for stem in ("status_share_by_band", "ta_age_by_band", "pa_per_year_by_band"):
        root = ET.parse(output / (stem + ".svg")).getroot()
        tags = {node.tag.rsplit("}", 1)[-1] for node in root.iter()}
        labels = [el.text or "" for el in root.findall(".//{*}text")]
        clean_labels = all(token not in text for text in labels for token in ("–", "—", "to under"))
        audit.check(stem + " SVG", "text" in tags and clean_labels and
                    not tags.intersection({"clipPath", "pattern", "filter", "mask"}),
                    "editable text, label and SVG element checks")
        with Image.open(output / (stem + ".png")) as pic:
            pic.verify()
            audit.check(stem + " PNG", pic.format == "PNG" and min(pic.size) > 0,
                        f"{pic.width} × {pic.height} pixels")
    index = json.loads((output / "numbers.json").read_bytes())
    frames = {name: pd.read_csv(output / name, dtype=str, keep_default_na=False)
              for name in CSV_HEADLINES}
    seen = set()
    for entry in index["headlines"]:
        name, key, col = entry["table"], entry["filter"], entry["field"]
        rows = frames[name]
        for k, v in key.items():
            rows = rows.loc[rows[k].eq(str(v))]
        raw_value = rows[col].item()  # the locator must select exactly one cell
        identity = (name, key["band"], key.get("year"), col)
        if identity in seen or entry["value"] != (json.loads(raw_value) if raw_value else None):
            raise ValueError(f"Duplicate or inconsistent headline: {entry}")
        seen.add(identity)
    expected = {(name, band, 2025 if name == "pa_pace_by_band.csv" else None, col)
                for name, fields in CSV_HEADLINES.items()
                for col in fields for band in [*SERIES, NO_DEPTH, ALL]}
    expected.update(("pa_pace_by_band.csv", band, year, "pa_wells")
                    for band in [*SERIES, NO_DEPTH, ALL] for year in YEARS)
    audit.check("headline table/row/field/value readback", seen == expected,
                f"{len(index['headlines'])} numeric or null entries")
    regression = pd.read_csv(output / "r4-reproduction.csv")
    audit.check("r4 comparisons have a disposition at publication precision",
                ((regression.disposition.eq("match") & regression.difference.eq(0)) |
                 (regression.disposition.ne("match") & regression.explanation.notna())).all(),
                f"{len(regression)} comparisons, {regression.disposition.ne('match').sum()} differences")
    return regression


def build(output, data_dir):
    from eor import eor_counts, eor_diagnostics
    from charts import render_charts

    audit = Audit()
    members = verified_members(data_dir)
    audit.check("all source SHA-256 values verified before record reads", True,
                f"{len(members)} BSEE ZIPs, {len(members)} data members")
    raw = read_table(members[BORE], BORE_COLS)
    wells = select_wells(raw, audit)
    raw_eor = read_table(members[EOR], EOR_COLS)
    events = eor_counts(raw_eor, wells, audit)
    eor_diagnostics(raw_eor, wells, events, audit)
    r4 = summarize(wells, events, "r4", audit)
    comparison = reproduction(r4, audit, events)
    write_table(output, "r4-reproduction.csv", comparison)
    ledger = output / "r4-reproduction.csv"
    check_hash(ledger.name, REPRODUCTION_SHA256, hashlib.sha256(ledger.read_bytes()).hexdigest())
    ta_count = int(r4[0].iloc[-1].TA)
    audit.check("r4 TA stock on 23 Nov 2026", ta_count == 2896, f"computed {ta_count}, published 2896")
    s, t, p = summarize(wells, events, "series", audit)
    for name, frame in [("status_by_band.csv", s), ("ta_by_band.csv", t), ("pa_pace_by_band.csv", p)]:
        write_table(output, name, frame)
    with (output / "numbers.json").open("w", encoding="utf-8", newline="\n") as f:
        json.dump(headline_index(output), f, indent=2, allow_nan=False)
        f.write("\n")
    pace = pd.read_csv(output / "pa_pace_by_band.csv")
    annual = figure3_table(wells, pace)
    chart_csv = "pa_per_year_by_band.csv"
    write_table(output, chart_csv, annual.reset_index())
    plotted = pd.read_csv(output / chart_csv, index_col="year")
    if not annual.equals(plotted):
        raise ValueError("Figure 3 plotted CSV differs from the verified counts")
    check_figure3(plotted, wells, events, audit)
    render_charts(output, s, t, plotted)
    validate_saved(output, audit)
    (output / "checks.txt").write_text("\n".join(audit.lines) + "\n", encoding="utf-8", newline="\n")
    if any(line.startswith("FAIL") for line in audit.lines):
        raise RuntimeError("\n".join(line for line in audit.lines if line.startswith("FAIL")))
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_data = os.environ.get("BSEE_W1_DATA_DIR") or None
    parser.add_argument("--data-dir", type=Path, default=default_data, required=default_data is None,
                        help="Directory containing the pinned ZIPs (default: BSEE_W1_DATA_DIR)")
    parser.add_argument("--output", "--output-dir", type=Path, default=ROOT / "output",
                        help="Destination for the regenerated tables, figures and checks")
    args = parser.parse_args()
    dest = args.output.resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=dest.parent, prefix=".derive-") as scratch:
        os.environ.setdefault("MPLCONFIGDIR", str(Path(scratch) / "mplconfig"))
        stage = Path(scratch) / "output"
        stage.mkdir()
        audit = build(stage, args.data_dir)
        expected = {*CSV_HEADLINES, "r4-reproduction.csv", "checks.txt", "numbers.json",
                    "pa_per_year_by_band.csv",
                    *(f"{name}.{ext}" for name in ("ta_age_by_band", "status_share_by_band", "pa_per_year_by_band")
                      for ext in ("png", "svg"))}
        if {p.name for p in stage.iterdir()} != expected:
            raise RuntimeError("Incomplete output inventory")
        dest.mkdir(parents=True, exist_ok=True)
        for artifact in sorted(stage.iterdir()):
            artifact.replace(dest / artifact.name)
        print(json.dumps(audit.diagnostics, indent=2))
        print(f"{len(audit.lines)} checks passed")


if __name__ == "__main__":
    main()
