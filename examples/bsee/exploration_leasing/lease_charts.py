"""Render the Part 1 annual figure set from the saved lease series."""

import csv
import json
import math
import textwrap
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from email.utils import parsedate_to_datetime
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

from worldenergydata.bsee import series
from worldenergydata.bsee.half_decade import _COLORS, _FONT, BANDS
from worldenergydata.bsee.series.charts import assign_scales, scale

ALL = "All water depths"
OBSERVED = "Observed by file date"
FIVE = "Within five years"
STATUS_ORDER = (
    "RELINQ",
    "EXPIR",
    "PRIMRY",
    "TERMIN",
    "UNIT",
    "PROD",
    "CANCEL",
    "OPERNS",
    "SOP",
)
MEASURE_COLORS = (
    "#245476",
    "#ac501e",
    "#00796e",
    "#924975",
    "#82701a",
    "#5247a1",
    "#9b372e",
    "#407834",
    "#575b63",
)
CRUDE = (
    "Leases effective from 2005 through 2020 have 60 complete reporting months. "
    "First crude is the first positive crude oil month in months 0 through 59."
)


def line_style(group):
    metric = group.partition("|")[0]
    return "dashed" if metric in {"spud_years_5y", "spud_share_5y"} else "solid"


def appendix_figures():
    figures = []
    pins = json.loads(Path(__file__).with_name("source_pins.json").read_bytes())
    bore = next(pin for pin in pins["sources"] if pin["name"] == "BoreholeRawData.zip")
    file_date = parsedate_to_datetime(bore["last_modified"])
    boundaries = {
        "solid": f"through the {file_date.day} {file_date:%B %Y} borehole file",
        "dashed": "through each lease’s fifth anniversary, inclusive",
    }

    def add(number, title, ylabel, measure, metrics, note, *, by_depth=False):
        series = (
            [(metrics[0][0], band, band) for band in BANDS]
            if by_depth
            else [(metric, ALL, label) for metric, label in metrics]
        )
        number = "A" + number
        stem = f"figure-{number.lower()}"
        figures.append(
            {
                "figure_number": number,
                "title": title,
                "ylabel": ylabel,
                "measure": measure,
                "note": note,
                "role": "appendix",
                "x_unit": "year",
                "trend": "moving_average_5y_trailing",
                "view": "annual",
                "layout": "4x1_shared_x" if by_depth else "overlay",
                "panel_by": "depth_band" if by_depth else "none",
                "series_by": "depth_band" if by_depth else "measure",
                "groups": [f"{metric}|{band}" for metric, band, _ in series],
                "labels": [label for _, _, label in series],
                "csv": "annual_trends.csv",
                "svg": stem + ".svg",
                "interactive": stem + ".html",
            }
        )
        return figures[-1]

    for figure, stem, name, ylabel in (
        (
            "2",
            "spud_share",
            "Leases with a first exploratory spud",
            "Share of effective leases (%)",
        ),
        (
            "3",
            "spud_years",
            "Median time to first exploratory spud",
            "Median time from effectiveness (years)",
        ),
    ):
        metrics = [(stem + "_observed", OBSERVED), (stem + "_5y", FIVE)]
        note = (
            f"{OBSERVED} includes first qualifying spuds through the {file_date:%B %Y} borehole file. "
            f"{FIVE} stops at the fifth anniversary. Both use leases effective from 2005 through 2020."
        )
        if figure == "3":
            note += " Medians include only leases with a qualifying spud."
        combined = add(
            figure + "A", name + " across all water depths", ylabel, stem, metrics, note
        )
        windows = {}
        for group, label in zip(combined["groups"], combined["labels"]):
            style = line_style(group)
            windows[style] = {"label": label, "definition": boundaries[style]}
        combined["windows"] = windows
        combined["caption"] = " ".join(
            f"The {style} line ({window['label']}) includes first qualifying spuds "
            f"{window['definition']}."
            for style, window in windows.items()
        )
        for suffix, (metric, label) in zip(("B", "C"), metrics):
            add(
                figure + suffix,
                name + " by block water depth",
                ylabel,
                stem,
                [(metric, label)],
                label + ". " + note,
                by_depth=True,
            )
    for number, metric, name, ylabel, by_depth in (
        (
            "4A",
            "crude_share_5y",
            "Leases reaching first crude",
            "Share of effective leases (%)",
            False,
        ),
        (
            "4B",
            "crude_years_5y",
            "Median time to first crude",
            "Median time from effectiveness (years)",
            False,
        ),
        (
            "4C",
            "crude_share_5y",
            "Leases reaching first crude",
            "Share of effective leases (%)",
            True,
        ),
        (
            "4D",
            "crude_years_5y",
            "Median time to first crude",
            "Median time from effectiveness (years)",
            True,
        ),
    ):
        scope = " by block water depth" if by_depth else " across all water depths"
        add(
            number,
            name + scope,
            ylabel,
            metric,
            [(metric, "First crude within five years")],
            CRUDE,
            by_depth=by_depth,
        )
    add(
        "5",
        "Lease status across all water depths",
        "Share of effective leases (%)",
        "status_share",
        [("status_" + code, code) for code in STATUS_ORDER],
        "Each code is the status on the November 2, 2026 lease tape. The final effective month is October 2026. A blank share means no leases took effect that year.",
    )
    return figures


