"""Render the Part 3 annual charts from the saved completion series."""

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[2] / "packages/worldenergydata-bsee/src"))
from worldenergydata.bsee.series import BANDS, make_figure
from worldenergydata.bsee.series import write_figures as write_series_figures

ALL = "All water depths"
CUTOFF = "Hollow markers show partial 2026 through 23 November 2026. Means end in 2025."
APPROVAL_YEAR = "Calendar year of approval"
SPUD_YEAR = "Calendar year of first drilling (spud year)"
PERMITS = "Approved permits per year"
SHARE = "Share of drilled wells (%)"
INITIAL = "Initial completion"
OTHER = "Other completion work"
RECOMPLETION = "Recompletion"
EXPLORATORY = "Exploratory wells"
DEVELOPMENT = "Development wells"
SHARE_NOTE = (
    "Each well counts in its first spud year. The numerator counts wells with an initial "
    "completion approval by the file date. Recent cohorts have shorter follow up. A blank "
    "means no wells of this type were first drilled in that band and year."
)


def specifications():
    """Declare the article order, identities, axes and denominators separately from drawing."""
    figures = []

    def add(
        number,
        title,
        ylabel,
        xlabel,
        measure,
        metrics,
        note,
        *,
        bands=False,
        appendix=False,
    ):
        series = [
            (f"{metric}|{band}", band if bands and not appendix else label)
            for metric, label in metrics
            for band in (BANDS if bands else (ALL,))
        ]
        fig = make_figure(
            number,
            title,
            ylabel,
            measure,
            series,
            note + " " + CUTOFF,
            by_depth=bands and not appendix,
        )
        fig["xlabel"] = xlabel
        if measure == "share_of_drilled_wells":
            fig["empty_denominator_label"] = "No wells first drilled"
        if appendix:
            fig.update(role="appendix", layout="4x1_shared_x", panel_by="depth_band")
            del fig["interactive"]
            if measure == "approvals_per_well":
                fig["empty_denominator_label"] = "No January standing wells"
        figures.append(fig)

    initial = ("initial", INITIAL)
    other = ("other", OTHER)
    recompletion = ("recompletion", RECOMPLETION)
    approval = "approvals_per_year"
    add(
        "1A",
        "Completion approvals across all water depths",
        PERMITS,
        APPROVAL_YEAR,
        approval,
        [initial, other],
        "Each approved permit counts once. Solid lines show initial completion "
        "(INITCOMP). Dashed lines show other completion work without a change of zone.",
    )
    add(
        "1B",
        "Initial completion approvals by water depth",
        PERMITS,
        APPROVAL_YEAR,
        approval,
        [initial],
        "Each approved completion permit carrying INITCOMP counts once.",
        bands=True,
    )
    add(
        "1C",
        "Other completion approvals by water depth",
        PERMITS,
        APPROVAL_YEAR,
        approval,
        [other],
        "Each approved permit for other completion work without a change of zone "
        "counts once.",
        bands=True,
    )
    zone = "Each approved permit classed as a change of zone counts once."
    add(
        "2A",
        "Recompletion approvals across all water depths",
        PERMITS,
        APPROVAL_YEAR,
        approval,
        [recompletion],
        zone,
    )
    add(
        "2B",
        "Recompletion approvals by water depth",
        PERMITS,
        APPROVAL_YEAR,
        approval,
        [recompletion],
        zone,
        bands=True,
    )
    wells = "share_of_drilled_wells"
    exploration = ("exploratory_share", EXPLORATORY)
    development = ("development_share", DEVELOPMENT)
    add(
        "3A",
        "Drilled wells with an initial approval across all water depths",
        SHARE,
        SPUD_YEAR,
        wells,
        [exploration, development],
        "Solid lines show exploratory wells. Dashed lines "
        "show development wells. " + SHARE_NOTE,
    )
    add(
        "3B",
        "Exploratory wells with an initial approval by water depth",
        SHARE,
        SPUD_YEAR,
        wells,
        [exploration],
        SHARE_NOTE,
        bands=True,
    )
    add(
        "3C",
        "Development wells with an initial approval by water depth",
        SHARE,
        SPUD_YEAR,
        wells,
        [development],
        SHARE_NOTE,
        bands=True,
    )
    add(
        "E3",
        "Completion approvals per January standing well",
        "Approved permits per January well",
        APPROVAL_YEAR,
        "approvals_per_well",
        [("approvals_per_well", "Completion approvals")],
        "The denominator is the number of wells standing on 1 January. The numerator includes "
        "approvals for wells first drilled later in the year. An empty denominator gives a blank.",
        bands=True,
        appendix=True,
    )
    add(
        "E4",
        "Other completion approvals with perforation flags",
        PERMITS,
        APPROVAL_YEAR,
        approval,
        [
            ("modify_perforations", "Modify Perforations"),
            ("reperforation", "Reperforation"),
        ],
        "Flags are counted on permits for other completion work without a change of zone. "
        "A permit may carry both flags.",
        bands=True,
        appendix=True,
    )
    return figures


def write_figures(output):
    figures = specifications()
    # Saved CSVs may include all-depth observations beyond the plotted groups.
    selected = {key for fig in figures for key in fig["groups"]}
    metrics = {key.split("|")[0] for key in selected}
    with (output / "annual_trends.csv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if (
                row["group"] != f"{row['metric']}|{row['band']}"
                or row["metric"] not in metrics
                or row["band"] not in (ALL, *BANDS)
            ):
                raise ValueError(f"Invalid COMP series identity: {row['group']}")
    write_series_figures(output, figures, xlabel=APPROVAL_YEAR)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "output/yearly")
    write_figures(parser.parse_args().out)
