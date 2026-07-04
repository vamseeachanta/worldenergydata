"""Render self-contained Texas RRC field-architecture dossier HTML."""

from __future__ import annotations

from html import escape
from typing import Any

import pandas as pd

from worldenergydata.texas_rrc.dossiers.models import FieldArchitectureDossierPage
from worldenergydata.texas_rrc.dossiers.quality import FieldArchitectureDossierQuality

_STYLE = """
body{font-family:Arial,sans-serif;margin:2rem;color:#202124;background:#fff}
table{border-collapse:collapse;width:100%;margin:1rem 0}
th,td{border:1px solid #d0d7de;padding:.45rem;text-align:left}
th{background:#f6f8fa}
.metric{display:inline-block;margin:.35rem 1rem .35rem 0}
.gap,.flag{font-family:monospace;background:#f6f8fa;padding:.1rem .25rem}
"""


def render_field_architecture_dossier_summary_html(
    index: pd.DataFrame,
    quality: FieldArchitectureDossierQuality,
) -> str:
    """Render the dossier batch summary page."""
    rows = "\n".join(_summary_table_row(row) for row in index.to_dict("records"))
    return _document(
        "Texas RRC Field Architecture Dossiers",
        f"""
<h1>Texas RRC Field Architecture Dossiers</h1>
<p>{quality.row_count} selected fields.</p>
<h2>Selected Fields</h2>
<table>
<thead><tr><th>Rank</th><th>Field</th><th>Source Atlas</th><th>Architecture</th><th>Score</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<h2>Source Gaps</h2>
{_token_list([*quality.blocking_source_gaps, *quality.informational_source_gaps])}
<h2>Limitations</h2>
<p>Screening-only dossier output; no reserves, economics, tariffs, capacity,
right-of-way, route, or engineered facility design conclusions.</p>
""",
    )


def render_field_architecture_dossier_html(
    page: FieldArchitectureDossierPage,
) -> str:
    """Render one self-contained field-architecture dossier page."""
    summary = page.summary
    return _document(
        f"{page.field_name} Field Architecture Dossier",
        f"""
<h1>{escape(page.field_name)}</h1>
<p>District {escape(page.district)} field {escape(page.field_number)}</p>
<h2>Opportunity</h2>
{_metrics(summary, ["architecture_signal_class", "opportunity_rank", "opportunity_score", "recommended_followup"])}
<h2>Lifecycle and Production</h2>
{_metrics(summary, ["first_production_month", "last_production_month", "production_span_months", "well_count", "active_well_count", "cumulative_boe"])}
<h2>Infrastructure</h2>
{_metrics(summary, ["infrastructure_access_class", "infrastructure_access_score", "nearest_pipeline_distance_miles"])}
<h2>Operator and Lease Context</h2>
{_metrics(summary, ["top_operator_name", "top_operator_share", "lease_count", "operator_count"])}
<h2>Evidence and Provenance</h2>
{_source_link(page)}
{_token_list(page.source_caveats)}
{_token_list(page.quality_flags, css_class="flag")}
<h2>Limitations</h2>
{_token_list(page.limitations)}
""",
    )


def _document(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{escape(title)}</title>
<style>{_STYLE}</style>
</head>
<body>
{body}
</body>
</html>
"""


def _summary_table_row(row: dict[str, Any]) -> str:
    path = escape(str(row.get("dossier_path") or ""))
    name = escape(str(row.get("field_name") or ""))
    return (
        "<tr>"
        f"<td>{escape(str(row.get('dossier_rank') or ''))}</td>"
        f"<td><a href=\"{path}\">{name}</a></td>"
        f"<td>{_summary_source_link(row)}</td>"
        f"<td>{escape(str(row.get('architecture_signal_class') or ''))}</td>"
        f"<td>{escape(str(row.get('opportunity_score') or ''))}</td>"
        "</tr>"
    )


def _summary_source_link(row: dict[str, Any]) -> str:
    path = str(row.get("source_field_atlas_report_path") or "")
    if not path:
        return "None"
    if "source_link_not_relative_to_output_root" in str(row.get("source_caveats") or ""):
        return escape(path)
    href = "../../" + path
    return f"<a href=\"{escape(href)}\">{escape(path)}</a>"


def _metrics(summary: dict[str, Any], columns: list[str]) -> str:
    items = []
    for column in columns:
        value = summary.get(column)
        if value is None or value == "":
            continue
        label = column.replace("_", " ").title()
        items.append(
            f"<span class=\"metric\"><strong>{escape(label)}:</strong> "
            f"{escape(str(value))}</span>"
        )
    return "<p>" + "\n".join(items) + "</p>"


def _source_link(page: FieldArchitectureDossierPage) -> str:
    path = page.source_field_atlas_report_path
    if not path:
        return "<p>No source field-atlas report link available.</p>"
    href = page.source_field_atlas_href
    if not href:
        return f"<p>Source field-atlas report: {escape(path)}</p>"
    return f"<p>Source field-atlas report: <a href=\"{escape(href)}\">{escape(path)}</a></p>"


def _token_list(tokens: list[str] | tuple[str, ...], css_class: str = "gap") -> str:
    if not tokens:
        return "<p>None</p>"
    items = "".join(
        f"<li><span class=\"{escape(css_class)}\">{escape(str(token))}</span></li>"
        for token in tokens
    )
    return f"<ul>{items}</ul>"


__all__ = [
    "render_field_architecture_dossier_html",
    "render_field_architecture_dossier_summary_html",
]
