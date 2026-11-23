# ABOUTME: Base HTML report generator with Plotly interactive charts and summary cards.
"""
Base Report Generator

Provides the foundation for all safety analysis HTML reports with
Plotly interactive charts, responsive summary cards, and a
professional gradient header layout.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import List

import plotly.graph_objects as go

from worldenergydata.common import get_logger

logger = get_logger(__name__)


class ReportSection:
    """A section containing a title, Plotly figure, and optional description."""

    def __init__(
        self,
        title: str,
        figure: go.Figure,
        description: str = "",
    ) -> None:
        self.title = title
        self.figure = figure
        self.description = description


class SummaryStat:
    """A summary statistic displayed as a card in the report header area."""

    def __init__(self, label: str, value: str, unit: str = "") -> None:
        self.label = label
        self.value = value
        self.unit = unit


class BaseReport:
    """Base class for generating interactive HTML reports.

    Subclasses should add sections and summary stats, then call
    ``generate_html`` to write the final HTML file.
    """

    def __init__(self, title: str, subtitle: str = "") -> None:
        self.title = title
        self.subtitle = subtitle
        self.sections: List[ReportSection] = []
        self.summary_stats: List[SummaryStat] = []

    def add_section(
        self,
        title: str,
        figure: go.Figure,
        description: str = "",
    ) -> None:
        """Append a chart section to the report."""
        self.sections.append(ReportSection(title, figure, description))

    def add_summary_stat(
        self,
        label: str,
        value: str,
        unit: str = "",
    ) -> None:
        """Append a summary statistic card."""
        self.summary_stats.append(SummaryStat(label, value, unit))

    def generate_html(self, output_path: Path) -> Path:
        """Generate the full HTML report and write to disk.

        Args:
            output_path: Destination file path for the HTML report.

        Returns:
            The resolved output path.
        """
        html = self._render()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
        logger.info("Report generated: %s", output_path)
        return output_path

    # ------------------------------------------------------------------
    # Internal rendering helpers
    # ------------------------------------------------------------------

    def _render(self) -> str:
        """Combine all parts into a complete HTML document."""
        parts = [
            self._build_head(),
            '<body>\n<div class="container">',
            self._build_header(),
            self._build_summary_cards(),
            self._build_sections(),
            self._build_footer(),
            "</div>",
            self._build_scripts(),
            "</body>\n</html>",
        ]
        return "\n".join(parts)

    def _build_head(self) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
    <style>{self._css()}</style>
</head>"""

    def _build_header(self) -> str:
        subtitle_html = ""
        if self.subtitle:
            subtitle_html = f'<p class="report-subtitle">{self.subtitle}</p>'
        now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return f"""<div class="report-header">
    <h1>{self.title}</h1>
    {subtitle_html}
    <p class="report-meta">Generated: {now}</p>
</div>"""

    def _build_summary_cards(self) -> str:
        if not self.summary_stats:
            return ""
        cards = []
        for stat in self.summary_stats:
            unit_span = (
                f'<span class="stat-unit">{stat.unit}</span>' if stat.unit else ""
            )
            cards.append(
                f'<div class="stat-card">'
                f'<div class="stat-label">{stat.label}</div>'
                f'<div class="stat-value">{stat.value}{unit_span}</div>'
                f"</div>"
            )
        return '<div class="summary-stats">\n' + "\n".join(cards) + "\n</div>"

    def _build_sections(self) -> str:
        parts = []
        for idx, section in enumerate(self.sections):
            desc_html = ""
            if section.description:
                desc_html = f'<p class="section-desc">{section.description}</p>'
            parts.append(
                f'<div class="plot-container">'
                f"<h2>{section.title}</h2>"
                f"{desc_html}"
                f'<div id="plot{idx}" class="plot"></div>'
                f"</div>"
            )
        return "\n".join(parts)

    def _build_footer(self) -> str:
        now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return (
            '<div class="footer">'
            f"<p>Safety Analysis Report | Generated {now}</p>"
            "<p>All plots are interactive: hover for details, "
            "click and drag to zoom, double-click to reset</p>"
            "</div>"
        )

    def _build_scripts(self) -> str:
        lines = ["<script>"]
        for idx, section in enumerate(self.sections):
            plot_json = section.figure.to_json()
            lines.append(
                f"(function() {{"
                f"  var d = {plot_json};"
                f"  Plotly.newPlot('plot{idx}', d.data, d.layout, "
                f"{{responsive: true}});"
                f"}})();"
            )
        lines.append("</script>")
        return "\n".join(lines)

    @staticmethod
    def _css() -> str:
        """Return professional responsive CSS."""
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
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
    transition: transform 0.2s, box-shadow 0.2s;
}
.stat-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 16px rgba(0,0,0,0.12);
}
.stat-label {
    font-size: 0.9em; color: #718096; margin-bottom: 8px;
    text-transform: uppercase; letter-spacing: 0.5px;
}
.stat-value { font-size: 2.5em; font-weight: 700; color: #667eea; line-height: 1; }
.stat-unit { font-size: 0.5em; color: #a0aec0; margin-left: 5px; }
.plot-container {
    background: white; padding: 30px; border-radius: 10px;
    margin-bottom: 25px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.08);
}
.plot-container h2 {
    font-size: 1.5em; margin-bottom: 15px; color: #2d3748; font-weight: 600;
}
.section-desc { color: #718096; margin-bottom: 15px; font-size: 0.95em; }
.plot { width: 100%; }
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
