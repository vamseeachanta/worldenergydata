# ABOUTME: Generates HTML documentation of the HSE risk scoring methodology.
"""HSE Risk Index Methodology Documentation Generator.

Produces a standalone HTML section describing the three-dimensional risk
scoring framework, data sources, normalization approach, composite formula,
risk categories, and caveats.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def generate_methodology_html(metadata: Optional[Dict[str, Any]] = None) -> str:
    """Generate HTML documentation of the risk scoring methodology.

    Args:
        metadata: Optional dict with generation metadata (timestamp, version, etc.)

    Returns:
        HTML string containing the methodology documentation section.
    """
    timestamp = _resolve_timestamp(metadata)
    version = (metadata or {}).get("version", "1.0")

    sections = [
        _css(),
        _header(version, timestamp),
        _overview_section(),
        _data_sources_section(),
        _scoring_method_section(),
        _risk_categories_section(),
        _caveats_section(),
        _footer(timestamp),
    ]
    return "\n".join(sections)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _resolve_timestamp(metadata: Optional[Dict[str, Any]]) -> str:
    """Extract or generate an ISO-8601 timestamp string."""
    if metadata and "timestamp" in metadata:
        ts = metadata["timestamp"]
        if isinstance(ts, datetime):
            return ts.isoformat()
        return str(ts)
    return datetime.now(timezone.utc).isoformat()


def _css() -> str:
    """Inline CSS for the methodology section."""
    return """<style>
