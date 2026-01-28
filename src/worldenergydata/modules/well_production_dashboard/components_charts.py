"""
Chart components for interactive dashboard.

This module provides well-specific chart visualizations including type curves,
bubble maps, waterfall charts, gauges, and 3D surfaces.
"""

import logging
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .components_base import PLOTLY_AVAILABLE, go

logger = logging.getLogger(__name__)


class WellChartLibrary:
    """Extended chart library with well-specific visualizations."""

    def __init__(self):
        """Initialize chart library."""
        self.chart_types = [
            "type_curve",
            "bubble_map",
            "waterfall",
            "gauge",
            "3d_surface",
            "radar",
            "sunburst",
            "treemap",
        ]

    def create_type_curve(self, data: pd.DataFrame, well_name: str) -> Any:
        """Create type curve visualization for well production."""
        if not PLOTLY_AVAILABLE:
            logger.warning("Plotly not available, returning mock chart")
            return {"type": "type_curve", "data": data.to_dict()}

        fig = go.Figure()

        # Normalize time to days from start
        data = data.copy()
        data["days"] = (data["date"] - data["date"].min()).dt.days

        # Add production traces
        for column in ["oil", "gas", "water"]:
            if column in data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=data["days"],
                        y=data[column],
                        mode="lines+markers",
                        name=column.capitalize(),
                        hovertemplate=f"{column.capitalize()}: %{{y:.2f}}<br>Day: %{{x}}",
                    )
                )

        fig.update_layout(
            title=f"Type Curve - {well_name}",
            xaxis_title="Days from Start",
            yaxis_title="Production Rate",
            hovermode="x unified",
            showlegend=True,
        )

        return fig

    def create_bubble_map(self, wells_data: pd.DataFrame) -> Any:
        """Create bubble map for multi-well visualization."""
        if not PLOTLY_AVAILABLE:
            return {"type": "bubble_map", "data": wells_data.to_dict()}

        fig = go.Figure()

        # Create bubble map
        fig.add_trace(
            go.Scattergeo(
                lon=wells_data.get("longitude", []),
                lat=wells_data.get("latitude", []),
                text=wells_data.get("well_name", []),
                mode="markers",
                marker=dict(
                    size=wells_data.get("production", [100])
                    / 50,  # Scale for visibility
                    color=wells_data.get("production", []),
                    colorscale="Viridis",
                    showscale=True,
                    colorbar=dict(title="Production"),
                    sizemode="diameter",
                    sizemin=5,
                ),
                hovertemplate="<b>%{text}</b><br>Production: %{marker.color:.0f}<extra></extra>",
            )
        )

        fig.update_layout(
            title="Well Locations and Production",
            geo=dict(
                projection_type="albers usa",
                showland=True,
                landcolor="rgb(243, 243, 243)",
                coastlinecolor="rgb(204, 204, 204)",
            ),
            height=600,
        )

        return fig

    def create_waterfall_chart(self, data: pd.DataFrame) -> Any:
        """Create waterfall chart for production changes."""
        if not PLOTLY_AVAILABLE:
            return {"type": "waterfall", "data": data.to_dict()}

        # Calculate changes
        if "oil" in data.columns:
            values = data["oil"].values
            changes = np.diff(values)

            fig = go.Figure(
                go.Waterfall(
                    name="Oil Production Changes",
                    orientation="v",
                    measure=["absolute"] + ["relative"] * len(changes),
                    x=data["date"].dt.strftime("%Y-%m-%d").tolist(),
                    y=[values[0]] + changes.tolist(),
                    connector={"line": {"color": "rgb(63, 63, 63)"}},
                    decreasing={"marker": {"color": "crimson"}},
                    increasing={"marker": {"color": "green"}},
                    totals={"marker": {"color": "blue"}},
                )
            )

            fig.update_layout(
                title="Production Waterfall",
                xaxis_title="Date",
                yaxis_title="Production Change",
                showlegend=False,
            )

            return fig

        return None

    def create_gauge_chart(
        self, value: float, title: str, min_val: float = 0, max_val: float = 100
    ) -> Any:
        """Create gauge chart for KPIs."""
        if not PLOTLY_AVAILABLE:
            return {"type": "gauge", "value": value, "title": title}

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=value,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": title},
                gauge={
                    "axis": {"range": [min_val, max_val]},
                    "bar": {"color": "darkblue"},
                    "steps": [
                        {
                            "range": [min_val, min_val + (max_val - min_val) * 0.5],
                            "color": "lightgray",
                        },
                        {
                            "range": [min_val + (max_val - min_val) * 0.5, max_val],
                            "color": "gray",
                        },
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": max_val * 0.9,
                    },
                },
            )
        )

        fig.update_layout(height=400)
        return fig

    def create_3d_surface(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> Any:
        """Create 3D surface plot for reservoir visualization."""
        if not PLOTLY_AVAILABLE:
            return {"type": "3d_surface", "shape": z.shape}

        fig = go.Figure(
            data=[go.Surface(x=x, y=y, z=z, colorscale="Viridis", showscale=True)]
        )

        fig.update_layout(
            title="3D Surface Visualization",
            scene=dict(
                xaxis_title="X Coordinate",
                yaxis_title="Y Coordinate",
                zaxis_title="Z Value",
                camera=dict(eye=dict(x=1.5, y=1.5, z=1.5)),
            ),
            height=600,
        )

        return fig


# Export main components
__all__ = [
    "WellChartLibrary",
]
