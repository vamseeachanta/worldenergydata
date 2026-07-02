"""Render self-contained Texas RRC field-opportunity HTML summaries."""

from __future__ import annotations

from html import escape

import pandas as pd

from worldenergydata.texas_rrc.opportunities.quality import FieldOpportunityQuality


def render_field_opportunity_summary_html(
    rankings: pd.DataFrame,
    quality: FieldOpportunityQuality,
) -> str:
    """Render a deterministic HTML summary for opportunity rankings."""
    rows = "\n".join(_table_row(row) for row in _top_rows(rankings))
    arch_rows = "\n".join(
        f"<li>{escape(name)}: {count}</li>"
        for name, count in quality.architecture_class_counts.items()
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Texas RRC Field Opportunity Ranking</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; color: #1f2933; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccd5df; padding: 6px 8px; text-align: left; }}
th {{ background: #eef3f8; }}
.metric {{ display: inline-block; margin: 0 18px 16px 0; }}
.value {{ font-size: 24px; font-weight: 700; }}
.note {{ border-left: 4px solid #7c8b9a; padding-left: 12px; color: #46515c; }}
</style>
</head>
<body>
<h1>Texas RRC Field Opportunity Ranking</h1>
<p class="note">Scores are a screening heuristic from direct Texas RRC-derived
curated artifacts. They are not reserves, economics, tariff, capacity,
right-of-way, or engineered facility-design estimates.</p>
<section>
<div class="metric"><div class="value">{quality.row_count}</div><div>Ranked Fields</div></div>
<div class="metric"><div class="value">{_format(quality.score_max)}</div><div>Top Score</div></div>
<div class="metric"><div class="value">{quality.low_data_confidence_count}</div><div>Low Confidence</div></div>
</section>
<section>
<h2>Architecture Signals</h2>
<ul>{arch_rows}</ul>
</section>
<section>
<h2>Top Ranked Fields</h2>
<table>
<thead>
<tr><th>Rank</th><th>Field</th><th>Score</th><th>Class</th><th>Architecture Signal</th><th>Follow-up</th><th>Drivers</th></tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
</section>
</body>
</html>
"""


def _top_rows(rankings: pd.DataFrame) -> list[dict[str, object]]:
    if rankings.empty:
        return []
    return (
        rankings.head(100).where(pd.notna(rankings.head(100)), None).to_dict("records")
    )


def _table_row(row: dict[str, object]) -> str:
    field = escape(_text(row.get("field_name")))
    path = escape(_text(row.get("report_path")))
    link = f'<a href="{path}">{field}</a>' if path else field
    return (
        "<tr>"
        f"<td>{escape(_text(row.get('opportunity_rank')))}</td>"
        f"<td>{link}</td>"
        f"<td>{escape(_text(row.get('opportunity_score')))}</td>"
        f"<td>{escape(_text(row.get('opportunity_class')))}</td>"
        f"<td>{escape(_text(row.get('architecture_signal_class')))}</td>"
        f"<td>{escape(_text(row.get('recommended_followup')))}</td>"
        f"<td>{escape(_text(row.get('key_drivers')))}</td>"
        "</tr>"
    )


def _format(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


__all__ = [
    "render_field_opportunity_summary_html",
]
