"""Render the Part 3 annual charts from the saved completion series."""

import argparse
import csv
import json
import math
import sys
import textwrap
from collections import defaultdict
from decimal import Decimal
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[2] / "packages/worldenergydata-bsee/src"))
from worldenergydata.bsee.half_decade import _COLORS, _FONT, BANDS
from worldenergydata.bsee.yearly_trend import render_svg as render_panels

ALL = "All water depths"
MEASURE_COLORS = ("#245476", "#ac501e")
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
        selection = [
            (metric, band, band if bands and not appendix else label)
            for metric, label in metrics
            for band in (BANDS if bands else (ALL,))
        ]
        stem = "figure-" + number.lower()
        fig = {
            "figure_number": number,
            "title": title,
            "ylabel": ylabel,
            "xlabel": xlabel,
            "measure": measure,
            "note": note + " " + CUTOFF,
            "role": "appendix" if appendix else "main",
            "x_unit": "year",
            "trend": "moving_average_5y_trailing",
            "view": "annual",
            "layout": "4x1_shared_x" if appendix else "overlay",
            "panel_by": "depth_band" if appendix else "none",
            "series_by": "depth_band" if bands and not appendix else "measure",
            "groups": [f"{metric}|{band}" for metric, band, _ in selection],
            "labels": [label for _, _, label in selection],
            "csv": "annual_trends.csv",
            "svg": stem + ".svg",
        }
        if not appendix:
            fig["interactive"] = stem + ".html"
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


def scale(peak):
    """Smallest covering nice top with four to six ticks on a zero based axis."""
    if peak <= 0:
        return 1, 0.2
    unit = 10 ** math.floor(math.log10(peak))
    for factor, steps in ((1, 5), (2, 4), (5, 5), (10, 5)):
        top = factor * unit
        if top >= peak:
            return top, top / steps
    raise ValueError(f"Invalid peak {peak}")


def format_tick(value):
    return format(Decimal(str(value)).normalize(), ",f")


def assign_scales(figures, peaks):
    measures = defaultdict(list)
    for fig in figures:
        measures[fig["measure"]].append(fig)
    for measure, members in measures.items():
        maxima = [max(peaks[group] for group in f["groups"]) for f in members]
        pooled = scale(max(maxima))
        eligible = [peak >= 0.3 * pooled[0] for peak in maxima]
        for fig, peak, qualifies in zip(members, maxima, eligible):
            shared = qualifies and sum(eligible) >= 2
            top, step = pooled if shared else scale(peak)
            fig["y_scale"] = {
                "max": top,
                "step": step,
                "shared": f"measure:{measure}" if shared else "panels",
            }
        if len({f["y_scale"]["max"] for f in members}) > 1:
            for fig in members:
                peers = [
                    f"{format_tick(f['y_scale']['max'])} in Figure {f['figure_number']}"
                    for f in members
                    if f is not fig
                ]
                fig["scale_note"] = (
                    f"Y maximum {format_tick(fig['y_scale']['max'])}, against "
                    + ", ".join(peers)
                    + "."
                )


def element(parent, tag, **attrs):
    return ET.SubElement(
        parent, tag, {k.replace("_", "-"): str(v) for k, v in attrs.items()}
    )


def label(parent, x, y, words, **attrs):
    element(parent, "text", x=x, y=y, **attrs).text = words


