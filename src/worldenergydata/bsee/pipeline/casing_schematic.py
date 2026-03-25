"""Casing schematic generator for the BSEE field analysis pipeline.

Reads well tubular data from ``well_tubulars.csv``, produces a tabular
casing matrix (:func:`casing_matrix`) and a self-contained SVG schematic
(:func:`render_casing_svg`).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CasingString:
    """Immutable representation of a single casing/liner/drive-pipe interval.

    Attributes:
        interval_type: ``"C"`` (Casing), ``"L"`` (Liner), ``"D"`` (Drive Pipe).
        hole_size: Borehole diameter in inches.
        casing_size: Casing outer diameter in inches.
        casing_weight: Weight in lbs/ft.
        casing_grade: Steel grade (e.g. ``"P-110"``).
        top_md: Top measured depth in feet.
        bottom_md: Bottom measured depth in feet.
        liner_test_psi: Internal pressure test (psi), or ``None``.
        shoe_test_psi: Shoe test pressure (psi), or ``None``.
        cement_vol_bbl: Cement volume in barrels, or ``None``.
    """

    interval_type: str
    hole_size: float
    casing_size: float
    casing_weight: float
    casing_grade: str
    top_md: float
    bottom_md: float
    liner_test_psi: float | None
    shoe_test_psi: float | None
    cement_vol_bbl: float | None


# ---------------------------------------------------------------------------
# Type label map
# ---------------------------------------------------------------------------

_TYPE_LABELS: dict[str, str] = {
    "C": "Casing",
    "L": "Liner",
    "D": "Drive Pipe",
}

# Color map by interval type
_TYPE_COLORS: dict[str, str] = {
    "D": "#795548",  # brown
    "C": "#1565c0",  # blue
    "L": "#2e7d32",  # green
}


# ---------------------------------------------------------------------------
# Public API — data loading
# ---------------------------------------------------------------------------

def load_well_casing(api12: str, tubulars_path: Path) -> list[CasingString]:
    """Load casing data for a single well from ``well_tubulars.csv``.

    Filters rows to *api12*, keeps only the latest ``WAR_START_DT`` per well,
    and sorts by ``CSNG_HOLE_SIZE`` descending (outermost first).

    Returns an empty list when the file is missing, unreadable, or contains
    no matching rows.
    """
    if not tubulars_path.exists():
        logger.warning("Tubulars file not found: %s", tubulars_path)
        return []

    try:
        df = pd.read_csv(tubulars_path, dtype={"API_WELL_NUMBER": str})
    except Exception as exc:
        logger.error("Cannot read %s: %s", tubulars_path, exc)
        return []

    if df.empty:
        return []

    # Filter to the requested well
    df = df[df["API_WELL_NUMBER"] == api12]
    if df.empty:
        return []

    # Parse WAR_START_DT and keep only the latest reporting period
    df = df.copy()
    df["_war_dt"] = pd.to_datetime(df["WAR_START_DT"], format="mixed", dayfirst=False)
    latest_dt = df["_war_dt"].max()
    df = df[df["_war_dt"] == latest_dt]

    # Sort by hole size descending (largest = outermost)
    df = df.sort_values("CSNG_HOLE_SIZE", ascending=False).reset_index(drop=True)

    return [_row_to_casing_string(row) for _, row in df.iterrows()]


def _row_to_casing_string(row: pd.Series) -> CasingString:
    """Convert a DataFrame row to a :class:`CasingString`."""
    return CasingString(
        interval_type=str(row.get("CSNG_INTV_TYPE_CD", "")).strip(),
        hole_size=_safe_float(row.get("CSNG_HOLE_SIZE")),
        casing_size=_safe_float(row.get("CASING_SIZE")),
        casing_weight=_safe_float(row.get("CASING_WEIGHT")),
        casing_grade=str(row.get("CASING_GRADE", "")).strip(),
        top_md=_safe_float(row.get("CSNG_SETTING_TOP_MD")),
        bottom_md=_safe_float(row.get("CSNG_SETTING_BOTM_MD")),
        liner_test_psi=_safe_float_or_none(row.get("CSNG_LINER_TEST_PRSS")),
        shoe_test_psi=_safe_float_or_none(row.get("CSNG_SHOE_TEST_PRSS")),
        cement_vol_bbl=_safe_float_or_none(row.get("CSNG_CEMENT_VOL")),
    )


# ---------------------------------------------------------------------------
# Public API — tabular matrix
# ---------------------------------------------------------------------------

def casing_matrix(strings: list[CasingString]) -> pd.DataFrame:
    """Build a tabular casing program matrix from casing strings.

    Returns a :class:`~pandas.DataFrame` with human-readable column names,
    sorted by hole size descending (outer to inner).  Returns an empty
    DataFrame for empty input.
    """
    if not strings:
        return pd.DataFrame()

    sorted_strings = sorted(strings, key=lambda s: s.hole_size, reverse=True)

    records = []
    for cs in sorted_strings:
        records.append(
            {
                "Type": _TYPE_LABELS.get(cs.interval_type, cs.interval_type),
                "Hole Size (in)": cs.hole_size,
                "Casing OD (in)": cs.casing_size,
                "Weight (lb/ft)": cs.casing_weight,
                "Grade": cs.casing_grade,
                "Top MD (ft)": cs.top_md,
                "Bottom MD (ft)": cs.bottom_md,
                "Test Pressure (psi)": cs.liner_test_psi,
                "Shoe Test (psi)": cs.shoe_test_psi,
                "Cement (bbl)": cs.cement_vol_bbl,
            }
        )

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Public API — SVG rendering
# ---------------------------------------------------------------------------

def render_casing_svg(
    strings: list[CasingString],
    well_name: str = "",
) -> str:
    """Render a self-contained SVG casing schematic.

    Args:
        strings: Casing strings to draw (outermost first preferred).
        well_name: Optional well identifier for the title.

    Returns:
        A complete SVG document as a string.
    """
    width, height = 600, 800

    if not strings:
        return _empty_svg(width, height, well_name)

    sorted_strings = sorted(strings, key=lambda s: s.hole_size, reverse=True)

    title = f"Casing Program \u2014 {well_name}" if well_name else "Casing Program"

    # Coordinate mapping
    margin_left = 100
    margin_right = 60
    margin_top = 60
    margin_bottom = 40
    draw_width = width - margin_left - margin_right
    draw_height = height - margin_top - margin_bottom

    max_depth = max(cs.bottom_md for cs in sorted_strings)
    min_depth = min(cs.top_md for cs in sorted_strings)
    depth_range = max_depth - min_depth
    if depth_range <= 0:
        depth_range = 1.0  # avoid division by zero

    max_hole = sorted_strings[0].hole_size
    if max_hole <= 0:
        max_hole = 1.0

    center_x = margin_left + draw_width / 2.0

    def depth_to_y(depth: float) -> float:
        frac = (depth - min_depth) / depth_range
        return margin_top + frac * draw_height

    def hole_to_half_width(hole_size: float) -> float:
        frac = hole_size / max_hole
        return frac * (draw_width / 2.0) * 0.8

    # Build SVG
    parts: list[str] = [_svg_header(width, height)]

    # Title
    parts.append(
        _svg_text(width / 2, 30, title, color="#222", size=16, anchor="middle")
    )

    # Depth axis
    parts.extend(_depth_axis(margin_left, margin_top, draw_height, min_depth, max_depth))

    # Draw casing strings (outermost first for correct layering)
    for cs in sorted_strings:
        y_top = depth_to_y(cs.top_md)
        y_bot = depth_to_y(cs.bottom_md)
        half_w = hole_to_half_width(cs.casing_size)
        color = _TYPE_COLORS.get(cs.interval_type, "#666")

        # Left wall
        parts.append(_svg_line(center_x - half_w, y_top, center_x - half_w, y_bot, color, width=2.0))
        # Right wall
        parts.append(_svg_line(center_x + half_w, y_top, center_x + half_w, y_bot, color, width=2.0))
        # Bottom shoe line
        parts.append(_svg_line(center_x - half_w, y_bot, center_x + half_w, y_bot, color, width=1.5))

        # Annotation at shoe depth
        label = f'{cs.casing_size}" {cs.casing_grade}'
        parts.append(
            _svg_text(
                center_x + half_w + 5,
                y_bot + 4,
                label,
                color=color,
                size=10,
                anchor="start",
            )
        )

    parts.append(_svg_footer())
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# SVG primitives (self-contained — no external dependency)
# ---------------------------------------------------------------------------

def _svg_header(width: int, height: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    )


def _svg_footer() -> str:
    return "</svg>"


def _svg_rect(
    x: float,
    y: float,
    w: float,
    h: float,
    color: str,
    width: float = 1.0,
    fill: str = "none",
) -> str:
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'stroke="{escape(color)}" stroke-width="{width}" fill="{escape(fill)}" />'
    )


def _svg_line(
    x1: float, y1: float, x2: float, y2: float, color: str, width: float = 1.0
) -> str:
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{escape(color)}" stroke-width="{width}" />'
    )


def _svg_text(
    x: float,
    y: float,
    text: str,
    color: str = "#333",
    size: int = 12,
    anchor: str = "middle",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{escape(color)}" '
        f'font-size="{size}" text-anchor="{anchor}" '
        f'font-family="Arial, sans-serif">{escape(text)}</text>'
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _empty_svg(width: int, height: int, well_name: str) -> str:
    """Return a minimal SVG with a 'no data' message."""
    title = f"Casing Program \u2014 {well_name}" if well_name else "Casing Program"
    parts = [
        _svg_header(width, height),
        _svg_text(width / 2, 30, title, color="#222", size=16, anchor="middle"),
        _svg_text(width / 2, height / 2, "No casing data available", color="#999", size=14),
        _svg_footer(),
    ]
    return "\n".join(parts)


def _depth_axis(
    margin_left: float,
    margin_top: float,
    draw_height: float,
    min_depth: float,
    max_depth: float,
) -> list[str]:
    """Generate depth axis tick marks and labels."""
    parts: list[str] = []

    # Axis label (rotated)
    parts.append(
        f'<text x="15" y="{margin_top + draw_height / 2:.1f}" '
        f'fill="#555" font-size="12" text-anchor="middle" '
        f'font-family="Arial, sans-serif" '
        f'transform="rotate(-90, 15, {margin_top + draw_height / 2:.1f})">'
        f"{escape('Measured Depth (ft)')}</text>"
    )

    # Choose tick interval
    depth_range = max_depth - min_depth
    if depth_range <= 0:
        return parts

    raw_interval = depth_range / 8.0
    magnitude = 10 ** math.floor(math.log10(max(raw_interval, 1)))
    nice = magnitude
    for candidate in [1, 2, 5, 10]:
        if candidate * magnitude >= raw_interval:
            nice = candidate * magnitude
            break

    # Draw ticks
    tick_depth = math.ceil(min_depth / nice) * nice
    x_line = margin_left - 5
    while tick_depth <= max_depth:
        frac = (tick_depth - min_depth) / depth_range
        y = margin_top + frac * draw_height
        parts.append(_svg_line(x_line, y, margin_left, y, "#999", 0.5))
        parts.append(
            _svg_text(x_line - 5, y + 4, f"{int(tick_depth)}", color="#555", size=10, anchor="end")
        )
        tick_depth += nice

    return parts


def _safe_float(val: object) -> float:
    """Convert *val* to float, returning 0.0 for NaN/None/empty."""
    if val is None:
        return 0.0
    try:
        result = float(val)
        return result if not math.isnan(result) else 0.0
    except (ValueError, TypeError):
        return 0.0


def _safe_float_or_none(val: object) -> float | None:
    """Convert *val* to float, returning ``None`` for NaN/empty/missing."""
    if val is None:
        return None
    try:
        result = float(val)
        return None if math.isnan(result) else result
    except (ValueError, TypeError):
        return None