def format_tick(value):
    return format(Decimal(str(value)).normalize(), ",f")


def element(parent, tag, **attrs):
    return ET.SubElement(
        parent, tag, {k.replace("_", "-"): str(v) for k, v in attrs.items()}
    )


def label(parent, x, y, words, **attrs):
    element(parent, "text", x=x, y=y, **attrs).text = words


def format_readout(value):
    rounded = Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    return f"{rounded:,.3f}".rstrip("0").rstrip(".")


def tint(color):
    channels = [int(color[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(c + (255 - c) * 0.42):02x}" for c in channels)


def draw_series(parent, index, cells, name, color, dash, years, partial, xpos, ypos):
    group = element(parent, "g", data_series=index, data_label=name)
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
        result = "unavailable" if mean is None else format_readout(mean)
        when = str(yr) + (" (partial through October 2026)" if yr in partial else "")
        element(point, "title").text = (
            f"{name}, {when}. Annual value {format_readout(value)}. Five year mean {result}."
        )


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
    notes = textwrap.wrap(figure["note"], width=76)
    if "coverage_note" in figure:
        notes += textwrap.wrap(figure["coverage_note"], width=76)
    if "scale_note" in figure:
        notes += textwrap.wrap(figure["scale_note"], width=76)
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
    label(root, 22, 32, figure["title"], font_size=22, font_weight="bold")
    label(
        root,
        22,
        58,
        "Markers show annual values. Thick lines show the 5 year trailing mean.",
    )
    colors = _COLORS if figure["series_by"] == "depth_band" else MEASURE_COLORS
    styles = []
    for index, (name, group, (x, y)) in enumerate(
        zip(labels, figure["groups"], legend)
    ):
        color = colors[index]
        dash = {"stroke_dasharray": "9 6"} if line_style(group) == "dashed" else {}
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
        label(root, left - 9, round(y + 5, 2), format_tick(tick), text_anchor="end")
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
        "Lease effective year",
        text_anchor="middle",
        font_weight="bold",
    )

    for index, (cells, name, (color, dash)) in enumerate(zip(series, labels, styles)):
        draw_series(root, index, cells, name, color, dash, years, partial, xpos, ypos)
    for i, line in enumerate(notes):
        label(root, 22, bottom + 86 + i * 22, line)
    return ET.tostring(root, encoding="unicode") + "\n"


def interactive(figure, svg, groups):
    data = [
        [
            (
                year,
                row["value"],
                row["moving_average"],
                row["partial"] == "1",
                row["availability"],
            )
            for year, row in sorted(groups[key].items())
        ]
        for key in figure["groups"]
    ]
    options = "".join(
        f'<option value="{year}">{year}{" (partial through October 2026)" if partial else ""}</option>'
        for year, _, _, partial, _ in data[0]
    )
    return (
        Path(__file__)
        .with_name("lease_chart.html")
        .read_text(encoding="utf-8")
        .replace("{{TITLE}}", escape(figure["title"]))
        .replace("{{SVG}}", svg.rstrip())
        .replace("{{OPTIONS}}", options)
        .replace("{{UNIT}}", escape(figure["ylabel"]))
        .replace("{{DATA}}", json.dumps(data, separators=(",", ":"), allow_nan=False))
    )


def read_spud_counts(exploration_path):
    """Read annual lease counts, excluding pooled years and unknown depth."""
    from lease_analysis import COHORT_END, COHORT_START

    counts = {}
    with exploration_path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            band, year = row["depth_band"], row["issue_year"]
            if year == "All years" or band not in (*BANDS, "All bands"):
                continue
            band = ALL if band == "All bands" else band
            key = (int(year), band)
            count = int(row["explored_within_five_years"])
            if key in counts or not 0 <= count <= int(row["leases"]):
                raise ValueError(f"Invalid five year spud count at {key}")
            counts[key] = count

    cohort = range(COHORT_START, COHORT_END + 1)
    if set(counts) != {(year, band) for year in cohort for band in (ALL, *BANDS)}:
        raise ValueError("Missing or unexpected five year spud cohort")
    for year in cohort:
        if counts[year, ALL] != sum(counts[year, band] for band in BANDS):
            raise ValueError(f"Depth counts differ from the all-depth count in {year}")

    return counts


def write_main_figures(output, groups, exploration_path):
    csv_name = "lease_counts.csv"
    issued = "effective_leases"
    spuds = "explored_within_five_years"
    counts = read_spud_counts(exploration_path)
    count_label = "Within five years"
    rows = [
        {"group": f"{spuds}|{band}", "year": year, "value": count, "partial": 0}
        for (year, band), count in counts.items()
    ]
    for band in (ALL, *BANDS):
        for year, row in groups[f"{issued}|{band}"].items():
            rows.append(
                {
                    "group": f"{issued}|{band}",
                    "year": year,
                    "value": row["value"],
                    "partial": int(row["partial"]),
                    "availability": row["availability"],
                }
            )
            if band == ALL and (year, ALL) not in counts:
                # Outside the comparison cohort the dashed series has no eligible value.
                rows.append(
                    {
                        "group": f"{spuds}|{ALL}",
                        "year": year,
                        "value": None,
                        "partial": int(row["partial"]),
                    }
                )

    note = (
        "Each lease counts once in its effective year. "
        "The lease tape does not distinguish new grants from renewals. "
        "The final effective month is October 2026."
    )
    window = "through each lease’s fifth anniversary, inclusive"

    def by_band(metric):
        return [(f"{metric}|{band}", band) for band in BANDS]

    figures = [
        series.make_figure(
            "1A",
            "Effective leases and first spuds across all water depths",
            "Leases per effective year",
            issued,
            [(f"{issued}|{ALL}", "Effective leases"), (f"{spuds}|{ALL}", count_label)],
            note + " The spud series covers leases effective from 2005 through 2020.",
            csv_name=csv_name,
            window_definitions={
                f"{issued}|{ALL}": "all leases effective through October 2026",
                f"{spuds}|{ALL}": window,
            },
        ),
        series.make_figure(
            "1B",
            "Effective leases by block water depth",
            "Effective leases (leases per year)",
            issued,
            by_band(issued),
            note,
            by_depth=True,
            csv_name=csv_name,
        ),
        series.make_figure(
            "2",
            "Leases with a first exploratory spud within five years",
            "Leases per effective year",
            spuds,
            by_band(spuds),
            "Each lease counts once if its first qualifying exploratory spud on the bottom lease "
            "fell on or before its fifth anniversary. Cohorts cover 2005 through 2020.",
            by_depth=True,
            csv_name=csv_name,
        ),
    ]
    annual = series.with_trends(rows)
    series.write_figures(
        output,
        figures,
        annual.to_dict("records"),
        xlabel="Lease effective year",
        partial_label="partial through October 2026",
    )
    return json.loads((output / "figures.json").read_bytes())


def write_figures(output, exploration_path):
    from lease_panels import render_panels

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
    figures = appendix_figures()
    expected = {key for fig in figures for key in fig["groups"]}
    expected.update(f"effective_leases|{band}" for band in (ALL, *BANDS))
    if set(groups) != expected:
        raise ValueError(
            f"Unexpected or missing annual chart series: {sorted(expected ^ set(groups))}"
        )
    main = write_main_figures(output, groups, exploration_path)
    assign_scales(figures, peaks)
    for fig in figures:
        blanks = [
            f"{year} {label}" if len(fig["groups"]) > 1 else str(year)
            for key, label in zip(fig["groups"], fig["labels"])
            for year, row in sorted(groups[key].items())
            if row["value"] is None
        ]
        if blanks:
            fig["blank_cells"] = blanks
            caption = fig.get("caption", fig["note"])
            fig["caption"] = (
                f"{caption} Annual values are blank for {', '.join(blanks)}."
            )
        if "caption" in fig and "scale_note" in fig:
            fig["caption"] += " " + fig["scale_note"]
        missing = [
            row
            for key in fig["groups"]
            for row in groups[key].values()
            if row["availability"] == "unavailable"
        ]
        if missing:
            fig["unavailable_cells"] = len(missing)
            fig["coverage_note"] = (
                f"Source records are unavailable for {len(missing)} annual series observations. "
                "The chart omits those points and any mean requiring them. "
                "The interactive year table identifies the affected series."
            )
        renderer = render_panels if fig["panel_by"] == "depth_band" else render
        svg = renderer(fig, groups)
        (output / fig["svg"]).write_text(svg, encoding="utf-8", newline="\n")
        (output / fig["interactive"]).write_text(
            interactive(fig, svg, groups), encoding="utf-8", newline="\n"
        )
    figures = [*main, *figures]
    series.write_manifest(output, figures)
    return figures
