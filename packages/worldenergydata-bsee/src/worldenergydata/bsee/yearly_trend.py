"""Yearly values and five year trailing means for the BSEE well series."""

from __future__ import annotations

import math
import textwrap
import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal
from xml.etree import ElementTree as ET

from .half_decade import _COLORS, _FONT, BANDS

_COLOUR = dict(zip(BANDS, _COLORS))
_BAND_LABEL = {b.lower().replace(",", ""): b for b in BANDS}

# Named series use blue, vermilion, green and purple in caller order.
# Each moving average mixes its yearly colour with 42 percent white.
_SERIES_COLOURS = ("#0072b2", "#d55e00", "#009e73", "#663399")

ARTICLE_WIDTH_PX = 860
_VIEWBOX_WIDTH = 960


def _article_units(css_px):
    """Round a size in rendered CSS pixels up to SVG units at article width."""
    return math.ceil(css_px * _VIEWBOX_WIDTH / ARTICLE_WIDTH_PX)


_YEARLY_WIDTH = _article_units(2)
_AVERAGE_WIDTH = _article_units(4)
_MARKER_RADIUS = _article_units(9) / 2


def _series_palette(names):
    if names is None:
        return None
    if isinstance(names, str) or not isinstance(names, Sequence):
        raise ValueError("supply an ordered list of series names")
    if len(names) > len(_SERIES_COLOURS):
        raise ValueError(
            "chart-standard.md item 6 allows at most 4 named series per panel"
        )
    if not names or any(
        not isinstance(name, str) or not name.strip() for name in names
    ):
        raise ValueError("supply nonempty series names")
    if len(set(names)) != len(names):
        raise ValueError("supply distinct series names")
    return dict(zip(names, _SERIES_COLOURS))


def _grouped_rows(rows, palette, *, normalize_depth=False):
    """Identify series and keep a named panel within a single input population."""
    bands = set()
    for row in rows:
        group = row.get("group", "")
        if palette is None:
            band = row["band"]
            if normalize_depth:
                band = _BAND_LABEL.get(band.lower().replace(",", ""))
                if band is None:
                    raise ValueError(f"unknown water depth band: {row['band']}")
        else:
            if group not in palette:
                raise ValueError(f"unknown named series: {group}")
            band = row.get("band", "")
            bands.add(band)
            if len(bands) > 1:
                raise ValueError("named series must share one band")
        yield group, band, row


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


def with_trend(rows, *, is_count=False, partial_year=None, series_names=None):
    """Complete the calendar for each group and band, retaining source counts.

    With ordered series_names, group holds the series name and band may be
    omitted or carry one common population label. Supply preaggregated totals
    when a series spans several depth bands.
    """
    palette = _series_palette(series_names)
    series = defaultdict(dict)
    years = set()
    for group, band, row in _grouped_rows(rows, palette, normalize_depth=True):
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
    keys = list(series)
    if palette is not None:
        keys.sort(key=lambda key: series_names.index(key[0]))
    for group, band in keys:
        cells = series[group, band]
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
    size = _article_units(size)
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