def tint(color):
    channels = [int(color[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(c + (255 - c) * 0.42):02x}" for c in channels)


def render(figure, groups):
    labels = figure["labels"]
    series = [groups[k] for k in figure["groups"]]
    years = sorted(series[0])
    if any(set(s) != set(years) for s in series) or years != list(
        range(years[0], years[-1] + 1)
    ):
        raise ValueError("Figure series require a common complete calendar")
    partial = {
        year for cells in series for year, row in cells.items() if row["partial"] == "1"
    }
    if partial and partial != {years[-1]}:
        raise ValueError("Only the final calendar year may be partial")
    # Lay out the legend above the plot; each entry toggles its data and trend together.
    legend = []
    left, right = 68, 764
    x, y = left, 88
    for name in labels:
        width = 66 + 9 * len(name)
        if x + width > 786:
            x, y = left, y + 30
        legend.append((x, y))
        x += width
    top, bottom = y + 57, y + 332
    notes = textwrap.wrap(figure["note"], width=90)
    if "coverage_note" in figure:
        notes += textwrap.wrap(figure["coverage_note"], width=90)
    if "scale_note" in figure:
        notes += textwrap.wrap(figure["scale_note"], width=90)
    height = bottom + 100 + 22 * len(notes)
    root = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "role": "img",
            "aria-label": figure["title"],
            "font-family": _FONT,
            "font-size": "16",
            "fill": "#203340",
            "width": "800",
            "height": str(height),
            "viewBox": f"0 0 800 {height}",
        },
    )
    element(root, "title").text = figure["title"]
    element(root, "rect", width="800", height=height, fill="white")
    label(root, 22, 32, figure["title"], font_size=18, font_weight="bold")
    label(
        root,
        22,
        58,
        "Markers and thin lines show annual values. Thick, lighter lines show the 5 year trailing mean.",
    )
    colors = _COLORS if figure["series_by"] == "depth_band" else MEASURE_COLORS
    styles = []
    for index, (name, (x, y)) in enumerate(zip(labels, legend)):
        color = colors[index]
        dash = (
            {"stroke_dasharray": "9 6"}
            if figure["series_by"] == "measure" and index == 1
            else {}
        )
        styles.append((color, dash))
        key = element(root, "g", data_legend=index)
        element(
            key,
            "rect",
            x=x - 6,
            y=y - 18,
            height=27,
            width=55 + 9 * len(name),
            fill="white",
        )
        element(
            key,
            "line",
            x1=x,
            y1=y - 5,
            x2=x + 32,
            y2=y - 5,
            stroke=color,
            stroke_width=3,
            **dash,
        )
        label(key, x + 38, y, name)
    label(root, left, top - 12, figure["ylabel"], font_weight="bold")
    maximum, step = (figure["y_scale"][k] for k in ("max", "step"))

    def xpos(year):
        return left + (right - left) * (year - years[0]) / max(1, years[-1] - years[0])

    def ypos(value):
        return bottom - (bottom - top) * value / maximum

    for i in range(round(maximum / step) + 1):
        tick = Decimal(str(step)) * i
        y = round(ypos(float(tick)), 2)
        element(root, "line", x1=left, x2=right, y1=y, y2=y, stroke="#cfd9de")
        label(root, left - 9, y + 5, format_tick(tick), text_anchor="end")
    xticks = [
        years[0],
        *(yr for yr in years[1:-1] if yr % 5 == 0 and years[-1] - yr >= 2),
        years[-1],
    ]
    for yr in dict.fromkeys(xticks):
        label(root, round(xpos(yr), 2), bottom + 27, str(yr), text_anchor="middle")
    if partial:
        label(root, right, bottom + 48, "partial", text_anchor="middle")
    label(
        root,
        (left + right) / 2,
        bottom + 54,
        figure["xlabel"],
        text_anchor="middle",
        font_weight="bold",
    )

    for index, (cells, name, (color, dash)) in enumerate(zip(series, labels, styles)):
        group = element(root, "g", data_series=index, data_label=name)
        for key, kind, stroke, width in (
            ("moving_average", "trend", tint(color), 4.5),
            ("value", "annual", color, 2),
        ):
            points = []
            connected = False
            for yr in years:
                value = cells[yr][key]
                if value is None:
                    connected = False
                    continue
                vertex = f"{xpos(yr):.2f},{ypos(value):.2f}"
                points.append("L" + vertex if connected else "M" + vertex + "l0,0")
                connected = True
            if points:
                element(
                    group,
                    "path",
                    d=" ".join(points),
                    fill="none",
                    stroke=stroke,
                    stroke_width=width,
                    stroke_linecap="round",
                    **{"class": kind},
                    **dash,
                )
        for yr in years:
            row = cells[yr]
            if row["value"] is None:
                continue
            value = row["value"]
            mean = row["moving_average"]
            point = element(
                group,
                "circle",
                cx=f"{xpos(yr):.2f}",
                cy=f"{ypos(value):.2f}",
                r=5,
                stroke=color,
                stroke_width=2,
                fill="white" if yr in partial else color,
                data_year=yr,
            )
            result = "unavailable" if mean is None else f"{mean:,.4g}"
            when = str(yr) + (" (partial)" if yr in partial else "")
            element(point, "title").text = (
                f"{name}, {when}. Annual value {value:,.4g}. Five year mean {result}."
            )
    for i, line in enumerate(notes):
        label(root, 22, bottom + 86 + i * 22, line)
    return ET.tostring(root, encoding="unicode") + "\n"


def blank_reason(row):
    if row["value"] is not None:
        return ""
    if row["denominator"] == "0":
        return (
            "No January standing wells"
            if row["metric"] == "approvals_per_well"
            else "No wells first drilled"
        )
    return (
        "Source records unavailable"
        if row["availability"] == "unavailable"
        else "No eligible value"
    )


