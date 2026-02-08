# ABOUTME: Interactive Plotly HTML dashboard for HSE Risk Index visualization.
"""
HSE Risk Index Dashboard

Generates a self-contained interactive HTML dashboard from CompositeScore
data, including heatmap, bar chart, radar charts, risk matrix, treemap,
and a methodology documentation section.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import plotly.graph_objects as go

from worldenergydata.common import get_logger
from worldenergydata.safety_analysis.risk_index.models import (
    ActivityRiskScore,
    CompositeScore,
    RiskCategory,
)

logger = get_logger(__name__)


class RiskDashboard:
    """Generates interactive Plotly HTML dashboard for risk index visualization."""

    CATEGORY_COLORS = {
        RiskCategory.LOW: "#2ecc71",
        RiskCategory.MEDIUM: "#f39c12",
        RiskCategory.HIGH: "#e74c3c",
        RiskCategory.CRITICAL: "#8e44ad",
    }

    DIMENSION_LABELS = ["Acute", "Chronic", "Compliance"]

    def generate(self, composite: CompositeScore) -> str:
        """Generate complete HTML dashboard from CompositeScore.

        Args:
            composite: The composite score container with activity scores.

        Returns:
            A self-contained HTML string with embedded Plotly charts.
        """
        scores = composite.scores
        figures: Dict[str, go.Figure] = {}

        if scores:
            figures["heatmap"] = self._create_heatmap(scores)
            figures["bar"] = self._create_composite_bar(scores)
            figures["radar"] = self._create_radar_charts(scores)
            figures["matrix"] = self._create_risk_matrix(scores)
            figures["treemap"] = self._create_treemap(scores)

        methodology = self._create_methodology_section(composite)
        metadata = {
            "generated_at": datetime.now(tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"
            ),
            "activity_count": len(scores),
        }
        return self._assemble_html(figures, methodology, metadata)

    def save(self, composite: CompositeScore, path: str | Path) -> Path:
        """Generate and save dashboard to HTML file.

        Args:
            composite: The composite score container.
            path: Destination file path for the HTML.

        Returns:
            The resolved output path.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        html = self.generate(composite)
        path.write_text(html, encoding="utf-8")
        logger.info("Dashboard saved: %s", path)
        return path

    # ------------------------------------------------------------------
    # Chart builders
    # ------------------------------------------------------------------

    def _create_heatmap(self, scores: List[ActivityRiskScore]) -> go.Figure:
        """Activity vs. Dimension heatmap, color-coded by score."""
        activities = [s.activity_name for s in scores]
        z_values = [
            [s.acute.score, s.chronic.score, s.compliance.score] for s in scores
        ]

        fig = go.Figure(
            data=go.Heatmap(
                z=z_values,
                x=self.DIMENSION_LABELS,
                y=activities,
                colorscale="RdYlGn_r",
                zmin=1.0,
                zmax=10.0,
                colorbar={"title": "Score"},
                text=[[f"{v:.1f}" for v in row] for row in z_values],
                texttemplate="%{text}",
                hovertemplate=(
                    "Activity: %{y}<br>"
                    "Dimension: %{x}<br>"
                    "Score: %{z:.1f}<extra></extra>"
                ),
            )
        )
        fig.update_layout(
            title="Risk Heatmap: Activity vs. Dimension",
            xaxis_title="Dimension",
            yaxis_title="Activity",
            height=max(300, 80 * len(activities)),
        )
        return fig

    def _create_composite_bar(self, scores: List[ActivityRiskScore]) -> go.Figure:
        """Ranked composite risk horizontal bar chart."""
        sorted_scores = sorted(scores, key=lambda s: s.composite_score)
        names = [s.activity_name for s in sorted_scores]
        values = [s.composite_score for s in sorted_scores]
        colors = [self.CATEGORY_COLORS[s.category] for s in sorted_scores]

        fig = go.Figure(
            data=go.Bar(
                x=values,
                y=names,
                orientation="h",
                marker={"color": colors},
                text=[f"{v:.1f}" for v in values],
                textposition="outside",
                hovertemplate=(
                    "Activity: %{y}<br>" "Composite Risk: %{x:.2f}<extra></extra>"
                ),
            )
        )
        fig.update_layout(
            title="Composite Risk Index by Activity",
            xaxis_title="Composite Score (1-10)",
            yaxis_title="Activity",
            xaxis={"range": [0, 11]},
            height=max(300, 60 * len(names)),
        )
        return fig

    def _create_radar_charts(self, scores: List[ActivityRiskScore]) -> go.Figure:
        """Per-activity radar/polar charts (3 axes: acute, chronic, compliance)."""
        fig = go.Figure()
        theta = self.DIMENSION_LABELS + [self.DIMENSION_LABELS[0]]

        for s in scores:
            r = [
                s.acute.score,
                s.chronic.score,
                s.compliance.score,
                s.acute.score,
            ]
            fig.add_trace(
                go.Scatterpolar(
                    r=r,
                    theta=theta,
                    fill="toself",
                    name=s.activity_name,
                    hovertemplate=(
                        "%{theta}: %{r:.1f}<extra>" + s.activity_name + "</extra>"
                    ),
                )
            )

        fig.update_layout(
            title="Dimension Profile Radar Charts",
            polar={
                "radialaxis": {"visible": True, "range": [0, 10]},
            },
            showlegend=True,
            height=500,
        )
        return fig

    def _create_risk_matrix(self, scores: List[ActivityRiskScore]) -> go.Figure:
        """Frequency vs. Severity scatter plot (classic risk matrix)."""
        x_vals = []
        y_vals = []
        sizes = []
        names = []
        colors = []

        for s in scores:
            frequency = s.acute.raw_metrics.get("total_incidents", 0)
            severity = s.acute.raw_metrics.get("fatality_rate", 0)
            x_vals.append(frequency)
            y_vals.append(severity)
            sizes.append(max(10, s.composite_score * 8))
            names.append(s.activity_name)
            colors.append(self.CATEGORY_COLORS[s.category])

        fig = go.Figure(
            data=go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="markers+text",
                marker={
                    "size": sizes,
                    "color": colors,
                    "line": {"width": 1, "color": "#333"},
                    "opacity": 0.8,
                },
                text=names,
                textposition="top center",
                hovertemplate=(
                    "Activity: %{text}<br>"
                    "Frequency: %{x}<br>"
                    "Severity: %{y:.3f}<extra></extra>"
                ),
            )
        )
        fig.update_layout(
            title="Risk Matrix: Frequency vs. Severity",
            xaxis_title="Frequency (Total Incidents)",
            yaxis_title="Severity (Fatality Rate)",
            height=500,
        )
        return fig

    def _create_treemap(self, scores: List[ActivityRiskScore]) -> go.Figure:
        """Hierarchical activity risk breakdown treemap."""
        labels = ["All Activities"]
        parents = [""]
        values = [0]
        colors = ["#f5f7fa"]

        for s in scores:
            labels.append(s.activity_name)
            parents.append("All Activities")
            values.append(round(s.composite_score, 2))
            colors.append(self.CATEGORY_COLORS[s.category])

            # Sub-dimensions as children of the activity
            for dim_label, dim_score in [
                ("Acute", s.acute),
                ("Chronic", s.chronic),
                ("Compliance", s.compliance),
            ]:
                child_label = f"{s.activity_code} - {dim_label}"
                labels.append(child_label)
                parents.append(s.activity_name)
                values.append(round(dim_score.score, 2))
                colors.append(self.CATEGORY_COLORS[s.category])

        fig = go.Figure(
            data=go.Treemap(
                labels=labels,
                parents=parents,
                values=values,
                marker={"colors": colors},
                textinfo="label+value",
                hovertemplate=("%{label}<br>Score: %{value:.1f}<extra></extra>"),
            )
        )
        fig.update_layout(
            title="Risk Treemap: Activity and Dimension Breakdown",
            height=500,
        )
        return fig

    # ------------------------------------------------------------------
    # Methodology section
    # ------------------------------------------------------------------

    def _create_methodology_section(self, composite: CompositeScore) -> str:
        """HTML section documenting the scoring methodology."""
        weights = composite.metadata.get("weights", {})
        method = composite.metadata.get("method", "unknown")
        version = composite.metadata.get("version", "n/a")

        weight_rows = ""
        if weights:
            for dim, w in weights.items():
                weight_rows += f"<tr><td>{dim.title()}</td>" f"<td>{w}</td></tr>\n"

        sources_list = set()
        for s in composite.scores:
            sources_list.update(s.sources)
        sources_html = ", ".join(sorted(sources_list)) if sources_list else "N/A"

        return f"""
<div class="methodology-section">
    <h2>Methodology</h2>
    <div class="methodology-content">
        <h3>Scoring Approach</h3>
        <p>
            The HSE Risk Index uses a three-dimensional framework that
            evaluates each activity across <strong>Acute</strong>,
            <strong>Chronic</strong>, and <strong>Compliance</strong>
            dimensions. Each dimension is normalized to a 1-10 scale
            using the <em>{method}</em> method.
        </p>

        <h3>Dimension Weights</h3>
        <table class="methodology-table">
            <thead>
                <tr><th>Dimension</th><th>Weight</th></tr>
            </thead>
            <tbody>
                {weight_rows if weight_rows else
                 "<tr><td colspan='2'>No weights specified</td></tr>"}
            </tbody>
        </table>

        <h3>Risk Categories</h3>
        <ul>
            <li><span class="cat-low">LOW</span>: 1.0 - 3.0</li>
            <li><span class="cat-medium">MEDIUM</span>: 3.1 - 5.0</li>
            <li><span class="cat-high">HIGH</span>: 5.1 - 7.0</li>
            <li><span class="cat-critical">CRITICAL</span>: 7.1 - 10.0</li>
        </ul>

        <h3>Data Sources</h3>
        <p>{sources_html}</p>

        <h3>Caveats</h3>
        <ul>
            <li>Scores reflect relative risk within the assessed activity set,
                not absolute risk levels.</li>
            <li>Confidence varies by data availability; check individual
                activity confidence ratings.</li>
            <li>Normalization method: <em>{method}</em> (v{version}).</li>
        </ul>
    </div>
</div>"""

    # ------------------------------------------------------------------
    # HTML assembly
    # ------------------------------------------------------------------

    def _assemble_html(
        self,
        figures: Dict[str, go.Figure],
        methodology: str,
        metadata: dict,
    ) -> str:
        """Assemble all figures and methodology into a single HTML page."""
        chart_sections = []
        chart_scripts = []

        chart_titles = {
            "heatmap": "Risk Heatmap",
            "bar": "Composite Risk Rankings",
            "radar": "Dimension Profile Radar",
            "matrix": "Risk Matrix",
            "treemap": "Risk Treemap",
        }

        for _idx, (key, fig) in enumerate(figures.items()):
            div_id = f"chart-{key}"
            title = chart_titles.get(key, key.title())
            chart_sections.append(
                f'<div class="plot-container">'
                f"<h2>{title}</h2>"
                f'<div id="{div_id}" class="plot"></div>'
                f"</div>"
            )
            plot_json = fig.to_json()
            chart_scripts.append(
                f"(function() {{"
                f"  var d = {plot_json};"
                f"  Plotly.newPlot('{div_id}', d.data, d.layout, "
                f"{{responsive: true}});"
                f"}})();"
            )

        generated_at = metadata.get("generated_at", "")
        activity_count = metadata.get("activity_count", 0)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HSE Risk Index Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
    <style>{self._css()}</style>
