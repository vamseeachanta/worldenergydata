"""
Production charts for comprehensive reports.

Provides production trend charts, cumulative production, and forecast visualizations.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


@dataclass
class ChartConfig:
    """Configuration for chart generation."""

    title: str
    height: int = 600
    width: int = 1200
    theme: str = "plotly_white"
    show_legend: bool = True
    show_grid: bool = True
    animate: bool = False


class ProductionChart:
    """
    Creates production-related visualizations for comprehensive reports.

    Supports trend charts, cumulative production, forecasts, and comparisons.
    """

    def __init__(self, config: Optional[ChartConfig] = None):
        """
        Initialize production chart generator.

        Args:
            config: Optional chart configuration
        """
        self.config = config or ChartConfig(title="Production Analysis")

    def create_production_trend(
        self, data: pd.DataFrame, products: List[str] = None, title: str = None
    ) -> go.Figure:
        """
        Create production trend chart over time.

        Args:
            data: DataFrame with date index and production columns
            products: List of products to plot (e.g., ['oil', 'gas', 'water'])
            title: Override default title

        Returns:
            Plotly figure with production trends
        """
        if products is None:
            products = ["oil", "gas", "water"]

        fig = go.Figure()

        # Color scheme for products
        colors = {
            "oil": "#2E7D32",  # Green
            "gas": "#E65100",  # Orange
            "water": "#1565C0",  # Blue
            "condensate": "#6A1B9A",  # Purple
        }

        # Add trace for each product
        for product in products:
            if product in data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=data[product],
                        name=product.capitalize(),
                        mode="lines",
                        line=dict(color=colors.get(product, "#757575"), width=2),
                        hovertemplate=f"<b>{product.capitalize()}</b><br>"
                        + "Date: %{x}<br>"
                        + "Production: %{y:,.0f}<br>"
                        + "<extra></extra>",
                    )
                )

        # Update layout
        fig.update_layout(
            title=title or self.config.title,
            xaxis_title="Date",
            yaxis_title="Production Rate (BBL/day or MCF/day)",
            height=self.config.height,
            width=self.config.width,
            template=self.config.theme,
            showlegend=self.config.show_legend,
            hovermode="x unified",
            xaxis=dict(showgrid=self.config.show_grid, rangeslider=dict(visible=True)),
            yaxis=dict(showgrid=self.config.show_grid),
        )

        return fig

    def create_cumulative_production(
        self, data: pd.DataFrame, products: List[str] = None, title: str = None
    ) -> go.Figure:
        """
        Create cumulative production chart.

        Args:
            data: DataFrame with production data
            products: Products to include
            title: Chart title

        Returns:
            Plotly figure with cumulative production
        """
        if products is None:
            products = ["oil", "gas", "water"]

        # Calculate cumulative values
        cumulative_data = data[products].cumsum()

        fig = go.Figure()

        # Add area traces
        for product in products:
            if product in cumulative_data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=cumulative_data.index,
                        y=cumulative_data[product],
                        name=f"Cumulative {product.capitalize()}",
                        mode="lines",
                        fill="tonexty" if product != products[0] else "tozeroy",
                        stackgroup="cumulative",
                        hovertemplate=f"<b>{product.capitalize()}</b><br>"
                        + "Date: %{x}<br>"
                        + "Cumulative: %{y:,.0f}<br>"
                        + "<extra></extra>",
                    )
                )

        fig.update_layout(
            title=title or "Cumulative Production",
            xaxis_title="Date",
            yaxis_title="Cumulative Production (BBL or MCF)",
            height=self.config.height,
            width=self.config.width,
            template=self.config.theme,
            showlegend=self.config.show_legend,
            hovermode="x unified",
        )

        return fig

    def create_production_forecast(
        self,
        historical: pd.DataFrame,
        forecast: pd.DataFrame,
        confidence_intervals: Optional[Dict] = None,
        title: str = None,
    ) -> go.Figure:
        """
        Create production forecast visualization.

        Args:
            historical: Historical production data
            forecast: Forecast production data
            confidence_intervals: Optional confidence intervals
            title: Chart title

        Returns:
            Plotly figure with forecast
        """
        fig = go.Figure()

        # Historical data
        fig.add_trace(
            go.Scatter(
                x=historical.index,
                y=(
                    historical["oil"]
                    if "oil" in historical.columns
                    else historical.iloc[:, 0]
                ),
                name="Historical",
                mode="lines",
                line=dict(color="#1976D2", width=2),
                hovertemplate="<b>Historical</b><br>"
                + "Date: %{x}<br>"
                + "Production: %{y:,.0f}<br>"
                + "<extra></extra>",
            )
        )

        # Forecast data
        forecast_col = "oil" if "oil" in forecast.columns else forecast.columns[0]
        fig.add_trace(
            go.Scatter(
                x=forecast.index,
                y=forecast[forecast_col],
                name="Forecast",
                mode="lines",
                line=dict(color="#E53935", width=2, dash="dash"),
                hovertemplate="<b>Forecast</b><br>"
                + "Date: %{x}<br>"
                + "Production: %{y:,.0f}<br>"
                + "<extra></extra>",
            )
        )

        # Add confidence intervals if provided
        if confidence_intervals:
            if "upper" in confidence_intervals and "lower" in confidence_intervals:
                # Upper bound
                fig.add_trace(
                    go.Scatter(
                        x=forecast.index,
                        y=confidence_intervals["upper"],
                        name="Upper CI (95%)",
                        mode="lines",
                        line=dict(width=0),
                        fillcolor="rgba(229, 57, 53, 0.2)",
                        fill="tonexty",
                        showlegend=False,
                        hovertemplate="<b>Upper CI</b><br>"
                        + "Date: %{x}<br>"
                        + "Value: %{y:,.0f}<br>"
                        + "<extra></extra>",
                    )
                )

                # Lower bound
                fig.add_trace(
                    go.Scatter(
                        x=forecast.index,
                        y=confidence_intervals["lower"],
                        name="Lower CI (95%)",
                        mode="lines",
                        line=dict(width=0),
                        fillcolor="rgba(229, 57, 53, 0.2)",
                        fill="tonexty",
                        showlegend=False,
                        hovertemplate="<b>Lower CI</b><br>"
                        + "Date: %{x}<br>"
                        + "Value: %{y:,.0f}<br>"
                        + "<extra></extra>",
                    )
                )

        # Add vertical line at forecast start
        if len(historical) > 0 and len(forecast) > 0:
            forecast_start = forecast.index[0]
            fig.add_vline(
                x=forecast_start,
                line_dash="dot",
                line_color="gray",
                annotation_text="Forecast Start",
            )

        fig.update_layout(
            title=title or "Production Forecast",
            xaxis_title="Date",
            yaxis_title="Production Rate (BBL/day)",
            height=self.config.height,
            width=self.config.width,
            template=self.config.theme,
            showlegend=self.config.show_legend,
            hovermode="x unified",
        )

        return fig

    def create_well_comparison(
        self, well_data: Dict[str, pd.DataFrame], metric: str = "oil", title: str = None
    ) -> go.Figure:
        """
        Create comparison chart for multiple wells.

        Args:
            well_data: Dictionary of well names to production DataFrames
            metric: Metric to compare (oil, gas, water)
            title: Chart title

        Returns:
            Plotly figure with well comparison
        """
        fig = go.Figure()

        # Color palette for wells
        colors = [
            "#1F77B4",
            "#FF7F0E",
            "#2CA02C",
            "#D62728",
            "#9467BD",
            "#8C564B",
            "#E377C2",
            "#7F7F7F",
            "#BCBD22",
            "#17BECF",
        ]

        for i, (well_name, data) in enumerate(well_data.items()):
            if metric in data.columns:
                color = colors[i % len(colors)]

                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=data[metric],
                        name=well_name,
                        mode="lines",
                        line=dict(color=color, width=2),
                        hovertemplate=f"<b>{well_name}</b><br>"
                        + "Date: %{x}<br>"
                        + f"{metric.capitalize()}: "
                        + "%{y:,.0f}<br>"
                        + "<extra></extra>",
                    )
                )

        fig.update_layout(
            title=title or f"Well {metric.capitalize()} Production Comparison",
            xaxis_title="Date",
            yaxis_title=f"{metric.capitalize()} Production (BBL/day or MCF/day)",
            height=self.config.height,
            width=self.config.width,
            template=self.config.theme,
            showlegend=self.config.show_legend,
            hovermode="x unified",
        )

        return fig

    def create_production_efficiency(
        self, data: pd.DataFrame, target: float, title: str = None
    ) -> go.Figure:
        """
        Create production efficiency chart with target line.

        Args:
            data: Production data with efficiency metrics
            target: Target efficiency value
            title: Chart title

        Returns:
            Plotly figure with efficiency visualization
        """
        fig = go.Figure()

        # Actual efficiency
        efficiency_col = (
            "efficiency" if "efficiency" in data.columns else data.columns[0]
        )

        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data[efficiency_col],
                name="Actual Efficiency",
                mode="lines+markers",
                line=dict(color="#1976D2", width=2),
                marker=dict(size=6),
                hovertemplate="<b>Actual</b><br>"
                + "Date: %{x}<br>"
                + "Efficiency: %{y:.1f}%<br>"
                + "<extra></extra>",
            )
        )

        # Target line
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=[target] * len(data),
                name="Target",
                mode="lines",
                line=dict(color="#4CAF50", width=2, dash="dash"),
                hovertemplate="<b>Target</b><br>"
                + "Efficiency: %{y:.1f}%<br>"
                + "<extra></extra>",
            )
        )

        # Add shading for above/below target
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data[efficiency_col],
                fill="tonexty",
                fillcolor=(
                    "rgba(76, 175, 80, 0.2)"
                    if data[efficiency_col].mean() >= target
                    else "rgba(244, 67, 54, 0.2)"
                ),
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            )
        )

        fig.update_layout(
            title=title or "Production Efficiency vs Target",
            xaxis_title="Date",
            yaxis_title="Efficiency (%)",
            height=self.config.height,
            width=self.config.width,
            template=self.config.theme,
            showlegend=self.config.show_legend,
            hovermode="x unified",
            yaxis=dict(range=[0, max(100, data[efficiency_col].max() * 1.1)]),
        )

        return fig

    def create_monthly_summary(
        self, data: pd.DataFrame, products: List[str] = None, title: str = None
    ) -> go.Figure:
        """
        Create monthly production summary as bar chart.

        Args:
            data: Production data
            products: Products to include
            title: Chart title

        Returns:
            Plotly figure with monthly summary
        """
        if products is None:
            products = ["oil", "gas", "water"]

        # Resample to monthly
        monthly_data = data[products].resample("M").sum()

        fig = go.Figure()

        # Add bar for each product
        for product in products:
            if product in monthly_data.columns:
                fig.add_trace(
                    go.Bar(
                        x=monthly_data.index,
                        y=monthly_data[product],
                        name=product.capitalize(),
                        hovertemplate=f"<b>{product.capitalize()}</b><br>"
                        + "Month: %{x}<br>"
                        + "Total: %{y:,.0f}<br>"
                        + "<extra></extra>",
                    )
                )

        fig.update_layout(
            title=title or "Monthly Production Summary",
            xaxis_title="Month",
            yaxis_title="Total Production (BBL or MCF)",
            height=self.config.height,
            width=self.config.width,
            template=self.config.theme,
            showlegend=self.config.show_legend,
            barmode="group",
            hovermode="x unified",
        )

        return fig

    def export_chart(
        self, fig: go.Figure, filename: str, format: str = "png", **kwargs
    ) -> bool:
        """
        Export chart to file.

        Args:
            fig: Plotly figure to export
            filename: Output filename
            format: Export format (png, svg, pdf, html)
            **kwargs: Additional export options

        Returns:
            Success status
        """
        try:
            if format.lower() == "html":
                fig.write_html(filename, **kwargs)
            elif format.lower() == "png":
                fig.write_image(filename, format="png", **kwargs)
            elif format.lower() == "svg":
                fig.write_image(filename, format="svg", **kwargs)
            elif format.lower() == "pdf":
                fig.write_image(filename, format="pdf", **kwargs)
            else:
                raise ValueError(f"Unsupported format: {format}")

            return True
        except Exception as e:
            print(f"Error exporting chart: {e}")
            return False

    def create_decline_curve(
        self,
        data: pd.DataFrame,
        decline_params: Dict[str, float] = None,
        title: str = None,
    ) -> go.Figure:
        """
        Create decline curve analysis visualization.

        Args:
            data: Production data
            decline_params: Decline curve parameters
            title: Chart title

        Returns:
            Plotly figure with decline curve
        """
        fig = go.Figure()

        # Actual production
        production_col = "oil" if "oil" in data.columns else data.columns[0]

        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data[production_col],
                name="Actual Production",
                mode="markers",
                marker=dict(color="#1976D2", size=6),
                hovertemplate="<b>Actual</b><br>"
                + "Date: %{x}<br>"
                + "Production: %{y:,.0f}<br>"
                + "<extra></extra>",
            )
        )

        # Calculate decline curve if parameters provided
        if decline_params:
            initial_rate = decline_params.get("qi", data[production_col].iloc[0])
            decline_rate = decline_params.get("di", 0.1)  # Annual decline
            b_factor = decline_params.get("b", 0)  # Hyperbolic factor

            # Generate decline curve
            time_days = (data.index - data.index[0]).days

            if b_factor == 0:
                # Exponential decline
                decline_production = initial_rate * np.exp(
                    -decline_rate * time_days / 365
                )
            else:
                # Hyperbolic decline
                decline_production = initial_rate / (
                    1 + b_factor * decline_rate * time_days / 365
                ) ** (1 / b_factor)

            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=decline_production,
                    name="Decline Curve",
                    mode="lines",
                    line=dict(color="#E53935", width=2),
                    hovertemplate="<b>Decline Curve</b><br>"
                    + "Date: %{x}<br>"
                    + "Production: %{y:,.0f}<br>"
                    + "<extra></extra>",
                )
            )

        fig.update_layout(
            title=title or "Production Decline Curve Analysis",
            xaxis_title="Date",
            yaxis_title="Production Rate (BBL/day)",
            height=self.config.height,
            width=self.config.width,
            template=self.config.theme,
            showlegend=self.config.show_legend,
            hovermode="x unified",
            yaxis_type="log",
        )

        return fig