def interactive(figure, svg, groups):
    data = [
        [
            (
                year,
                row["value"],
                row["moving_average"],
                row["partial"] == "1",
                blank_reason(row),
            )
            for year, row in sorted(groups[key].items())
        ]
        for key in figure["groups"]
    ]
    options = "".join(
        f'<option value="{year}">{year}{" (partial)" if partial else ""}</option>'
        for year, _, _, partial, _ in data[0]
    )
    return (
        Path(__file__)
        .with_name("comp_chart.html")
        .read_text(encoding="utf-8")
        .replace("{{TITLE}}", escape(figure["title"]))
        .replace("{{SVG}}", svg.rstrip())
        .replace("{{OPTIONS}}", options)
        .replace("{{UNIT}}", escape(figure["ylabel"]))
        .replace("{{YEAR}}", escape(figure["xlabel"]))
        .replace("{{DATA}}", json.dumps(data, separators=(",", ":"), allow_nan=False))
    )


def write_figures(output):
    groups = defaultdict(dict)
    peaks = defaultdict(float)
    with (output / "annual_trends.csv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            key, year = row["group"], int(row["year"])
            if key != row["metric"] + "|" + row["band"] or year in groups[key]:
                raise ValueError(
                    f"Invalid series identity or duplicate at {key}, {year}"
                )
            if (
                row["partial"] not in {"0", "1"}
                or row["partial"] == "1"
                and row["moving_average"] != ""
            ):
                raise ValueError(f"Invalid partial year information at {key}, {year}")
            if row["availability"] not in {"verified", "unavailable"}:
                raise ValueError(f"Unknown availability at {key}, {year}")
            if row["availability"] == "unavailable" and (
                row["value"] or row["moving_average"]
            ):
                raise ValueError(
                    f"Unavailable source marked as a result at {key}, {year}"
                )
            for column in ("value", "moving_average"):
                value = float(row[column]) if row[column] != "" else None
                if value is not None and (not math.isfinite(value) or value < 0):
                    raise ValueError(f"Invalid {column} at {key}, {year}")
                row[column] = value
                peaks[key] = max(peaks[key], value or 0)
            groups[key][year] = row
    figures = specifications()
    expected = {key for fig in figures for key in fig["groups"]}
    # The data also retain all-depth appendix rows for independent count checks.
    allowed = {
        key.split("|")[0] + "|" + band for key in expected for band in (ALL, *BANDS)
    }
    if expected - set(groups) or set(groups) - allowed:
        raise ValueError(
            f"Unexpected or missing annual chart series: {sorted((expected - set(groups)) | (set(groups) - allowed))}"
        )
    assign_scales(figures, peaks)
    for fig in figures:
        if fig["role"] == "appendix":
            rows = [
                dict(row, group=name, partial_year=row["partial"] == "1")
                for key, name in zip(fig["groups"], fig["labels"])
                for row in groups[key].values()
            ]
            axis = fig["y_scale"]
            step = Decimal(str(axis["step"]))
            ticks = [
                float(i * step) for i in range(round(axis["max"] / axis["step"]) + 1)
            ]
            svg = render_panels(
                rows,
                title=fig["title"],
                ylabel=fig["ylabel"],
                xlabel=fig["xlabel"],
                note=" ".join(s for s in (fig["note"], fig.get("scale_note")) if s),
                y_scale=ticks,
            )
            (output / fig["svg"]).write_text(svg, encoding="utf-8", newline="\n")
            continue
        missing = [
            row
            for key in fig["groups"]
            for row in groups[key].values()
            if row["availability"] == "unavailable"
        ]
        if missing:
            fig["unavailable_cells"] = len(missing)
            empty = sum(row["denominator"] == "0" for row in missing)
            reasons = []
            if empty:
                reasons.append(
                    f"A zero denominator leaves {empty} annual shares blank."
                )
            if len(missing) > empty:
                reasons.append(
                    f"Source records are unavailable for {len(missing) - empty} annual observations."
                )
            fig["coverage_note"] = " ".join(reasons) + (
                " "
                "The chart omits those points and any mean requiring them. "
                "The interactive year table identifies the affected series."
            )
        svg = render(fig, groups)
        (output / fig["svg"]).write_text(svg, encoding="utf-8", newline="\n")
        (output / fig["interactive"]).write_text(
            interactive(fig, svg, groups), encoding="utf-8", newline="\n"
        )
    (output / "figures.json").write_text(
        json.dumps(figures, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "output/yearly")
    write_figures(parser.parse_args().out)
