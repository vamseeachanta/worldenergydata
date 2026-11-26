"""Half decade charts for the BSEE well series, 2005 through partial 2026."""

from __future__ import annotations

import math
import textwrap
import unicodedata
from bisect import bisect_right
from collections import defaultdict
from decimal import Decimal
from xml.etree import ElementTree as ET

BANDS = ("Under 100 m", "100 to 500 m", "500 to 1,500 m", "1,500 m and deeper")
_INTERVALS = ((2005, 2009), (2010, 2014), (2015, 2019), (2020, 2024), (2025, 2026))
PERIODS = tuple(
    f"{start} to {end}" + (" (partial)" if end == 2026 else "")
    for start, end in _INTERVALS
)
_BAND_NAMES = {name.lower().replace(",", ""): name for name in BANDS}
_COLORS = ("#6588a6", "#427298", "#245476", "#102e46")
_DASHES = ("none", "5.5 2.4", "9.6 2.4 1.5 2.4", "1.5 2.4")
_FONT = "'DejaVu Sans','Segoe UI',Arial,sans-serif"


def _number(value, name):
    try:
        n = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"expected a finite nonnegative {name}") from None
    if not math.isfinite(n) or n < 0:
        raise ValueError(f"expected a finite nonnegative {name}")
    if isinstance(value, int):
        return value
    return int(n) if n.is_integer() else n


def depth_band(metres):
    """Assign a metric water depth to a band with an inclusive lower bound."""
    return BANDS[bisect_right((100, 500, 1500), _number(metres, "depth"))]


