"""
Interactive dashboard components with quality filters for well production dashboard.

This module provides interactive UI components that are quality-aware and integrate
with the verification system for data quality indicators.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

# Optional imports with fallback
try:
    import plotly.graph_objs as go
    from plotly.subplots import make_subplots

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None
    make_subplots = None

try:
    import dash
    import dash_bootstrap_components as dbc
    from dash import Input, Output, State, callback_context, dcc, html

    DASH_AVAILABLE = True
except ImportError:
    DASH_AVAILABLE = False
    dcc = html = Input = Output = State = callback_context = dbc = None

logger = logging.getLogger(__name__)


class QualityLevel(Enum):
    """Quality level enumeration."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    FAILED = "failed"


class FreshnessStatus(Enum):
    """Data freshness status."""

    FRESH = "fresh"
    RECENT = "recent"
    STALE = "stale"
    OUTDATED = "outdated"


@dataclass
class FilterConfig:
    """Configuration for filters."""

    quality_threshold: int = 70
    freshness_days: int = 7
    anomaly_threshold: float = 3.0
    date_format: str = "YYYY-MM-DD"


class QualityFilter:
    """Quality-aware filter component for dashboard data."""

    def __init__(self, config: Optional[FilterConfig] = None):
        """Initialize quality filter."""
        self.config = config or FilterConfig()
        self.quality_levels = {
            QualityLevel.HIGH: (90, 100),
            QualityLevel.MEDIUM: (70, 89),
            QualityLevel.LOW: (50, 69),
            QualityLevel.FAILED: (0, 49),
        }

    def filter_by_quality(
        self, data: pd.DataFrame, min_score: int = 70
    ) -> pd.DataFrame:
        """Filter data by quality score threshold."""
        if "quality_score" not in data.columns:
            logger.warning("No quality_score column found, returning all data")
            return data

        return data[data["quality_score"] >= min_score].copy()

    def filter_by_status(self, data: pd.DataFrame, statuses: List[str]) -> pd.DataFrame:
        """Filter data by verification status."""
        if "verification_status" not in data.columns:
            logger.warning("No verification_status column found, returning all data")
            return data

        return data[data["verification_status"].isin(statuses)].copy()

    def create_quality_dropdown(self, component_id: str) -> Dict[str, Any]:
        """Create quality filter dropdown component."""
        if not DASH_AVAILABLE:
            return {
                "id": component_id,
                "options": [
                    {"label": "All Data", "value": "all"},
                    {"label": "High Quality (90+)", "value": "high"},
                    {"label": "Medium Quality (70-89)", "value": "medium"},
                    {"label": "Verified Only", "value": "verified"},
                ],
                "value": "all",
            }

        return dcc.Dropdown(
            id=component_id,
            options=[
                {"label": "All Data", "value": "all"},
                {"label": "High Quality (90+)", "value": "high"},
                {"label": "Medium Quality (70-89)", "value": "medium"},
                {"label": "Verified Only", "value": "verified"},
                {"label": "Exclude Failed", "value": "exclude_failed"},
            ],
            value="all",
            placeholder="Select quality filter...",
        )

    def apply_filter_chain(
        self, data: pd.DataFrame, filters: Dict[str, Any]
    ) -> pd.DataFrame:
        """Apply multiple filters in sequence."""
        result = data.copy()

        # Apply quality score filter
        if "quality_score" in filters and filters["quality_score"] is not None:
            result = self.filter_by_quality(result, filters["quality_score"])

        # Apply verification status filter
        if "verification_status" in filters and filters["verification_status"]:
            result = self.filter_by_status(result, filters["verification_status"])

        # Apply custom filters
        for key, value in filters.items():
            if (
                key not in ["quality_score", "verification_status"]
                and value is not None
            ):
                if key in result.columns:
                    if isinstance(value, list):
                        result = result[result[key].isin(value)]
                    else:
                        result = result[result[key] == value]

        return result

    def get_quality_badges(self, data: pd.DataFrame) -> List[Dict[str, str]]:
        """Generate quality badges for data points."""
        badges = []

        if "quality_score" not in data.columns:
            return badges

        for _, row in data.iterrows():
            score = row.get("quality_score", 0)

            if score >= 90:
                color = "success"
                text = "High Quality"
            elif score >= 70:
                color = "warning"
                text = "Medium Quality"
            elif score >= 50:
                color = "info"
                text = "Low Quality"
            else:
                color = "danger"
                text = "Failed"

            badges.append(
                {"color": color, "text": f"{text} ({score:.0f}%)", "score": score}
            )

        return badges


