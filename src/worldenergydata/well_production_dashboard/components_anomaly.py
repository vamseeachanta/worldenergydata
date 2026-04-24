"""
Anomaly detection and highlighting components for interactive dashboard.

This module provides anomaly detection using statistical methods and
visualization highlighting for charts.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .components_base import PLOTLY_AVAILABLE, go

logger = logging.getLogger(__name__)


class AnomalyHighlighter:
    """Anomaly highlighting in charts."""

    def __init__(self, threshold: float = 3.0):
        """Initialize anomaly highlighter."""
        self.threshold = threshold

    def detect_anomalies(
        self,
        values: pd.Series,
        method: str = "zscore",
        threshold: Optional[float] = None,
    ) -> List[bool]:
        """Detect anomalies in data."""
        threshold = threshold or self.threshold

        if method == "zscore":
            mean = values.mean()
            std = values.std()
            z_scores = np.abs((values - mean) / std)
            return (z_scores > threshold).tolist()

        elif method == "iqr":
            Q1 = values.quantile(0.25)
            Q3 = values.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            return ((values < lower_bound) | (values > upper_bound)).tolist()

        else:
            return [False] * len(values)

    def create_annotations(self, anomaly_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Create annotations for anomalies."""
        annotations = []

        for _, row in anomaly_data.iterrows():
            annotations.append(
                {
                    "x": row.get("date", row.get("x", 0)),
                    "y": row.get("value", row.get("y", 0)),
                    "text": "Anomaly Detected",
                    "showarrow": True,
                    "arrowhead": 2,
                    "arrowcolor": "red",
                    "ax": 0,
                    "ay": -40,
                    "bgcolor": "rgba(255, 0, 0, 0.1)",
                    "bordercolor": "red",
                }
            )

        return annotations

    def highlight_in_chart(
        self, figure: Any, data: pd.DataFrame, anomaly_column: str
    ) -> Any:
        """Highlight anomalies in existing chart."""
        if not PLOTLY_AVAILABLE or figure is None:
            return figure

        # Get anomaly points
        anomaly_data = (
            data[data[anomaly_column]]
            if anomaly_column in data.columns
            else pd.DataFrame()
        )

        if not anomaly_data.empty:
            # Add anomaly markers
            figure.add_trace(
                go.Scatter(
                    x=anomaly_data.get("date", anomaly_data.index),
                    y=anomaly_data.get("value", []),
                    mode="markers",
                    name="Anomalies",
                    marker=dict(
                        color="red",
                        size=12,
                        symbol="x",
                        line=dict(width=2, color="darkred"),
                    ),
                    hovertemplate="Anomaly<br>Value: %{y}<extra></extra>",
                )
            )

            # Add annotations
            annotations = self.create_annotations(anomaly_data)
            if hasattr(figure, "layout"):
                figure.layout.annotations = annotations

        return figure

    def get_anomaly_summary(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generate anomaly summary statistics."""
        if "is_anomaly" not in data.columns:
            return {"total_anomalies": 0, "anomaly_rate": 0.0, "recent_anomalies": []}

        anomaly_data = data[data["is_anomaly"]]

        return {
            "total_anomalies": len(anomaly_data),
            "anomaly_rate": len(anomaly_data) / len(data) * 100 if len(data) > 0 else 0,
            "recent_anomalies": anomaly_data.tail(5).to_dict("records"),
            "anomaly_dates": (
                anomaly_data["date"].tolist() if "date" in anomaly_data.columns else []
            ),
        }

    def create_anomaly_heatmap(
        self, data: pd.DataFrame, value_column: str
    ) -> Dict[str, Any]:
        """Create anomaly heatmap data."""
        if value_column not in data.columns:
            return {"z": [[]], "x": [], "y": []}

        # Detect anomalies
        anomalies = self.detect_anomalies(data[value_column])

        # Create heatmap matrix (simplified for example)
        # In practice, this would create a proper time-based heatmap
        z_values = [[1 if a else 0 for a in anomalies]]

        return {
            "z": z_values,
            "x": data.index.tolist() if not data.empty else [],
            "y": ["Anomalies"],
            "colorscale": [[0, "green"], [1, "red"]],
        }


# Export main components
__all__ = [
    "AnomalyHighlighter",
]