def summarize(rows, mode="count"):
    """Reduce additive observations into a complete group, period and band grid.

    Supply mappings with year, band, count (or value), and optional group.
    Absent counts within the supplied observation window mean zero events.
    per_year divides by five or two nominal calendar years. per_well requires
    additive exposure on every input row and divides the pooled numerator by
    pooled exposure. A zero denominator produces None, written as an empty
    field by csv.DictWriter. Records outside 2005 through 2026 are excluded.
    """
    if mode not in ("count", "per_year", "per_well"):
        raise ValueError(f"unknown aggregation mode: {mode}")
    counts, exposures = defaultdict(int), defaultdict(int)
    groups = {}
    for row in rows:
        year = _number(row["year"], "year")
        if not isinstance(year, int):
            raise ValueError("expected an integral year")
        if year < 2005 or year > 2026:
            continue
        band = _BAND_NAMES.get(str(row["band"]).lower().replace(",", ""))
        if band is None:
            raise ValueError(f"unrecognised depth band: {row['band']}")
        group = row.get("group", "")
        groups[group] = None
        key = (group, (year - 2005) // 5, band)
        counts[key] += _number(row.get("count", row.get("value")), "count or value")
        if mode == "per_well":
            exposures[key] += _number(row.get("exposure"), "exposure")

    result = []
    for group in groups or [""]:
        for i, (start, end) in enumerate(_INTERVALS):
            years = end - start + 1
            for band in BANDS:
                key = (group, i, band)
                count = counts[key]
                exposure = exposures[key] if mode == "per_well" else ""
                value = count
                if mode == "per_year":
                    value = count / years
                elif mode == "per_well":
                    value = count / exposure if exposure else None
                result.append(
                    dict(
                        period=PERIODS[i],
                        years=years,
                        band=band,
                        group=group,
                        count=count,
                        exposure=exposure,
                        value=value,
                    )
                )
    return result


def _add(parent, tag, **attrs):
    positions = {"x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "width", "height"}
    return ET.SubElement(
        parent,
        tag,
        {
            key: f"{value:.2f}" if key in positions else str(value)
            for key, value in attrs.items()
        },
    )


def _label(parent, x, y, words, size=11, anchor="middle", **attrs):
    if any(unicodedata.category(c) == "Pd" or c == "\u2212" for c in words):
        raise ValueError(f"chart labels must use words without dashes: {words}")
    _add(
        parent, "text", x=x, y=y, **{"font-size": size, "text-anchor": anchor}, **attrs
    ).text = words


def _line(parent, x1, y1, x2, y2, color, width=0.8, dashes="none"):
    _add(
        parent,
        "line",
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        stroke=color,
        **{"stroke-width": width, "stroke-dasharray": dashes},
    )


def _marker(parent, band, x, y, size):
    style = {"stroke": "#333333", "stroke-width": 0.5, "fill": _COLORS[band]}
    if band == 0:
        _add(parent, "circle", cx=x, cy=y, r=size, **style)
    elif band == 1:
        _add(
            parent,
            "rect",
            x=x - size,
            y=y - size,
            width=2 * size,
            height=2 * size,
            **style,
        )
    else:
        offsets = (
            [(0, -1), (1, 1), (-1, 1)]
            if band == 2
            else [(0, -1.3), (1.3, 0), (0, 1.3), (-1.3, 0)]
        )
        points = " ".join(f"{x + dx*size:.2f},{y + dy*size:.2f}" for dx, dy in offsets)
        _add(parent, "polygon", points=points, **style)


def _ticks(maximum):
    # Choose about five grid intervals, in units of 1, 2, 2.5, 5 or 10.
    ceiling = maximum or 1
    target = ceiling / 5
    scale = 10 ** math.floor(math.log10(target))
    step = next(s * scale for s in (1, 2, 2.5, 5, 10) if s * scale >= target)
    return [n * step for n in range(math.ceil(ceiling / step) + 1)]


def render_svg(
    rows,
    *,
    ylabel,
    xlabel="Approval period",
    note="",
    periods=PERIODS,
    panel_ylabels=None,
):
    """Draw a summarized table (or its CSV readback) using C6 line styles.

    Units belong in ylabel, or in panel_ylabels for mixed units. Select periods
    to plot a shorter observation window. The optional note states the cutoff and rate
    basis. Each panel has a zero based scale. The geometry has no generated IDs or
    timestamps, so output does not depend on a backend hash salt or clock.
    """
    if not ylabel.strip():
        raise ValueError("the y axis requires a quantity and units")
    periods = tuple(periods)
    if not periods or periods != tuple(p for p in PERIODS if p in periods):
        raise ValueError("expected distinct series periods in chronological order")
    panels = {}
    for row in rows:
        values = panels.setdefault(row["group"], {})
        key = row["band"], row["period"]
        if key in values or key[0] not in BANDS or key[1] not in periods:
            raise ValueError(f"invalid or duplicate chart cell: {key}")
        raw = row["value"]
        values[key] = None if raw in (None, "") else _number(raw, "plotted value")
    if not panels or any(
        len(panel) != len(BANDS) * len(periods) for panel in panels.values()
    ):
        raise ValueError("expected a complete period and depth grid for each panel")

    if panel_ylabels is not None and (
        set(panel_ylabels) != set(panels)
        or not all(v.strip() for v in panel_ylabels.values())
    ):
        raise ValueError("each panel requires a y axis label with units")
    notes = [
        line for para in note.splitlines() for line in textwrap.wrap(para, width=130)
    ]
    panel_step, plot_height = 206, 164
    left, right = 78, 838
    slot = 152 if periods == PERIODS else (right - left) / len(periods)
    height = 72 + panel_step * len(panels) + len(notes) * 13
    title = f"{ylabel} by water depth and period"
    group_names = ", ".join(group for group in panels if group)
    if group_names:
        title += f" ({group_names})"
    root = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": f"0.00 0.00 864.00 {height:.2f}",
            "width": "960.00",
            "height": f"{round(height * 960 / 864):.2f}",
            "role": "img",
            "aria-label": title,
            "font-family": _FONT,
        },
    )
    _add(root, "title").text = title
    _add(root, "rect", width=864, height=height, fill="white")
    # Fixed geometry in points matches the 12 inch wide C6 reference.
    widths = [40 + len(name) * 4.8 for name in BANDS]
    x = (864 - sum(widths)) / 2
    for b, (name, width) in enumerate(zip(BANDS, widths)):
        _line(root, x, 17, x + 20, 17, _COLORS[b], 1.5, _DASHES[b])
        _marker(root, b, x + 10, 17, 2)
        _label(root, x + 24, 20, name, 9, "start")
        x += width

    for idx, (group, values) in enumerate(panels.items()):
        ticks = _ticks(max((v for v in values.values() if v is not None), default=0))
        top = 54 + idx * panel_step
        bottom, middle = top + plot_height, top + plot_height / 2
        if group:
            _label(root, left, top - 8, group, 13, "start")
        if PERIODS[-1] in periods:
            _add(
                root,
                "rect",
                x=right - slot,
                y=top,
                width=slot,
                height=plot_height,
                fill="#f0f0f0",
            )
        for tick in ticks:
            y = round(bottom - plot_height * tick / ticks[-1], 2)
            _line(root, left, y, right, y, "#dddddd", 0.6)
            _line(root, left - 3.5, y, left, y, "black")
            _label(
                root,
                left - 7,
                y + 3.5,
                format(Decimal(f"{tick:.9g}"), "f"),
                anchor="end",
            )
        _line(root, left, top, left, bottom, "black")
        _line(root, left, bottom, right, bottom, "black")
        axis_label = panel_ylabels[group] if panel_ylabels else ylabel
        _label(
            root, 20, middle, axis_label, transform=f"rotate(-90 20.00 {middle:.2f})"
        )
        for b, band in enumerate(BANDS):
            previous = None
            for i, period in enumerate(periods):
                v = values[band, period]
                if v is None:
                    previous = None
                    continue
                x = left + (i + 0.5) * slot
                y = round(bottom - plot_height * v / ticks[-1], 2)
                full = period != PERIODS[-1]
                if full and previous is not None:
                    _line(root, *previous, x, y, _COLORS[b], 1.5, _DASHES[b])
                _marker(root, b, x, y, 2 if full else 3.3)
                previous = x, y
        for i, period in enumerate(periods):
            x = left + (i + 0.5) * slot
            _line(root, x, bottom, x, bottom + 3.5, "black")
            if idx == len(panels) - 1:
                _label(root, x, bottom + 16, period)
    _label(root, (left + right) / 2, bottom + 36, xlabel)
    for i, line in enumerate(notes):
        _label(root, 60, bottom + 55 + i * 13, line, 9, "start")
    ET.indent(root)
    return ET.tostring(root, encoding="unicode") + "\n"
