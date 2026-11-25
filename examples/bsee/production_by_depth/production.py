"""OGOR-A monthly volumes and well production histories from the public ZIP files."""

import csv
import re
from collections import Counter, defaultdict
from io import TextIOWrapper
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

# Positional schema from worldenergydata's ogor_production_loader. Its materialized
# pickle reader loses the first physical record. Read the headerless ZIP member
# as in lower_tertiary/v30_reproducer.py, also including the current-year ZIP.
OGOR_COLUMNS = [
    "LEASE_NUMBER",
    "COMPLETION_NAME",
    "PRODUCTION_DATE",
    "DAYS_ON_PROD",
    "PRODUCT_CODE",
    "MON_O_PROD_VOL",
    "MON_G_PROD_VOL",
    "MON_WTR_PROD_VOL",
    "API_WELL_NUMBER",
    "WELL_STAT_CD",
    "AREA_CODE_BLOCK_NUM",
    "OPERATOR_NUM",
    "SORT_NAME",
    "BOEM_FIELD",
    "INJECTION_VOLUME",
    "PROD_INTERVAL_CD",
    "FIRST_PROD_DATE",
    "UNIT_AGT_NUMBER",
    "UNIT_ALOC_SUFFIX",
]
DEPTH_BANDS = ["<100 m", "100–<500 m", "500–<1,500 m", "≥1,500 m"]
VOLUMES = ["oil_bbl", "gas_mcf"]
API12 = r"[0-9]{12}"


def ogor_filename(year, current_year):
    return "ogoradelimit.zip" if year == current_year else f"ogora{year}delimit.zip"


def read_ogor(path):
    """Check the delimited layout before assigning the positional field names."""
    with ZipFile(path) as archive:
        member = path.with_suffix(".txt").name
        with archive.open(member) as stream:
            raw = pd.read_csv(
                stream,
                header=None,
                dtype=str,
                encoding="latin-1",
                na_filter=False,
                skip_blank_lines=False,
                index_col=False,
            )
    if len(raw.columns) != len(OGOR_COLUMNS):
        raise ValueError(f"{path.name}: expected {len(OGOR_COLUMNS)} fields; got {len(raw.columns)}")
    raw.columns = OGOR_COLUMNS
    fields = {
        "API_WELL_NUMBER": "api12",
        "PRODUCTION_DATE": "ym",
        "DAYS_ON_PROD": "days",
        "MON_O_PROD_VOL": "oil_bbl",
        "MON_G_PROD_VOL": "gas_mcf",
        "FIRST_PROD_DATE": "reported_first",
    }
    data = raw[list(fields)].rename(columns=fields)
    api12 = data.pop("api12").str.strip()
    data["api10"] = api12.str[:10].where(api12.str.fullmatch(API12))
    data["month"] = pd.to_datetime(data.pop("ym"), format="%Y%m", errors="raise")
    for col in VOLUMES:
        # Signed corrections remain in volumetric sums. A blank/invalid volume
        # cannot be treated as zero or conserved as an integer.
        data[col] = data[col].astype("int64")
    data["days"] = pd.to_numeric(data["days"], errors="coerce")
    first = data["reported_first"].str.strip().replace("", pd.NA)
    data["reported_first"] = pd.to_datetime(first, format="%Y%m%d", errors="raise")
    return data


def collapse_well_months(raw):
    """Sum volumes; identify exact producing-day denominators from day-count bounds."""
    producing_record = (raw["oil_bbl"] > 0) | (raw["gas_mcf"] > 0)
    days = raw["days"]
    calendar_days = raw["month"].dt.days_in_month
    bad_days = producing_record & (~days.between(1, calendar_days) | days.mod(1).ne(0))
    prepared = raw.assign(active_days=days.where(producing_record, 0), bad_days=bad_days)
    frame = prepared.groupby(["api10", "month"], as_index=False, sort=False).agg(
        oil_bbl=("oil_bbl", "sum"),
        gas_mcf=("gas_mcf", "sum"),
        max_days=("active_days", "max"),
        sum_days=("active_days", "sum"),
        bad_days=("bad_days", "any"),
    )
    frame["positive"] = frame.oil_bbl.gt(0) | frame.gas_mcf.gt(0)
    upper = np.minimum(frame.pop("sum_days"), frame["month"].dt.days_in_month)
    lower = frame.pop("max_days")
    frame["rate_status"] = np.select(
        [~frame["positive"], frame.pop("bad_days"), lower.ne(upper)],
        ["no_hydrocarbon_production", "invalid_days", "unresolved_overlap"],
        default="observed",
    )
    frame["oil_rate"] = frame["oil_bbl"].div(lower.where(frame["rate_status"].eq("observed")))
    return frame


