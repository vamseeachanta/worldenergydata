"""
Main orchestrator for interactive dashboard components.

This module provides the InteractiveDashboardComponents class that coordinates
all component modules and manages layout, callbacks, and filter application.
"""

import logging
from typing import Any, Dict, Optional

import pandas as pd

from .components_anomaly import AnomalyHighlighter
from .components_audit import AuditTrailDrilldown
from .components_base import DASH_AVAILABLE, FilterConfig, Input, Output, dcc, html
from .components_charts import WellChartLibrary
from .components_filters import (
    DataFreshnessIndicator,
    DateRangeSelector,
    FilterChain,
    QualityFilter,
)
from .components_interactions import ChartInteractions

logger = logging.getLogger(__name__)


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
    "InteractiveDashboardComponents",
]
