# ABOUTME: Correlation analysis report with lag heatmaps and cross-correlation plots.
"""
Correlation Analysis Report

Generates interactive HTML reports showing the lagged cross-correlation
between safety observations and incidents, including peak summary
charts and rolling correlation heatmaps.
"""

from typing import Dict, List, Optional

import numpy as np
import plotly.graph_objects as go

from worldenergydata.common import get_logger
from worldenergydata.modules.safety_analysis.core.models import CorrelationResult
from worldenergydata.modules.safety_analysis.reports.base_report import BaseReport

logger = get_logger(__name__)


class CorrelationReport(BaseReport):
    """Generates correlation analysis reports between observations and incidents."""

    def __init__(
        self,
        title: str = "Observation-Incident Correlation Report",
    ) -> None:
        super().__init__(
            title=title,
            subtitle="Lag Cross-Correlation Analysis",
        )

    @classmethod
    def from_results(
        cls,
        results: List[CorrelationResult],
        heatmap_data: Optional[Dict[str, List[List[float]]]] = None,
    ) -> "CorrelationReport":
        """Build a complete correlation report from analysis results.

        Args:
            results: List of CorrelationResult objects (one per asset).
            heatmap_data: Optional dict mapping asset_id to a 2-D list
                suitable for a rolling-correlation heatmap.

        Returns:
            Populated CorrelationReport ready for HTML generation.
        """
        report = cls()

        report.add_summary_stat("Assets Analysed", str(len(results)))

        if results:
            best = max(results, key=lambda r: abs(r.peak_correlation))
            report.add_summary_stat(
                "Strongest Correlation",
                f"{best.peak_correlation:.3f}",
            )
            report.add_summary_stat(
                "Best Lag",
                f"{best.peak_lag}",
                "periods",
            )

        for result in results:
            report.add_section(
                title=f"Lag Correlation - {result.asset_id}",
                figure=cls._lag_correlation_chart(result),
                description=(
                    f"Peak r={result.peak_correlation:.3f} " f"at lag={result.peak_lag}"
                ),
            )

        if heatmap_data:
            for asset_id, matrix in heatmap_data.items():
                report.add_section(
                    title=f"Rolling Correlation Heatmap - {asset_id}",
                    figure=cls._rolling_heatmap(matrix),
                    description="Rolling window correlation over time and lag.",
                )

        if len(results) > 1:
            report.add_section(
                title="Peak Correlation by Asset",
                figure=cls._peak_summary_chart(results),
                description="Comparison of peak absolute correlations across assets.",
            )

        return report

    # ------------------------------------------------------------------
    # Chart builders
    # ------------------------------------------------------------------

    @staticmethod
    def _lag_correlation_chart(result: CorrelationResult) -> go.Figure:
        """Plotly line chart of correlation vs lag."""
        fig = go.Figure(
            data=[
                go.Scatter(
                    x=result.lag_values,
                    y=result.correlation_values,
                    mode="lines+markers",
                    line={"color": "#667eea", "width": 2},
                    marker={"size": 4},
                )
            ]
        )
        fig.add_vline(
            x=result.peak_lag,
            line_dash="dash",
            line_color="#e53e3e",
            annotation_text=f"Peak lag={result.peak_lag}",
        )
        fig.update_layout(
            template="plotly_white",
            xaxis_title="Lag (periods)",
            yaxis_title="Correlation",
            hovermode="x unified",
            height=400,
        )
        return fig

    @staticmethod
    def _rolling_heatmap(
        matrix: List[List[float]],
    ) -> go.Figure:
        """Plotly heatmap of rolling correlations."""
        z = np.array(matrix) if not isinstance(matrix, np.ndarray) else matrix
        fig = go.Figure(
            data=go.Heatmap(
                z=z,
                colorscale="RdBu",
                zmid=0,
                hovertemplate="Row %{y}, Col %{x}: %{z:.3f}<extra></extra>",
            )
        )
        fig.update_layout(
            template="plotly_white",
            xaxis_title="Lag",
            yaxis_title="Window Index",
            height=450,
        )
        return fig

    @staticmethod
    def _peak_summary_chart(
        results: List[CorrelationResult],
    ) -> go.Figure:
        """Bar chart of peak correlations by asset."""
        asset_ids = [r.asset_id for r in results]
        peaks = [r.peak_correlation for r in results]
        colors = ["#e53e3e" if p < 0 else "#667eea" for p in peaks]

        fig = go.Figure(
            data=[
                go.Bar(
                    x=asset_ids,
                    y=peaks,
                    marker_color=colors,
                )
            ]
        )
        fig.update_layout(
            template="plotly_white",
            xaxis_title="Asset",
            yaxis_title="Peak Correlation",
            height=400,
        )
        return fig
