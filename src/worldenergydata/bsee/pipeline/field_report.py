"""HTML report renderer for BSEE field analysis pipeline.

Generates a self-contained HTML page from a :class:`FieldReport` produced
by the pipeline runner.  All CSS is inlined and the only external resource
is the Plotly CDN for interactive charts.
"""

from __future__ import annotations

import html
import json
import logging
from pathlib import Path

import pandas as pd

from worldenergydata.bsee.pipeline.pipeline_runner import FieldReport

logger = logging.getLogger(__name__)

_PLOTLY_CDN = "https://cdn.plot.ly/plotly-basic-2.35.2.min.js"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_html(report: FieldReport) -> str:
    """Render a self-contained HTML report from a :class:`FieldReport`.

    All user-derived text is escaped via :func:`html.escape` to prevent
    cross-site scripting.

    Returns:
        A complete HTML document as a string.
    """
    sections = [
        _header_section(report),
        _summary_cards(report),
        _production_section(report),
        _casing_section(report),
        _activity_section(report),
        _warnings_section(report),
    ]

    body = "\n".join(s for s in sections if s)

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        "<title>"
        f"BSEE Field Report \u2014 {html.escape(report.context.field_name)}"
        "</title>\n"
        f"<style>\n{_css_styles()}\n</style>\n"
        f'<script src="{_PLOTLY_CDN}"></script>\n'
        "</head>\n"
        "<body>\n"
        '<div class="container">\n'
        f"{body}\n"
        "</div>\n"
        "</body>\n"
        "</html>"
    )


