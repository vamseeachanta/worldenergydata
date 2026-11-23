"""Render self-contained Texas RRC field-architecture portfolio HTML."""

from __future__ import annotations

from html import escape
from urllib.parse import urlparse

import pandas as pd

from worldenergydata.texas_rrc.architecture_portfolio.quality import (
    FieldArchitecturePortfolioQuality,
)


def render_field_architecture_portfolio_html(
    action_queue: pd.DataFrame,
    class_summary: pd.DataFrame,
    followup_summary: pd.DataFrame,
    quality: FieldArchitecturePortfolioQuality,
) -> str:
    """Render the portfolio packet as one self-contained HTML document."""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Texas RRC Field Architecture Portfolio</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 2rem; color: #202124; }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0 2rem; }}
th, td {{ border: 1px solid #d0d7de; padding: 0.4rem; text-align: left; }}
th {{ background: #f6f8fa; }}
.muted {{ color: #57606a; }}
</style>
</head>
<body>
<h1>Texas RRC Field Architecture Portfolio</h1>
<p>Screening-only portfolio summary; no reserves, economics, tariffs, capacity,
right-of-way, route, or engineered facility design conclusions.</p>
<h2>Source Health</h2>
{_source_health(quality)}
<h2>Architecture Class Distribution</h2>
{_table(class_summary)}
<h2>Portfolio Action Queue</h2>
{_action_queue_table(action_queue)}
<h2>Follow-up Summary</h2>
{_table(followup_summary)}
<h2>Limitations</h2>
{_limitations(action_queue)}
</body>
</html>
"""


def _source_health(quality: FieldArchitecturePortfolioQuality) -> str:
    blocking = _tags(quality.blocking_source_gaps)
    informational = _tags(quality.informational_source_gaps)
    none = '<span class="muted">None</span>'
    return (
        f"<p><strong>Rows:</strong> {quality.row_count}</p>"
        f"<p><strong>Blocking gaps:</strong> {blocking or none}</p>"
        f"<p><strong>Informational gaps:</strong> {informational or none}</p>"
    )


def _action_queue_table(frame: pd.DataFrame) -> str:
    columns = [
        "portfolio_rank",
        "field_name",
        "architecture_signal_class",
        "portfolio_action",
        "followup_priority",
        "opportunity_score",
        "recommended_followup",
        "source_dossier_href",
        "dossier_path",
        "source_caveats",
        "quality_flags",
    ]
    rows = []
    for _, row in frame.iterrows():
        cells = []
        for column in columns:
            if column == "source_dossier_href":
                cells.append(f"<td>{_dossier_link(row)}</td>")
            else:
                cells.append(f"<td>{escape(str(row.get(column, '')))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return _table_shell(columns, rows)


def _dossier_link(row: pd.Series) -> str:
    href = str(row.get("source_dossier_href") or "")
    path = str(row.get("dossier_path") or "")
    if not href or not _safe_href(href):
        return escape(path)
    return f'<a href="{escape(href, quote=True)}">{escape(path)}</a>'


def _safe_href(href: str) -> bool:
    parsed = urlparse(href)
    return not parsed.scheme and not href.startswith("/") and "\x00" not in href


def _table(frame: pd.DataFrame) -> str:
    columns = [str(column) for column in frame.columns]
    rows = []
    for _, row in frame.iterrows():
        rows.append(
            "<tr>"
            + "".join(
                f"<td>{escape(str(row.get(column, '')))}</td>" for column in columns
            )
            + "</tr>"
        )
    return _table_shell(columns, rows)


def _table_shell(columns: list[str], rows: list[str]) -> str:
    header = "".join(f"<th>{escape(column)}</th>" for column in columns)
    body = (
        "\n".join(rows)
        or f'<tr><td colspan="{len(columns)}" class="muted">None</td></tr>'
    )
    return f"<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>"


def _limitations(action_queue: pd.DataFrame) -> str:
    values = []
    if "portfolio_limitations" in action_queue:
        for value in action_queue["portfolio_limitations"]:
            values.extend(
                part.strip() for part in str(value).split(";") if part.strip()
            )
    tags = _tags(tuple(dict.fromkeys(values)))
    return tags or '<p class="muted">None</p>'


def _tags(values: tuple[str, ...]) -> str:
    return " ".join(f"<span>{escape(value)}</span>" for value in values)


__all__ = ["render_field_architecture_portfolio_html"]
