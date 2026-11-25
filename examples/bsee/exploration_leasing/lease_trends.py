"""Half-decade figures and CSV-backed reading notes for the lease study."""

import csv
import json

import pandas as pd
from lease_analysis import ALL_YEARS, DAYS_PER_YEAR, FOLLOWUP_YEARS, period_groups

from worldenergydata.bsee.half_decade import BANDS, PERIODS, render_svg, summarize

MATURE = PERIODS[:3]
AS_OF, FIVE_YEARS = "Observed by file date", "Within five years"
EFFECTIVE = "Lease effective period"
COVERAGE = (
    "Only complete half decades with five years of follow up are plotted. "
    "The cohort tables also include leases effective in 2020."
)
LEASES = "lease records"
BORES = "borehole spud dates"
PRODUCTION = "monthly production"


def annual_rows(table):
    return table.loc[table.issue_year.ne(ALL_YEARS) & table.depth_band.isin(BANDS)]


def spud_rows(older):
    """Pool first spuds on individual leases before calculating a period median."""
    for period, cohort in period_groups(older):
        if period not in MATURE:
            continue
        for band in BANDS:
            g = cohort.loc[cohort.depth_band.eq(band)]
            spud = g.exploration_spud
            within = spud.between(
                g.effective_date, g.effective_date + pd.DateOffset(years=FOLLOWUP_YEARS)
            )
            for group, mask in [(AS_OF, spud.notna()), (FIVE_YEARS, within)]:
                days = (spud[mask] - g.effective_date[mask]).dt.days
                yield dict(
                    period=period,
                    band=band,
                    group=group,
                    leases=len(g),
                    spud_leases=len(days),
                    share_pct=100 * len(days) / len(g) if len(g) else None,
                    median_years=days.median() / DAYS_PER_YEAR if len(days) else None,
                )


def crude_rows(production):
    crude = production.loc[
        production.period.isin(MATURE)
        & production.depth_band.isin(BANDS)
        & production.event.eq("Crude oil")
    ]
    for group, column in [
        ("Share reaching first crude", "share_pct"),
        ("Time among those reaching first crude", "median_years"),
    ]:
        for r in crude.to_dict("records"):
            yield dict(
                period=r["period"],
                band=r["depth_band"],
                group=group,
                leases=r["leases"],
                first_crude_leases=r["timed_leases"],
                value=None if pd.isna(r[column]) else r[column],
            )


def save_figure(
    output,
    stem,
    rows,
    *,
    question,
    sources,
    ylabel,
    note,
    periods=PERIODS,
    panel_ylabels=None,
):
    csv_path = output / f"{stem}.csv"
    svg_path = output / f"{stem}.svg"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with csv_path.open(encoding="utf-8", newline="") as stream:
        saved = list(csv.DictReader(stream))
    svg = render_svg(
        saved,
        ylabel=ylabel,
        periods=periods,
        xlabel=EFFECTIVE,
        panel_ylabels=panel_ylabels,
        note=note,
    )
    svg_path.write_text(svg, encoding="utf-8", newline="\n")
    return (
        dict(
            question=question,
            record_types=sources,
            csv=csv_path.name,
            svg=svg_path.name,
            note=note,
            bullets=[],
        ),
        saved,
    )


def add_comparison(
    figure, rows, *, band, group="", first, last, metric, unit, fmt=".1f"
):
    cells = []
    values = []
    for period in (first, last):
        match = dict(period=period, band=band, group=group)
        (row,) = [r for r in rows if all(r[k] == v for k, v in match.items())]
        values.append(format(float(row["value"]), fmt) if row["value"] else None)
        cells.append(dict(filter=match, column="value", format=fmt))
    if None in values:
        raise ValueError(f"Selected comparison has no eligible sample: {cells}")
    figure["bullets"].append(
        dict(
            text=f"{metric} in the {band.lower()} band was {values[0]}{unit} in {first} and {values[1]}{unit} in {last}.",
            cells=cells,
        )
    )


