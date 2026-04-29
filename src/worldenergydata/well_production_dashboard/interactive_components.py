"""
Interactive dashboard components with quality filters for well production dashboard.

This module provides interactive UI components that are quality-aware and integrate
with the verification system for data quality indicators.

NOTE: This module has been refactored into smaller, focused modules:
- components_base.py: Enums, config, and shared imports
- components_filters.py: QualityFilter, DateRangeSelector, FilterChain, DataFreshnessIndicator
- components_charts.py: WellChartLibrary
- components_audit.py: AuditTrailDrilldown
- components_anomaly.py: AnomalyHighlighter
- components_interactions.py: ChartInteractions
- components_orchestrator.py: InteractiveDashboardComponents

This file re-exports all public names for backward compatibility.
"""

# Re-export chart/orchestrator compatibility targets. Keep ``go``/Dash objects on
# this module because legacy tests/callers patch ``interactive_components.*``.
from . import components_charts as _components_charts
from . import components_orchestrator as _components_orchestrator
from .components_anomaly import AnomalyHighlighter
from .components_audit import AuditTrailDrilldown
from .components_base import (
    FilterConfig,
    FreshnessStatus,
    Input,
    Output,
    QualityLevel,
    dcc,
    go,
    html,
)
from .components_filters import (
    DataFreshnessIndicator,
    DateRangeSelector,
    FilterChain,
    QualityFilter,
)
from .components_interactions import ChartInteractions


class WellChartLibrary(_components_charts.WellChartLibrary):
    """Compatibility wrapper for chart methods that patch Plotly via this module."""

    @staticmethod
    def _sync_plotly_graph_objects():
        _components_charts.go = go

    def create_type_curve(self, *args, **kwargs):
        self._sync_plotly_graph_objects()
        return super().create_type_curve(*args, **kwargs)

    def create_bubble_map(self, *args, **kwargs):
        self._sync_plotly_graph_objects()
        return super().create_bubble_map(*args, **kwargs)

    def create_waterfall_chart(self, *args, **kwargs):
        self._sync_plotly_graph_objects()
        return super().create_waterfall_chart(*args, **kwargs)

    def create_gauge_chart(self, *args, **kwargs):
        self._sync_plotly_graph_objects()
        return super().create_gauge_chart(*args, **kwargs)

    def create_3d_surface(self, *args, **kwargs):
        self._sync_plotly_graph_objects()
        return super().create_3d_surface(*args, **kwargs)


class InteractiveDashboardComponents(
    _components_orchestrator.InteractiveDashboardComponents
):
    """Compatibility wrapper for layout/callback methods patched via this module."""

    @staticmethod
    def _sync_dash_components():
        _components_orchestrator.dcc = dcc
        _components_orchestrator.html = html
        _components_orchestrator.Input = Input
        _components_orchestrator.Output = Output

    def create_interactive_layout(self, *args, **kwargs):
        self._sync_dash_components()
        return super().create_interactive_layout(*args, **kwargs)

    def register_callbacks(self, *args, **kwargs):
        self._sync_dash_components()
        return super().register_callbacks(*args, **kwargs)


# Export main components (backward compatible)
__all__ = [
    # Base types
    "QualityLevel",
    "FreshnessStatus",
    "FilterConfig",
    # Filter components
    "QualityFilter",
    "DateRangeSelector",
    "DataFreshnessIndicator",
    "FilterChain",
    # Chart components
    "WellChartLibrary",
    # Audit components
    "AuditTrailDrilldown",
    # Anomaly components
    "AnomalyHighlighter",
    # Interaction components
    "ChartInteractions",
    # Orchestrator
    "InteractiveDashboardComponents",
]