def _marker(parent, x, y, colour, *, partial=False):
    _element(
        parent,
        "circle",
        cx=x,
        cy=y,
        r=_MARKER_RADIUS,
        stroke=colour,
        stroke_width=_YEARLY_WIDTH,
        fill="white" if partial else colour,
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


def _nice(value):
    """A nonzero decimal tick or bound with one significant digit: 1, 2 or 5."""
    return value > 0 and value.scaleb(-value.adjusted()) in (1, 2, 5)


def _depth_ticks(low, high):
    if low == high == 0:
        high = Decimal(1)
    unit = Decimal(1).scaleb((high - low).adjusted())
    candidates = []
    # Consider zero-aligned axes with three to five intervals. Prefer the
    # lowest covering top, then the shortest span, then the finer tick step.
    for factor in ("0.1", "0.2", "0.5", "1", "2", "5", "10"):
        step = Decimal(factor) * unit
        first = math.floor(low / step)
        for last in range(math.ceil(high / step), first + 6):
            start = min(first, last - 3) if low < 0 else first
            top = last * step
            if 3 <= last - start <= 5 and (top == 0 or _nice(top)):
                candidates.append((top, (last - start) * step, step, start, last))
    _, _, step, start, last = min(candidates)
    return tuple(float(i * step) for i in range(start, last + 1))


def _depth_range(rows):
    low, peak = Decimal(0), None
    for row in rows:
        for key in ("value", "moving_average"):
            if row[key] in (None, ""):
                continue
            value = Decimal(str(row[key]))
            if not value.is_finite():
                raise ValueError("expected finite depth-panel values")
            low = min(low, value)
            peak = value if peak is None else max(peak, value)
    return low, peak


def depth_y_scale(rows):
    """Return shared tick values covering every yearly value and moving average."""
    low, peak = _depth_range(rows)
    return _depth_ticks(low, max(Decimal(0), peak or 0))


def shared_depth_y_scales(figures):
    """Map qualifying figure keys to pooled ticks when at least two can share."""
    ranges = {key: _depth_range(rows) for key, rows in figures.items()}
    peaks = {key: peak for key, (_, peak) in ranges.items() if peak is not None}
    if len(peaks) < 2:
        return {}
    low = min(low for low, _ in ranges.values())
    ticks = _depth_ticks(low, max(Decimal(0), max(peaks.values())))
    threshold = Decimal("0.3") * Decimal(str(ticks[-1]))
    shared = {key: ticks for key, peak in peaks.items() if peak >= threshold}
    return shared if len(shared) >= 2 else {}


def _check_depth_scale(ticks):
    if not 4 <= len(ticks) <= 6 or not all(math.isfinite(v) for v in ticks):
        raise ValueError("expected four to six finite y ticks")
    values = [Decimal(str(tick)) for tick in ticks]
    step = values[1] - values[0]
    if (
        0 not in values
        or not _nice(step)
        or (values[-1] != 0 and not _nice(values[-1]))
        or any(right - left != step for left, right in zip(values, values[1:]))
    ):
        raise ValueError("expected evenly spaced nice y ticks including zero")


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
            stroke_width=_AVERAGE_WIDTH if kind == "average" else _YEARLY_WIDTH,
            stroke_linecap="round",
            **{"class": kind},
            **dashed,
        )


