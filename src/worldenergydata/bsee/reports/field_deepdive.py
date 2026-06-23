"""Per-field deep-dive report generator.

Generalizes the prior Lower-Tertiary per-field deep-dives to *every* GoM
field: one self-contained interactive HTML page per field, combining

1. a per-field annual **production timeline** built directly from the OGOR-A
   monthly ``.bin`` archives (oil / gas / water / distinct wells per year), and
2. the per-field **atlas metrics** already produced by the all-fields atlas
   (one row of the atlas CSV).

Design rules (shared with :mod:`atlas_charts`):
- Deterministic; no network, no external data.
- Flag-don't-fake: metric columns that are absent or null are omitted, never
  imputed.  Whatever metric columns the atlas row carries are rendered; missing
  ones are gracefully dropped (so this keeps working when a pending PR adds
  ``NETBACK_*`` / ``BREAKEVEN_OPEX_USD_BBL``).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Mapping, Optional, Union

import pandas as pd

from worldenergydata.bsee.data.sources.bin.ogor_production_loader import load_ogor_bin
from worldenergydata.common.data_resolver import get_module_data_safe

logger = logging.getLogger(__name__)

_DEFAULT_SUBDIR = "historical_production_yearly"
_TIMELINE_COLUMNS = ["YEAR", "OIL_MMBBL", "GAS_BCF", "WATER_MMBBL", "WELLS"]

_OIL_COLOR = "#1f77b4"
_GAS_COLOR = "#ff7f0e"

DATA_VINTAGE = "BSEE OGOR-A monthly production, 1996-2025"

# Human labels + formatting for known atlas metric columns, grouped sensibly.
# (column, label, kind) where kind drives formatting.
_METRIC_GROUPS = [
    (
        "Production",
        [
            ("WELL_COUNT", "Well Count", "int"),
            ("FIRST_PRODUCTION", "First Production Year", "int"),
            ("LAST_PRODUCTION", "Last Production Year", "int"),
            ("CUM_OIL_MMBBL", "Cumulative Oil", "mmbbl"),
            ("CUM_GAS_BCF", "Cumulative Gas", "bcf"),
            ("CUM_WATER_MMBBL", "Cumulative Water", "mmbbl"),
            ("PEAK_OIL_BOPD", "Peak Oil Rate", "bopd"),
            ("REC_PER_WELL_MMBBL", "Recovery per Well", "mmbbl"),
            ("AVG_BOPD_PER_WELL", "Average Oil Rate per Well", "bopd"),
        ],
    ),
    (
        "Geology",
        [
            ("WATER_DEPTH_AVG", "Average Water Depth", "ft"),
            ("GEOLOGICAL_ERA", "Geological Era", "text"),
            ("IS_LOWER_TERTIARY", "Lower Tertiary", "bool"),
        ],
    ),
    (
        "Operators",
        [
            ("N_OPERATORS", "Number of Operators", "int"),
            ("DOMINANT_OPERATOR", "Dominant Operator", "text"),
        ],
    ),
    (
        "Economics",
        [
            ("GROSS_OIL_REVENUE_MM_USD", "Gross Oil Revenue", "musd"),
            ("NETBACK_BASE_MM_USD", "Netback (base case)", "musd"),
            ("NETBACK_LOW_MM_USD", "Netback (low case)", "musd"),
            ("NETBACK_HIGH_MM_USD", "Netback (high case)", "musd"),
            ("BREAKEVEN_OPEX_USD_BBL", "Breakeven (opex)", "usd_bbl"),
            ("DECOM_P50_MM_USD", "Decommissioning P50", "musd"),
            ("DECOM_P70_MM_USD", "Decommissioning P70", "musd"),
            ("DECOM_P90_MM_USD", "Decommissioning P90", "musd"),
        ],
    ),
]

# Columns rendered as the title / never in the metric table.
_TITLE_COLUMNS = {"FIELD_CODE", "FIELD_NAME"}


def _default_data_dir() -> Path:
    return get_module_data_safe("bsee") / "bin" / _DEFAULT_SUBDIR


def build_field_timeline(
    field_code: str,
    data_dir: Optional[Union[str, Path]] = None,
    start_year: int = 1996,
    end_year: int = 2025,
) -> pd.DataFrame:
    """Build a per-year production timeline for one field from OGOR-A bins.

    Parameters
    ----------
    field_code:
        BOEM field code (e.g. ``"MC807"``).  Compared after stripping.
    data_dir:
        Directory of ``ogora{year}delimit.bin`` files.  Defaults to the
        resolved ``<bsee module>/bin/historical_production_yearly``.
    start_year, end_year:
        Inclusive year range to scan.

    Returns
    -------
    pd.DataFrame
        Columns ``YEAR, OIL_MMBBL, GAS_BCF, WATER_MMBBL, WELLS`` sorted by
        year.  Oil/water are in MMBBL (volumes / 1e6); gas in BCF
        (volume / 1e6).  Empty (correctly-typed) frame when the field has no
        rows in the range.
    """
    if data_dir is None:
        data_dir = _default_data_dir()
    data_dir = Path(data_dir)
    target = str(field_code).strip()

    frames = []
    for year in range(start_year, end_year + 1):
        path = data_dir / f"ogora{year}delimit.bin"
        if not path.exists():
            continue
        raw = load_ogor_bin(path)
        if raw.empty:
            continue
        field = raw["BOEM_FIELD"].astype(str).str.strip()
        sub = raw[field == target]
        if sub.empty:
            continue
        frames.append(sub)

    if not frames:
        return _empty_timeline()

    df = pd.concat(frames, ignore_index=True)
    prod_date = pd.to_numeric(df["PRODUCTION_DATE"], errors="coerce")
    df = df.assign(YEAR=(prod_date // 100).astype("Int64"))
    df = df[df["YEAR"].notna()]
    if df.empty:
        return _empty_timeline()

    for col in ("MON_O_PROD_VOL", "MON_G_PROD_VOL", "MON_WTR_PROD_VOL"):
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace('"', "", regex=False).str.strip(),
            errors="coerce",
        ).fillna(0.0)
    df["API_WELL_NUMBER"] = df["API_WELL_NUMBER"].astype(str).str.strip()

    grouped = df.groupby("YEAR")
    out = pd.DataFrame(
        {
            "YEAR": [int(y) for y in grouped.groups.keys()],
            "OIL_MMBBL": grouped["MON_O_PROD_VOL"].sum().to_numpy() / 1e6,
            "GAS_BCF": grouped["MON_G_PROD_VOL"].sum().to_numpy() / 1e6,
            "WATER_MMBBL": grouped["MON_WTR_PROD_VOL"].sum().to_numpy() / 1e6,
            "WELLS": grouped["API_WELL_NUMBER"].nunique().to_numpy(),
        }
    )
    out["YEAR"] = out["YEAR"].astype(int)
    out["WELLS"] = out["WELLS"].astype(int)
    return out.sort_values("YEAR").reset_index(drop=True)[_TIMELINE_COLUMNS]


def _empty_timeline() -> pd.DataFrame:
    out = pd.DataFrame(columns=_TIMELINE_COLUMNS)
    return out.astype(
        {
            "YEAR": "int64",
            "OIL_MMBBL": "float64",
            "GAS_BCF": "float64",
            "WATER_MMBBL": "float64",
            "WELLS": "int64",
        }
    )


def _is_present(value) -> bool:
    """True when a metric value is real (present and not NaN)."""
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _format_metric(value, kind: str) -> str:
    """Format a metric value for display (caller guarantees it is present)."""
    if kind == "text":
        return str(value).strip()
    if kind == "bool":
        return "Yes" if bool(value) else "No"
    if kind == "int":
        return f"{int(round(float(value))):,}"
    num = float(value)
    if kind == "mmbbl":
        return f"{num:,.2f} MMBBL"
    if kind == "bcf":
        return f"{num:,.2f} BCF"
    if kind == "bopd":
        return f"{num:,.0f} BOPD"
    if kind == "ft":
        return f"{num:,.0f} ft"
    if kind == "musd":
        return f"${num:,.1f} MM"
    if kind == "usd_bbl":
        return f"${num:,.2f} / bbl"
    return f"{num:,.2f}"


def _metrics_table_html(field_row: Mapping) -> str:
    """Render the grouped metrics table for present, non-null columns."""
    sections = []
    for group_name, specs in _METRIC_GROUPS:
        rows = []
        for col, label, kind in specs:
            if col not in field_row:
                continue
            value = field_row[col]
            if not _is_present(value):
                continue
            rows.append(
                f"<tr><td class='metric-label'>{label}</td>"
                f"<td class='metric-value'>{_format_metric(value, kind)}</td></tr>"
            )
        if rows:
            sections.append(
                f"<h3>{group_name}</h3>"
                "<table class='metrics'>" + "".join(rows) + "</table>"
            )
    if not sections:
        return "<p>No atlas metrics available for this field.</p>"
    return "\n".join(sections)


def _timeline_figure_html(field_name: str, timeline: pd.DataFrame) -> str:
    """Dual-series (oil MMBBL / gas BCF) annual timeline as embedded HTML."""
    import plotly.graph_objects as go

    title = f"{field_name} - Annual Production Timeline"
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=timeline["YEAR"].tolist(),
            y=timeline["OIL_MMBBL"].tolist(),
            mode="lines+markers",
            name="Oil (MMBBL)",
            line=dict(color=_OIL_COLOR),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=timeline["YEAR"].tolist(),
            y=timeline["GAS_BCF"].tolist(),
            mode="lines+markers",
            name="Gas (BCF)",
            yaxis="y2",
            line=dict(color=_GAS_COLOR),
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis=dict(title="Oil (MMBBL)", color=_OIL_COLOR),
        yaxis2=dict(
            title="Gas (BCF)",
            color=_GAS_COLOR,
            overlaying="y",
            side="right",
        ),
        legend=dict(orientation="h", y=-0.2),
        height=480,
    )
    return fig.to_html(full_html=False, include_plotlyjs="inline")


def _footnote_html(field_row: Mapping) -> str:
    notes = [
        f"Production timeline source: {DATA_VINTAGE} "
        "(monthly volumes summed to annual; wells = distinct API well numbers)."
    ]
    has_revenue = _is_present(field_row.get("GROSS_OIL_REVENUE_MM_USD"))
    has_decom = any(
        _is_present(field_row.get(c))
        for c in ("DECOM_P50_MM_USD", "DECOM_P70_MM_USD", "DECOM_P90_MM_USD")
    )
    has_netback = any(
        _is_present(field_row.get(c))
        for c in (
            "NETBACK_BASE_MM_USD",
            "NETBACK_LOW_MM_USD",
            "NETBACK_HIGH_MM_USD",
            "BREAKEVEN_OPEX_USD_BBL",
        )
    )
    if has_revenue:
        notes.append(
            "Gross oil revenue is oil-only, gross (pre-royalty, pre-cost) at "
            "real historical WTI - not a net or after-tax figure."
        )
    if has_decom:
        notes.append(
            "Decommissioning P50/P70/P90 are BSEE-provided abandonment cost "
            "estimates (with their own uncertainty), not a model output."
        )
    if has_netback:
        notes.append(
            "Netback / breakeven figures are a price-cost sensitivity, not an "
            "NPV; they ignore the time value of money."
        )
    items = "".join(f"<li>{n}</li>" for n in notes)
    return f"<div class='footnote'><strong>Notes</strong><ul>{items}</ul></div>"


_CSS = """
body { font-family: Arial, Helvetica, sans-serif; margin: 2rem; color: #222; }
h1 { font-size: 1.6rem; }
h3 { margin-bottom: 0.25rem; color: #1f4e79; }
table.metrics { border-collapse: collapse; margin-bottom: 1rem; }
table.metrics td { border: 1px solid #ddd; padding: 4px 10px; }
td.metric-label { color: #555; }
td.metric-value { font-weight: bold; }
.footnote { color: #555; font-size: 0.9em; margin-top: 1.5rem;
            border-top: 1px solid #ddd; padding-top: 0.5rem; }
.no-timeline { color: #a33; font-style: italic; margin: 1rem 0; }
"""


def render_field_deepdive(
    field_row: Union[Mapping, pd.Series], timeline: pd.DataFrame
) -> str:
    """Render a self-contained interactive HTML deep-dive page for one field.

    Parameters
    ----------
    field_row:
        One field's atlas metrics (dict or :class:`pandas.Series`).  Only the
        columns actually present (and non-null) are rendered.
    timeline:
        Output of :func:`build_field_timeline` for the same field.  An empty
        timeline renders the metrics plus a "no production timeline" note
        rather than crashing.

    Returns
    -------
    str
        A complete HTML document (Plotly inlined; no external assets).
    """
    if isinstance(field_row, pd.Series):
        field_row = field_row.to_dict()

    name = field_row.get("FIELD_NAME") or field_row.get("FIELD_CODE") or "Field"
    name = str(name).strip()
    code = str(field_row.get("FIELD_CODE", "")).strip()
    heading = name if not code or code == name else f"{name} ({code})"

    metrics_html = _metrics_table_html(field_row)

    if timeline is None or timeline.empty:
        timeline_html = (
            "<p class='no-timeline'>No production timeline: this field has no "
            "OGOR-A production records in the covered period.</p>"
        )
    else:
        timeline_html = _timeline_figure_html(name, timeline)

    footnote_html = _footnote_html(field_row)

    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{heading} - Field Deep-Dive</title>"
        f"<style>{_CSS}</style></head><body>"
        f"<h1>{heading} - Field Deep-Dive</h1>"
        f"<h2>Production Timeline</h2>{timeline_html}"
        f"<h2>Field Metrics</h2>{metrics_html}"
        f"{footnote_html}"
        "</body></html>"
    )