def save_report(report: FieldReport, path: Path) -> None:
    """Write the HTML report to *path*, creating parent directories."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html(report), encoding="utf-8")
    logger.info("Report saved to %s", path)


# ---------------------------------------------------------------------------
# Section builders (private)
# ---------------------------------------------------------------------------

def _header_section(report: FieldReport) -> str:
    ctx = report.context
    field_name = html.escape(ctx.field_name)
    field_code = html.escape(ctx.field_code)
    era = html.escape(ctx.geological_era)
    ts = html.escape(report.generated_at)

    return (
        '<div class="header">\n'
        f'  <h1>BSEE Field Report \u2014 {field_name}</h1>\n'
        f'  <p class="subtitle">'
        f"Field Code: {field_code} | "
        f"Era: {era} | "
        f"Generated: {ts}"
        "</p>\n"
        "</div>"
    )


def _summary_cards(report: FieldReport) -> str:
    ctx = report.context
    cards = [
        ("Well Count", str(report.wellbore_count)),
        ("Lease Count", str(report.lease_count)),
        ("Area Code", html.escape(ctx.area_code) if ctx.area_code else "N/A"),
        ("Query Type", html.escape(ctx.query_type)),
    ]
    items = []
    for label, value in cards:
        items.append(
            '<div class="card">\n'
            f'  <div class="card-value">{value}</div>\n'
            f'  <div class="card-label">{label}</div>\n'
            "</div>"
        )
    return '<div class="cards-row">\n' + "\n".join(items) + "\n</div>"


def _production_section(report: FieldReport) -> str:
    parts = ['<div class="section">', "  <h2>Production Summary</h2>"]

    if report.production_summary.empty:
        parts.append('  <p class="empty-msg">No production data available</p>')
        parts.append("</div>")
        return "\n".join(parts)

    # Table
    parts.append(_dataframe_to_html(report.production_summary))

    # Plotly bar chart of key metrics
    chart_html = _production_chart(report.production_summary)
    if chart_html:
        parts.append(chart_html)

    parts.append("</div>")
    return "\n".join(parts)


def _production_chart(df: pd.DataFrame) -> str:
    """Build an inline Plotly bar chart for production metrics."""
    metric_cols = [
        c for c in ("CUM_OIL_MMBBL", "CUM_GAS_BCF", "PEAK_OIL_BOPD")
        if c in df.columns
    ]
    if not metric_cols:
        return ""

    values = [float(df[c].iloc[0]) for c in metric_cols]
    labels = [c.replace("_", " ") for c in metric_cols]

    trace = {
        "x": labels,
        "y": values,
        "type": "bar",
        "marker": {"color": "#1a3a5c"},
    }
    layout = {
        "title": {"text": "Key Production Metrics"},
        "margin": {"t": 40, "b": 60, "l": 60, "r": 20},
        "height": 320,
    }

    chart_id = "prod-chart"
    return (
        f'<div id="{chart_id}" style="width:100%;max-width:700px;'
        f'margin:1rem auto;"></div>\n'
        "<script>\n"
        f"Plotly.newPlot('{chart_id}',"
        f" [{json.dumps(trace)}],"
        f" {json.dumps(layout)},"
        " {responsive:true});\n"
        "</script>"
    )


def _casing_section(report: FieldReport) -> str:
    parts = ['<div class="section">', "  <h2>Casing Schematics</h2>"]

    if not report.casing_svgs:
        parts.append('  <p class="empty-msg">No casing data available</p>')
        parts.append("</div>")
        return "\n".join(parts)

    for api12, svg_str in report.casing_svgs.items():
        api_esc = html.escape(api12)
        parts.append(f'  <div class="well-casing">')
        parts.append(f"    <h3>Well {api_esc}</h3>")

        # Inline SVG
        parts.append(f'    <div class="svg-container">{svg_str}</div>')

        # Casing matrix table
        matrix_df = report.casing_matrices.get(api12)
        if matrix_df is not None and not matrix_df.empty:
            parts.append("    <h4>Casing Program</h4>")
            parts.append(f"    {_dataframe_to_html(matrix_df)}")

        parts.append("  </div>")

    parts.append("</div>")
    return "\n".join(parts)


def _activity_section(report: FieldReport) -> str:
    parts = ['<div class="section">', "  <h2>Activity Analysis</h2>"]

    if not report.activity_analysis:
        parts.append('  <p class="empty-msg">No activity data available</p>')
        parts.append("</div>")
        return "\n".join(parts)

    for module_name, module_data in report.activity_analysis.items():
        module_esc = html.escape(str(module_name))
        parts.append(f'  <div class="activity-module">')
        parts.append(f"    <h3>{module_esc}</h3>")

        if isinstance(module_data, dict):
            for sub_key, sub_val in module_data.items():
                sub_esc = html.escape(str(sub_key))
                parts.append(f"    <h4>{sub_esc}</h4>")
                if isinstance(sub_val, pd.DataFrame) and not sub_val.empty:
                    parts.append(f"    {_dataframe_to_html(sub_val)}")
                else:
                    parts.append(
                        f'    <p>{html.escape(str(sub_val))}</p>'
                    )
        elif isinstance(module_data, pd.DataFrame):
            if not module_data.empty:
                parts.append(f"    {_dataframe_to_html(module_data)}")
        else:
            parts.append(f'    <p>{html.escape(str(module_data))}</p>')

        parts.append("  </div>")

    parts.append("</div>")
    return "\n".join(parts)


def _warnings_section(report: FieldReport) -> str:
    if not report.warnings:
        return ""

    items = "\n".join(
        f"  <li>{html.escape(w)}</li>" for w in report.warnings
    )
    return (
        '<div class="section warnings">\n'
        "  <h2>Warnings</h2>\n"
        f"  <ul>\n{items}\n  </ul>\n"
        "</div>"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dataframe_to_html(df: pd.DataFrame) -> str:
    """Convert a DataFrame to an HTML table with escaped cell values."""
    if df.empty:
        return '<p class="empty-msg">No data</p>'

    parts = ['<table class="data-table">', "  <thead>", "    <tr>"]
    for col in df.columns:
        parts.append(f"      <th>{html.escape(str(col))}</th>")
    parts.append("    </tr>")
    parts.append("  </thead>")
    parts.append("  <tbody>")

    for _, row in df.iterrows():
        parts.append("    <tr>")
        for val in row:
            parts.append(f"      <td>{html.escape(str(val))}</td>")
        parts.append("    </tr>")

    parts.append("  </tbody>")
    parts.append("</table>")
    return "\n".join(parts)


def _css_styles() -> str:
    """Return the complete CSS stylesheet for the report."""
    return (
        "* { box-sizing: border-box; margin: 0; padding: 0; }\n"
        "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',"
        " Roboto, Arial, sans-serif; background: #f5f5f5;"
        " color: #333; line-height: 1.6; }\n"
        ".container { max-width: 1200px; margin: 0 auto;"
        " padding: 2rem 1.5rem; }\n"
        ".header { background: #1a3a5c; color: #fff;"
        " padding: 1.5rem 2rem; border-radius: 8px 8px 0 0; }\n"
        ".header h1 { font-size: 1.6rem; font-weight: 600;"
        " margin-bottom: 0.3rem; }\n"
        ".header .subtitle { font-size: 0.9rem; opacity: 0.85; }\n"
        ".cards-row { display: flex; gap: 1rem; flex-wrap: wrap;"
        " background: #fff; padding: 1.2rem 2rem;"
        " border-bottom: 1px solid #ddd; }\n"
        ".card { flex: 1 1 140px; text-align: center; padding: 0.8rem;"
        " background: #f9f9f9; border-radius: 6px;"
        " border: 1px solid #e0e0e0; }\n"
        ".card-value { font-size: 1.5rem; font-weight: 700;"
        " color: #1a3a5c; }\n"
        ".card-label { font-size: 0.8rem; color: #666;"
        " text-transform: uppercase; letter-spacing: 0.5px;"
        " margin-top: 0.2rem; }\n"
        ".section { background: #fff; padding: 1.5rem 2rem;"
        " border-bottom: 1px solid #ddd; }\n"
        ".section h2 { color: #1a3a5c; font-size: 1.3rem;"
        " margin-bottom: 1rem; padding-bottom: 0.4rem;"
        " border-bottom: 2px solid #1a3a5c; }\n"
        ".section h3 { color: #2c5f8a; font-size: 1.1rem;"
        " margin: 1rem 0 0.5rem; }\n"
        ".section h4 { color: #555; font-size: 0.95rem;"
        " margin: 0.8rem 0 0.4rem; }\n"
        ".data-table { width: 100%; border-collapse: collapse;"
        " margin: 0.8rem 0; font-size: 0.9rem; }\n"
        ".data-table th { background: #1a3a5c; color: #fff;"
        " padding: 0.6rem 0.8rem; text-align: left;"
        " font-weight: 600; }\n"
        ".data-table td { padding: 0.5rem 0.8rem;"
        " border-bottom: 1px solid #e0e0e0; }\n"
        ".data-table tbody tr:nth-child(even) { background: #f9f9f9; }\n"
        ".data-table tbody tr:hover { background: #eef3f8; }\n"
        ".empty-msg { color: #888; font-style: italic;"
        " padding: 1rem 0; }\n"
        ".well-casing { margin-bottom: 2rem; padding-bottom: 1rem;"
        " border-bottom: 1px solid #eee; }\n"
        ".svg-container { text-align: center; margin: 1rem 0;"
        " overflow-x: auto; }\n"
        ".activity-module { margin-bottom: 1.5rem; }\n"
        ".warnings { border-left: 4px solid #e6a817; }\n"
        ".warnings h2 { color: #b8860b;"
        " border-bottom-color: #e6a817; }\n"
        ".warnings ul { list-style: disc; padding-left: 1.5rem; }\n"
        ".warnings li { padding: 0.3rem 0; color: #7a5a00; }"
    )
