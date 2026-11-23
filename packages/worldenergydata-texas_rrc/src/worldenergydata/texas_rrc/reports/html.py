"""Self-contained HTML rendering for Texas RRC field-atlas reports."""

from __future__ import annotations

import html
import math
from collections import Counter
from typing import Any, Iterable

import pandas as pd

from worldenergydata.texas_rrc.reports.field_atlas import FieldAtlasPage

_STYLE = """
body{margin:0;font-family:Arial,Helvetica,sans-serif;background:#f7f8fa;color:#1f2933}
main{max-width:1180px;margin:0 auto;padding:24px}
a{color:#0b5cad;text-decoration:none}a:hover{text-decoration:underline}
.hero{background:#102a43;color:white;padding:28px 32px}
.hero h1{margin:0 0 8px;font-size:30px;line-height:1.2}
.hero p{margin:0;color:#d9e2ec}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:20px 0}
.metric,.section{background:white;border:1px solid #d9e2ec;border-radius:6px;padding:16px}
.metric .label{color:#627d98;font-size:12px;text-transform:uppercase}
.metric .value{font-size:24px;font-weight:700;margin-top:4px}
h2{font-size:20px;margin:26px 0 10px}h3{font-size:16px;margin:0 0 10px}
table{border-collapse:collapse;width:100%;background:white;border:1px solid #d9e2ec}
th,td{padding:9px 10px;border-bottom:1px solid #e6edf3;text-align:left}
th{background:#eef3f8;font-size:12px;text-transform:uppercase;color:#486581}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}
.pill{display:inline-block;background:#e6f6ff;border:1px solid #9fdaff;border-radius:4px;padding:2px 6px}
.muted{color:#627d98}.footer{margin-top:28px;color:#627d98;font-size:13px}
"""


def render_index_html(summary: pd.DataFrame, pages: tuple[FieldAtlasPage, ...]) -> str:
    """Render the index page for a published field-atlas report set."""
    rows = summary.to_dict("records") if not summary.empty else []
    body = [
        _document_start("Texas RRC Onshore Field Atlas"),
        _hero(
            "Texas RRC Onshore Field Atlas",
            "Direct-source field development, production, and infrastructure reports.",
        ),
        "<main>",
        _index_metrics(rows),
        "<h2>Top Fields By Cumulative BOE</h2>",
        _top_fields_table(rows[:25]),
        '<div class="two">',
        _distribution_section("Production Maturity", rows, "production_maturity_class"),
        _distribution_section(
            "Infrastructure Access", rows, "infrastructure_access_class"
        ),
        "</div>",
        _footer("Sources: Texas RRC curated direct-source artifacts under /mnt/ace."),
        "</main>",
        "</body></html>",
    ]
    return "".join(body)


def render_field_html(page: FieldAtlasPage) -> str:
    """Render one field deep-dive page."""
    body = [
        _document_start(f"{page.field_name} Field Atlas"),
        _hero(_e(page.field_name), _field_subtitle(page)),
        "<main>",
        '<p><a href="../index.html">Back to index</a></p>',
        _field_metrics(page.summary),
        '<div class="two">',
        _section("Lifecycle", _definition_table(_lifecycle_rows(page.summary))),
        _section("Production", _definition_table(_production_rows(page.summary))),
        _section(
            "Infrastructure",
            _definition_table(_infrastructure_rows(page.summary)),
        ),
        _section(
            "Lease And Operator Context",
            _definition_table(_operator_rows(page.summary)),
        ),
        "</div>",
        "<h2>Top Leases</h2>",
        _lease_table(page.lease_rows),
        "<h2>Provenance And Caveats</h2>",
        _provenance(page),
        _footer("Generated from direct Texas RRC curated artifacts."),
        "</main>",
        "</body></html>",
    ]
    return "".join(body)


def _document_start(title: str) -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{_e(title)}</title><style>{_STYLE}</style></head><body>"
    )


def _hero(title: str, subtitle: str) -> str:
    return f'<header class="hero"><h1>{title}</h1><p>{subtitle}</p></header>'


def _index_metrics(rows: list[dict[str, Any]]) -> str:
    total_boe = sum(_number(row.get("cumulative_boe")) for row in rows)
    active_fields = sum(1 for row in rows if _number(row.get("active_well_count")) > 0)
    access_count = sum(1 for row in rows if _has_infrastructure_access(row))
    return _metric_grid(
        [
            ("Fields", len(rows)),
            ("Active Fields", active_fields),
            ("Cumulative BOE", total_boe),
            ("Fields With Infrastructure Row", access_count),
        ]
    )


def _field_metrics(summary: dict[str, Any]) -> str:
    return _metric_grid(
        [
            ("Cumulative BOE", summary.get("cumulative_boe")),
            ("Wells", summary.get("well_count")),
            ("Active Wells", summary.get("active_well_count")),
            ("Access Class", summary.get("infrastructure_access_class")),
        ]
    )


def _metric_grid(items: Iterable[tuple[str, object]]) -> str:
    cells = [
        f'<div class="metric"><div class="label">{_e(label)}</div>'
        f'<div class="value">{_fmt(value)}</div></div>'
        for label, value in items
    ]
    return '<section class="grid">' + "".join(cells) + "</section>"