</head>
<body>
<div class="container">
    <div class="report-header">
        <h1>HSE Risk Index Dashboard</h1>
        <p class="report-subtitle">Three-Dimensional Risk Assessment</p>
        <p class="report-meta">Generated: {generated_at}</p>
    </div>

    <div class="summary-stats">
        <div class="stat-card">
            <div class="stat-label">Activities Assessed</div>
            <div class="stat-value">{activity_count}</div>
        </div>
    </div>

    {"".join(chart_sections)}

    {methodology}

    <div class="footer">
        <p>HSE Risk Index Dashboard | Generated {generated_at}</p>
        <p>All plots are interactive: hover for details,
           click and drag to zoom, double-click to reset</p>
    </div>
</div>

<script>
{"".join(chart_scripts)}
</script>
</body>
</html>"""

    @staticmethod
    def _css() -> str:
        """Dashboard-specific responsive CSS."""
        return """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                 Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    background-color: #f5f7fa;
    padding: 20px;
    color: #2d3748;
}
.container { max-width: 1400px; margin: 0 auto; }
.report-header {
    background: linear-gradient(135deg, #e74c3c 0%, #8e44ad 100%);
    color: white; padding: 40px; border-radius: 12px;
    margin-bottom: 30px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
.report-header h1 { font-size: 2.5em; margin-bottom: 10px; font-weight: 700; }
.report-subtitle { font-size: 1.2em; opacity: 0.95; margin-bottom: 8px; }
.report-meta { font-size: 0.95em; opacity: 0.8; }
.summary-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 20px; margin-bottom: 30px;
}
.stat-card {
    background: white; padding: 25px; border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.08);
}
.stat-label {
    font-size: 0.9em; color: #718096; margin-bottom: 8px;
    text-transform: uppercase; letter-spacing: 0.5px;
}
.stat-value { font-size: 2.5em; font-weight: 700; color: #e74c3c; }
.plot-container {
    background: white; padding: 30px; border-radius: 10px;
    margin-bottom: 25px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.08);
}
.plot-container h2 {
    font-size: 1.5em; margin-bottom: 15px; color: #2d3748; font-weight: 600;
}
.plot { width: 100%; }
.methodology-section {
    background: white; padding: 30px; border-radius: 10px;
    margin-bottom: 25px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.08);
}
.methodology-section h2 {
    font-size: 1.5em; margin-bottom: 20px; color: #2d3748; font-weight: 600;
}
.methodology-content h3 {
    font-size: 1.15em; margin: 18px 0 8px; color: #4a5568;
}
.methodology-content p {
    line-height: 1.7; margin-bottom: 10px; color: #4a5568;
}
.methodology-content ul {
    margin-left: 20px; margin-bottom: 10px; color: #4a5568;
}
.methodology-content li { margin-bottom: 6px; line-height: 1.6; }
.methodology-table {
    width: 100%; border-collapse: collapse; margin-bottom: 15px;
}
.methodology-table th, .methodology-table td {
    padding: 10px 15px; border: 1px solid #e2e8f0; text-align: left;
}
.methodology-table th { background: #f7fafc; font-weight: 600; }
.cat-low { color: #2ecc71; font-weight: 600; }
.cat-medium { color: #f39c12; font-weight: 600; }
.cat-high { color: #e74c3c; font-weight: 600; }
.cat-critical { color: #8e44ad; font-weight: 600; }
.footer {
    background: white; padding: 20px; border-radius: 10px;
    margin-top: 30px; text-align: center; color: #718096; font-size: 0.9em;
}
@media (max-width: 768px) {
    .report-header { padding: 25px; }
    .report-header h1 { font-size: 1.8em; }
    .summary-stats { grid-template-columns: 1fr; }
    .stat-value { font-size: 2em; }
}
"""
