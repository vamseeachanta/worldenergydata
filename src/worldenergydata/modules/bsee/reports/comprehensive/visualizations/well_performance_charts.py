"""
Well performance visualizations for comprehensive reports.

Provides scatter plots, heat maps, bubble charts for well analysis.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


@dataclass
class PerformanceMetrics:
    """Well performance metrics."""

    well_name: str
    efficiency: float
    uptime: float
    production_rate: float
    water_cut: float
    gas_oil_ratio: float
    operating_cost: float


class WellPerformanceChart:
    """
    Creates well performance visualizations for comprehensive reports.

    Supports scatter plots, heat maps, bubble charts, and KPI dashboards.
    """

    def __init__(self, theme: str = "plotly_white"):
        """
        Initialize well performance chart generator.

        Args:
            theme: Plotly theme to use
        """
        self.theme = theme

    def create_scatter_plot(
        self,
        data: pd.DataFrame,
        x_column: str,
        y_column: str,
        color_column: Optional[str] = None,
        size_column: Optional[str] = None,
        title: str = None,
    ) -> go.Figure:
        """
        Create scatter plot for well performance metrics.

        Args:
            data: DataFrame with well data
            x_column: Column for x-axis
            y_column: Column for y-axis
            color_column: Optional column for color coding
            size_column: Optional column for bubble size
            title: Chart title

        Returns:
            Plotly figure with scatter plot
        """
        # Base scatter plot
        if color_column and size_column:
            fig = px.scatter(
                data,
                x=x_column,
                y=y_column,
                color=color_column,
                size=size_column,
                title=title or f"{y_column} vs {x_column}",
                template=self.theme,
                hover_data=data.columns,
            )
        elif color_column:
            fig = px.scatter(
                data,
                x=x_column,
                y=y_column,
                color=color_column,
                title=title or f"{y_column} vs {x_column}",
                template=self.theme,
                hover_data=data.columns,
            )
        else:
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=data[x_column],
                    y=data[y_column],
                    mode="markers",
                    marker=dict(
                        size=10, color="#1976D2", line=dict(width=1, color="white")
                    ),
                    text=data.get("well_name", data.index),
                    hovertemplate="<b>%{text}</b><br>"
                    + f"{x_column}: %{{x:.2f}}<br>"
                    + f"{y_column}: %{{y:.2f}}<br>"
                    + "<extra></extra>",
                )
            )

        # Add trend line
        if len(data) > 2:
            z = np.polyfit(data[x_column].fillna(0), data[y_column].fillna(0), 1)
            p = np.poly1d(z)
            x_trend = np.linspace(data[x_column].min(), data[x_column].max(), 100)

            fig.add_trace(
                go.Scatter(
                    x=x_trend,
                    y=p(x_trend),
                    mode="lines",
                    name="Trend",
                    line=dict(color="red", width=2, dash="dash"),
                    hoverinfo="skip",
                )
            )

        fig.update_layout(
            title=title or f"{y_column} vs {x_column}",
            xaxis_title=x_column,
            yaxis_title=y_column,
            height=600,
            width=900,
            template=self.theme,
            hovermode="closest",
        )

        return fig

    def create_heat_map(
        self,
        data: pd.DataFrame,
        wells: List[str] = None,
        metrics: List[str] = None,
        title: str = None,
    ) -> go.Figure:
        """
        Create heat map of well performance metrics.

        Args:
            data: DataFrame with well metrics
            wells: List of wells to include
            metrics: List of metrics to display
            title: Chart title

        Returns:
            Plotly figure with heat map
        """
        # Filter data if specified
        if wells:
            data = data[
                data.index.isin(wells) | data.get("well_name", pd.Series()).isin(wells)
            ]
        if metrics:
            data = data[metrics]

        # Normalize data for heat map (0-1 scale)
        normalized_data = (data - data.min()) / (data.max() - data.min())

        fig = go.Figure(
            data=go.Heatmap(
                z=normalized_data.values,
                x=normalized_data.columns,
                y=normalized_data.index if wells is None else wells,
                colorscale="RdYlGn",
                reversescale=False,
                text=data.values,
                texttemplate="%{text:.2f}",
                textfont={"size": 10},
                hovertemplate="Well: %{y}<br>"
                + "Metric: %{x}<br>"
                + "Value: %{text}<br>"
                + "Normalized: %{z:.2f}<br>"
                + "<extra></extra>",
            )
        )

        fig.update_layout(
            title=title or "Well Performance Heat Map",
            xaxis_title="Performance Metrics",
            yaxis_title="Wells",
            height=max(400, len(normalized_data) * 30),
            width=1000,
            template=self.theme,
        )

        return fig

    def create_bubble_chart(
        self,
        data: pd.DataFrame,
        x_metric: str,
        y_metric: str,
        size_metric: str,
        color_metric: Optional[str] = None,
        title: str = None,
    ) -> go.Figure:
        """
        Create bubble chart for multi-dimensional well analysis.

        Args:
            data: DataFrame with well data
            x_metric: Metric for x-axis
            y_metric: Metric for y-axis
            size_metric: Metric for bubble size
            color_metric: Optional metric for color
            title: Chart title

        Returns:
            Plotly figure with bubble chart
        """
        # Scale bubble sizes
        size_values = data[size_metric]
        size_scaled = (size_values - size_values.min()) / (
            size_values.max() - size_values.min()
        ) * 50 + 10

        if color_metric:
            fig = go.Figure()

            # Create color scale
            color_values = data[color_metric]

            fig.add_trace(
                go.Scatter(
                    x=data[x_metric],
                    y=data[y_metric],
                    mode="markers",
                    marker=dict(
                        size=size_scaled,
                        color=color_values,
                        colorscale="Viridis",
                        showscale=True,
                        colorbar=dict(title=color_metric),
                        line=dict(width=1, color="white"),
                    ),
                    text=data.get("well_name", data.index),
                    hovertemplate="<b>%{text}</b><br>"
                    + f"{x_metric}: %{{x:.2f}}<br>"
                    + f"{y_metric}: %{{y:.2f}}<br>"
                    + f"{size_metric}: %{{customdata[0]:.2f}}<br>"
                    + f"{color_metric}: %{{customdata[1]:.2f}}<br>"
                    + "<extra></extra>",
                    customdata=np.column_stack((data[size_metric], color_values)),
                )
            )
        else:
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=data[x_metric],
                    y=data[y_metric],
                    mode="markers",
                    marker=dict(
                        size=size_scaled,
                        color="#1976D2",
                        line=dict(width=1, color="white"),
                    ),
                    text=data.get("well_name", data.index),
                    hovertemplate="<b>%{text}</b><br>"
                    + f"{x_metric}: %{{x:.2f}}<br>"
                    + f"{y_metric}: %{{y:.2f}}<br>"
                    + f"{size_metric}: %{{customdata:.2f}}<br>"
                    + "<extra></extra>",
                    customdata=data[size_metric],
                )
            )

        fig.update_layout(
            title=title or f"Well Performance: {y_metric} vs {x_metric}",
            xaxis_title=x_metric,
            yaxis_title=y_metric,
            height=600,
            width=900,
            template=self.theme,
            hovermode="closest",
        )

        # Add annotation for bubble size
        fig.add_annotation(
            text=f"Bubble size: {size_metric}",
            xref="paper",
            yref="paper",
            x=0.02,
            y=0.98,
            showarrow=False,
            font=dict(size=10, color="gray"),
        )

        return fig

    def create_performance_radar(
        self,
        metrics: PerformanceMetrics,
        targets: Optional[Dict[str, float]] = None,
        title: str = None,
    ) -> go.Figure:
        """
        Create radar chart for well performance metrics.

        Args:
            metrics: Performance metrics for a well
            targets: Optional target values for each metric
            title: Chart title

        Returns:
            Plotly figure with radar chart
        """
        categories = [
            "Efficiency",
            "Uptime",
            "Production Rate",
            "Water Cut",
            "GOR",
            "Operating Cost",
        ]

        values = [
            metrics.efficiency,
            metrics.uptime,
            metrics.production_rate,
            100 - metrics.water_cut,  # Invert water cut (lower is better)
            min(100, metrics.gas_oil_ratio / 10),  # Scale GOR
            100 - metrics.operating_cost,  # Invert cost (lower is better)
        ]

        fig = go.Figure()

        # Add actual values
        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=categories,
                fill="toself",
                name="Actual",
                line=dict(color="#1976D2", width=2),
                hovertemplate="<b>%{theta}</b><br>"
                + "Value: %{r:.1f}<br>"
                + "<extra></extra>",
            )
        )

        # Add target values if provided
        if targets:
            target_values = [
                targets.get("efficiency", 85),
                targets.get("uptime", 95),
                targets.get("production_rate", 80),
                100 - targets.get("water_cut", 30),
                min(100, targets.get("gas_oil_ratio", 5) / 10),
                100 - targets.get("operating_cost", 20),
            ]

            fig.add_trace(
                go.Scatterpolar(
                    r=target_values,
                    theta=categories,
                    fill="toself",
                    name="Target",
                    line=dict(color="#4CAF50", width=2, dash="dash"),
                    fillcolor="rgba(76, 175, 80, 0.1)",
                    hovertemplate="<b>%{theta}</b><br>"
                    + "Target: %{r:.1f}<br>"
                    + "<extra></extra>",
                )
            )

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title=title or f"Performance Radar: {metrics.well_name}",
            height=500,
            width=500,
            template=self.theme,
            showlegend=True,
        )

        return fig

    def create_well_ranking(
        self, data: pd.DataFrame, metric: str, top_n: int = 10, title: str = None
    ) -> go.Figure:
        """
        Create horizontal bar chart showing well rankings.

        Args:
            data: DataFrame with well data
            metric: Metric to rank by
            top_n: Number of top wells to show
            title: Chart title

        Returns:
            Plotly figure with ranking chart
        """
        # Sort and get top N
        sorted_data = data.sort_values(metric, ascending=False).head(top_n)

        # Create color scale based on performance
        colors = [
            (
                "#4CAF50"
                if val >= data[metric].quantile(0.75)
                else (
                    "#FFC107"
                    if val >= data[metric].quantile(0.5)
                    else "#FF9800" if val >= data[metric].quantile(0.25) else "#F44336"
                )
            )
            for val in sorted_data[metric]
        ]

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=sorted_data[metric],
                y=(
                    sorted_data.index
                    if "well_name" not in sorted_data.columns
                    else sorted_data["well_name"]
                ),
                orientation="h",
                marker=dict(color=colors),
                text=sorted_data[metric].round(2),
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>"
                + f"{metric}: %{{x:.2f}}<br>"
                + "<extra></extra>",
            )
        )

        fig.update_layout(
            title=title or f"Top {top_n} Wells by {metric}",
            xaxis_title=metric,
            yaxis_title="Well",
            height=max(400, top_n * 40),
            width=800,
            template=self.theme,
            yaxis=dict(autorange="reversed"),
            margin=dict(l=150),
        )

        return fig

    def create_time_series_comparison(
        self, data: Dict[str, pd.DataFrame], metric: str, title: str = None
    ) -> go.Figure:
        """
        Create time series comparison for multiple wells.

        Args:
            data: Dictionary of well names to DataFrames
            metric: Metric to compare
            title: Chart title

        Returns:
            Plotly figure with time series comparison
        """
        fig = go.Figure()

        colors = px.colors.qualitative.Plotly

        for i, (well_name, well_data) in enumerate(data.items()):
            if metric in well_data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=well_data.index,
                        y=well_data[metric],
                        name=well_name,
                        mode="lines",
                        line=dict(color=colors[i % len(colors)], width=2),
                        hovertemplate=f"<b>{well_name}</b><br>"
                        + "Date: %{x}<br>"
                        + f"{metric}: %{{y:.2f}}<br>"
                        + "<extra></extra>",
                    )
                )

        fig.update_layout(
            title=title or f"{metric} Performance Over Time",
            xaxis_title="Date",
            yaxis_title=metric,
            height=600,
            width=1200,
            template=self.theme,
            hovermode="x unified",
            xaxis=dict(rangeslider=dict(visible=True)),
        )

        return fig

    def create_efficiency_matrix(
        self, data: pd.DataFrame, title: str = None
    ) -> go.Figure:
        """
        Create efficiency matrix showing multiple KPIs.

        Args:
            data: DataFrame with efficiency metrics
            title: Chart title

        Returns:
            Plotly figure with efficiency matrix
        """
        # Create subplots
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "Production Efficiency",
                "Operating Time",
                "Cost Efficiency",
                "Overall Performance",
            ),
            specs=[
                [{"type": "indicator"}, {"type": "indicator"}],
                [{"type": "indicator"}, {"type": "indicator"}],
            ],
        )

        # Production Efficiency
        prod_eff = data.get("production_efficiency", pd.Series([85])).mean()
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=prod_eff,
                title={"text": "Production<br>Efficiency"},
                delta={"reference": 80},
                gauge={
                    "axis": {"range": [None, 100]},
                    "bar": {"color": "darkgreen"},
                    "steps": [
                        {"range": [0, 50], "color": "lightgray"},
                        {"range": [50, 80], "color": "gray"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 90,
                    },
                },
                domain={"row": 1, "column": 1},
            ),
            row=1,
            col=1,
        )

        # Operating Time
        op_time = data.get("uptime", pd.Series([92])).mean()
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=op_time,
                title={"text": "Operating<br>Time"},
                delta={"reference": 90},
                gauge={
                    "axis": {"range": [None, 100]},
                    "bar": {"color": "darkblue"},
                    "steps": [
                        {"range": [0, 60], "color": "lightgray"},
                        {"range": [60, 85], "color": "gray"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 95,
                    },
                },
                domain={"row": 1, "column": 2},
            ),
            row=1,
            col=2,
        )

        # Cost Efficiency
        cost_eff = 100 - data.get("cost_index", pd.Series([25])).mean()
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=cost_eff,
                title={"text": "Cost<br>Efficiency"},
                delta={"reference": 70},
                gauge={
                    "axis": {"range": [None, 100]},
                    "bar": {"color": "darkorange"},
                    "steps": [
                        {"range": [0, 40], "color": "lightgray"},
                        {"range": [40, 70], "color": "gray"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 85,
                    },
                },
                domain={"row": 2, "column": 1},
            ),
            row=2,
            col=1,
        )

        # Overall Performance
        overall = (prod_eff + op_time + cost_eff) / 3
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=overall,
                title={"text": "Overall<br>Performance"},
                delta={"reference": 80},
                gauge={
                    "axis": {"range": [None, 100]},
                    "bar": {"color": "purple"},
                    "steps": [
                        {"range": [0, 50], "color": "lightgray"},
                        {"range": [50, 80], "color": "gray"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 90,
                    },
                },
                domain={"row": 2, "column": 2},
            ),
            row=2,
            col=2,
        )

        fig.update_layout(
            title=title or "Well Efficiency Matrix",
            height=600,
            width=900,
            template=self.theme,
            showlegend=False,
        )

        return fig