def _panel(
    root,
    left,
    top,
    label,
    label_colour,
    data,
    years,
    partial_year,
    tick_years,
    *,
    y_ticks=None,
    show_year_labels=True,
    width=830,
    height=122,
):
    panel = _element(root, "g", **{"class": "panel"})
    if label:
        _text(panel, left, top, label, 17, font_weight="bold", fill=label_colour)
    top += 17
    first, last = years[0], years[-1]
    ticks = (
        y_ticks
        if y_ticks is not None
        else _ticks(
            [
                v
                for series, _, _ in data
                for value, mean in series.values()
                for v in (value, mean)
                if v is not None
            ]
        )
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
    if show_year_labels:
        for year in tick_years:
            _text(
                panel,
                x_of(year),
                top + height + 24,
                str(year),
                15,
                text_anchor="middle",
            )
        if partial_year is not None:
            _text(
                panel,
                x_of(partial_year),
                top + height + 43,
                "partial",
                15,
                text_anchor="middle",
            )
    for col, kind in [(1, "average"), (0, "yearly")]:
        for series, colour, dashed in data:
            stroke = _tint(colour) if kind == "average" else colour
            points = []
            for year, pair in sorted(series.items()):
                value = pair[col]
                points.append(
                    (year, None if value is None else (x_of(year), y_of(value)))
                )
            _path(panel, points, kind, stroke, dashed)
    for series, colour, _ in data:
        for year, (value, _) in sorted(series.items()):
            if value is not None:
                _marker(
                    panel,
                    f"{x_of(year):.2f}",
                    f"{y_of(value):.2f}",
                    colour,
                    partial=year == partial_year,
                )


def _band_panels(root, ylabel, measures, cells, years, partial_year, ticks, y_ticks):
    _line(root, 34, 60, 68, 60, _COLORS[2], _YEARLY_WIDTH)
    _marker(root, 51, 60, _COLORS[2])
    _text(root, 80, 66, "Yearly value")
    _line(root, 220, 60, 258, 60, _tint(_COLORS[2]), _AVERAGE_WIDTH)
    _text(root, 270, 66, "5 year trailing moving average")
    _text(root, 32, 99, ylabel, 17, font_weight="bold")
    if len(measures) > 2:
        raise ValueError(
            "split depth figures with more than two measures (four lines per panel)"
        )
    x, y = 40, 126
    for idx, group in enumerate(measures):
        if group:
            style = {"stroke_dasharray": "8 6"} if idx else {}
            _line(root, x, y - 5, x + 42, y - 5, "#334b5c", _YEARLY_WIDTH, **style)
            _text(root, x + 52, y, group, 16)
            x += 90 + len(group) * 10
    if any(measures):
        y += 31
    for i, band in enumerate(BANDS):
        data = [
            (
                cells.get((g, band), {}),
                _COLOUR[band],
                {"stroke_dasharray": "8 6"} if idx else {},
            )
            for idx, g in enumerate(measures)
        ]
        _panel(
            root,
            82,
            y,
            band,
            _COLOUR[band],
            data,
            years,
            partial_year,
            ticks,
            y_ticks=y_ticks,
            show_year_labels=i == len(BANDS) - 1,
        )
        y += 181
    # The shared year ticks and partial-year annotation sit below the bottom row.
    return y + 43


def _named_panel(root, ylabel, panel_title, palette, cells, years, partial_year, ticks):
    _text(root, 32, 66, "Series")
    _text(root, 510, 66, "Yearly value")
    _text(root, 650, 66, "5 year trailing moving average")
    y = 92
    by_name = {name: series for (name, _), series in cells.items()}
    data = []
    for name, colour in palette.items():
        entry = _element(root, "g")
        _line(entry, 512, y - 5, 552, y - 5, colour, _YEARLY_WIDTH)
        _marker(entry, 532, y - 5, colour)
        _line(entry, 652, y - 5, 692, y - 5, _tint(colour), _AVERAGE_WIDTH)
        for line in textwrap.wrap(name, 38):
            _text(entry, 32, y, line)
            y += 24
        data.append((by_name.get(name, {}), colour, {}))
    _text(root, 32, y + 6, ylabel, 17, font_weight="bold")
    top = y + 33
    _panel(
        root,
        82,
        top,
        panel_title,
        "#183143",
        data,
        years,
        partial_year,
        ticks,
        width=830,
        height=240,
    )
    return top + 336


def render_svg(
    rows,
    *,
    title,
    ylabel,
    xlabel,
    note="",
    series_names=None,
    panel_title=None,
    y_scale=None,
):
    """Render with_trend rows or their CSV readback, preserving measure order.

    The four depth bands form one column with up to two measures per band.
    They share a year axis and one vertical scale. Pass the ticks returned by
    shared_depth_y_scales for qualifying figures of the same measure.
    Set series_names to draw the named groups in order on one panel, with an
    optional panel_title. The note appears below the horizontal axis label.
    """
    if not all(t.strip() for t in (title, xlabel, ylabel)):
        raise ValueError("supply a title and axis labels with units")
    palette = _series_palette(series_names)
    if panel_title is not None and palette is None:
        raise ValueError("panel_title requires named series")
    if palette is None:
        if y_scale is None:
            rows = list(rows)
            y_scale = depth_y_scale(rows)
        else:
            _check_depth_scale(y_scale)
    elif y_scale is not None:
        raise ValueError("y_scale is for depth-band panels")
    cells = defaultdict(dict)
    partial = set()
    groups = {}
    years = set()
    for group, band, row in _grouped_rows(rows, palette):
        year = int(row["year"])
        if (palette is None and band not in BANDS) or year in cells[group, band]:
            raise ValueError("unknown depth band or duplicate yearly cell")
        groups[group] = None
        years.add(year)
        if row["partial_year"] in (True, "True"):
            partial.add(year)
        pair = tuple(
            None if row[k] in ("", None) else float(row[k])
            for k in ("value", "moving_average")
        )
        if y_scale is not None and any(
            v is not None and not y_scale[0] <= v <= y_scale[-1] for v in pair
        ):
            raise ValueError("y scale must cover every yearly value and moving average")
        cells[group, band][year] = pair
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
    if palette is None:
        y = _band_panels(
            root, ylabel, list(groups), cells, years, partial_year, ticks, y_scale
        )
    else:
        y = _named_panel(
            root, ylabel, panel_title, palette, cells, years, partial_year, ticks
        )
    _text(
        root,
        _VIEWBOX_WIDTH / 2,
        y - 7,
        xlabel,
        17,
        text_anchor="middle",
        font_weight="bold",
    )
    for line in textwrap.wrap(note, 103, break_long_words=False):
        y += 23
        _text(root, 32, y, line, 15)
    height = y + 20
    root.set("width", str(_VIEWBOX_WIDTH))
    root.set("height", str(height))
    root.set("viewBox", f"0 0 {_VIEWBOX_WIDTH} {height}")
    ET.indent(root)
    return ET.tostring(root, encoding="unicode") + "\n"