.methodology {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    max-width: 900px;
    margin: 0 auto;
    padding: 2rem;
    color: #1a1a2e;
    line-height: 1.6;
}
.methodology h1 {
    font-size: 1.8rem;
    border-bottom: 3px solid #0f3460;
    padding-bottom: 0.5rem;
    color: #0f3460;
}
.methodology h2 {
    font-size: 1.3rem;
    margin-top: 2rem;
    color: #16213e;
}
.methodology table {
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
    font-size: 0.95rem;
}
.methodology th {
    background: #0f3460;
    color: #fff;
    padding: 0.6rem 0.8rem;
    text-align: left;
}
.methodology td {
    padding: 0.5rem 0.8rem;
    border-bottom: 1px solid #ddd;
}
.methodology tr:nth-child(even) {
    background: #f4f4f8;
}
.methodology .formula {
    background: #f0f4f8;
    border-left: 4px solid #0f3460;
    padding: 1rem 1.2rem;
    margin: 1rem 0;
    font-family: 'Courier New', Courier, monospace;
    font-size: 0.95rem;
}
.methodology .category-badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 4px;
    font-weight: bold;
    font-size: 0.85rem;
    color: #fff;
}
.methodology .cat-low { background: #27ae60; }
.methodology .cat-medium { background: #f39c12; }
.methodology .cat-high { background: #e74c3c; }
.methodology .cat-critical { background: #8e44ad; }
.methodology .caveat-list li {
    margin-bottom: 0.5rem;
}
.methodology .meta {
    font-size: 0.85rem;
    color: #666;
    margin-top: 2rem;
    border-top: 1px solid #ddd;
    padding-top: 0.5rem;
}
</style>"""


def _header(version: str, timestamp: str) -> str:
    return (
        '<div class="methodology">\n'
        "<h1>HSE Risk Index Methodology</h1>\n"
        f'<p class="meta">Version {version}</p>'
    )


def _overview_section() -> str:
    return """<h2>1. Overview</h2>
<p>
The HSE Risk Index quantifies occupational and environmental risk across
energy-sector activities using a <strong>three-dimensional framework</strong>:
</p>
<ul>
    <li><strong>Acute Risk</strong> &mdash; likelihood and severity of sudden
        incidents (fatalities, injuries, explosions, spills).</li>
    <li><strong>Chronic Risk</strong> &mdash; long-term exposure hazards
        proxied by toxic chemical releases (EPA TRI).</li>
    <li><strong>Compliance Risk</strong> &mdash; regulatory non-compliance
        rate derived from inspection and violation records.</li>
</ul>
<p>
Each activity receives a composite score on a 1&ndash;10 scale, where 1
represents the lowest relative risk and 10 the highest within the dataset.
</p>"""


def _data_sources_section() -> str:
    return """<h2>2. Data Sources</h2>
<table>
    <thead>
        <tr>
            <th>Source</th>
            <th>Weight</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>BSEE</td>
            <td>0.30</td>
            <td>Mandatory federal offshore incident reporting
                (Bureau of Safety and Environmental Enforcement)</td>
        </tr>
        <tr>
            <td>Marine Safety</td>
            <td>0.25</td>
            <td>Multi-authority maritime incident data
                (USCG, NTSB marine investigations)</td>
        </tr>
        <tr>
            <td>OSHA</td>
            <td>0.20</td>
            <td>Onshore workplace safety accident and injury data
                (Occupational Safety and Health Administration)</td>
        </tr>
        <tr>
            <td>PHMSA</td>
            <td>0.15</td>
            <td>Pipeline-specific incident data
                (Pipeline and Hazardous Materials Safety Administration)</td>
        </tr>
        <tr>
            <td>EPA TRI</td>
            <td>0.10</td>
            <td>Toxic Release Inventory &mdash; chronic exposure proxy
                (Environmental Protection Agency)</td>
        </tr>
    </tbody>
</table>
<p>
Source weights reflect reporting completeness, regulatory mandate strength,
and relevance to energy-sector occupational risk. Weights sum to 1.0.
</p>"""


def _scoring_method_section() -> str:
    return """<h2>3. Scoring Method</h2>

<h3>3.1 Percentile-Rank Normalization</h3>
<p>
Raw metrics (fatality rates, injury rates, release volumes, violation rates)
are converted to percentile ranks within the dataset, then mapped to a
1&ndash;10 integer scale. This ensures scores reflect relative standing
rather than absolute magnitudes, making cross-source comparison meaningful.
</p>

<h3>3.2 Dimension Weights</h3>
<table>
    <thead>
        <tr>
            <th>Dimension</th>
            <th>Sub-metric</th>
            <th>Weight within Dimension</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td rowspan="3"><strong>Acute</strong></td>
            <td>Fatality rate</td>
            <td>0.40</td>
        </tr>
        <tr>
            <td>Injury rate</td>
            <td>0.35</td>
        </tr>
        <tr>
            <td>Weighted incident count</td>
            <td>0.25</td>
        </tr>
        <tr>
            <td><strong>Chronic</strong></td>
            <td>TRI carcinogen release (lbs)</td>
            <td>1.00</td>
        </tr>
        <tr>
            <td><strong>Compliance</strong></td>
            <td>INC (non-compliance) rate</td>
            <td>1.00</td>
        </tr>
    </tbody>
</table>

<h3>3.3 Composite Formula</h3>
<div class="formula">
Composite = 0.50 &times; Acute + 0.25 &times; Chronic + 0.25 &times; Compliance
</div>
<p>
The acute dimension receives the highest weight (0.50) because immediate
harm to personnel is the primary safety concern. Chronic and compliance
dimensions each contribute 0.25 to capture long-term exposure and
regulatory standing respectively.
</p>"""


def _risk_categories_section() -> str:
    return """<h2>4. Risk Categories</h2>
<table>
    <thead>
        <tr>
            <th>Category</th>
            <th>Score Range</th>
            <th>Interpretation</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><span class="category-badge cat-low">LOW</span></td>
            <td>1 &ndash; 3</td>
            <td>Below-average risk relative to peer activities</td>
        </tr>
        <tr>
            <td><span class="category-badge cat-medium">MEDIUM</span></td>
            <td>4 &ndash; 5</td>
            <td>Average risk; standard monitoring recommended</td>
        </tr>
        <tr>
            <td><span class="category-badge cat-high">HIGH</span></td>
            <td>6 &ndash; 7</td>
            <td>Above-average risk; enhanced controls warranted</td>
        </tr>
        <tr>
            <td><span class="category-badge cat-critical">CRITICAL</span></td>
            <td>8 &ndash; 10</td>
            <td>Highest relative risk; immediate review recommended</td>
        </tr>
    </tbody>
</table>"""


def _caveats_section() -> str:
    return """<h2>5. Caveats and Limitations</h2>
<ul class="caveat-list">
    <li><strong>Relative rankings, not absolute probabilities.</strong>
        Scores indicate where an activity falls within the dataset, not
        the absolute likelihood of an incident occurring.</li>
    <li><strong>Source coverage varies by domain.</strong>
        BSEE covers offshore operations, OSHA covers onshore workplaces,
        and PHMSA covers pipelines. Activities outside these domains may
        have incomplete coverage.</li>
    <li><strong>Chronic dimension relies on EPA TRI as proxy.</strong>
        The Toxic Release Inventory captures chemical releases but does
        not directly measure worker exposure or health outcomes.</li>
    <li><strong>Low-confidence flag for sparse data.</strong>
        Activities with fewer than 10 total incidents are flagged as
        low confidence. Scores for these activities should be
        interpreted with caution.</li>
    <li><strong>Historical data ranges vary by source.</strong>
        Each regulatory source has different reporting periods and
        update frequencies, which may affect temporal comparability.</li>
</ul>"""


def _footer(timestamp: str) -> str:
    return '<p class="meta">' f"Generated: {timestamp}" "</p>\n" "</div>"