def _top_fields_table(rows: list[dict[str, Any]]) -> str:
    table_rows = []
    for row in rows:
        link = _e(str(row.get("report_path") or ""))
        name = _e(row.get("field_name"))
        table_rows.append(
            "<tr>"
            f'<td><a href="{link}">{name}</a></td>'
            f"<td>{_e(row.get('district'))}</td>"
            f"<td>{_e(row.get('field_number'))}</td>"
            f"<td>{_fmt(row.get('cumulative_boe'))}</td>"
            f"<td>{_e(row.get('production_maturity_class'))}</td>"
            f"<td>{_e(row.get('infrastructure_access_class'))}</td>"
            "</tr>"
        )
    return _table(
        ["Field", "District", "Field Number", "Cumulative BOE", "Maturity", "Access"],
        table_rows,
    )


def _distribution_section(title: str, rows: list[dict[str, Any]], column: str) -> str:
    counts = Counter(str(row.get(column) or "not_available") for row in rows)
    table_rows = [
        f"<tr><td>{_e(label)}</td><td>{count}</td></tr>"
        for label, count in counts.most_common()
    ]
    return _section(title, _table(["Class", "Fields"], table_rows))


def _section(title: str, content: str) -> str:
    return f'<section class="section"><h3>{_e(title)}</h3>{content}</section>'


def _definition_table(rows: Iterable[tuple[str, object]]) -> str:
    table_rows = [
        f"<tr><th>{_e(label)}</th><td>{_fmt(value)}</td></tr>" for label, value in rows
    ]
    return "<table><tbody>" + "".join(table_rows) + "</tbody></table>"


def _lifecycle_rows(summary: dict[str, Any]) -> list[tuple[str, object]]:
    return [
        ("Production maturity", summary.get("production_maturity_class")),
        ("Remaining activity score", summary.get("remaining_activity_score")),
        ("Permits", summary.get("permit_count")),
        ("Completions", summary.get("completion_count")),
        ("Rank by remaining activity", summary.get("rank_remaining_activity")),
    ]


def _production_rows(summary: dict[str, Any]) -> list[tuple[str, object]]:
    return [
        ("Oil bbl", summary.get("cumulative_oil_bbl")),
        ("Gas mcf", summary.get("cumulative_gas_mcf")),
        ("Condensate bbl", summary.get("cumulative_condensate_bbl")),
        ("BOE per well", summary.get("production_per_well_boe")),
        ("Rank by cumulative BOE", summary.get("rank_cumulative_boe")),
    ]


def _infrastructure_rows(summary: dict[str, Any]) -> list[tuple[str, object]]:
    return [
        ("Access class", summary.get("infrastructure_access_class")),
        ("Access score", summary.get("infrastructure_access_score")),
        ("Nearest pipeline", summary.get("nearest_pipeline_identifier")),
        ("Nearest pipeline miles", summary.get("nearest_pipeline_distance_miles")),
        ("Pipelines within 1 mile", summary.get("nearby_pipeline_count_1mi")),
        ("Pipelines within 5 miles", summary.get("nearby_pipeline_count_5mi")),
        ("Pipelines within 10 miles", summary.get("nearby_pipeline_count_10mi")),
    ]


def _operator_rows(summary: dict[str, Any]) -> list[tuple[str, object]]:
    return [
        ("Lease count", summary.get("lease_count")),
        ("Operator count", summary.get("operator_count")),
        ("Top operator number", summary.get("top_operator_number")),
        ("Top operator", summary.get("top_operator_name")),
        ("Top operator share", _percent(summary.get("top_operator_share"))),
    ]


def _lease_table(rows: tuple[dict[str, Any], ...]) -> str:
    if not rows:
        return '<p class="muted">No lease-level production rows are available.</p>'
    body = [
        "<tr>"
        f"<td>{_e(row.get('lease_number'))}</td>"
        f"<td>{_e(row.get('lease_name'))}</td>"
        f"<td>{_e(row.get('operator_name'))}</td>"
        f"<td>{_fmt(row.get('cumulative_boe'))}</td>"
        "</tr>"
        for row in rows
    ]
    return _table(["Lease", "Lease Name", "Operator", "Cumulative BOE"], body)


def _provenance(page: FieldAtlasPage) -> str:
    caveats = _tag_list(page.source_caveats)
    flags = _tag_list(page.quality_flags) or '<span class="muted">None</span>'
    return (
        f"<p><strong>Source caveats:</strong> {caveats}</p>"
        f"<p><strong>Quality flags:</strong> {flags}</p>"
    )


def _tag_list(values: tuple[str, ...]) -> str:
    return " ".join(f'<span class="pill">{_e(value)}</span>' for value in values)


def _table(headers: list[str], rows: list[str]) -> str:
    header = "".join(f"<th>{_e(value)}</th>" for value in headers)
    body = "".join(rows) or f'<tr><td colspan="{len(headers)}">No rows</td></tr>'
    return f"<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>"


def _field_subtitle(page: FieldAtlasPage) -> str:
    return (
        f"District {_e(page.district)} &bull; Field {_e(page.field_number)} "
        f"&bull; {_e(page.summary.get('production_maturity_class'))}"
    )


def _footer(text: str) -> str:
    return f'<footer class="footer">{_e(text)}</footer>'


def _fmt(value: object) -> str:
    if value is None or _is_nan(value):
        return "Not available"
    if isinstance(value, str):
        return _e(value or "Not available")
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return _e(value)


def _percent(value: object) -> str:
    if value is None or _is_nan(value):
        return "Not available"
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return str(value)


def _number(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if math.isnan(number) else number


def _has_infrastructure_access(row: dict[str, Any]) -> bool:
    access_class = row.get("infrastructure_access_class")
    return bool(access_class and access_class != "not_available")


def _is_nan(value: object) -> bool:
    return isinstance(value, float) and math.isnan(value)


def _e(value: object) -> str:
    if value is None or _is_nan(value):
        return ""
    return html.escape(str(value), quote=True)


__all__ = ["render_field_html", "render_index_html"]
