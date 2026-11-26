"""Portable annual SVG overlays, offline year readouts and the standard figure manifest."""

import csv
import json
import math
import re
import textwrap
from collections import defaultdict
from decimal import Context, Decimal
from html import escape
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

from ..half_decade import _FONT
from ..yearly_trend import render_svg as render_depth_panels
from .annual import BAND_COLORS, BANDS, with_trends

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


def _validate_measure(measure):
    if not isinstance(measure, str) or not measure.strip():
        raise ValueError("measure must be a nonblank string")


def make_figure(
    number,
    title,
    ylabel,
    measure,
    series,
    note,
    *,
    by_depth=False,
    csv_name="annual_trends.csv",
    window_definitions=None,
):
    """Describe one main overlay. Series are ordered (group key, legend label) pairs."""
    _validate_measure(measure)
    series = list(series)
    if not series or len(series) > len(MEASURE_COLORS):
        raise ValueError("A figure needs one to nine named series")
    if by_depth and tuple(label for _, label in series) != BANDS:
        raise ValueError("A depth overlay needs the four standard bands in order")
    stem = f"figure-{number.lower()}"
    figure = {
        "figure_number": number,
        "title": title,
        "ylabel": ylabel,
        "measure": measure,
        "note": note,
        "role": "main",
        "x_unit": "year",
        "trend": "moving_average_5y_trailing",
        "view": "annual",
        "layout": "overlay",
        "panel_by": "none",
        "series_by": "depth_band" if by_depth else "measure",
        "groups": [group for group, _ in series],
        "labels": [label for _, label in series],
        "csv": csv_name,
        "svg": stem + ".svg",
        "interactive": stem + ".html",
    }
    if window_definitions is not None:
        groups, labels = figure["groups"], figure["labels"]
        if (
            by_depth
            or len(series) != 2
            or len(set(groups)) != 2
            or len({label.strip().casefold() for label in labels}) != 2
            or set(window_definitions) != set(groups)
        ):
            raise ValueError(
                "Window definitions require two distinct plotted groups and labels"
            )
        windows = {}
        for style, (key, label) in zip(("solid", "dashed"), series):
            definition = window_definitions[key]
            if (
                not isinstance(definition, str)
                or not definition.strip()
                or not label.strip()
                or definition.strip().casefold() == label.strip().casefold()
            ):
                raise ValueError(f"Expected a time boundary for {label}")
            windows[style] = {"label": label, "definition": definition.strip()}
        figure["windows"] = windows
    return figure


def scale(peak):
    """Smallest covering nice top with four to six ticks on a zero based axis."""
    if peak <= 0:
        return 1, 0.2
    peak = Decimal(str(peak))
    exponent = peak.adjusted()
    # Smaller decades cannot cover the peak even with five intervals at step 5.
    steps = [
        Decimal(factor).scaleb(k)
        for k in (exponent - 1, exponent)
        for factor in (1, 2, 5)
    ]
    top, step = min(
        (count * step, step)
        for step in steps
        for count in (3, 4, 5)
        if count * step >= peak
    )
    return float(top), float(step)


def format_number(value, *, grouped=True):
    """Display measured values in fixed point and calendar years without grouping."""
    decimal = Decimal(str(value))
    if not decimal:
        return "0"
    return format(decimal.normalize(Context(prec=15)), ",f" if grouped else "f")