def make_panel(by_band, pooled, times, time_name, value_cols):
    grid = pd.MultiIndex.from_product([times, DEPTH_BANDS], names=[time_name, "band"])
    bands = by_band.reindex(grid, fill_value=0)[value_cols].reset_index()
    totals = pooled.reindex(times, fill_value=0)[value_cols].rename_axis(time_name).reset_index()
    totals["band"] = "All"
    return pd.concat([bands, totals], ignore_index=True).sort_values(time_name, kind="stable")


def build_activity_summary(months, check):
    """Monthly headcounts and period medians, with a positive API10-month as one observation."""
    active = months.loc[months["positive"], ["month", "band", "api10", *VOLUMES]]
    times = pd.date_range(months.month.min(), months.month.max(), freq="MS", name="month")
    field = "monthly_producing_wells"
    by_band = active.groupby(["month", "band"])["api10"].nunique().to_frame(field)
    pooled = active.groupby("month")["api10"].nunique().to_frame(field)
    activity = make_panel(by_band, pooled, times, "month", [field])
    period = []
    for band in [*DEPTH_BANDS, "All"]:
        obs = active if band == "All" else active.loc[active.band.eq(band)]
        period.append(
            {
                "band": band,
                "distinct_producing_wells": obs.api10.nunique(),
                "producing_well_months": len(obs),
                "median_well_month_oil_bbl": obs.oil_bbl.median(),
                "median_well_month_gas_mcf": obs.gas_mcf.median(),
            }
        )
    summary = pd.DataFrame(period)
    additive = ["distinct_producing_wells", "producing_well_months"]
    check(
        "Period activity | band counts sum to pooled distinct wells and well-months",
        summary.loc[summary.band.ne("All"), additive].sum().tolist()
        == summary.loc[summary.band.eq("All"), additive].iloc[0].tolist(),
    )
    check(
        "Monthly activity | depth counts sum to pooled distinct API10s in each month",
        activity.loc[activity.band.ne("All")]
        .groupby("month")[field]
        .sum()
        .equals(activity.loc[activity.band.eq("All")].set_index("month")[field]),
    )
    check(
        "Monthly activity | monthly headcounts sum to distinct active well-months in each band",
        activity.groupby("band")[field]
        .sum()
        .sort_index()
        .equals(summary.set_index("band")["producing_well_months"].sort_index()),
    )
    return activity, summary


def check_recent_source(prod_dir, lookup, months, last, check, audit=None):
    """Re-count both months directly with the CSV reader and signed API10 totals."""
    previous = last - pd.DateOffset(months=1)
    targets = {m.strftime("%Y%m"): m for m in (previous, last)}
    covered = lookup["band"].dropna().to_dict()
    bands = ["All", DEPTH_BANDS[-1]]
    monthly = {ym: defaultdict(lambda: [0, 0]) for ym in targets}
    rows, kept = Counter(), Counter()
    drops = {ym: Counter() for ym in targets}
    for year in sorted({previous.year, last.year}):
        path = Path(prod_dir) / ogor_filename(year, last.year)
        wanted = {ym for ym, date in targets.items() if date.year == year}
        with ZipFile(path) as archive, archive.open(path.with_suffix(".txt").name) as stream:
            for row in csv.reader(TextIOWrapper(stream, encoding="latin-1", newline="")):
                ym = row[2]
                if ym not in wanted:
                    continue
                rows[ym] += 1
                api12 = row[8].strip()
                if not re.fullmatch(API12, api12):
                    drops[ym]["invalid API12"] += 1
                    continue
                api = api12[:10]
                if api not in covered:
                    drops[ym]["outside classified Gulf inventory"] += 1
                    continue
                kept[ym] += 1
                tally = monthly[ym][api]
                tally[0] += int(row[5])
                tally[1] += int(row[6])
    notes = []
    producing_counts = {}
    for ym, date in targets.items():
        if audit is not None:
            audit(f"OGOR raw recount / {date:%Y-%m}", rows[ym], kept[ym], dict(drops[ym]))
        sample = months.loc[months.month.eq(date)]
        for band in bands:
            direct = {
                api: volumes
                for api, volumes in monthly[ym].items()
                if band == "All" or covered[api] == band
            }
            producers = {api for api, (oil, gas) in direct.items() if oil > 0 or gas > 0}
            oil = sum(v[0] for v in direct.values())
            gas = sum(v[1] for v in direct.values())
            sub = sample if band == "All" else sample.loc[sample.band.eq(band)]
            detail = f"{len(producers):,} producing wells, {oil:,} bbl, {gas:,} Mcf"
            check(
                f"Raw CSV recount | {date:%Y-%m} {band} unique producers, oil and gas",
                rows[ym] > 0
                and set(sub.loc[sub.positive, "api10"]) == producers
                and int(sub.oil_bbl.sum()) == oil
                and int(sub.gas_mcf.sum()) == gas,
                detail,
            )
            if band == "All":
                producing_counts[ym] = len(producers)
                notes.append(f"{date:%B %Y}: {rows[ym]:,} raw rows; classified Gulf total {detail}.")
    last_ym, prior_ym = last.strftime("%Y%m"), previous.strftime("%Y%m")
    if rows[last_ym] < rows[prior_ym] and producing_counts[last_ym] < producing_counts[prior_ym]:
        notes.append(
            "The final month has fewer source rows and producing wells than the previous month. "
            "This snapshot cannot separate reporting coverage changes from operating changes. "
            "Treat the last month as provisional."
        )
    return notes


