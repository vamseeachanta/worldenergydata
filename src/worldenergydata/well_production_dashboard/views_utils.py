"""
Shared utilities for well detail views.

Contains common configuration, constants, and helper classes used across
all view modules.
"""

import logging
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml

# Try to import plotly, handle if not available
try:
    import plotly.graph_objects as go

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    warnings.warn("Plotly not available, chart functionality will be limited")

logger = logging.getLogger(__name__)


@dataclass
class WellDetailConfig:
    """Configuration for well detail views."""

    show_quality_indicators: bool = True
    enable_audit_links: bool = True
    chart_refresh_rate: int = 500  # milliseconds
    quality_threshold: float = 0.8
    chart_types: List[str] = field(
        default_factory=lambda: [
            "production_time_series",
            "decline_curve",
            "economic_waterfall",
            "quality_timeline",
        ]
    )
    export_formats: List[str] = field(default_factory=lambda: ["pdf", "excel"])

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "WellDetailConfig":
        """Load configuration from YAML file."""
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)


class ChartQualityIndicator:
    """Adds quality indicators to charts."""

    @staticmethod
    def add_quality_overlay(
        fig: Any, quality_scores: pd.Series, threshold: float = 0.8
    ) -> Any:
        """Add quality score overlay to chart."""
        if not PLOTLY_AVAILABLE:
            return fig

        # Add quality score as secondary y-axis
        fig.add_trace(
            go.Scatter(
                x=quality_scores.index,
                y=quality_scores.values,
                name="Quality Score",
                mode="lines",
                line=dict(color="rgba(128, 128, 128, 0.3)", width=1),
                yaxis="y2",
                hovertemplate="Quality: %{y:.2f}<extra></extra>",
            )
        )

        # Add threshold line
        fig.add_hline(
            y=threshold,
            line_dash="dash",
            line_color="orange",
            annotation_text=f"Quality Threshold ({threshold})",
            yref="y2",
        )

        # Update layout for dual y-axis
        fig.update_layout(
            yaxis2=dict(
                title="Quality Score",
                overlaying="y",
                side="right",
                range=[0, 1],
                showgrid=False,
            )
        )

        return fig

    @staticmethod
    def add_verification_markers(fig: Any, verification_status: pd.Series) -> Any:
        """Add verification status markers to chart."""
        if not PLOTLY_AVAILABLE:
            return fig

        # Color mapping for verification status
        color_map = {"verified": "green", "pending": "yellow", "failed": "red"}

        # Add markers for different verification statuses
        for status in ["verified", "pending", "failed"]:
            mask = verification_status == status
            if mask.any():
                fig.add_trace(
                    go.Scatter(
                        x=verification_status[mask].index,
                        y=[0] * mask.sum(),
                        mode="markers",
                        marker=dict(color=color_map[status], size=8, symbol="circle"),
                        name=f"{status.capitalize()} Data",
                        showlegend=True,
                        yaxis="y3",
                        hovertemplate=f"Status: {status}<extra></extra>",
                    )
                )

        return fig


# Export all public names
__all__ = [
    "PLOTLY_AVAILABLE",
    "logger",
    "WellDetailConfig",
    "ChartQualityIndicator",
]