def assign_scales(figures, peaks):
    measures = defaultdict(list)
    for fig in figures:
        _validate_measure(fig["measure"])
        measures[fig["measure"]].append(fig)
    for measure, members in measures.items():
        maxima = [max(peaks[group] for group in f["groups"]) for f in members]
        pooled = scale(max(maxima))
        cutoff = Decimal("0.3") * Decimal(str(pooled[0]))
        eligible = [Decimal(str(peak)) >= cutoff for peak in maxima]
        can_share = sum(eligible) >= 2
        for fig, peak, qualifies in zip(members, maxima, eligible):
            fig.pop("scale_note", None)
            shared = qualifies and can_share
            top, step = pooled if shared else scale(peak)
            fig["y_scale"] = {
                "max": top,
                "step": step,
                "shared": f"measure:{measure}" if shared else "panels",
            }
        if len({f["y_scale"]["max"] for f in members}) > 1:
            for fig in members:
                peers = [
                    f"{format_number(f['y_scale']['max'])} in Figure {f['figure_number']}"
                    for f in members
                    if f is not fig
                ]
                fig["scale_note"] = (
                    f"Y maximum {format_number(fig['y_scale']['max'])}, against "
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


def _caption(fig):
    note = (fig["note"] or "").strip()
    if note and not note.endswith((".", "!", "?", ";")):
        note += "."
    clauses = [note]
    for style, window in fig.get("windows", {}).items():
        clauses.append(
            f"{window['label']} ({style}) covers {window['definition'].rstrip('.')}."
        )
    if fig.get("blank_cells"):
        clauses.append("Blank annual values: " + ", ".join(fig["blank_cells"]) + ".")
    clauses.extend(fig[key] for key in ("coverage_note", "scale_note") if key in fig)
    return " ".join(clause for clause in clauses if clause)


def render(
    figure,
    groups,
    *,
    xlabel,
    dashed_groups=(),
    partial_label="partial",
    previous=None,
    next_part=None,
    coordinate_decimals=2,
):
    """Render an overlay from selected, aligned annual row mappings."""
    if type(coordinate_decimals) is not int or coordinate_decimals < 0:
        raise ValueError("coordinate_decimals must be a nonnegative integer")
    labels = figure["labels"]
    series = [groups[k] for k in figure["groups"]]
    years = sorted(series[0])
    if any(set(s) != set(years) for s in series) or years != list(
        range(years[0], years[-1] + 1)
    ):
        raise ValueError("Figure series require a common complete calendar")
    partial = {
        year for cells in series for year, row in cells.items() if row["partial"]
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
    caption = figure.get("caption")
    if caption is None:
        caption = _caption(figure)
    notes = textwrap.wrap(caption, width=90)
    links = [
        (name, part)
        for name, part in (("Previous part", previous), ("Next part", next_part))
        if part
    ]
    height = bottom + 100 + 22 * (len(notes) + len(links))
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
        "Markers and thin lines show annual values. "
        "Thick, lighter lines show the 5 year trailing mean.",
    )
    colors = (
        [BAND_COLORS[name] for name in labels]
        if figure["series_by"] == "depth_band"
        else MEASURE_COLORS
    )
    styles = []
    for index, (name, group, (x, y)) in enumerate(
        zip(labels, figure["groups"], legend)
    ):
        color = colors[index]
        if (
            "windows" in figure
            and name == figure["windows"]["solid"]["label"]
            and group in dashed_groups
        ):
            raise ValueError(f"Solid window {name} conflicts with dashed_groups")
        dash = (
            {"stroke_dasharray": "9 6"}
            if group in dashed_groups
            or (figure["series_by"] == "measure" and len(labels) == 2 and index == 1)
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
        y = ypos(float(tick))
        element(root, "line", x1=left, x2=right, y1=y, y2=y, stroke="#cfd9de")
        label(root, left - 9, y + 5, format_number(tick), text_anchor="end")
    xticks = [
        years[0],
        *(yr for yr in years[1:-1] if yr % 5 == 0 and years[-1] - yr >= 2),
        years[-1],
    ]
    for yr in dict.fromkeys(xticks):
        label(
            root,
            xpos(yr),
            bottom + 27,
            format_number(yr, grouped=False),
            text_anchor="middle",
        )
    if partial:
        label(
            root,
            right,
            bottom + 48,
            partial_label,
            text_anchor="middle" if partial_label == "partial" else "end",
        )
    label(
        root,
        (left + right) / 2,
        bottom + 54,
        xlabel,
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
                vertex = f"{xpos(yr):.{coordinate_decimals}f},{ypos(value):.{coordinate_decimals}f}"
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
                cx=xpos(yr),
                cy=ypos(value),
                r=5,
                stroke=color,
                stroke_width=2,
                fill="white" if yr in partial else color,
                data_year=yr,
            )
            result = "unavailable" if mean is None else format_number(mean)
            when = format_number(yr, grouped=False) + (
                " (partial)" if yr in partial else ""
            )
            element(point, "title").text = (
                f"{name}, {when}. Annual value {format_number(value)}. Five year mean {result}."
            )
    for i, line in enumerate(notes):
        label(root, 22, bottom + 86 + i * 22, line)
    for i, (direction, (title, href)) in enumerate(links, start=len(notes)):
        if not href.strip() or urlsplit(href).scheme.lower() not in {
            "",
            "http",
            "https",
        }:
            raise ValueError("A part link needs a relative, HTTP or HTTPS destination")
        link = element(root, "a", href=href)
        label(
            link,
            22,
            bottom + 86 + i * 22,
            f"{direction}: {title}",
            fill="#245476",
            text_decoration="underline",
        )
    positions = {"x", "y", "x1", "y1", "x2", "y2", "cx", "cy"}
    for node in root.iter():
        for attr in positions.intersection(node.attrib):
            value = node.get(attr)
            if "." in value:
                node.set(attr, f"{float(value):.{coordinate_decimals}f}")
    return ET.tostring(root, encoding="unicode") + "\n"


def _empty_denominator_label(figure, row):
    label = figure.get("empty_denominator_label")
    denominator = row.get("denominator")
    if label and row["value"] is None and denominator not in (None, ""):
        if Decimal(str(denominator)).is_zero():
            return label
    return None


def interactive(figure, svg, groups, *, xlabel):
    """Embed the same points and static chart in an offline year selector."""
    data = [
        [
            (
                year,
                row["value"],
                row["moving_average"],
                row["partial"],
                row["availability"],
                (
                    format_number(row["value"])
                    if row["value"] is not None
                    else _empty_denominator_label(figure, row)
                ),
                (
                    format_number(row["moving_average"])
                    if row["moving_average"] is not None
                    else None
                ),
            )
            for year, row in sorted(groups[key].items())
        ]
        for key in figure["groups"]
    ]
    options = "".join(
        f'<option value="{year}">{format_number(year, grouped=False)}'
        f'{" (partial)" if partial else ""}</option>'
        for year, _, _, partial, *_ in data[0]
    )
    # A substitution pass keeps braces in source text literal. UNIT is inside a
    # single-quoted JavaScript string; the other text substitutions are HTML.
    unit = (
        json.dumps(figure["ylabel"])[1:-1]
        .replace("'", "\\u0027")
        .replace("<", "\\u003c")
    )
    substitutions = {
        "TITLE": escape(figure["title"]),
        "SVG": svg.rstrip(),
        "OPTIONS": options,
        "XLABEL": escape(xlabel),
        "UNIT": unit,
        "DATA": json.dumps(data, separators=(",", ":"), allow_nan=False).replace(
            "<", "\\u003c"
        ),
    }
    template = Path(__file__).with_name("chart.html").read_text(encoding="utf-8")
    return re.sub(r"{{([A-Z]+)}}", lambda m: substitutions[m[1]], template)


def _artifact(output, name):
    path = (output / name).resolve()
    if path.parent != output.resolve():
        raise ValueError(
            f"Chart artifact must be a file in the output directory: {name}"
        )
    return path


def write_manifest(output, figures):
    """Write a chart-standard JSON manifest referencing the adjacent artifacts."""
    _artifact(Path(output), "figures.json").write_text(
        json.dumps(figures, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _read_groups(rows):
    groups = defaultdict(dict)
    peaks = defaultdict(Decimal)
    for source in rows:
        row = dict(source)
        key, year = row["group"], int(str(row["year"]))
        if not 1 <= year <= 9999:
            raise ValueError(f"Invalid calendar year at {key}, {year}")
        if year in groups[key]:
            raise ValueError(f"Duplicate annual observation at {key}, {year}")
        partial = row.get("partial", 0)
        if partial not in (0, 1, "0", "1"):
            raise ValueError(f"Invalid partial year information at {key}, {year}")
        row["partial"] = partial in (1, "1")
        availability = row.setdefault("availability", "verified")
        if availability not in {"verified", "unavailable"}:
            raise ValueError(f"Unknown availability at {key}, {year}")
        for column in ("value", "moving_average"):
            raw = row[column]
            value = None if raw is None or raw == "" else float(raw)
            if isinstance(raw, float) and math.isnan(raw):
                value = None
            if value is not None:
                if (
                    not math.isfinite(value)
                    or value < 0
                    or availability == "unavailable"
                ):
                    raise ValueError(f"Invalid {column} at {key}, {year}")
                if row["partial"] and column == "moving_average":
                    raise ValueError(
                        f"Partial year has a moving average at {key}, {year}"
                    )
                # Retain the decimal boundary the checker reads from the CSV.
                peaks[key] = max(peaks[key], Decimal(str(raw)))
            row[column] = value
        groups[key][year] = row
    return groups, peaks


def _verify_trends(groups, selected):
    rows = (row for key in selected for row in groups[key].values())
    for row in with_trends(rows).itertuples(index=False):
        supplied = groups[row.group][row.year]["moving_average"]
        if supplied is None and math.isnan(row.moving_average):
            continue
        if supplied is None or not math.isclose(
            supplied, row.moving_average, rel_tol=1e-12
        ):
            raise ValueError(f"Inconsistent moving_average at {row.group}, {row.year}")


def _calendar(figure, groups):
    """Represent omitted years as unavailable cells for both output formats."""
    selected = {key: groups[key] for key in figure["groups"]}
    years = set().union(*(cells.keys() for cells in selected.values()))
    partial = {
        year
        for cells in selected.values()
        for year, row in cells.items()
        if row["partial"]
    }
    if partial and partial != {max(years)}:
        raise ValueError("Only the final calendar year may be partial")
    blank = {"value": None, "moving_average": None, "availability": "unavailable"}
    result = {}
    for key, cells in selected.items():
        result[key] = {
            year: cells.get(year, dict(blank, partial=year in partial))
            for year in range(min(years), max(years) + 1)
        }
        if any(cells[yr]["partial"] != (yr in partial) for yr in cells):
            raise ValueError("Overlaid series must agree on the partial year")
    return result


def _describe_coverage(fig, cells, labels):
    """Name selected blank observations and distinguish known empty populations."""
    blank_cells = []
    missing = empty = 0
    for key, label in zip(fig["groups"], labels):
        for year, row in cells[key].items():
            if row["value"] is None:
                blank_cells.append(f"{format_number(year, grouped=False)} {label}")
                if _empty_denominator_label(fig, row):
                    empty += 1
                elif row["availability"] == "unavailable":
                    missing += 1
    fig["blank_cells"] = blank_cells
    fig.pop("coverage_note", None)
    fig.pop("unavailable_cells", None)
    if missing or empty:
        clauses = []
        if empty:
            clauses.append(
                f"A zero denominator leaves {format_number(empty)} annual values blank."
            )
        if missing:
            clauses.append(
                f"Source records are unavailable for {format_number(missing)} "
                "annual series observations."
            )
        clauses.append("The chart omits those points and any mean requiring them.")
        if "interactive" in fig:
            clauses.append("The interactive year table identifies the affected series.")
        fig["unavailable_cells"] = missing + empty
        fig["coverage_note"] = " ".join(clauses)
    fig["caption"] = _caption(fig)


def _appendix_svg(fig, cells, groups, xlabel):
    rows = []
    labels = []
    for key, label in zip(fig["groups"], fig["labels"]):
        bands = {row["band"] for row in groups[key].values()}
        if len(bands) != 1:
            raise ValueError(f"Appendix series {key} must identify one depth band")
        (band,) = bands
        labels.append(f"{label} ({band})")
        rows.extend(
            dict(row, year=year, group=label, band=band, partial_year=row["partial"])
            for year, row in cells[key].items()
        )
    _describe_coverage(fig, cells, labels)
    axis = fig["y_scale"]
    step = Decimal(str(axis["step"]))
    ticks = [float(i * step) for i in range(round(axis["max"] / axis["step"]) + 1)]
    return render_depth_panels(
        rows,
        title=fig["title"],
        ylabel=fig["ylabel"],
        xlabel=xlabel,
        note=fig["caption"],
        y_scale=ticks,
    )


def write_figures(
    output,
    figures,
    rows=None,
    *,
    xlabel,
    dashed_groups=(),
    partial_label="partial",
    previous=None,
    next_part=None,
    coordinate_decimals=2,
):
    """Write each SVG/page pair and their manifest from one annual table.

    Pass row mappings to write their CSV, or omit rows to read the existing CSV
    declared by the figures. Each part link is a (title, href) pair.
    """
    output = Path(output)
    figures = [dict(fig) for fig in figures]
    csv_names = {fig["csv"] for fig in figures}
    if len(csv_names) != 1:
        raise ValueError("A figure set requires one annual CSV")
    csv_path = _artifact(output, csv_names.pop())
    paths = []
    for fig in figures:
        paths.append(_artifact(output, fig["svg"]))
        if fig.get("layout") == "4x1_shared_x":
            if (
                fig.get("role") != "appendix"
                or fig.get("panel_by") != "depth_band"
                or "interactive" in fig
            ):
                raise ValueError(
                    "Depth panels require a static depth-band appendix figure"
                )
        else:
            paths.append(_artifact(output, fig["interactive"]))
    if (
        len(set([*paths, csv_path, _artifact(output, "figures.json")]))
        != len(paths) + 2
    ):
        raise ValueError("Chart output names must be distinct")
    if rows is None:
        with csv_path.open(encoding="utf-8", newline="") as stream:
            groups, peaks = _read_groups(csv.DictReader(stream))
    else:
        rows = list(rows)
        groups, peaks = _read_groups(rows)
    expected = {key for fig in figures for key in fig["groups"]}
    if missing := expected.difference(groups):
        raise ValueError(f"Missing annual chart series: {sorted(missing)}")
    _verify_trends(groups, expected)
    assign_scales(figures, peaks)
    dashed_groups = set(dashed_groups)
    artifacts = {}
    for fig in figures:
        cells = _calendar(fig, groups)
        axis_label = fig.get("xlabel", xlabel)
        if fig.get("layout") == "4x1_shared_x":
            artifacts[fig["svg"]] = _appendix_svg(fig, cells, groups, axis_label)
            continue
        _describe_coverage(fig, cells, fig["labels"])
        svg = render(
            fig,
            cells,
            xlabel=axis_label,
            dashed_groups=dashed_groups,
            partial_label=partial_label,
            previous=previous,
            next_part=next_part,
            coordinate_decimals=coordinate_decimals,
        )
        artifacts[fig["svg"]] = svg
        artifacts[fig["interactive"]] = interactive(fig, svg, cells, xlabel=axis_label)
    output.mkdir(parents=True, exist_ok=True)
    if rows is not None:
        fields = dict.fromkeys(key for row in rows for key in row)
        with csv_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                record = dict(row)
                cell = groups[row["group"]][int(row["year"])]
                if "partial" in fields:
                    record["partial"] = int(cell["partial"])
                if "availability" in fields:
                    record["availability"] = cell["availability"]
                for col in ("value", "moving_average"):
                    if cell[col] is None:
                        record[col] = None
                writer.writerow(record)
    for name, content in artifacts.items():
        _artifact(output, name).write_text(content, encoding="utf-8", newline="\n")
    write_manifest(output, figures)
