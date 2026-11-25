"""Yearly values and five year trailing means for the BSEE well series."""

from __future__ import annotations

import math
import textwrap
import unicodedata
from collections import defaultdict
from decimal import Decimal
from xml.etree import ElementTree as ET

from .half_decade import _COLORS, _FONT, BANDS

_COLOUR = dict(zip(BANDS, _COLORS))
_BAND_LABEL = {b.lower().replace(",", ""): b for b in BANDS}


def trailing_average(values, *, is_count=False, partial_year=None):
    """Map each calendar year to the mean of its five complete yearly values.

    Only absent count years inside the observation window are zero. An explicit
    None represents an unknown observation, including a rate with no exposure.
    """
    if not values:
        return {}
    first, last = min(values), max(values)
    if partial_year is not None and partial_year != last:
        raise ValueError("only the final year can be partial")
    default = 0 if is_count else None
    result = {}
    for year in range(first, last + 1):
        result[year] = None
        if year < first + 4 or year == partial_year:
            continue
        window = [values.get(y, default) for y in range(year - 4, year + 1)]
        if None not in window:
            result[year] = math.fsum(window) / 5
    return result


def with_trend(rows, *, is_count=False, partial_year=None):
    """Complete the calendar for each group and band, retaining source counts."""
    series = defaultdict(dict)
    years = set()
    for row in rows:
        band = _BAND_LABEL.get(row["band"].lower().replace(",", ""))
        if band is None:
            raise ValueError(f"unknown water depth band: {row['band']}")
        group = row.get("group", "")
        year = int(row["year"])
        if str(year) != str(row["year"]):
            raise ValueError("expected an integral calendar year")
        value = row["value"]
        if value not in (None, "") and not math.isfinite(float(value)):
            raise ValueError("expected a finite yearly value")
        cells = series[group, band]
        if year in cells:
            raise ValueError(f"duplicate observation for {group}, {band}, {year}")
        cells[year] = row
        years.add(year)
    if not years:
        return []
    calendar = range(min(years), max(years) + 1)
    result = []
    for (group, band), cells in series.items():
        values = {}
        for y in calendar:
            v = cells[y]["value"] if y in cells else (0 if is_count else None)
            value = float(v) if v not in (None, "") else None
            if is_count and value is not None:
                if not value.is_integer() or value < 0:
                    raise ValueError("expected a nonnegative integer count")
                value = int(value)
            values[y] = value
        means = trailing_average(values, is_count=is_count, partial_year=partial_year)
        for y in calendar:
            result.append(
                dict(
                    cells.get(y, {}),
                    group=group,
                    band=band,
                    year=y,
                    value=values[y],
                    moving_average=means[y],
                    partial_year=y == partial_year,
                )
            )
    return result


def _element(parent, tag, **attrs):
    return ET.SubElement(
        parent, tag, {k.replace("_", "-"): str(v) for k, v in attrs.items()}
    )


def _text(parent, x, y, words, size=16, **attrs):
    if any(unicodedata.category(c) == "Pd" or c == "\u2212" for c in words):
        raise ValueError("use chart text without dashes")
    _element(parent, "text", x=x, y=y, font_size=size, **attrs).text = words


def _line(parent, x1, y1, x2, y2, colour, width, **attrs):
    _element(
        parent,
        "line",
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        stroke=colour,
        stroke_width=width,
        **attrs,
    )


