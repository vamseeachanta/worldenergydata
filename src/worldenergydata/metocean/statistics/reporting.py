"""
ABOUTME: HTML report combining all metocean statistical analyses.
ABOUTME: Assembles EVA, joint probability, contours, and weather window plots.

Generates a self-contained Plotly HTML report — no external dependencies
at render time (all assets inlined via plotly.io.to_html with full_html=True).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Optional

import plotly.graph_objects as go
import plotly.io as pio

from worldenergydata.metocean.statistics.environmental_contours import (
    ContourResult,
    EnvironmentalContour,
)
from worldenergydata.metocean.statistics.eva import EVAResult, ExtremeValueAnalysis
from worldenergydata.metocean.statistics.joint_probability import JointModel
from worldenergydata.metocean.statistics.weather_windows import OperabilityResult


@dataclass
class _ReportSection:
    """Internal container for a single report section."""

    title: str
    html_content: str
    section_type: str  # 'eva', 'joint', 'contour', 'weather_windows'


class MetoceanReport:
    """
    Assemble a self-contained Plotly HTML report of metocean analyses.

    Sections are added via ``add_*`` methods and rendered together via
    ``save_html``.  Each section embeds its Plotly figure inline.

    Examples
    --------
    >>> report = MetoceanReport("GoM Site A", lat=29.0, lon=-94.0)
    >>> report.add_eva(eva_result)
    >>> report.add_joint(joint_model)
    >>> report.save_html("metocean_report.html")
    """

    def __init__(
        self,
        location_name: str,
        lat: float,
        lon: float,
    ) -> None:
        self.location_name = location_name
        self.lat = lat
        self.lon = lon
        self._sections: list[_ReportSection] = []
        self._generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat(
            timespec="seconds"
        )

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def add_eva(self, result: EVAResult) -> None:
        """
        Add an Extreme Value Analysis section.

        Parameters
        ----------
        result:
            EVAResult from ExtremeValueAnalysis.fit_pot / fit_annual_maxima.
        """
        eva = ExtremeValueAnalysis()
        fig = eva.plot_return_period(result)
        table = eva.return_period_table(result)

        fig_html = self._fig_to_html(fig)
        table_html = table.to_html(
            classes="report-table",
            float_format=lambda x: f"{x:.3f}",
            border=0,
        )

        content = f"""
        <h2>Extreme Value Analysis</h2>
        <p>Method: <strong>{result.method}</strong> | Distribution: <strong>{result.distribution}</strong></p>
        {("" if result.threshold is None else f"<p>Threshold: {result.threshold:.3f}</p>")}
        <h3>Return Period Table</h3>
        {table_html}
        <h3>Return Period Curve</h3>
        {fig_html}
        """

        self._sections.append(
            _ReportSection(
                title="Extreme Value Analysis",
                html_content=content,
                section_type="eva",
            )
        )

    def add_joint(self, model: JointModel) -> None:
        """
        Add a joint probability model section.

        Parameters
        ----------
        model:
            JointModel from JointProbabilityModel.fit().
        """
        params_html = self._params_to_html(
            {
                "n_samples": model.n_samples,
                "marginal_hs_distribution": model.marginal_hs.get("distribution", ""),
                **{
                    f"marginal_hs_{k}": v
                    for k, v in model.marginal_hs.items()
                    if k != "distribution"
                },
                "conditional_tp_model": model.conditional_tp.get("model", ""),
                "mu_tp": model.conditional_tp.get("mu", ""),
                "sigma_tp": model.conditional_tp.get("sigma", ""),
            }
        )

        content = f"""
        <h2>Joint Probability Model</h2>
        <p>Conditional Hs-Tp joint distribution (metocean-stats CMA method)</p>
        {params_html}
        """

        self._sections.append(
            _ReportSection(
                title="Joint Probability Model",
                html_content=content,
                section_type="joint",
            )
        )

    def add_contour(self, result: ContourResult) -> None:
        """
        Add an environmental contour section.

        Parameters
        ----------
        result:
            ContourResult from EnvironmentalContour.iform / isorm.
        """
        ec = EnvironmentalContour()
        fig = ec.plot_contour(result)
        fig_html = self._fig_to_html(fig)

        content = f"""
        <h2>Environmental Contour</h2>
        <p>Method: <strong>{result.method}</strong> | Return period: <strong>{result.return_period} years</strong></p>
        <p>Contour points: {len(result.hs_values)}</p>
        {fig_html}
        """

        self._sections.append(
            _ReportSection(
                title=f"{result.method} Contour ({result.return_period}-yr)",
                html_content=content,
                section_type="contour",
            )
        )

    def add_weather_windows(self, result: OperabilityResult) -> None:
        """
        Add a weather windows / operability section.

        Parameters
        ----------
        result:
            OperabilityResult from WeatherWindowAnalysis.operability().
        """
        summary_html = self._params_to_html(
            {
                "Threshold": f"{result.threshold:.2f}",
                "Min window (h)": result.min_window_hours,
                "Operability (%)": f"{result.operability_pct:.1f}%",
                "Mean window (h)": f"{result.mean_window_hours:.1f}",
                "Total windows": result.total_windows,
            }
        )

        content = f"""
        <h2>Weather Window Analysis</h2>
        {summary_html}
        """

        self._sections.append(
            _ReportSection(
                title="Weather Windows",
                html_content=content,
                section_type="weather_windows",
            )
        )

    # ------------------------------------------------------------------
    # HTML output
    # ------------------------------------------------------------------

    def save_html(self, path: str) -> None:
        """
        Write the assembled report to a self-contained HTML file.

        Parameters
        ----------
        path:
            File path for the output HTML (e.g. 'report.html').
        """
        html = self._render_html()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)

    def _render_html(self) -> str:
        """Render the full HTML document."""
        toc_items = "\n".join(
            f'<li><a href="#section-{i}">{sec.title}</a></li>'
            for i, sec in enumerate(self._sections)
        )

        sections_html = "\n".join(
            f'<section id="section-{i}">{sec.html_content}</section>'
            for i, sec in enumerate(self._sections)
        )

        # Embed Plotly.js once (CDN reference — small file; avoids 3MB inline)
        plotly_cdn = (
            '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"'
            ' charset="utf-8"></script>'
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Metocean Report — {self.location_name}</title>
  {plotly_cdn}
  <style>
    body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
    h1 {{ color: #1a4a7a; border-bottom: 3px solid #1a4a7a; padding-bottom: 10px; }}
    h2 {{ color: #2c6fad; margin-top: 40px; border-left: 4px solid #2c6fad; padding-left: 12px; }}
    h3 {{ color: #444; }}
    .report-table {{ border-collapse: collapse; margin: 16px 0; }}
    .report-table th, .report-table td {{ padding: 6px 14px; border: 1px solid #ccc; }}
    .report-table th {{ background: #eef2f7; }}
    .summary-table {{ border-collapse: collapse; margin: 12px 0; }}
    .summary-table td {{ padding: 4px 12px; border: 1px solid #ddd; }}
    .meta {{ color: #666; font-size: 0.9em; margin: 8px 0; }}
    nav {{ background: #f4f8ff; border: 1px solid #ccd; padding: 16px; border-radius: 4px; }}
    nav ul {{ list-style: none; padding: 0; }}
    nav li {{ margin: 4px 0; }}
    nav a {{ color: #2c6fad; text-decoration: none; }}
    section {{ margin-bottom: 48px; }}
  </style>
</head>
<body>
  <h1>Metocean Statistical Report</h1>
  <p class="meta">
    <strong>Location:</strong> {self.location_name} &nbsp;|&nbsp;
    <strong>Lat:</strong> {self.lat:.4f}° &nbsp;|&nbsp;
    <strong>Lon:</strong> {self.lon:.4f}° &nbsp;|&nbsp;
    <strong>Generated:</strong> {self._generated_at}
  </p>
  <nav>
    <strong>Contents</strong>
    <ul>{toc_items}</ul>
  </nav>
  {sections_html}
</body>
</html>"""

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fig_to_html(fig: go.Figure) -> str:
        """Render a Plotly figure to an HTML div (no full page wrapping)."""
        return pio.to_html(
            fig,
            full_html=False,
            include_plotlyjs=False,
            config={"displayModeBar": True, "responsive": True},
        )

    @staticmethod
    def _params_to_html(params: dict) -> str:
        """Render a key-value dict as an HTML summary table."""
        rows = "".join(
            f"<tr><td><strong>{k}</strong></td><td>{v}</td></tr>"
            for k, v in params.items()
        )
        return f'<table class="summary-table">{rows}</table>'