class DateRangeSelector:
    """Date range selector with data freshness indicators."""

    def __init__(self):
        """Initialize date range selector."""
        self.presets = self._create_preset_ranges()

    def create_date_range_picker(self, component_id: str) -> Dict[str, Any]:
        """Create date range picker component."""
        today = datetime.now().date()

        if not DASH_AVAILABLE:
            return {
                "id": component_id,
                "start_date": (today - timedelta(days=30)).isoformat(),
                "end_date": today.isoformat(),
                "display_format": "YYYY-MM-DD",
            }

        return dcc.DatePickerRange(
            id=component_id,
            start_date=today - timedelta(days=30),
            end_date=today,
            display_format="YYYY-MM-DD",
            style={"marginBottom": "10px"},
        )

    def filter_by_date_range(
        self, data: pd.DataFrame, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """Filter data by date range."""
        if "date" not in data.columns:
            logger.warning("No date column found, returning all data")
            return data

        # Ensure date column is datetime
        data["date"] = pd.to_datetime(data["date"])

        mask = (data["date"] >= start_date) & (data["date"] <= end_date)
        return data[mask].copy()

    def calculate_freshness(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate data freshness metrics."""
        if "last_updated" not in data.columns and "date" not in data.columns:
            return {"days_old": -1, "freshness_score": 0, "status": "unknown"}

        # Use last_updated if available, otherwise use date
        date_col = "last_updated" if "last_updated" in data.columns else "date"
        latest_date = pd.to_datetime(data[date_col]).max()

        if pd.isna(latest_date):
            return {"days_old": -1, "freshness_score": 0, "status": "unknown"}

        days_old = (datetime.now() - latest_date).days

        # Calculate freshness score (100 = today, 0 = 30+ days old)
        freshness_score = max(0, min(100, 100 - (days_old * 3.33)))

        # Determine status
        if days_old <= 1:
            status = FreshnessStatus.FRESH.value
        elif days_old <= 7:
            status = FreshnessStatus.RECENT.value
        elif days_old <= 30:
            status = FreshnessStatus.STALE.value
        else:
            status = FreshnessStatus.OUTDATED.value

        return {
            "days_old": days_old,
            "freshness_score": freshness_score,
            "status": status,
            "latest_date": latest_date.isoformat(),
        }

    def create_freshness_indicator(self, data: pd.DataFrame) -> Dict[str, str]:
        """Create freshness indicator component."""
        freshness = self.calculate_freshness(data)

        color_map = {
            FreshnessStatus.FRESH.value: "success",
            FreshnessStatus.RECENT.value: "info",
            FreshnessStatus.STALE.value: "warning",
            FreshnessStatus.OUTDATED.value: "danger",
        }

        icon_map = {
            FreshnessStatus.FRESH.value: "✓",
            FreshnessStatus.RECENT.value: "⚡",
            FreshnessStatus.STALE.value: "⚠",
            FreshnessStatus.OUTDATED.value: "✗",
        }

        return {
            "color": color_map.get(freshness["status"], "secondary"),
            "text": f"Data freshness: {freshness['days_old']} days old",
            "icon": icon_map.get(freshness["status"], "?"),
            "score": freshness["freshness_score"],
        }

    def get_preset_ranges(self) -> Dict[str, Tuple[datetime, datetime]]:
        """Get preset date range options."""
        return self.presets

    def _create_preset_ranges(self) -> Dict[str, Tuple[datetime, datetime]]:
        """Create preset date ranges."""
        today = datetime.now().date()

        return {
            "Last 7 Days": (today - timedelta(days=7), today),
            "Last 30 Days": (today - timedelta(days=30), today),
            "Last 90 Days": (today - timedelta(days=90), today),
            "Year to Date": (datetime(today.year, 1, 1).date(), today),
            "Last Year": (
                datetime(today.year - 1, 1, 1).date(),
                datetime(today.year - 1, 12, 31).date(),
            ),
            "All Time": (datetime(2000, 1, 1).date(), today),
        }


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


class AuditTrailDrilldown:
    """Audit trail drill-down functionality."""

    def __init__(self):
        """Initialize audit trail drilldown."""
        self.audit_cache = {}

    def create_audit_link(self, well_id: str, verification_id: str) -> Dict[str, str]:
        """Create audit trail link."""
        return {
            "href": f"/audit/{well_id}/{verification_id}",
            "text": "View Audit Trail",
            "icon": "📋",
            "target": "_blank",
        }

    def get_audit_history(self, well_id: str) -> List[Dict[str, Any]]:
        """Retrieve audit history for a well."""
        # Check cache first
        if well_id in self.audit_cache:
            return self.audit_cache[well_id]

        # Fetch from verification system
        history = self._fetch_audit_data(well_id)

        # Cache the result
        self.audit_cache[well_id] = history

        return history

    def create_audit_modal(self, modal_id: str) -> Dict[str, Any]:
        """Create audit modal component."""
        if not DASH_AVAILABLE:
            return {
                "id": modal_id,
                "title": "Audit Trail",
                "content": "Audit history will be displayed here",
            }

        return dbc.Modal(
            [
                dbc.ModalHeader("Audit Trail"),
                dbc.ModalBody(id=f"{modal_id}-body"),
                dbc.ModalFooter(
                    dbc.Button("Close", id=f"{modal_id}-close", className="ml-auto")
                ),
            ],
            id=modal_id,
            size="lg",
        )

    def format_audit_entry(self, audit_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Format audit entry for display."""
        formatted = {
            "timestamp": (
                audit_entry.get("timestamp", "").isoformat()
                if isinstance(audit_entry.get("timestamp"), datetime)
                else audit_entry.get("timestamp", "")
            ),
            "well_id": audit_entry.get("well_id", ""),
            "verification_id": audit_entry.get("verification_id", ""),
            "changes": [],
        }

        # Format changes
        for change in audit_entry.get("changes", []):
            formatted["changes"].append(
                {
                    "field": change.get("field", ""),
                    "old_value": change.get("old", ""),
                    "new_value": change.get("new", ""),
                    "reason": change.get("reason", ""),
                }
            )

        return formatted

    def create_change_timeline(
        self, audit_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create timeline visualization of changes."""
        timeline = {"events": [], "start_date": None, "end_date": None}

        for entry in audit_history:
            event = {
                "timestamp": entry.get("timestamp"),
                "title": f"Verification {entry.get('verification_id', '')}",
                "description": f"{len(entry.get('changes', []))} changes",
                "type": "verification",
            }
            timeline["events"].append(event)

        if timeline["events"]:
            timestamps = [
                e["timestamp"] for e in timeline["events"] if e["timestamp"] is not None
            ]
            if timestamps:
                timeline["start_date"] = min(timestamps)
                timeline["end_date"] = max(timestamps)

        return timeline

    def _fetch_audit_data(self, well_id: str) -> List[Dict[str, Any]]:
        """Fetch audit data from verification system (mock implementation)."""
        # This would connect to the actual verification system
        return []


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
            data[data[anomaly_column] == True]
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

        anomaly_data = data[data["is_anomaly"] == True]

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


class DataFreshnessIndicator:
    """Data freshness indicator component."""

    def __init__(self):
        """Initialize freshness indicator."""
        self.freshness_thresholds = {
            "fresh": 1,  # 1 day
            "recent": 7,  # 7 days
            "stale": 30,  # 30 days
        }

    def calculate_age(self, last_update: datetime) -> Dict[str, Any]:
        """Calculate data age from last update."""
        if not isinstance(last_update, datetime):
            last_update = pd.to_datetime(last_update)

        age = datetime.now() - last_update
        days = age.days
        hours = age.seconds // 3600

        if days <= self.freshness_thresholds["fresh"]:
            status = "fresh"
        elif days <= self.freshness_thresholds["recent"]:
            status = "recent"
        elif days <= self.freshness_thresholds["stale"]:
            status = "stale"
        else:
            status = "outdated"

        return {
            "days": days,
            "hours": hours,
            "status": status,
            "last_update": last_update.isoformat(),
        }

    def get_freshness_color(self, days_old: int) -> str:
        """Get color code based on data age."""
        if days_old <= self.freshness_thresholds["fresh"]:
            return "success"
        elif days_old <= self.freshness_thresholds["recent"]:
            return "warning"
        else:
            return "danger"

    def create_freshness_badge(self, last_update: datetime) -> Dict[str, str]:
        """Create freshness badge component."""
        age_info = self.calculate_age(last_update)

        if age_info["days"] == 0:
            text = f"Updated {age_info['hours']} hours ago"
        else:
            text = f"Updated {age_info['days']} days ago"

        return {
            "color": self.get_freshness_color(age_info["days"]),
            "text": text,
            "status": age_info["status"],
        }


class FilterChain:
    """Chain multiple filters together."""

    def __init__(self):
        """Initialize filter chain."""
        self.filters = {}

    def add_filter(self, name: str, filter_func: callable):
        """Add filter to chain."""
        self.filters[name] = filter_func

    def remove_filter(self, name: str):
        """Remove filter from chain."""
        if name in self.filters:
            del self.filters[name]

    def apply(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply all filters in chain."""
        result = data

        for name, filter_func in self.filters.items():
            try:
                result = filter_func(result)
                logger.debug(f"Applied filter '{name}', rows: {len(result)}")
            except Exception as e:
                logger.error(f"Error applying filter '{name}': {e}")

        return result

    def clear(self):
        """Clear all filters."""
        self.filters = {}


class ChartInteractions:
    """Handle chart interaction events."""

    def __init__(self):
        """Initialize chart interactions."""
        self.selected_points = []
        self.hover_data = {}

    def handle_click(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle click events on charts."""
        if not event_data or "points" not in event_data:
            return {}

        point = event_data["points"][0]

        return {
            "well_id": point.get("customdata", ""),
            "date": point.get("x", ""),
            "value": point.get("y", 0),
            "series": point.get("curveNumber", 0),
        }

    def handle_hover(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle hover events on charts."""
        if not event_data or "points" not in event_data:
            return {}

        point = event_data["points"][0]

        return {
            "tooltip": f"Value: {point.get('y', 0):.2f}",
            "x": point.get("x", ""),
            "y": point.get("y", 0),
        }

    def handle_selection(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle selection events on charts."""
        if not event_data or "points" not in event_data:
            return {"selected": []}

        selected = []
        for point in event_data["points"]:
            selected.append(
                {
                    "x": point.get("x", ""),
                    "y": point.get("y", 0),
                    "index": point.get("pointIndex", 0),
                }
            )

        self.selected_points = selected
        return {"selected": selected}

    def create_context_menu(self, menu_items: List[str]) -> Dict[str, Any]:
        """Create context menu for chart interactions."""
        return {
            "items": [
                {
                    "label": item,
                    "action": f'handle_{item.lower().replace(" ", "_")}',
                    "icon": self._get_menu_icon(item),
                }
                for item in menu_items
            ]
        }

    def _get_menu_icon(self, item: str) -> str:
        """Get icon for menu item."""
        icons = {
            "Export": "💾",
            "Zoom": "🔍",
            "Reset": "↺",
            "Filter": "🔽",
            "Settings": "⚙️",
        }
        return icons.get(item, "•")


class InteractiveDashboardComponents:
    """Main orchestrator for interactive dashboard components."""

    def __init__(self, config: Optional[FilterConfig] = None):
        """Initialize interactive dashboard components."""
        self.config = config or FilterConfig()
        self.components = {}
        self.callbacks = []

    def initialize_components(self) -> Dict[str, Any]:
        """Initialize all interactive components."""
        self.components = {
            "quality_filter": QualityFilter(self.config),
            "date_selector": DateRangeSelector(),
            "chart_library": WellChartLibrary(),
            "audit_drilldown": AuditTrailDrilldown(),
            "anomaly_highlighter": AnomalyHighlighter(),
            "freshness_indicator": DataFreshnessIndicator(),
            "filter_chain": FilterChain(),
            "chart_interactions": ChartInteractions(),
        }

        logger.info("Initialized all interactive components")
        return self.components

    def create_filter_panel(self) -> Dict[str, Any]:
        """Create comprehensive filter panel."""
        if not self.components:
            self.initialize_components()

        panel = {
            "quality_filters": self.components[
                "quality_filter"
            ].create_quality_dropdown("quality-dropdown"),
            "date_filters": self.components["date_selector"].create_date_range_picker(
                "date-picker"
            ),
            "well_filters": self._create_well_selector(),
            "field_filters": self._create_field_selector(),
            "anomaly_toggle": self._create_anomaly_toggle(),
        }

        return panel

    def apply_all_filters(
        self, data: pd.DataFrame, filters: Dict[str, Any]
    ) -> pd.DataFrame:
        """Apply all active filters to data."""
        if not self.components:
            self.initialize_components()

        filter_chain = self.components["filter_chain"]
        filter_chain.clear()

        # Add quality filter
        if "quality_min" in filters and filters["quality_min"]:
            filter_chain.add_filter(
                "quality",
                lambda df: self.components["quality_filter"].filter_by_quality(
                    df, filters["quality_min"]
                ),
            )

        # Add date filter
        if "date_start" in filters and "date_end" in filters:
            filter_chain.add_filter(
                "date",
                lambda df: self.components["date_selector"].filter_by_date_range(
                    df,
                    pd.to_datetime(filters["date_start"]),
                    pd.to_datetime(filters["date_end"]),
                ),
            )

        # Add well filter
        if "wells" in filters and filters["wells"]:
            filter_chain.add_filter(
                "wells",
                lambda df: (
                    df[df["well_name"].isin(filters["wells"])]
                    if "well_name" in df.columns
                    else df
                ),
            )

        return filter_chain.apply(data)

    def create_interactive_layout(self) -> Any:
        """Create complete interactive layout."""
        if not DASH_AVAILABLE:
            return {"type": "layout", "components": list(self.components.keys())}

        layout = html.Div(
            [
                # Header
                html.H1("Well Production Dashboard", className="dashboard-header"),
                # Filter Panel
                html.Div(
                    [
                        html.H3("Filters"),
                        html.Div(
                            id="filter-panel",
                            children=[
                                # Quality filter
                                html.Label("Quality Filter"),
                                dcc.Dropdown(id="quality-filter"),
                                # Date filter
                                html.Label("Date Range"),
                                dcc.DatePickerRange(id="date-range"),
                                # Well filter
                                html.Label("Select Wells"),
                                dcc.Dropdown(id="well-filter", multi=True),
                            ],
                        ),
                    ],
                    className="filter-container",
                ),
                # Main content area
                html.Div(
                    [dcc.Graph(id="main-chart"), html.Div(id="chart-details")],
                    className="content-container",
                ),
                # Anomaly panel
                html.Div(id="anomaly-panel"),
                # Audit modal
                html.Div(id="audit-modal"),
            ]
        )

        return layout

    def register_callbacks(self, app: Any):
        """Register interactive callbacks."""
        if not DASH_AVAILABLE or not app:
            logger.warning("Dash not available, skipping callback registration")
            return

        # Filter callback
        @app.callback(
            Output("main-chart", "figure"),
            [
                Input("quality-filter", "value"),
                Input("date-range", "start_date"),
                Input("date-range", "end_date"),
                Input("well-filter", "value"),
            ],
        )
        def update_chart(quality, start_date, end_date, wells):
            """Update chart based on filters."""
            # This would be implemented with actual data
            return {}

        # Click callback
        @app.callback(
            Output("chart-details", "children"), [Input("main-chart", "clickData")]
        )
        def display_click_data(clickData):
            """Display details on click."""
            if clickData:
                interactions = self.components.get("chart_interactions")
                if interactions:
                    details = interactions.handle_click(clickData)
                    return html.Div(
                        [
                            html.H4("Selected Point"),
                            html.P(f"Well: {details.get('well_id', 'N/A')}"),
                            html.P(f"Date: {details.get('date', 'N/A')}"),
                            html.P(f"Value: {details.get('value', 0):.2f}"),
                        ]
                    )
            return html.Div()

        logger.info("Registered interactive callbacks")

    def _create_well_selector(self) -> Dict[str, Any]:
        """Create well selector dropdown."""
        return {
            "id": "well-selector",
            "options": [],  # Would be populated from data
            "multi": True,
            "placeholder": "Select wells...",
        }

    def _create_field_selector(self) -> Dict[str, Any]:
        """Create field selector dropdown."""
        return {
            "id": "field-selector",
            "options": [],  # Would be populated from data
            "multi": True,
            "placeholder": "Select fields...",
        }

    def _create_anomaly_toggle(self) -> Dict[str, Any]:
        """Create anomaly display toggle."""
        return {
            "id": "anomaly-toggle",
            "options": [
                {"label": "Show Anomalies", "value": "show"},
                {"label": "Highlight Only", "value": "highlight"},
                {"label": "Hide", "value": "hide"},
            ],
            "value": "show",
        }


# Export main components
__all__ = [
    "QualityFilter",
    "DateRangeSelector",
    "WellChartLibrary",
    "AuditTrailDrilldown",
    "AnomalyHighlighter",
    "InteractiveDashboardComponents",
    "DataFreshnessIndicator",
    "FilterChain",
    "ChartInteractions",
    "QualityLevel",
    "FreshnessStatus",
    "FilterConfig",
]
