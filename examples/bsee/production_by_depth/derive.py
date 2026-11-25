# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas==3.1.1", "numpy==2.4.6", "matplotlib==3.11.2", "pillow==13.0.0"]
# [tool.uv]
# exclude-newer = "2026-11-25T05:06:21Z"
# ///
"""Rebuild the BSEE Gulf production article evidence. Run with uv run derive.py."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
PUBLIC_PINS_SHA256 = "6d8124715cc4304425701f34e5cfb0c6921e45bb0008f3277411be1f326b5a46"
ORIGINAL_MANIFESTS = {
    "2026-11-23-series-basis": "9f1de6e28bd96b945b9939b09a458459a1716e59cbed467214fd631084007c1d",
    "2026-11-25-production-lease": "56d6ea4036d136c7a6cdd75051dc024e9767fcb266410d7ff5b7aecd831893d3",
}
BANDS = ["<100 m", "100–<500 m", "500–<1,500 m", "≥1,500 m"]
TYPES = ["Subsea", "No subsea flag (NO)", "Unknown"]
WINDOW = pd.Timestamp("2005-01-01")


def self_test():
    """Hand-worked boundary cases, independent of the public file totals."""
    dt = pd.to_datetime
    sm = pd.DataFrame(
        {
            "api10": ["a", "a", "a", "a", "b", "b", "c", "c", "d", "d"],
            "band": BANDS[0],
            "month": dt(
                [
                    "2005-01-01",
                    "2005-02-01",
                    "2005-04-01",
                    "2005-05-01",
                    "2005-01-01",
                    "2005-03-01",
                    "2005-01-01",
                    "2005-02-01",
                    "2005-01-01",
                    "2005-03-01",
                ]
            ),
            "oil_rate": [10, 20, 40, 0, np.nan, 10, 5, 6, 0, 0],
            "oil_bbl": [100, 200, 400, 0, 40, 30, 50, 60, 0, 0],
            "positive": True,
            "reported_first": dt(["2005-01-01"] * 6 + ["2001-01-01"] * 2 + ["2005-01-01"] * 2),
        }
    )
    src = pd.DataFrame(
        {
            "api10": list("abcd"),
            "band": BANDS[0],
            "first_spud": dt(["2004-12-01"] * 4),
            "completion_date": dt(["2005-01-31", "2005-02-01", "2005-01-01", None]),
            "completion_type": "Subsea",
            "war_date": dt(["2005-04-05", None, None, None]),
            "permit_date": dt([None] * 4),
        }
    )
    discard = lambda *args: None

    def verify(name, condition, detail=""):
        if not condition:
            raise AssertionError(name + " " + detail)

    starts = first_months(sm, src, discard, verify)
    verify("supported starts", set(starts.loc[starts.start_supported, "api10"]) == {"a", "b", "d"})
    lag = completion_lags(src, starts, discard, verify)
    pooled_lags = lag.loc[lag.band.eq("All")].set_index("population")
    verify("signed lag median", pooled_lags.loc["signed", "median_months"] == -0.5)
    verify("ordered lag count", pooled_lags.loc["ordered", "wells"] == 1)
    decline = decline_curve(sm, starts, discard, verify)
    curve = decline.query("band == 'All' and completion_type == 'All'").set_index("age_month")
    rates = curve.median_relative_rate
    verify("relative rates at ages one and four", rates.loc[1] == 0.5 and rates.loc[4] == 2)
    verify("missing and zero rates", curve.loc[3, "wells"] == 0 and rates.loc[5] == 0)
    events = intervention_curve(starts, pd.Timestamp("2006-01-01"), discard, verify)
    ev = events.query("band == 'All' and measure == 'Post-completion WAR'").set_index("age_year")
    verify("events at years zero and one", ev.event_wells.loc[0] == 0 and ev.event_wells.loc[1] == 1)
    first_year = ev.loc[1]
    verify(
        "eligible and completion-observed wells",
        first_year.eligible_wells == 3 and first_year.completion_observed_wells == 2,
    )


def month_number(dates):
    return dates.dt.year * 12 + dates.dt.month - 1


def count_filter(stage, frame, reasons, audit):
    """Assign each removed item its first applicable reason, in the listed order."""
    keep = pd.Series(True, index=frame.index)
    drops = {}
    for reason, mask in reasons.items():
        remove = keep & mask.fillna(False)
        drops[reason] = int(remove.sum())
        keep &= ~remove
    audit(stage, len(frame), int(keep.sum()), drops)
    return frame.loc[keep].copy()


def first_months(months, inventory, audit, check):
    positive = months.loc[months.positive]
    first = positive.groupby("api10", as_index=False).agg(
        first_month=("month", "min"), reported_first=("reported_first", "min")
    )
    starts = first.merge(inventory, on="api10", validate="one_to_one")
    check(
        "Each producing API10 has exactly one inventory record and one assigned band",
        len(starts) == len(first) and starts.band.isin(BANDS).all(),
    )
    # An earlier recorded first-production date is affirmative evidence of left censoring.
    # In its absence, a post-window spud or recorded start can establish window coverage.
    prewindow = starts.reported_first.lt(WINDOW)
    observed = month_number(starts.first_month)
    spud_in_time = month_number(starts.first_spud).le(observed)
    report_in_time = month_number(starts.reported_first).le(observed)
    evidenced = (starts.first_spud.ge(WINDOW) & spud_in_time) | (
        starts.reported_first.ge(WINDOW) & report_in_time
    )
    starts["start_supported"] = ~prewindow & evidenced
    starts["start_reason"] = np.select(
        [prewindow, ~evidenced],
        ["reported first production predates January 2005", "no timely in-window spud or reported start"],
        default="observed window covers start",
    )
    count_filter(
        "First positive month | API10 start evidence",
        starts,
        {
            "reported first production predates January 2005": prewindow,
            "no timely in-window spud or reported start": ~evidenced,
        },
        audit,
    )
    starts["type_at_start"] = starts.completion_type.where(
        starts.completion_date.notna()
        & (month_number(starts.completion_date) <= month_number(starts.first_month)),
        "Unknown",
    ).fillna("Unknown")
    check(
        "Completion type at start has one disjoint value per producing well",
        starts.type_at_start.isin(TYPES).all(),
    )
    return starts


def completion_lags(inventory, starts, audit, check):
    cohort = inventory.loc[inventory.completion_date.dt.year.between(2005, 2025)].copy()
    cohort = cohort.merge(
        starts[["api10", "first_month", "start_supported", "start_reason"]],
        on="api10",
        how="left",
        validate="one_to_one",
    )
    pair = count_filter(
        "Completion lag | first C dated 2005–2025, API10",
        cohort,
        {
            "no assigned Gulf depth band": ~cohort.band.isin(BANDS),
            "no positive joined OGOR month": cohort.first_month.isna(),
            "documented pre-window production": cohort.start_reason.eq(
                "reported first production predates January 2005"
            ),
            "start coverage unestablished": ~cohort.start_supported.eq(True),
        },
        audit,
    )
    pair["lag"] = month_number(pair.first_month) - month_number(pair.completion_date)
    ordered = count_filter(
        "Completion lag | chronological pair, API10",
        pair,
        {"first production month before first C month": pair.lag.lt(0)},
        audit,
    )
    rows = []
    for population, data in [("signed", pair), ("ordered", ordered)]:
        for band in [*BANDS, "All"]:
            values = data.lag if band == "All" else data.loc[data.band.eq(band), "lag"]
            p25, med, p75 = values.quantile([0.25, 0.5, 0.75])
            rows.append(
                {
                    "band": band,
                    "population": population,
                    "wells": len(values),
                    "p25_months": p25,
                    "median_months": med,
                    "p75_months": p75,
                    "pre_completion_wells": int(values.lt(0).sum()),
                    "same_month_wells": int(values.eq(0).sum()),
                }
            )
    out = pd.DataFrame(rows)
    check_parts(
        "Completion lag | depth counts for both populations",
        out,
        ["population"],
        ["wells", "pre_completion_wells", "same_month_wells"],
        check,
    )
    check(
        "Completion lag | ordered plus negative pairs equals signed pairs",
        len(pair) == len(ordered) + int(pair.lag.lt(0).sum()),
    )
    return out


def check_parts(name, frame, keys, columns, check, field="band"):
    parts = frame.loc[~frame[field].eq("All")].groupby(keys, dropna=False)[columns].sum().sort_index()
    all_rows = frame.loc[frame[field].eq("All")].set_index(keys)[columns].sort_index()
    check(name, parts.equals(all_rows), f"{len(all_rows)} pooled groups; {', '.join(columns)}")


def decline_curve(months, starts, audit, check):
    cohort = starts.loc[starts.start_supported & starts.first_month.dt.year.between(2005, 2020)]
    series = months.merge(
        cohort[["api10", "first_month", "type_at_start"]], on="api10", validate="many_to_one", how="inner"
    )
    series["age_month"] = 1 + month_number(series.month) - month_number(series.first_month)
    series = series.loc[series.age_month.between(1, 60)].copy()
    early = series.loc[series.age_month.le(3)]
    # An unresolved positive-oil rate could exceed the available maximum.
    indeterminate = early.loc[early.oil_bbl.gt(0) & early.oil_rate.isna(), "api10"].unique()
    candidates = cohort.set_index("api10").join(early.groupby("api10").oil_rate.max().rename("baseline"))
    valid = count_filter(
        "Decline | supported first production 2005–2020, API10",
        candidates,
        {
            "positive oil but producing-day rate unresolved in first three months": candidates.index.to_series().isin(
                indeterminate
            ),
            "no positive measurable oil rate in first three calendar months": ~candidates.baseline.gt(0),
        },
        audit,
    )
    panel = series.loc[series.api10.isin(valid.index)].copy()
    panel = count_filter(
        "Decline | observed baseline-eligible well-month records, ages 1–60",
        panel,
        {
            "no usable producing-day rate": panel.oil_rate.isna(),
            "negative net oil rate": panel.oil_rate.lt(0),
        },
        audit,
    )
    panel["relative_rate"] = panel.oil_rate / panel.api10.map(valid.baseline)
    check(
        "Decline | one value per API10 and calendar age; finite nonnegative rates",
        not panel.duplicated(["api10", "age_month"]).any()
        and np.isfinite(panel.relative_rate).all()
        and panel.relative_rate.ge(0).all(),
    )
    peaks = panel.loc[panel.age_month.le(3)].groupby("api10").relative_rate.max()
    check(
        "Decline | each retained well reaches 1 in its first three calendar months",
        len(peaks) == len(valid) and peaks.eq(1).all(),
        f"{len(peaks):,} wells",
    )
    rows = []
    for band in [*BANDS, "All"]:
        subset = panel if band == "All" else panel.loc[panel.band.eq(band)]
        base = valid if band == "All" else valid.loc[valid.band.eq(band)]
        for typ in [*TYPES, "All"]:
            data = subset if typ == "All" else subset.loc[subset.type_at_start.eq(typ)]
            n = len(base) if typ == "All" else int(base.type_at_start.eq(typ).sum())
            summary = data.groupby("age_month").relative_rate.agg(["median", "count"]).reindex(range(1, 61))
            for age, median, count in summary.itertuples():
                rows.append(
                    {
                        "band": band,
                        "completion_type": typ,
                        "age_month": age,
                        "baseline_wells": n,
                        "wells": int(count) if pd.notna(count) else 0,
                        "median_relative_rate": median,
                    }
                )
    out = pd.DataFrame(rows)
    check_parts(
        "Decline | depth counts at every age and completion type",
        out,
        ["completion_type", "age_month"],
        ["baseline_wells", "wells"],
        check,
    )
    check_parts(
        "Decline | completion-type counts at every age and depth",
        out,
        ["band", "age_month"],
        ["baseline_wells", "wells"],
        check,
        field="completion_type",
    )
    check(
        "Decline | monthly contributors within each baseline cohort; empty groups have no median",
        out.wells.le(out.baseline_wells).all() and out.wells.eq(0).equals(out.median_relative_rate.isna()),
    )
    return out


def intervention_curve(starts, cutoff, audit, check):
    cohort = starts.loc[starts.start_supported].copy()
    age_cap = cutoff.year * 12 + cutoff.month - 1 - month_number(cohort.first_month)
    opportunity = int(age_cap.max() // 12) if len(cohort) else 0
    completed = month_number(cohort.completion_date) - month_number(cohort.first_month)
    rows = []
    for col, measure in [("war_date", "Post-completion WAR"), ("permit_date", "Intervention approval")]:
        check(
            f"{measure} | every qualifying date is strictly after earliest completion",
            (cohort[col].isna() | cohort[col].gt(cohort.completion_date)).all(),
        )
        event = month_number(cohort[col]) - month_number(cohort.first_month)
        for age in range(opportunity + 1):
            elapsed = age * 12
            risk = age_cap.ge(elapsed)
            for band in [*BANDS, "All"]:
                group = risk if band == "All" else risk & cohort.band.eq(band)
                eligible = int(group.sum())
                recorded = int((group & completed.le(elapsed)).sum())
                count = int((group & event.le(elapsed)).sum())
                prior = int((group & event.lt(0)).sum())
                rows.append(
                    {
                        "band": band,
                        "measure": measure,
                        "age_year": age,
                        "eligible_wells": eligible,
                        "completion_observed_wells": recorded,
                        "event_wells": count,
                        "pre_origin_event_wells": prior,
                        "share": count / eligible if eligible else np.nan,
                        "share_among_completion_observed": count / recorded if recorded else np.nan,
                    }
                )
    out = pd.DataFrame(rows)
    check_parts(
        "Interventions | eligible, completion-observed and event counts at every age",
        out,
        ["measure", "age_year"],
        ["eligible_wells", "completion_observed_wells", "event_wells", "pre_origin_event_wells"],
        check,
    )
    check(
        "Interventions | events within observed completions within eligible cohort; empty denominators blank",
        (out.pre_origin_event_wells <= out.event_wells).all()
        and (out.event_wells <= out.completion_observed_wells).all()
        and (out.completion_observed_wells <= out.eligible_wells).all()
        and out.share.isna().equals(out.eligible_wells.eq(0)),
    )
    check(
        "Interventions | horizon-eligible denominators never grow with age",
        out.groupby(["measure", "band"]).eligible_wells.diff().dropna().le(0).all(),
    )
    return out


class Evidence:
    def __init__(self):
        self.records = []
        self.results = []
        self.stages = set()

    def check(self, name, condition, detail=""):
        status = "PASS" if condition else "FAIL"
        self.results.append(f"{status}  {name}" + (f" — {detail}" if detail else ""))
        if not condition:
            raise ValueError(self.results[-1])

    def audit(self, stage, read, kept, drops, volumes=None):
        if stage in self.stages:
            raise ValueError(f"Duplicate audit stage: {stage}")
        self.stages.add(stage)
        self.check(
            f"Record conservation | {stage}",
            min([read, kept, *drops.values()]) >= 0 and read == kept + sum(drops.values()),
            f"{read:,} read = {kept:,} kept + {sum(drops.values()):,} dropped",
        )
        for disposition, reason, rows in [
            ("read", "input", read),
            ("kept", "retained", kept),
            *(("dropped", k, v) for k, v in drops.items()),
        ]:
            rec = {"stage": stage, "disposition": disposition, "reason": reason, "rows": int(rows)}
            if volumes is not None:
                rec.update(volumes[disposition, reason])
            self.records.append(rec)


def hash_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_digest(name, expected, actual):
    if actual != expected:
        raise ValueError(f"{name}: SHA-256 mismatch: expected {expected}, got {actual}")


def verify_inputs(data_dir, check):
    path = ROOT / "source_pins.json"
    raw = path.read_bytes()
    require_digest(path.name, PUBLIC_PINS_SHA256, hashlib.sha256(raw).hexdigest())
    pins = json.loads(raw)
    # The public projection binds each original manifest's verified digest to
    # its complete archive inventory. The audit uses the original snapshot IDs.
    for snapshot, digest in ORIGINAL_MANIFESTS.items():
        archives = [entry for entry in pins["sources"] if entry["snapshot"] == snapshot]
        check(f"Manifest SHA-256 | {snapshot}", pins["manifest_sha256"][snapshot] == digest, digest)
        for entry in archives:
            archive = data_dir / entry["name"]
            require_digest(archive.name, entry["sha256"], hash_file(archive))
        check(f"Archive digests match every manifest entry | {snapshot}", True, f"{len(archives)} ZIPs")


def build_tables(data_dir, ev):
    from production import build_activity_summary, load_production
    from well_sources import load_wells

    inventory, well_notes = load_wells(data_dir, ev.audit, ev.check)
    months, monthly, annual, ogor_notes = load_production(data_dir, inventory, ev.audit, ev.check)
    activity, period = build_activity_summary(months, ev.check)
    monthly = monthly.merge(activity, on=["month", "band"], validate="one_to_one")
    starts = first_months(months, inventory, ev.audit, ev.check)
    last = monthly.month.max()
    lag = completion_lags(inventory, starts, ev.audit, ev.check)
    decline = decline_curve(months, starts, ev.audit, ev.check)
    intervention = intervention_curve(starts, last, ev.audit, ev.check)
    period = article_summary(period, inventory, starts, months, last, ev.check)
    # Annual volumes are included beside annual headcounts for direct citation.
    sums = (
        monthly.assign(year=monthly.month.dt.year)
        .groupby(["year", "band"], as_index=False)[["oil_bbl", "gas_mcf"]]
        .sum()
    )
    annual = annual.merge(sums, on=["year", "band"], validate="one_to_one")
    annual["months_reported"] = annual.year.map(monthly.groupby(monthly.month.dt.year).month.nunique())
    check_parts(
        "Published annual table | yearly well counts, oil and gas conserve across bands",
        annual,
        ["year"],
        ["producing_wells", "oil_bbl", "gas_mcf"],
        ev.check,
    )
    for band in [*BANDS, "All"]:
        a = annual.loc[annual.band.eq(band)]
        m = months if band == "All" else months.loc[months.band.eq(band)]
        well_years = (
            m.loc[m.positive].assign(year=lambda d: d.month.dt.year).drop_duplicates(["api10", "year"])
        )
        ev.check(
            f"Published years sum to whole-period source totals | {band}",
            a.oil_bbl.sum() == m.oil_bbl.sum()
            and a.gas_mcf.sum() == m.gas_mcf.sum()
            and a.producing_wells.sum() == len(well_years),
            f"{a.oil_bbl.sum():,} bbl, {a.gas_mcf.sum():,} Mcf, {len(well_years):,} well-years",
        )
    reported = starts.reported_first
    obs = starts.loc[starts.start_supported]
    mismatch = (
        month_number(obs.reported_first).ne(month_number(obs.first_month)) & obs.reported_first.notna()
    )
    notes = [
        (
            f"Of {len(starts):,} producing Gulf API10s with assigned depth, {len(obs):,} have evidence that the production window covers their start. "
            f"{reported.lt(WINDOW).sum():,} have a reported FIRST_PROD_DATE before 2005. "
            f"{(~starts.start_supported & ~reported.lt(WINDOW)).sum():,} have no in-window start evidence. "
            f"Among retained starts, {mismatch.sum():,} have a reported first-production month different from the first positive OGOR month. "
            "The measured first positive month controls the age calculation."
        ),
        (
            f"The decline split uses the flag on the earliest C record if its month is no later than first production. "
            f"Of the {len(obs):,} supported starts, {obs.completion_date.isna().sum():,} have no dated C report and "
            f"{month_number(obs.completion_date).gt(month_number(obs.first_month)).sum():,} have their first C in a later month. "
            "Those starts carry unknown completion type at production. Within-month ordering is unresolved."
        ),
    ]
    monthly = monthly.copy()
    monthly["year"] = monthly.month.dt.year
    monthly["month"] = monthly.month.dt.strftime("%Y-%m")
    tables = {
        "monthly_production": monthly,
        "annual_wells": annual,
        "completion_lag": lag,
        "article_summary": period,
        "decline": decline,
        "interventions": intervention,
        "record_counts": pd.DataFrame(ev.records),
    }
    return tables, [*ogor_notes, *notes, *well_notes]


def article_summary(period, inventory, starts, months, last, check):
    """Companion table for article text. Reach and elapsed time have different denominators."""
    cohort = inventory.loc[
        inventory.band.isin(BANDS) & inventory.completion_date.dt.year.between(2005, 2025)
    ].copy()
    latest = months.loc[months.positive].groupby("api10").month.max()
    cohort["ever_positive"] = cohort.api10.isin(latest.index)
    cohort["produced_since_c_month"] = month_number(cohort.api10.map(latest)).ge(
        month_number(cohort.completion_date)
    )
    supported = starts.loc[starts.start_supported].copy()
    summary = []
    additions = [
        "cohort_completions",
        "ever_produced_wells",
        "produced_in_or_after_c_month_wells",
        "supported_starts",
    ]
    for band in [*BANDS, "All"]:
        c = cohort if band == "All" else cohort[cohort.band.eq(band)]
        s = supported if band == "All" else supported[supported.band.eq(band)]
        rec = {
            "band": band,
            "cohort_completions": len(c),
            "ever_produced_wells": int(c.ever_positive.sum()),
            "produced_in_or_after_c_month_wells": int(c.produced_since_c_month.sum()),
            "supported_starts": len(s),
            "share_produced_in_or_after_c_month": c.produced_since_c_month.mean(),
        }
        for source, col in [("war", "war_date"), ("permit", "permit_date")]:
            event = s.loc[s[col].le(last + pd.offsets.MonthEnd(0))]
            rec[f"{source}_by_cutoff_wells"] = len(event)
            rec[f"{source}_by_cutoff_share"] = len(event) / len(s) if len(s) else np.nan
            rec[f"{source}_signed_event_age_median_months"] = (
                month_number(event[col]) - month_number(event.first_month)
            ).median()
        summary.append(rec)
    result = period.merge(pd.DataFrame(summary), on="band", validate="one_to_one")
    cols = additions + [
        "war_by_cutoff_wells",
        "permit_by_cutoff_wells",
        "distinct_producing_wells",
        "producing_well_months",
    ]
    check(
        "Companion article table | band counts sum to pooled source cohorts",
        result.loc[result.band.ne("All"), cols]
        .sum()
        .eq(result.loc[result.band.eq("All"), cols].iloc[0])
        .all(),
    )
    return result


def headline_spec(tables):
    """Declare citation filters in terms of table rows, including any aggregation."""
    specs = {}

    def add(key, table, filters, fields, operation="row"):
        specs[key] = {"table": f"{table}.csv", "filter": filters, "fields": fields, "operation": operation}

    last = tables["monthly_production"].month.max()
    for b, band in enumerate([*BANDS, "All"]):
        slug = ["under100", "100_500", "500_1500", "1500plus", "all"][b]
        for year in [2005, 2025, 2026]:
            add(
                f"{slug}/year/{year}",
                "annual_wells",
                {"year": year, "band": band},
                ["producing_wells", "oil_bbl", "gas_mcf", "months_reported"],
            )
        add(
            f"{slug}/period",
            "annual_wells",
            {"band": band},
            ["oil_bbl", "gas_mcf", "producing_wells"],
            "sum",
        )
        add(
            f"{slug}/period_wells",
            "article_summary",
            {"band": band},
            [c for c in tables["article_summary"] if c != "band"],
        )
        for date in ["2005-12", "2025-12", "2026-08", last]:
            add(
                f"{slug}/month/{date}",
                "monthly_production",
                {"month": date, "band": band},
                ["oil_bbl", "gas_mcf", "monthly_producing_wells"],
            )
        for year in [2005, 2025, 2026]:
            add(
                f"{slug}/monthly_mean/{year}",
                "monthly_production",
                {"band": band, "year": year},
                ["oil_bbl", "gas_mcf", "monthly_producing_wells"],
                "mean",
            )
        for population in ["ordered", "signed"]:
            add(
                f"{slug}/lag/{population}",
                "completion_lag",
                {"band": band, "population": population},
                [
                    "wells",
                    "p25_months",
                    "median_months",
                    "p75_months",
                    "pre_completion_wells",
                    "same_month_wells",
                ],
            )
        for typ in ["All", *TYPES]:
            for age in [1, 12, 60]:
                add(
                    f"{slug}/decline/{typ}/{age}",
                    "decline",
                    {"band": band, "completion_type": typ, "age_month": age},
                    ["baseline_wells", "wells", "median_relative_rate"],
                )
        for measure in ["Post-completion WAR", "Intervention approval"]:
            for age in [0, 1, 5, 10, 20]:
                add(
                    f"{slug}/{measure}/{age}",
                    "interventions",
                    {"band": band, "measure": measure, "age_year": age},
                    [
                        "eligible_wells",
                        "event_wells",
                        "share",
                        "completion_observed_wells",
                        "pre_origin_event_wells",
                    ],
                )
    for year in [2005, 2025, 2026]:
        for field in ["oil_bbl", "gas_mcf"]:
            key = f"deepest_share/{year}/{field}"
            specs[key] = {
                "table": "annual_wells.csv",
                "filter": {"year": year, "band": BANDS[-1]},
                "fields": [field],
                "operation": "ratio",
                "denominator_filter": {"year": year, "band": "All"},
            }
    stage = tables["record_counts"]
    for r in stage[~stage.stage.str.startswith("OGOR depth join") & stage.rows.gt(0)].itertuples():
        add(
            f"audit/{r.stage}/{r.disposition}/{r.reason}",
            "record_counts",
            {"stage": r.stage, "disposition": r.disposition, "reason": r.reason},
            ["rows", "oil_bbl", "gas_mcf"] if pd.notna(r.oil_bbl) else ["rows"],
        )
    return specs


def filtered(table, filters):
    mask = pd.Series(True, index=table.index)
    for key, value in filters.items():
        mask &= table[key].eq(value)
    return table.loc[mask]


def values_for(spec, tables):
    table = tables[Path(spec["table"]).stem]
    rows = filtered(table, spec["filter"])
    fields = spec["fields"]
    if spec["operation"] in ["sum", "mean"] and len(rows):
        values = rows[fields].agg(spec["operation"])
    elif len(rows) == 1:
        values = rows[fields].iloc[0]
        if spec["operation"] == "ratio":
            denominator = filtered(table, spec["denominator_filter"])
            if len(denominator) != 1:
                raise ValueError(f"Ambiguous denominator: {spec}")
            values = values / denominator[fields].iloc[0]
    else:
        raise ValueError(f"Missing or ambiguous citation: {spec}")
    # Converting the CSV cell directly preserves integers in rows mixing counts and ratios.
    result = {}
    for field in fields:
        v = values[field]
        if pd.isna(v):
            result[field] = None
        elif spec["operation"] not in ["ratio", "mean"] and pd.api.types.is_integer_dtype(table[field]):
            result[field] = int(v)
        else:
            result[field] = float(v)
    return result


def publish_numbers(tables, folder, check):
    specs = headline_spec(tables)
    for spec in specs.values():
        spec["values"] = values_for(spec, tables)
    payload = {
        "coverage_through": tables["monthly_production"].month.max(),
        "coverage_source": {
            "table": "monthly_production.csv",
            "filter": {"band": "All"},
            "operation": "max(month)",
        },
        "units": {
            "oil_bbl": "barrels",
            "gas_mcf": "thousand cubic feet",
            "lag": "calendar months",
            "median_relative_rate": "fraction of baseline",
            "share": "fraction of horizon-eligible wells",
            "sum(producing_wells)": "well-years",
            "ratio": "fraction",
        },
        "headlines": specs,
    }
    path = folder / "numbers.json"
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8", newline="\n",
    )
    reread = json.loads(path.read_text(encoding="utf-8"))
    check(
        "Headline values reproduce from their published CSV filters and operations",
        all(x["values"] == values_for(x, tables) for x in reread["headlines"].values()),
        f"{len(specs)} citations",
    )


def validate_records(frame, ev):
    for stage, data in frame.groupby("stage"):
        sums = data.groupby("disposition").rows.sum()
        if sums["read"] != sums["kept"] + sums.get("dropped", 0):
            ev.check(f"Published record count mismatch | {stage}", False)
    ev.check(
        "Published record ledger | read equals kept plus reason-coded drops for every stage",
        len(frame.stage.unique()) == len(ev.stages),
        f"{len(ev.stages)} stages",
    )
    total = frame.loc[frame.stage.eq("OGOR archives combined | source depth join")]
    by_file = frame[frame.stage.str.startswith("OGOR depth join / ")]
    ev.check(
        "Published OGOR row ledger | archive sum matches combined dispositions and reasons",
        by_file.groupby(["disposition", "reason"])
        .rows.sum()
        .sort_index()
        .equals(total.set_index(["disposition", "reason"]).rows.sort_index()),
    )
    for col in ["oil_bbl", "gas_mcf"]:
        ev.check(
            f"Published OGOR volume ledger | source equals retained plus rejected {col}",
            total.loc[total.disposition.eq("read"), col].sum()
            == total.loc[total.disposition.ne("read"), col].sum(),
        )


def verify_reference_code(ev):
    from production import OGOR_COLUMNS
    from well_sources import ARTICLE_CODE, REPO_ROOT

    for rel, pin in [
        (ARTICLE_CODE, "2139aede8544f5f41a2b2ef019efbddef454b56131fe00abfc48e49d236f23f5"),
        (
            "packages/worldenergydata-bsee/src/worldenergydata/bsee/data/utils/api_well_normalizer.py",
            "525cb5e58db30c59d72466685164ab70b330e64ffb05ea03a85d7305c316da08",
        ),
    ]:
        require_digest(Path(rel).name, pin, hash_file(REPO_ROOT / rel))
        ev.check(f"Executable reference matches series basis | {Path(rel).name}", True)
    layout = (
        REPO_ROOT
        / "packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/bin/ogor_production_loader.py"
    )
    declared = [
        ast.literal_eval(n.value)
        for n in ast.parse(layout.read_text(encoding="utf-8")).body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "OGOR_COLUMN_NAMES" for t in n.targets)
    ]
    ev.check(
        "Headerless OGOR columns match worldenergydata's declared positional layout",
        declared == [OGOR_COLUMNS],
    )


def publish(tables, destination, ev):
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination, prefix=".article-build-") as scratch:
        stage = Path(scratch)
        os.environ["MPLCONFIGDIR"] = str(stage / "font-cache")
        from PIL import Image

        from figures import render_charts

        output = stage / "output"
        output.mkdir()
        saved = {}
        for name, df in tables.items():
            path = output / f"{name}.csv"
            df.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
            reread = pd.read_csv(path, keep_default_na=False, na_values=[""])
            pd.testing.assert_frame_equal(
                df.reset_index(drop=True), reread, check_dtype=False, check_exact=True
            )
            saved[name] = reread
        ev.check(
            "Published CSV readback | all rows and cells match calculations",
            True,
            ", ".join(f"{k} {len(v):,}" for k, v in saved.items()),
        )
        validate_records(saved["record_counts"], ev)
        publish_numbers(saved, output, ev.check)
        files = render_charts(output, output)
        for path in files:
            if path.suffix == ".png":
                with Image.open(path) as im:
                    im.load()
                    ev.check(
                        f"PNG decoded | {path.stem}",
                        im.format == "PNG" and min(im.size) >= 600,
                        f"{im.width} × {im.height} px",
                    )
        expected = {"monthly_production", "annual_wells", "completion_lag", "decline", "interventions"}
        ev.check(
            "Five matched figure pairs | validated SVG, no pattern, clip-path, filter or mask",
            {p.name for p in files} == {n + suffix for n in expected for suffix in [".svg", ".png"]},
        )
        (output / "checks.txt").write_text("\n".join(ev.results) + "\n", encoding="utf-8", newline="\n")
        for path in output.iterdir():
            path.replace(destination / path.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir", type=Path, default=os.environ.get("BSEE_PROD_DATA_DIR"),
        help="Directory containing the pinned BSEE ZIPs (default: BSEE_PROD_DATA_DIR)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "output",
        help="Directory for the tables, check record and figures (default: output beside this script)",
    )
    args = parser.parse_args()
    if args.data_dir is None:
        parser.error("supply --data-dir or set BSEE_PROD_DATA_DIR")

    sys.dont_write_bytecode = True
    ev = Evidence()
    self_test()
    ev.check("Hand-worked startup, decline and intervention boundary fixtures", True)
    verify_inputs(args.data_dir, ev.check)
    verify_reference_code(ev)
    tables, notes = build_tables(args.data_dir, ev)
    publish(tables, args.output_dir, ev)
    print("\n\n".join(notes))
    print(f"{len(ev.results)} checks passed. See {args.output_dir / 'checks.txt'}.")


if __name__ == "__main__":
    main()
