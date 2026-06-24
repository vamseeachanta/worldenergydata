# ABOUTME: Incident analysis report with severity trends and hurt index visualisations.
"""
Incident Analysis Report

Generates interactive HTML reports covering incident severity
distributions, temporal trends, and weighted hurt index charts.
"""

from typing import Optional

import pandas as pd
import plotly.graph_objects as go

from worldenergydata.common import get_logger
from worldenergydata.safety_analysis.analysis.incident_aggregation import (
    aggregate_by_severity,
    aggregate_by_time,
    compute_time_series_hurt_index,
)
from worldenergydata.safety_analysis.config import AnalysisConfig
from worldenergydata.safety_analysis.reports.base_report import BaseReport

logger = get_logger(__name__)


class IncidentReport(BaseReport):
    """Generates incident analysis reports with severity distributions and trends."""

    def __init__(
        self,
        title: str = "Safety Incident Analysis Report",
    ) -> None:
        super().__init__(
            title=title,
            subtitle="Incident Severity & Trend Analysis",
        )

    @classmethod
    def from_dataframe(
        cls,
        incidents_df: pd.DataFrame,
        config: Optional[AnalysisConfig] = None,
    ) -> "IncidentReport":
        """Build a complete incident report from incident data.

        Args:
            incidents_df: DataFrame with standardised incident columns
                (``occurred_at``, ``actual_severity``, ``asset_id``).
            config: Optional analysis configuration for frequency, etc.

        Returns:
            Populated IncidentReport ready for HTML generation.
        """
        config = config or AnalysisConfig()
        report = cls()

        total = len(incidents_df)
        report.add_summary_stat("Total Incidents", f"{total:,}")

        severity_df = aggregate_by_severity(incidents_df)
        for _, row in severity_df.iterrows():
            report.add_summary_stat(
                str(row["actual_severity"]).replace("_", " ").title(),
                f"{int(row['count']):,}",
            )

        report.add_section(
            title="Severity Distribution",
            figure=cls._severity_distribution_chart(severity_df),
            description="Count of incidents grouped by severity level.",
        )

        trend_df = aggregate_by_time(
            incidents_df,
            freq=config.default_frequency,
        )
        report.add_section(
            title="Incident Trend Over Time",
            figure=cls._trend_over_time_chart(trend_df),
            description="Incident counts aggregated over time.",
        )

        hurt_df = compute_time_series_hurt_index(
            incidents_df,
            freq=config.default_frequency,
        )
        report.add_section(
            title="Hurt Index Over Time",
            figure=cls._hurt_index_chart(hurt_df),
            description=(
                "Weighted hurt index (severity sum) over time. "
                "Higher values indicate more severe incidents."
            ),
        )

        return report

    # ------------------------------------------------------------------
    # Chart builders
    # ------------------------------------------------------------------

    @staticmethod
    def _severity_distribution_chart(severity_df: pd.DataFrame) -> go.Figure:
        """Plotly bar chart of incidents by severity."""
        fig = go.Figure(
            data=[
                go.Bar(
                    x=severity_df["actual_severity"],
                    y=severity_df["count"],
                    marker_color="#667eea",
                )
            ]
        )
        fig.update_layout(
            template="plotly_white",
            xaxis_title="Severity Level",
            yaxis_title="Count",
            height=450,
        )
        return fig

    @staticmethod
    def _trend_over_time_chart(trend_df: pd.DataFrame) -> go.Figure:
        """Plotly line chart of incident counts over time."""
        fig = go.Figure(
            data=[
                go.Scatter(
                    x=trend_df["occurred_at"],
                    y=trend_df["count"],
                    mode="lines+markers",
                    line={"color": "#764ba2", "width": 2},
                    marker={"size": 4},
                )
            ]
        )
        fig.update_layout(
            template="plotly_white",
            xaxis_title="Date",
            yaxis_title="Incident Count",
            hovermode="x unified",
            height=450,
        )
        return fig

    @staticmethod
    def _hurt_index_chart(hurt_df: pd.DataFrame) -> go.Figure:
        """Plotly line chart of weighted hurt index over time."""
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=hurt_df["occurred_at"],
                y=hurt_df["actual_hurt_index"],
                mode="lines",
                name="Actual Hurt Index",
                line={"color": "#e53e3e", "width": 2},
            )
        )
        if "potential_hurt_index" in hurt_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=hurt_df["occurred_at"],
                    y=hurt_df["potential_hurt_index"],
                    mode="lines",
                    name="Potential Hurt Index",
                    line={"color": "#ed8936", "width": 2, "dash": "dash"},
                )
            )
        fig.update_layout(
            template="plotly_white",
            xaxis_title="Date",
            yaxis_title="Hurt Index",
            hovermode="x unified",
            height=450,
        )
        return fig