def _tint(colour):
    channels = [int(colour[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(v + 0.42*(255-v)):02x}" for v in channels)


def _ticks(values):
    low, high = min([0, *values]), max([0, *values])
    target = (high - low or 1) / 3
    scale = 10 ** math.floor(math.log10(target))
    step = next(s * scale for s in (1, 2, 2.5, 5, 10) if s * scale >= target)
    return [
        n * step
        for n in range(math.floor(low / step), max(1, math.ceil(high / step)) + 1)
    ]


def _path(panel, points, kind, colour, dashed):
    commands = []
    previous = None
    for year, point in points:
        if point is None:
            continue
        x, y = point
        # The zero length segment shows an isolated valid mean with a round cap.
        if previous != year - 1:
            commands.append(f"M{x:.2f},{y:.2f} l0,0")
        else:
            commands.append(f"L{x:.2f},{y:.2f}")
        previous = year
    if commands:
        _element(
            panel,
            "path",
            d=" ".join(commands),
            fill="none",
            stroke=colour,
            stroke_width=4.5 if kind == "average" else 2,
            stroke_linecap="round",
            **{"class": kind},
            **dashed,
        )


def _panel(root, left, top, band, groups, cells, years, partial_year, tick_years):
    panel = _element(root, "g", **{"class": "panel"})
    colour = _COLOUR[band]
    _text(panel, left, top, band, 17, font_weight="bold", fill=colour)
    top += 17
    width, height = 352, 122
    first, last = years[0], years[-1]
    data = [cells.get((group, band), {}) for group in groups]
    ticks = _ticks(
        [
            v
            for series in data
            for value, mean in series.values()
            for v in (value, mean)
            if v is not None
        ]
    )

    def y_of(value):
        return top + height * (ticks[-1] - value) / (ticks[-1] - ticks[0])

    def x_of(year):
        return left + (
            width * (year - first) / (last - first) if last > first else width / 2
        )

    for tick in ticks:
        y = y_of(tick)
        _line(panel, left, y, left + width, y, "#d9e0e6", 2)
        number = Decimal(f"{abs(tick):.8g}").normalize()
        word = f"{number:,f}" if tick >= 0 else f"({number:,f})"
        _text(panel, left - 11, y + 5, word, 15, text_anchor="end")
    for year in tick_years:
        _text(panel, x_of(year), top + height + 24, str(year), 15, text_anchor="middle")
    if partial_year is not None:
        _text(
            panel,
            x_of(partial_year),
            top + height + 43,
            "partial",
            15,
            text_anchor="middle",
        )
    for col, kind, stroke in [(1, "average", _tint(colour)), (0, "yearly", colour)]:
        for idx, series in enumerate(data):
            points = []
            for year, pair in sorted(series.items()):
                value = pair[col]
                points.append(
                    (year, None if value is None else (x_of(year), y_of(value)))
                )
            dashed = {"stroke_dasharray": "8 6"} if idx else {}
            _path(panel, points, kind, stroke, dashed)
    for series in data:
        for year, (value, _) in sorted(series.items()):
            if value is not None:
                _element(
                    panel,
                    "circle",
                    cx=f"{x_of(year):.2f}",
                    cy=f"{y_of(value):.2f}",
                    r=4.5,
                    stroke=colour,
                    stroke_width=2,
                    fill="white" if year == partial_year else colour,
                )


def render_svg(rows, *, title, ylabel, xlabel, note=""):
    """Render with_trend rows or their CSV readback, preserving measure order.

    Each panel covers one water depth and up to two measures. All panels share
    calendar coordinates. Their labelled vertical scales fit the local values.
    """
    if not all(t.strip() for t in (title, xlabel, ylabel)):
        raise ValueError("supply a title and axis labels with units")
    cells = defaultdict(dict)
    partial = set()
    groups = {}
    years = set()
    for row in rows:
        group, band, year = row.get("group", ""), row["band"], int(row["year"])
        if band not in BANDS or year in cells[group, band]:
            raise ValueError("unknown depth band or duplicate yearly cell")
        groups[group] = None
        years.add(year)
        if row["partial_year"] in (True, "True"):
            partial.add(year)
        cells[group, band][year] = tuple(
            None if row[k] in ("", None) else float(row[k])
            for k in ("value", "moving_average")
        )
    if not years or (partial and partial != {max(years)}):
        raise ValueError("expected calendar data with at most one partial final year")
    years = sorted(years)
    partial_year = next(iter(partial), None)
    span = years[-1] - years[0]
    step = (
        max(1, 5 * math.ceil(span / 30)) if span > 10 else max(1, math.ceil(span / 4))
    )
    ticks = [
        years[0],
        *(
            y
            for y in range(years[0] + 1, years[-1])
            if y % step == 0 and min(y - years[0], years[-1] - y) >= max(1, span / 7)
        ),
    ]
    if span:
        ticks.append(years[-1])
    root = ET.Element(
        "svg",
        xmlns="http://www.w3.org/2000/svg",
        role="img",
        **{"aria-label": title, "font-family": _FONT, "fill": "#183143"},
    )
    ET.SubElement(root, "title").text = title
    _element(root, "rect", width="100%", height="100%", fill="white")
    _text(root, 32, 32, title, 22, font_weight="bold")
    _line(root, 34, 60, 68, 60, _COLORS[2], 2)
    _element(root, "circle", cx=51, cy=60, r=4.5, fill=_COLORS[2])
    _text(root, 80, 66, "Yearly value")
    _line(root, 220, 60, 258, 60, _tint(_COLORS[2]), 4.5)
    _text(root, 270, 66, "5 year trailing moving average")
    _text(root, 32, 99, ylabel, 17, font_weight="bold")
    measures = list(groups)
    # A third measure begins a separate comparison, keeping the last pair together.
    sections = [measures[:1]] if len(measures) % 2 else []
    offset = len(measures) % 2
    sections += [measures[i : i + 2] for i in range(offset, len(measures), 2)]
    y = 126
    for section in sections:
        x = 40
        for idx, group in enumerate(section):
            if group:
                style = {"stroke_dasharray": "8 6"} if idx else {}
                _line(root, x, y - 5, x + 42, y - 5, "#334b5c", 2, **style)
                _text(root, x + 52, y, group, 16)
                x += 90 + len(group) * 10
        if any(section):
            y += 31
        bands = [b for b in BANDS if any((g, b) in cells for g in section)]
        for i, band in enumerate(bands):
            _panel(
                root,
                82 + (i % 2) * 463,
                y + (i // 2) * 218,
                band,
                section,
                cells,
                years,
                partial_year,
                ticks,
            )
        y += math.ceil(len(bands) / 2) * 218
    _text(root, 480, y - 7, xlabel, 17, text_anchor="middle", font_weight="bold")
    for line in textwrap.wrap(note, 103, break_long_words=False):
        y += 23
        _text(root, 32, y, line, 15)
    height = y + 20
    root.set("width", "960")
    root.set("height", str(height))
    root.set("viewBox", f"0 0 960 {height}")
    ET.indent(root)
    return ET.tostring(root, encoding="unicode") + "\n"