def write_trends(output, frame, older, tables):
    if not frame.depth_band.isin(BANDS).all():
        raise ValueError("Unallocated block depth in the four-band trend figures")
    manifest = []

    def save(stem, rows, **options):
        fig, saved = save_figure(output, stem, rows, **options)
        manifest.append(fig)
        return fig, saved

    issued = summarize(
        (
            dict(year=r.issue_year, band=r.depth_band, count=r.leases)
            for r in annual_rows(tables["issuance"]).itertuples()
        ),
        mode="per_year",
    )
    fig, saved = save(
        "issuance_trend",
        issued,
        question="Where did leases take effect, from shallow to deep water?",
        sources=[LEASES],
        ylabel="Effective leases per year",
        note="Lease counts divided by five calendar years, or by two for the partial 2025 to 2026 period. The last effective month is October 2026.",
    )
    for band, last in [
        (BANDS[0], PERIODS[3]),
        (BANDS[3], PERIODS[3]),
        (BANDS[3], PERIODS[4]),
    ]:
        add_comparison(
            fig,
            saved,
            band=band,
            first=PERIODS[0] if last == PERIODS[3] else PERIODS[3],
            last=last,
            metric="Effective leasing",
            unit=" leases per year",
        )

    spuds = list(spud_rows(older))
    for stem, metric, question, ylabel, unit in [
        (
            "spud_share_trend",
            "share_pct",
            "What share of leases recorded a first exploratory spud?",
            "Leases with a spud (%)",
            "%",
        ),
        (
            "spud_years_trend",
            "median_years",
            "How long did leases with a recorded first exploratory spud take to reach it?",
            "Median time to spud (years)",
            " years",
        ),
    ]:
        fig, saved = save(
            stem,
            [dict(r, value=r[metric]) for r in spuds],
            question=question,
            sources=[LEASES, BORES],
            ylabel=ylabel,
            periods=MATURE,
            note=f"{COVERAGE}\nThe first panel follows leases through November 2026, so older leases have longer observation. The second stops at the fifth anniversary. Timing uses leases with a qualifying spud and 365.25 days per year.",
        )
        for band, group in [
            (BANDS[0], AS_OF),
            (BANDS[3], AS_OF),
            (BANDS[3], FIVE_YEARS),
        ]:
            metric_name = (
                "The spud share" if metric == "share_pct" else "The median wait to spud"
            )
            basis = "by the file date" if group == AS_OF else "within five years"
            add_comparison(
                fig,
                saved,
                band=band,
                group=group,
                first=MATURE[0],
                last=MATURE[-1],
                metric=f"{metric_name} {basis}",
                unit=unit,
            )

    incidence, timing = (
        "Share reaching first crude",
        "Time among those reaching first crude",
    )
    fig, saved = save(
        "crude_trend",
        list(crude_rows(tables["first_production"])),
        question="How often and how soon did leases reach first crude oil in their first five years?",
        sources=[LEASES, PRODUCTION],
        ylabel="First crude oil",
        periods=MATURE,
        panel_ylabels={
            incidence: "Leases with first crude (%)",
            timing: "Median time (years)",
        },
        note=f"{COVERAGE}\nFirst positive crude report in months 0 through 59. Timing uses only leases with an event in the window. A gap means no median.",
    )
    for band, group in [
        (BANDS[0], incidence),
        (BANDS[3], incidence),
        (BANDS[0], timing),
    ]:
        add_comparison(
            fig,
            saved,
            band=band,
            group=group,
            first=MATURE[0],
            last=MATURE[-1],
            metric=(
                "The share reaching first crude"
                if group == incidence
                else "The median wait to first crude"
            ),
            unit="%" if group == incidence else " years",
        )

    statuses = annual_rows(tables["current_status"])
    code_order = (
        statuses.groupby("status_code").leases.sum().sort_values(ascending=False).index
    )
    statuses = statuses.set_index("status_code").loc[code_order].reset_index()
    grid = summarize(
        (
            dict(
                year=r.issue_year,
                band=r.depth_band,
                group=r.status_code,
                count=r.leases,
                exposure=r.cohort_leases,
            )
            for r in statuses.itertuples()
        ),
        mode="per_well",
    )
    rows = [
        dict(
            period=r["period"],
            band=r["band"],
            group=r["group"],
            status_leases=r["count"],
            leases=r["exposure"],
            value=100 * r["count"] / r["exposure"] if r["exposure"] else None,
        )
        for r in grid
    ]
    fig, saved = save(
        "status_trend",
        rows,
        question="Which status did each lease cohort carry on the November 2026 tape?",
        sources=[LEASES],
        ylabel="Share of cohort leases (%)",
        note="Each panel shows one lease status on the November 2, 2026 tape. Shares across codes sum to 100 percent within each band and period. Each panel has its own scale. The final period is partial.",
    )
    for band, code in [
        (BANDS[0], "RELINQ"),
        (BANDS[3], "RELINQ"),
        (BANDS[3], "PRIMRY"),
    ]:
        add_comparison(
            fig,
            saved,
            band=band,
            group=code,
            first=PERIODS[0],
            last=PERIODS[3],
            metric=f"The share coded {code}",
            unit="%",
        )
    (output / "figures.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
