# ABOUTME: Pure-Python inline-SVG primitives + a generic column-chart engine.
# ABOUTME: Zero external deps (no matplotlib); returns self-contained <svg> strings.
"""Inline-SVG drawing primitives and a small column-chart engine.

Everything here is pure Python and emits foreground vector markup, so the
figures embed directly in the brief HTML and print in the headless-Chrome PDF
(they are not ``file://`` subresources or CSS backgrounds).
"""

from __future__ import annotations

import math
from html import escape as _esc
from pathlib import Path
from typing import Callable, Optional, Sequence

import yaml

# --- palette (accessible, matches the brief accent #0b3d5c) ----------------
INK = "#15202b"
MUTED = "#5b6b7b"
RULE = "#cdd7e0"
GRID = "#e3e9ee"
ACCENT = "#0b3d5c"
BAR1 = "#0b3d5c"  # deep blue (primary series)
BAR2 = "#1c7ab0"  # mid blue (secondary series)
RISK = "#c0392b"  # red (ratio > 1, deepest/constrained band)
OK = "#2e7d4f"  # green
AMBER = "#d98a0b"
NEUTRAL = "#9bb0c1"

# --- repo + data paths -----------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
_BSEE = (
    REPO_ROOT
    / "packages/worldenergydata-bsee/src/worldenergydata/bsee"
    / "analysis/intervention/data"
)
_VESSEL = (
    REPO_ROOT
    / "packages/worldenergydata-vessel_fleet/src/worldenergydata"
    / "vessel_fleet/data"
)

DATA_FILES = {
    "well_inventory": _BSEE / "well_inventory_by_band.yml",
    "serviceability": _BSEE / "serviceability_matrix.yml",
    "planned": _BSEE / "planned_subsea_wells.yml",
    "access_gap": _BSEE / "access_gap.yml",
    "economics": _BSEE / "intervention_economics.yml",
    "fleet": _VESSEL / "intervention_fleet_catalog.yml",
}


def load_yaml(key: str) -> dict:
    """Load one committed source YAML by registry key."""
    with DATA_FILES[key].open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# --- low-level SVG helpers -------------------------------------------------
def t(s) -> str:
    return _esc(str(s))


def text(
    x: float,
    y: float,
    s,
    *,
    size: float = 11,
    fill: str = INK,
    anchor: str = "start",
    weight: str = "normal",
    rotate: Optional[float] = None,
) -> str:
    extra = ""
    if rotate is not None:
        extra = f' transform="rotate({rotate} {x:.1f} {y:.1f})"'
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}" font-weight="{weight}" '
        f'font-family="Helvetica,Arial,sans-serif"{extra}>{t(s)}</text>'
    )


def rect(x, y, w, h, *, fill, rx: float = 0, opacity: float = 1.0) -> str:
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'rx="{rx}" fill="{fill}" opacity="{opacity}"/>'
    )


def line(x1, y1, x2, y2, *, stroke, width=1.0, dash: str = "") -> str:
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{width}"{d}/>'
    )


def polyline(points: Sequence[tuple], *, stroke, width=2.0) -> str:
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return (
        f'<polyline points="{pts}" fill="none" stroke="{stroke}" '
        f'stroke-width="{width}"/>'
    )


def circle(cx, cy, r, *, fill, stroke="none", sw=0) -> str:
    return (
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{sw}"/>'
    )


def svg(width: float, height: float, body: str, *, title: str, desc: str) -> str:
    """Wrap a body in an accessible, self-contained root <svg>."""
    return (
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" width="100%" '
        f'role="img" aria-label="{t(title)}" '
        'xmlns="http://www.w3.org/2000/svg" '
        'style="max-width:760px;height:auto;font-family:Helvetica,Arial,sans-serif">'
        f"<title>{t(title)}</title><desc>{t(desc)}</desc>"
        f'<rect x="0" y="0" width="{width:.0f}" height="{height:.0f}" fill="#ffffff"/>'
        f"{body}</svg>"
    )


# --- numeric helpers -------------------------------------------------------
def nice_max(v: float) -> float:
    if v <= 0:
        return 1.0
    exp = math.floor(math.log10(v))
    base = 10**exp
    for m in (1, 1.5, 2, 2.5, 3, 4, 5, 7.5, 10):
        if m * base >= v:
            return m * base
    return 10 * base


def fmt_int(v: float) -> str:
    return f"{int(round(v)):,}"


def fmt_usd(v: float) -> str:
    if v >= 1e9:
        return f"${v / 1e9:.1f}B"
    if v >= 1e6:
        return f"${v / 1e6:.0f}M"
    if v >= 1e3:
        return f"${v / 1e3:.0f}k"
    return f"${v:.0f}"


