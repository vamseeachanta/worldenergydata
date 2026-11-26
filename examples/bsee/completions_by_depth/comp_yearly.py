"""Build the COMP article's annual table from its verified count outputs.

The original count run supplies complete year by depth grids. Its separate
permit-kind count also retains unmatched water depths for the all-depth view.
"""

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[2] / "packages/worldenergydata-bsee/src"))
from worldenergydata.bsee.series import BANDS, with_trends  # noqa: E402

TOTAL = "All water depths"
BAND_LABEL = {name.lower().replace(",", ""): name for name in BANDS}
KINDS = {"initial completion": "initial", "other completion work": "other"}
WORK = {
    "Recompletion": "recompletion",
    "Modify Perforations": "modify_perforations",
    "Reperforation": "reperforation",
}
COHORT = {
    "Exploratory wells": "exploratory_share",
    "Development wells": "development_share",
}


def rows(directory, stem):
    with (directory / f"{stem}.csv").open(encoding="utf-8", newline="") as stream:
        yield from csv.DictReader(stream)


def annual_series(directory, drilled):
    """Return value, five-year mean and underlying counts for each date and series."""
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    partial = summary["partial_year"]
    years = range(
        summary["first_full_year"], (partial or summary["last_full_year"]) + 1
    )
    series = defaultdict(dict)

    def add(metric, band, year, events, denominator=None, multiplier=1):
        year = int(year)
        if year not in years or year in series[metric, band]:
            raise ValueError(f"unexpected or duplicate year: {metric}, {band}, {year}")
        if events < 0 or (denominator is not None and denominator < 0):
            raise ValueError("negative count in annual series")
        value = (
            (multiplier * events / denominator if denominator else None)
            if denominator is not None
            else events
        )
        series[metric, band][year] = dict(
            group=f"{metric}|{band}",
            metric=metric,
            band=band,
            year=year,
            partial=int(year == partial),
            events=events,
            denominator=denominator,
            availability="unavailable" if value is None else "verified",
            value=value,
        )

    totals = defaultdict(dict)
    for row in rows(directory, "completion_approvals_by_year_band"):
        year, metric = int(row["year"]), KINDS[row["kind"]]
        band = row["band"]
        n = int(row["approvals"])
        by_band = totals[year, metric]
        if band in by_band or n < 0:
            raise ValueError("duplicate or negative completion approval cell")
        by_band[band] = n
        if band != "no depth":
            add(metric, BAND_LABEL[band], year, n)
    for (year, metric), counts in totals.items():
        if counts.keys() != {*BAND_LABEL, "no depth"}:
            raise ValueError("incomplete water-depth coverage for all-depth count")
        add(metric, TOTAL, year, sum(counts.values()))

    for row in rows(directory, "02_recompletion_by_period"):
        add(WORK[row["group"]], row["band"], row["year"], int(row["count"]))
    for row in rows(directory, "03_approvals_per_well"):
        add(
            "approvals_per_well",
            row["band"],
            row["year"],
            int(row["completion_approvals"]),
            int(row["january_well_years"]),
        )
    for row in rows(directory, "04_drilled_to_completed"):
        add(
            COHORT[row["group"]],
            row["band"],
            row["year"],
            int(row["with_initial_completion_approval"]),
            int(row["wells_first_drilled"]),
            100,
        )

    for year in years:
        # write_trend_tables rejects a recompletion with unresolved depth.
        add(
            "recompletion",
            TOTAL,
            year,
            sum(series["recompletion", b][year]["events"] for b in BANDS),
        )
    for group, observations in drilled.items():
        # Include wells without a depth; pool numerators and denominators by first spud.
        approved, wells = Counter(), Counter()
        for observation in observations:
            year = observation["year"]
            approved[year] += observation["count"]
            wells[year] += observation["exposure"]
        for year in years:
            add(COHORT[group], TOTAL, year, approved[year], wells[year], 100)

    expected = {
        (m, b)
        for m in (
            *KINDS.values(),
            *WORK.values(),
            *COHORT.values(),
            "approvals_per_well",
        )
        for b in BANDS
    }
    expected.update(
        (m, TOTAL) for m in (*KINDS.values(), "recompletion", *COHORT.values())
    )
    if set(series) != expected:
        raise ValueError("unexpected annual measure or water-depth coverage")
    result = []
    for key, cells in sorted(series.items()):
        if set(cells) != set(years):
            raise ValueError(f"incomplete calendar for {key}")
        result.extend(cells[y] for y in years)
    # Keep integer counts, denominators and raw annual values in their native types.
    # Only the rolling mean comes from the kit's numeric table.
    by_key = {(row["group"], row["year"]): row for row in result}
    for trend in with_trends(result, partial_year=partial).itertuples(index=False):
        by_key[trend.group, trend.year]["moving_average"] = (
            None if math.isnan(trend.moving_average) else trend.moving_average
        )
    return result


def write_annual_trends(directory, drilled):
    results = annual_series(directory, drilled)
    yearly = directory / "yearly"
    yearly.mkdir(exist_ok=True)
    with (yearly / "annual_trends.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, results[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(results)