def load_production(prod_dir, wells, audit, check):
    """Return well-months, monthly band volumes, yearly well counts and methods notes."""
    lookup = wells.set_index("api10", verify_integrity=True)
    eligible = lookup["band"].isin(DEPTH_BANDS)
    if (lookup["band"].notna() & ~eligible).any():
        raise ValueError("Unrecognized band in borehole lookup")
    inventory = lookup["inventory_status"]
    frames, source_months, raw_year_counts = [], [], []
    in_archive_months, reported = [], []
    exclusions = Counter()
    dropped_volumes = Counter()
    input_volume = Counter()
    source_rows = 0
    retained_rows = 0
    for year in range(2005, 2027):
        filename = ogor_filename(year, 2026)
        data = read_ogor(Path(prod_dir) / filename)
        source_rows += len(data)
        check(f"{filename} year identity", bool(data["month"].dt.year.eq(year).all()) and len(data) > 0)
        in_archive_months.extend(data["month"].unique())
        data["band"] = data["api10"].map(lookup["band"])
        mapped = data["api10"].map(inventory)
        reason = pd.Series("kept", index=data.index)
        unclassified = data["band"].isna()
        reason.loc[unclassified] = mapped[unclassified].fillna("no_borehole_match")
        reason.loc[unclassified & mapped.eq("gulf")] = "gulf_without_resolved_depth"
        reason.loc[data["api10"].isna()] = "invalid_api12"
        kept = data.loc[reason.eq("kept")]
        retained_rows += len(kept)
        dropped = data.loc[~reason.eq("kept")]
        reasons = reason.loc[dropped.index]
        count = reasons.value_counts().to_dict()
        exclusions.update(count)
        audit(f"OGOR depth join / {filename}", len(data), len(kept), count)
        for col in VOLUMES:
            input_volume[col] += int(data[col].sum())
            for label, amount in dropped.groupby(reasons)[col].sum().items():
                dropped_volumes[label, col] += int(amount)

        # Source totals and distinct API10s are computed directly from raw rows
        # before the well-month transform used by the four band series.
        source_months.append(kept.groupby("month")[VOLUMES].sum())
        signed = kept.groupby(["api10", "month"])[VOLUMES].sum()
        producing = signed.gt(0).any(axis=1)
        raw_year_counts.append((year, signed.index.get_level_values("api10")[producing].nunique()))
        reported.append(kept.groupby("api10")["reported_first"].min())
        frames.append(collapse_well_months(kept))

    last = pd.Timestamp(max(in_archive_months))
    times = pd.date_range("2005-01-01", last, freq="MS", name="month")
    check(
        "OGOR source coverage across consecutive calendar months",
        set(in_archive_months) == set(times),
        f"{times.min():%Y-%m} through {last:%Y-%m}; {len(times)} months",
    )
    well_months = pd.concat(frames, ignore_index=True)
    well_months["band"] = well_months["api10"].map(lookup["band"])
    first = pd.concat(reported).groupby(level=0).min()
    well_months["reported_first"] = well_months["api10"].map(first)
    well_months["rate_status"] = well_months["rate_status"].astype("category")
    check(
        "OGOR well-month identity and one depth band per producing well",
        not well_months.duplicated(["api10", "month"]).any()
        and well_months.groupby("api10")["band"].nunique().eq(1).all(),
    )
    monthly_raw = pd.concat(source_months, verify_integrity=True)
    amounts = {("read", "input"): input_volume, ("kept", "retained"): monthly_raw[VOLUMES].sum().to_dict()}
    for reason in exclusions:
        amounts["dropped", reason] = {col: dropped_volumes[reason, col] for col in VOLUMES}
    audit(
        "OGOR archives combined | source depth join",
        source_rows,
        retained_rows,
        dict(exclusions),
        volumes=amounts,
    )
    by_band = well_months.groupby(["month", "band"])[VOLUMES].sum()
    monthly = make_panel(by_band, monthly_raw, times, "month", VOLUMES)
    for col in VOLUMES:
        band_total = monthly.loc[monthly["band"].ne("All")].groupby("month")[col].sum()
        all_months = monthly.loc[monthly["band"].eq("All")].set_index("month")[col]
        check(
            f"Monthly four-band {col} sums to pooled OGOR source volume every month",
            band_total.equals(all_months),
            f"{len(all_months)} months; {int(all_months.sum()):,} retained",
        )
        raw_excluded = sum(volume for (reason, unit), volume in dropped_volumes.items() if unit == col)
        check(
            f"OGOR full archive {col} reconciles to classified and excluded volumes",
            int(all_months.sum()) + raw_excluded == input_volume[col],
            f"{input_volume[col]:,} = {int(all_months.sum()):,} classified + {raw_excluded:,} excluded",
        )
        annual_volume = band_total.groupby(band_total.index.year).sum()
        source_years = monthly_raw[col].groupby(monthly_raw.index.year).sum()
        check(
            f"Yearly {col} volumes and period sum agree with source",
            annual_volume.equals(source_years) and int(annual_volume.sum()) == int(monthly_raw[col].sum()),
            f"{int(annual_volume.sum()):,}",
        )

    active = well_months.loc[well_months["positive"], ["month", "api10", "band"]]
    audit(
        "OGOR well-months / producing activity",
        len(well_months),
        len(active),
        {"no positive net oil or gas": int((~well_months.positive).sum())},
    )
    active = active.assign(year=active["month"].dt.year)
    annual_by_band = active.groupby(["year", "band"])["api10"].nunique().to_frame("producing_wells")
    raw_counts = pd.DataFrame(raw_year_counts, columns=["year", "producing_wells"]).set_index("year")
    annual = make_panel(annual_by_band, raw_counts, range(2005, last.year + 1), "year", ["producing_wells"])
    years = annual.loc[annual["band"].ne("All")].groupby("year")["producing_wells"].sum()
    check(
        "Annual four-band producing wells sum to distinct API10 counts in raw rows every year",
        years.equals(raw_counts["producing_wells"]),
        f"{len(years)} years",
    )
    well_years = len(active.drop_duplicates(["year", "api10"]))
    check(
        "Yearly distinct producing-well counts sum to period well-years",
        int(years.sum()) == well_years == int(raw_counts["producing_wells"].sum()),
        f"{well_years:,} well-years; {active['api10'].nunique():,} distinct producing wells",
    )

    n_read = len(well_months)
    rate_counts = well_months["rate_status"].value_counts()
    valid = int(rate_counts.get("observed", 0))
    audit(
        "OGOR well-months / exact oil rate",
        n_read,
        valid,
        {str(key): int(value) for key, value in rate_counts.items() if key != "observed"},
    )
    notes = [
        (
            f"The 22 headerless OGOR-A files cover {len(times)} consecutive months from January 2005 "
            f"through {last:%B %Y}. Volumes sum every signed MON_O_PROD_VOL (bbl) and MON_G_PROD_VOL "
            "(Mcf, thousand cubic feet). No product-code restriction is used. Lease-level files are "
            "outside the API10 calculation. The 19-column order follows worldenergydata’s "
            "ogor_production_loader.py and the ZIP parser in lower_tertiary/v30_reproducer.py. "
            "Units and field meanings follow docs/modules/bsee/PRODUCTION_DATA_RETRIEVAL_GUIDE.md."
        ),
        (
            "A producing well has at least one API10-month with positive net oil or gas in the year. "
            f"The period contains {well_years:,} producing well-years and {active['api10'].nunique():,} distinct "
            "producing wells. Annual counts are additive in well-years."
        ),
        (
            "At API10, oil volume is divided by the number of distinct calendar days on which at least "
            "one hydrocarbon-producing record was online. Given only completion day counts, the union "
            "lies between the largest count and the lesser of their sum and the days in the month. "
            f"The rate is used when the bounds coincide and all producing records have valid days. "
            f"Overlap leaves {int(rate_counts.get('unresolved_overlap', 0)):,} positive well-months unresolved "
            f"and {int(rate_counts.get('invalid_days', 0)):,} have invalid day counts. Nonproducing "
            "months have no hydrocarbon-producing-day rate. A producing gas-only month has zero oil "
            "rate when its denominator is known. These restrictions affect rates only."
        ),
        (
            "The first positive OGOR-A month is measured within the available series. The earliest "
            "nonblank FIRST_PROD_DATE across all records of a well, including zero-volume records, "
            "is retained as evidence of earlier activity. The date is never substituted for the first "
            "positive monthly volume."
        ),
    ]
    for reason, count in sorted(exclusions.items()):
        notes.append(
            f"OGOR depth join excluded {count:,} rows for {reason.replace('_', ' ')} "
            f"({dropped_volumes[reason, 'oil_bbl']:,} bbl and "
            f"{dropped_volumes[reason, 'gas_mcf']:,} Mcf)."
        )
    notes.extend(check_recent_source(prod_dir, lookup, well_months, last, check, audit))
    return well_months, monthly, annual, notes
