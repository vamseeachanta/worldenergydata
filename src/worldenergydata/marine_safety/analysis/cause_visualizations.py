# ABOUTME: Interactive visualization module for marine safety incident cause analysis
# ABOUTME: Provides Plotly-based interactive charts for HTML reports with comprehensive cause analysis

"""
Cause Visualization Module

This module provides interactive visualizations for analyzing marine safety incident causes
using Plotly for HTML report generation. All visualizations are interactive with hover,
zoom, pan, and export capabilities.

Features:
- Bar charts for cause frequency distributions
- Time series plots for cause trends over time
- Pie charts for cause category proportions
- Heatmaps for cause vs severity cross-tabulation
- Specialized visualizations for hatch/opening maloperation incidents
- Sunburst charts for hierarchical cause analysis

All visualizations follow HTML reporting standards with:
- Interactive plots only (no static images)
- Responsive design for all screen sizes
- Consistent color scheme
- Proper titles, labels, and legends
- Export functionality to PNG/SVG
"""

from typing import Dict, Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..constants import CauseCategory, SeverityLevel


class CauseVisualizer:
    """
    Interactive visualization generator for marine safety incident cause analysis.

    This class provides methods to create various interactive Plotly visualizations
    for analyzing incident causes, trends, and patterns. All visualizations are
    optimized for HTML reports with full interactivity.

    Attributes:
        color_scheme (Dict): Color mapping for cause categories and severity levels
        default_template (str): Plotly template for consistent styling
    """

    # Default color scheme for cause categories
    DEFAULT_CAUSE_COLORS = {
        CauseCategory.HUMAN_ERROR: "#E74C3C",  # Red
        CauseCategory.EQUIPMENT_FAILURE: "#3498DB",  # Blue
        CauseCategory.DESIGN_FLAW: "#9B59B6",  # Purple
        CauseCategory.MAINTENANCE_ISSUE: "#F39C12",  # Orange
        CauseCategory.WEATHER: "#1ABC9C",  # Teal
        CauseCategory.ENVIRONMENTAL: "#27AE60",  # Green
        CauseCategory.PROCEDURAL: "#E67E22",  # Dark Orange
        CauseCategory.TRAINING: "#16A085",  # Dark Teal
        CauseCategory.COMMUNICATION: "#8E44AD",  # Dark Purple
        CauseCategory.MANAGEMENT: "#C0392B",  # Dark Red
        CauseCategory.EXTERNAL: "#7F8C8D",  # Gray
        CauseCategory.MULTIPLE: "#34495E",  # Dark Gray
        CauseCategory.UNKNOWN: "#95A5A6",  # Light Gray
    }

    # Color scheme for severity levels
    SEVERITY_COLORS = {
        SeverityLevel.MINIMAL: "#27AE60",  # Green
        SeverityLevel.MINOR: "#F1C40F",  # Yellow
        SeverityLevel.MODERATE: "#E67E22",  # Orange
        SeverityLevel.SERIOUS: "#E74C3C",  # Red
        SeverityLevel.CATASTROPHIC: "#8E44AD",  # Purple
    }

    def __init__(
        self, color_scheme: Optional[Dict] = None, template: str = "plotly_white"
    ):
        """
        Initialize CauseVisualizer with optional custom color scheme.

        Args:
            color_scheme: Optional custom color mapping for categories
            template: Plotly template for styling (default: 'plotly_white')
        """
        self.color_scheme = color_scheme or self.DEFAULT_CAUSE_COLORS.copy()
        self.severity_colors = self.SEVERITY_COLORS.copy()
        self.default_template = template

        # Common layout settings for all charts
        self.common_layout = dict(
            template=self.default_template,
            font=dict(size=12, family="Arial, sans-serif"),
            hovermode="closest",
            autosize=True,
            margin=dict(l=60, r=40, t=80, b=60),
        )

    def create_cause_frequency_chart(
        self,
        data: pd.DataFrame,
        cause_column: str = "cause_category",
        title: str = "Incident Cause Frequency Distribution",
        show_percentages: bool = True,
    ) -> go.Figure:
        """
        Create interactive bar chart showing frequency of each cause category.

        Args:
            data: DataFrame containing incident data
            cause_column: Column name containing cause categories
            title: Chart title
            show_percentages: Whether to show percentages in hover info

        Returns:
            Plotly Figure object with interactive bar chart
        """
        if data.empty:
            # Return empty figure with message
            fig = go.Figure()
            fig.update_layout(
                title=title,
                annotations=[
                    {
                        "text": "No data available",
                        "xref": "paper",
                        "yref": "paper",
                        "x": 0.5,
                        "y": 0.5,
                        "showarrow": False,
                        "font": {"size": 16},
                    }
                ],
            )
            return fig

        # Count frequency of each cause
        cause_counts = data[cause_column].value_counts().reset_index()
        cause_counts.columns = ["cause", "count"]

        # Calculate percentages
        total = cause_counts["count"].sum()
        cause_counts["percentage"] = (cause_counts["count"] / total * 100).round(1)

        # Map colors
        colors = [
            self.color_scheme.get(CauseCategory(c), "#95A5A6")
            for c in cause_counts["cause"]
        ]

        # Create bar chart
        fig = go.Figure(
            data=[
                go.Bar(
                    x=cause_counts["cause"],
                    y=cause_counts["count"],
                    marker=dict(
                        color=colors, line=dict(color="rgba(0,0,0,0.3)", width=1)
                    ),
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        + "Count: %{y}<br>"
                        + (
                            "Percentage: %{customdata:.1f}%<br>"
                            if show_percentages
                            else ""
                        )
                        + "<extra></extra>"
                    ),
                    customdata=cause_counts["percentage"] if show_percentages else None,
                    text=cause_counts["count"],
                    textposition="outside",
                )
            ]
        )

        # Update layout
        fig.update_layout(
            title=dict(text=title, x=0.5, xanchor="center"),
            xaxis=dict(title="Cause Category", tickangle=-45),
            yaxis=dict(title="Number of Incidents"),
            showlegend=False,
            **self.common_layout,
        )

        return fig

    def create_cause_trend_over_time(
        self,
        data: pd.DataFrame,
        date_column: str = "date",
        cause_column: str = "cause_category",
        aggregation: str = "monthly",
        title: str = "Incident Cause Trends Over Time",
    ) -> go.Figure:
        """
        Create time series plot showing cause trends over time.

        Args:
            data: DataFrame containing incident data with dates
            date_column: Column name containing dates
            cause_column: Column name containing cause categories
            aggregation: Time aggregation ('daily', 'weekly', 'monthly', 'yearly')
            title: Chart title

        Returns:
            Plotly Figure object with interactive time series
        """
        if data.empty or date_column not in data.columns:
            fig = go.Figure()
            fig.update_layout(title=title)
            return fig

        # Ensure date column is datetime
        data_copy = data.copy()
        if not pd.api.types.is_datetime64_any_dtype(data_copy[date_column]):
            data_copy[date_column] = pd.to_datetime(data_copy[date_column])

        # Set aggregation frequency
        freq_map = {"daily": "D", "weekly": "W", "monthly": "M", "yearly": "Y"}
        freq = freq_map.get(aggregation, "M")

        # Group by time period and cause
        data_copy["period"] = (
            data_copy[date_column].dt.to_period(freq).dt.to_timestamp()
        )

        # Count incidents by period and cause
        trends = (
            data_copy.groupby(["period", cause_column]).size().reset_index(name="count")
        )

        # Create line plot for each cause
        fig = go.Figure()

        for cause in trends[cause_column].unique():
            cause_data = trends[trends[cause_column] == cause]
            color = self.color_scheme.get(CauseCategory(cause), "#95A5A6")

            fig.add_trace(
                go.Scatter(
                    x=cause_data["period"],
                    y=cause_data["count"],
                    mode="lines+markers",
                    name=str(cause).replace("_", " ").title(),
                    line=dict(color=color, width=2),
                    marker=dict(size=6, symbol="circle"),
                    hovertemplate="<b>%{fullData.name}</b><br>Date: %{x}<br>Count: %{y}<extra></extra>",
                )
            )

        # Update layout
        fig.update_layout(
            title=dict(text=title, x=0.5, xanchor="center"),
            xaxis=dict(title="Time Period"),
            yaxis=dict(title="Number of Incidents"),
            legend=dict(
                title="Cause Category",
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02,
            ),
            **self.common_layout,
        )

        # Enable range slider for better interactivity
        fig.update_xaxes(rangeslider_visible=True)

        return fig

    def create_cause_proportion_pie_chart(
        self,
        data: pd.DataFrame,
        cause_column: str = "cause_category",
        title: str = "Incident Cause Category Distribution",
    ) -> go.Figure:
        """
        Create interactive pie chart showing proportions of each cause category.

        Args:
            data: DataFrame containing incident data
            cause_column: Column name containing cause categories
            title: Chart title

        Returns:
            Plotly Figure object with interactive pie chart
        """
        if data.empty or cause_column not in data.columns:
            fig = go.Figure()
            fig.update_layout(title=title)
            return fig

        # Count frequency of each cause
        cause_counts = data[cause_column].value_counts()

        # Prepare labels and colors
        labels = [str(c).replace("_", " ").title() for c in cause_counts.index]
        values = cause_counts.values
        colors = [
            self.color_scheme.get(CauseCategory(c), "#95A5A6")
            for c in cause_counts.index
        ]

        # Create pie chart
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    marker=dict(colors=colors, line=dict(color="white", width=2)),
                    textinfo="label+percent",
                    textposition="auto",
                    hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>",
                    pull=[
                        0.05 if v == max(values) else 0 for v in values
                    ],  # Pull out largest slice
                )
            ]
        )

        # Update layout
        fig.update_layout(
            title=dict(text=title, x=0.5, xanchor="center"),
            showlegend=True,
            legend=dict(
                orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02
            ),
            **self.common_layout,
        )

        return fig

    def create_cause_severity_heatmap(
        self,
        data: pd.DataFrame,
        cause_column: str = "cause_category",
        severity_column: str = "severity",
        title: str = "Incident Cause vs Severity Cross-Tabulation",
    ) -> go.Figure:
        """
        Create heatmap showing relationship between cause categories and severity levels.

        Args:
            data: DataFrame containing incident data
            cause_column: Column name containing cause categories
            severity_column: Column name containing severity levels
            title: Chart title

        Returns:
            Plotly Figure object with interactive heatmap
        """
        if (
            data.empty
            or cause_column not in data.columns
            or severity_column not in data.columns
        ):
            fig = go.Figure()
            fig.update_layout(title=title)
            return fig

        # Create cross-tabulation
        crosstab = pd.crosstab(data[cause_column], data[severity_column], margins=False)

        # Format labels
        y_labels = [str(c).replace("_", " ").title() for c in crosstab.index]
        x_labels = [
            f"Level {s}" if isinstance(s, int) else str(s) for s in crosstab.columns
        ]

        # Create heatmap
        fig = go.Figure(
            data=go.Heatmap(
                z=crosstab.values,
                x=x_labels,
                y=y_labels,
                colorscale="RdYlGn_r",  # Red (high) to Green (low)
                text=crosstab.values,
                texttemplate="%{text}",
                textfont={"size": 10},
                hovertemplate="Cause: %{y}<br>Severity: %{x}<br>Count: %{z}<extra></extra>",
                colorbar=dict(title="Count"),
            )
        )

        # Update layout
        fig.update_layout(
            title=dict(text=title, x=0.5, xanchor="center"),
            xaxis=dict(title="Severity Level", side="bottom"),
            yaxis=dict(title="Cause Category"),
            **self.common_layout,
        )

        return fig

    def create_hatch_maloperation_chart(
        self,
        data: pd.DataFrame,
        type_column: str = "maloperation_type",
        title: str = "Hatch/Opening Maloperation Incident Analysis",
    ) -> go.Figure:
        """
        Create visualization specific to hatch and opening maloperation incidents.

        Args:
            data: DataFrame containing hatch maloperation incident data
            type_column: Column name containing maloperation types
            title: Chart title

        Returns:
            Plotly Figure object with grouped bar chart
        """
        if data.empty or type_column not in data.columns:
            fig = go.Figure()
            fig.update_layout(title=title)
            return fig

        # Count by maloperation type
        type_counts = data[type_column].value_counts().reset_index()
        type_counts.columns = ["type", "count"]

        # Create bar chart
        fig = go.Figure(
            data=[
                go.Bar(
                    x=[str(t).replace("_", " ").title() for t in type_counts["type"]],
                    y=type_counts["count"],
                    marker=dict(
                        color="#3498DB", line=dict(color="rgba(0,0,0,0.3)", width=1)
                    ),
                    text=type_counts["count"],
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>Incidents: %{y}<extra></extra>",
                )
            ]
        )

        # Update layout
        fig.update_layout(
            title=dict(text=title, x=0.5, xanchor="center"),
            xaxis=dict(title="Maloperation Type", tickangle=-45),
            yaxis=dict(title="Number of Incidents"),
            showlegend=False,
            **self.common_layout,
        )

        return fig

    def create_hatch_maloperation_severity_breakdown(
        self,
        data: pd.DataFrame,
        type_column: str = "maloperation_type",
        severity_column: str = "severity",
        title: str = "Hatch Maloperation by Type and Severity",
    ) -> go.Figure:
        """
        Create grouped bar chart showing hatch maloperation incidents by type and severity.

        Args:
            data: DataFrame containing hatch maloperation data
            type_column: Column name containing maloperation types
            severity_column: Column name containing severity levels
            title: Chart title

        Returns:
            Plotly Figure object with grouped bar chart
        """
        if data.empty:
            fig = go.Figure()
            fig.update_layout(title=title)
            return fig

        # Group by type and severity
        grouped = (
            data.groupby([type_column, severity_column])
            .size()
            .reset_index(name="count")
        )

        # Create grouped bar chart
        fig = go.Figure()

        for severity in sorted(data[severity_column].unique()):
            severity_data = grouped[grouped[severity_column] == severity]
            color = self.severity_colors.get(severity, "#95A5A6")

            fig.add_trace(
                go.Bar(
                    name=f"Severity {severity}",
                    x=[
                        str(t).replace("_", " ").title()
                        for t in severity_data[type_column]
                    ],
                    y=severity_data["count"],
                    marker=dict(color=color),
                    hovertemplate="%{x}<br>Severity %{fullData.name}: %{y}<extra></extra>",
                )
            )

        # Update layout
        fig.update_layout(
            title=dict(text=title, x=0.5, xanchor="center"),
            xaxis=dict(title="Maloperation Type", tickangle=-45),
            yaxis=dict(title="Number of Incidents"),
            barmode="group",
            legend=dict(title="Severity Level"),
            **self.common_layout,
        )

        return fig

    def create_cause_hierarchy_sunburst(
        self,
        data: pd.DataFrame,
        cause_column: str = "cause_category",
        severity_column: str = "severity",
        title: str = "Hierarchical Cause Analysis",
    ) -> go.Figure:
        """
        Create interactive sunburst chart for hierarchical cause analysis.

        Shows causes as inner ring and severity breakdown as outer ring.

        Args:
            data: DataFrame containing incident data
            cause_column: Column name containing cause categories
            severity_column: Column name containing severity levels
            title: Chart title

        Returns:
            Plotly Figure object with interactive sunburst chart
        """
        if data.empty:
            fig = go.Figure()
            fig.update_layout(title=title)
            return fig

        # Prepare hierarchical data
        labels = ["All Incidents"]
        parents = [""]
        values = [len(data)]
        colors_list = ["#ECF0F1"]  # Root color

        # Add cause categories (first level)
        cause_counts = data[cause_column].value_counts()
        for cause, count in cause_counts.items():
            labels.append(str(cause).replace("_", " ").title())
            parents.append("All Incidents")
            values.append(count)
            colors_list.append(self.color_scheme.get(CauseCategory(cause), "#95A5A6"))

        # Add severity breakdown for each cause (second level)
        for cause in cause_counts.index:
            cause_data = data[data[cause_column] == cause]
            severity_counts = cause_data[severity_column].value_counts()

            for severity, count in severity_counts.items():
                labels.append(f"Severity {severity}")
                parents.append(str(cause).replace("_", " ").title())
                values.append(count)
                colors_list.append(self.severity_colors.get(severity, "#BDC3C7"))

        # Create sunburst chart
        fig = go.Figure(
            data=[
                go.Sunburst(
                    labels=labels,
                    parents=parents,
                    values=values,
                    marker=dict(colors=colors_list, line=dict(color="white", width=2)),
                    branchvalues="total",
                    hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percentParent}<extra></extra>",
                )
            ]
        )

        # Update layout
        fig.update_layout(
            title=dict(text=title, x=0.5, xanchor="center"), **self.common_layout
        )

        return fig

    def create_comprehensive_dashboard(
        self,
        data: pd.DataFrame,
        title: str = "Marine Safety Incident Cause Analysis Dashboard",
    ) -> go.Figure:
        """
        Create comprehensive dashboard with multiple visualizations.

        Combines multiple chart types into a single interactive dashboard.

        Args:
            data: DataFrame containing incident data
            title: Dashboard title

        Returns:
            Plotly Figure object with subplot dashboard
        """
        # Create subplots
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "Cause Frequency",
                "Cause Proportions",
                "Cause vs Severity",
                "Monthly Trends",
            ),
            specs=[
                [{"type": "bar"}, {"type": "pie"}],
                [{"type": "heatmap"}, {"type": "scatter"}],
            ],
            vertical_spacing=0.12,
            horizontal_spacing=0.12,
        )

        # Add frequency bar chart
        cause_counts = data["cause_category"].value_counts().head(10)
        fig.add_trace(
            go.Bar(
                x=cause_counts.index,
                y=cause_counts.values,
                marker=dict(color="#3498DB"),
                showlegend=False,
            ),
            row=1,
            col=1,
        )

        # Add pie chart
        pie_counts = data["cause_category"].value_counts()
        fig.add_trace(
            go.Pie(labels=pie_counts.index, values=pie_counts.values, showlegend=False),
            row=1,
            col=2,
        )

        # Add heatmap (cause vs severity)
        if "severity" in data.columns:
            crosstab = pd.crosstab(data["cause_category"], data["severity"])
            fig.add_trace(
                go.Heatmap(
                    z=crosstab.values,
                    x=[f"L{s}" for s in crosstab.columns],
                    y=crosstab.index,
                    colorscale="RdYlGn_r",
                    showscale=False,
                ),
                row=2,
                col=1,
            )

        # Add time trend
        if "date" in data.columns:
            data_copy = data.copy()
            data_copy["date"] = pd.to_datetime(data_copy["date"])
            data_copy["month"] = data_copy["date"].dt.to_period("M").dt.to_timestamp()
            monthly = data_copy.groupby("month").size()

            fig.add_trace(
                go.Scatter(
                    x=monthly.index,
                    y=monthly.values,
                    mode="lines+markers",
                    line=dict(color="#E74C3C"),
                    showlegend=False,
                ),
                row=2,
                col=2,
            )

        # Update layout
        fig.update_layout(
            title=dict(text=title, x=0.5, xanchor="center"),
            height=800,
            showlegend=False,
            **self.common_layout,
        )

        return fig