# --- generic grouped column chart -----------------------------------------
def column_chart(
    *,
    categories: Sequence[str],
    series: Sequence[dict],
    title: str,
    desc: str,
    y_label: str = "",
    value_fmt: Optional[Callable[[float], str]] = None,
    line_series: Optional[dict] = None,
    ref_line: Optional[dict] = None,
    y_max: Optional[float] = None,
    width: float = 720,
    height: float = 380,
    x_label_angle: float = 0,
) -> str:
    """Render a grouped column chart (1-2 series) with an optional overlaid
    line series (secondary axis), reference line, axis labels and value
    labels. ``series`` items: {name, values, color, colors?(per-bar)}.
    """
    if value_fmt is None:
        value_fmt = fmt_int
    n = len(categories)
    has_legend = len(series) > 1 or line_series is not None
    ml = 70
    mr = 66 if line_series else 26
    mt = 64 if has_legend else 44
    mb = 96 if x_label_angle else 64
    px0, px1 = ml, width - mr
    py0, py1 = mt, height - mb
    plot_w, plot_h = px1 - px0, py1 - py0

    allvals = [v for s in series for v in s["values"]]
    dmax = max(allvals + [0])
    if ref_line:
        dmax = max(dmax, ref_line.get("y", 0))
    ymax = y_max if y_max is not None else nice_max(dmax if dmax > 0 else 1)

    def yof(v):
        return py1 - (v / ymax) * plot_h

    parts: list[str] = []

    # gridlines + y ticks
    for i in range(5):
        yv = ymax * i / 4
        yy = yof(yv)
        parts.append(line(px0, yy, px1, yy, stroke=GRID, width=1))
        parts.append(
            text(px0 - 8, yy + 3.5, value_fmt(yv), size=9, fill=MUTED, anchor="end")
        )
    # axes
    parts.append(line(px0, py0, px0, py1, stroke=RULE, width=1.2))
    parts.append(line(px0, py1, px1, py1, stroke=RULE, width=1.2))
    if y_label:
        ly = (py0 + py1) / 2
        parts.append(
            text(18, ly, y_label, size=10, fill=MUTED, anchor="middle", rotate=-90)
        )

    # bars
    slot = plot_w / n
    ns = len(series)
    group_w = slot * 0.66
    bar_w = group_w / ns
    for ci, cat in enumerate(categories):
        cx = px0 + slot * (ci + 0.5)
        gx0 = cx - group_w / 2
        for si, s in enumerate(series):
            v = s["values"][ci]
            col = (s.get("colors") or [s["color"]] * n)[ci]
            bx = gx0 + si * bar_w
            by = yof(v)
            bh = py1 - by
            if v > 0:
                parts.append(rect(bx + 1, by, bar_w - 2, bh, fill=col, rx=2))
            lbl = value_fmt(v) if v else "0"
            parts.append(
                text(
                    bx + bar_w / 2,
                    by - 4 if v else py1 - 4,
                    lbl,
                    size=9,
                    fill=INK if v else MUTED,
                    anchor="middle",
                    weight="bold" if v else "normal",
                )
            )
        # category label
        if x_label_angle:
            parts.append(
                text(
                    cx,
                    py1 + 12,
                    cat,
                    size=8.5,
                    fill=INK,
                    anchor="end",
                    rotate=x_label_angle,
                )
            )
        else:
            parts.append(text(cx, py1 + 16, cat, size=9, fill=INK, anchor="middle"))

    # reference line
    if ref_line:
        ry = yof(ref_line["y"])
        parts.append(line(px0, ry, px1, ry, stroke=RISK, width=1.4, dash="5 3"))
        parts.append(
            text(
                px1 - 2,
                ry - 4,
                ref_line.get("label", ""),
                size=9,
                fill=RISK,
                anchor="end",
                weight="bold",
            )
        )

    # secondary line series
    if line_series:
        lvals = line_series["values"]
        lmax = line_series.get("axis_max") or nice_max(max(lvals))
        lcol = line_series.get("color", RISK)

        def lyof(v):
            return py1 - (v / lmax) * plot_h

        pts = []
        for ci in range(n):
            cx = px0 + slot * (ci + 0.5)
            pts.append((cx, lyof(lvals[ci])))
        parts.append(polyline(pts, stroke=lcol, width=2.2))
        lfmt = line_series.get("fmt", lambda v: f"{v:g}")
        for (cx, cy), v in zip(pts, lvals):
            parts.append(circle(cx, cy, 3.2, fill=lcol))
            parts.append(
                text(
                    cx,
                    cy - 7,
                    lfmt(v),
                    size=8.5,
                    fill=lcol,
                    anchor="middle",
                    weight="bold",
                )
            )
        # right axis ticks
        for i in range(5):
            vv = lmax * i / 4
            yy = lyof(vv)
            parts.append(
                text(px1 + 6, yy + 3.5, lfmt(vv), size=8.5, fill=lcol, anchor="start")
            )
        if line_series.get("axis_label"):
            parts.append(
                text(
                    width - 10,
                    (py0 + py1) / 2,
                    line_series["axis_label"],
                    size=10,
                    fill=lcol,
                    anchor="middle",
                    rotate=90,
                )
            )

    # legend
    if has_legend:
        lx = px0
        ly = mt - 22
        items = [(s["name"], s["color"], "rect") for s in series]
        if line_series:
            items.append((line_series["name"], line_series.get("color", RISK), "line"))
        for name, col, kind in items:
            if kind == "rect":
                parts.append(rect(lx, ly - 8, 12, 12, fill=col, rx=2))
            else:
                parts.append(line(lx, ly - 2, lx + 12, ly - 2, stroke=col, width=2.4))
                parts.append(circle(lx + 6, ly - 2, 2.6, fill=col))
            parts.append(text(lx + 17, ly + 2, name, size=9.5, fill=INK))
            lx += 17 + 7.0 * len(name) + 22

    parts.append(text(px0, 18, title, size=12.5, fill=ACCENT, weight="bold"))
    body = "".join(parts)
    return svg(width, height, body, title=title, desc=desc)
