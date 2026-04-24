"""
Production chart views for well detail dashboard.

Contains chart builders for time series, stacked production,
and production-related visualizations.
"""

from typing import Any, Dict, List

import pandas as pd

from .views_utils import (
    PLOTLY_AVAILABLE,
    ChartQualityIndicator,
)

# Import plotly components if available
if PLOTLY_AVAILABLE:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots


class ProductionChartBuilder:
    """Builds production-related charts."""

    def __init__(self):
        """Initialize chart builder."""
        self.quality_indicator = ChartQualityIndicator()

    def create_time_series_chart(
        self, data: pd.DataFrame, well_name: str
    ) -> Dict[str, Any]:
        """Create time series production chart."""
        if not PLOTLY_AVAILABLE:
            return {
                "type": "time_series",
                "data": data.to_dict(),
                "error": "Plotly not available",
            }

        fig = make_subplots(
            rows=1, cols=1, subplot_titles=[f"{well_name} Production Over Time"]
        )

        # Add oil production
        if "oil_production" in data.columns or "oil" in data.columns:
            oil_col = "oil_production" if "oil_production" in data.columns else "oil"
            fig.add_trace(
                go.Scatter(
                    x=data["date"] if "date" in data.columns else data.index,
                    y=data[oil_col],
                    name="Oil (bbl/d)",
                    mode="lines",
                    line=dict(color="green", width=2),
                    hovertemplate="Oil: %{y:,.0f} bbl/d<extra></extra>",
                )
            )

        # Add gas production
        if "gas_production" in data.columns or "gas" in data.columns:
            gas_col = "gas_production" if "gas_production" in data.columns else "gas"
            fig.add_trace(
                go.Scatter(
                    x=data["date"] if "date" in data.columns else data.index,
                    y=data[gas_col],
                    name="Gas (mcf/d)",
                    mode="lines",
                    line=dict(color="red", width=2),
                    hovertemplate="Gas: %{y:,.0f} mcf/d<extra></extra>",
                )
            )

        # Add water production
        if "water_production" in data.columns or "water" in data.columns:
            water_col = (
                "water_production" if "water_production" in data.columns else "water"
            )
            fig.add_trace(
                go.Scatter(
                    x=data["date"] if "date" in data.columns else data.index,
                    y=data[water_col],
                    name="Water (bbl/d)",
                    mode="lines",
                    line=dict(color="blue", width=2),
                    hovertemplate="Water: %{y:,.0f} bbl/d<extra></extra>",
                )
            )

        fig.update_layout(
            title=f"{well_name} Production Time Series",
            xaxis_title="Date",
            yaxis_title="Production Rate",
            hovermode="x unified",
            template="plotly_white",
            height=500,
        )

        return {
            "type": "time_series",
            "data": fig.data,
            "layout": fig.layout,
            "figure": fig,
        }

    def add_quality_indicators(
        self,
        chart: Dict[str, Any],
        quality_scores: pd.Series,
        verification_status: pd.Series,
    ) -> Dict[str, Any]:
        """Add quality indicators to existing chart."""
        if "figure" in chart and PLOTLY_AVAILABLE:
            fig = chart["figure"]
            fig = self.quality_indicator.add_quality_overlay(fig, quality_scores)
            fig = self.quality_indicator.add_verification_markers(
                fig, verification_status
            )
            chart["figure"] = fig
            chart["quality_overlay"] = True
            chart["verification_markers"] = True

        return chart

    def create_stacked_production_chart(
        self, data: pd.DataFrame, well_name: str
    ) -> Dict[str, Any]:
        """Create stacked area production chart."""
        if not PLOTLY_AVAILABLE:
            return {"type": "stacked_area", "error": "Plotly not available"}

        fig = go.Figure()

        # Prepare data columns
        oil_col = "oil_production" if "oil_production" in data.columns else "oil"
        gas_col = "gas_production" if "gas_production" in data.columns else "gas"
        water_col = (
            "water_production" if "water_production" in data.columns else "water"
        )
        date_col = "date" if "date" in data.columns else data.index

        # Add stacked areas
        fig.add_trace(
            go.Scatter(
                x=data[date_col] if isinstance(date_col, str) else date_col,
                y=data[oil_col] if oil_col in data.columns else [0] * len(data),
                name="Oil",
                mode="lines",
                stackgroup="one",
                fillcolor="rgba(0, 128, 0, 0.5)",
                line=dict(color="green"),
            )
        )

        fig.add_trace(
            go.Scatter(
                x=data[date_col] if isinstance(date_col, str) else date_col,
                y=data[gas_col] if gas_col in data.columns else [0] * len(data),
                name="Gas",
                mode="lines",
                stackgroup="one",
                fillcolor="rgba(255, 0, 0, 0.5)",
                line=dict(color="red"),
            )
        )

        fig.add_trace(
            go.Scatter(
                x=data[date_col] if isinstance(date_col, str) else date_col,
                y=data[water_col] if water_col in data.columns else [0] * len(data),
                name="Water",
                mode="lines",
                stackgroup="one",
                fillcolor="rgba(0, 0, 255, 0.5)",
                line=dict(color="blue"),
            )
        )

        fig.update_layout(
            title=f"{well_name} Stacked Production",
            xaxis_title="Date",
            yaxis_title="Total Production",
            hovermode="x unified",
            template="plotly_white",
            height=500,
        )

        return {
            "type": "stacked_area",
            "data": fig.data,
            "layout": fig.layout,
            "figure": fig,
        }

    def add_annotations(
        self, chart: Dict[str, Any], annotations: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Add annotations to chart for data quality issues."""
        if "figure" in chart and PLOTLY_AVAILABLE:
            fig = chart["figure"]

            # Create list for layout annotations
            layout_annotations = []
            for ann in annotations:
                layout_annotations.append(
                    {
                        "x": ann["date"],
                        "y": 0,
                        "text": ann["text"],
                        "showarrow": True,
                        "arrowhead": 2,
                        "arrowcolor": "red",
                        "ax": 0,
                        "ay": -40,
                    }
                )

            # Update layout with annotations
            if fig.layout.annotations:
                existing_annotations = list(fig.layout.annotations)
                existing_annotations.extend(layout_annotations)
                fig.update_layout(annotations=existing_annotations)
            else:
                fig.update_layout(annotations=layout_annotations)

            chart["figure"] = fig
            chart["layout"] = fig.layout
            chart["annotations"] = annotations

        return chart


# Export all public names
__all__ = ["ProductionChartBuilder"]
