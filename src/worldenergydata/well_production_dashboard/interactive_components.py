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

# Re-export base types and configuration
from .components_base import (
    DASH_AVAILABLE,
    PLOTLY_AVAILABLE,
    FilterConfig,
    FreshnessStatus,
    QualityLevel,
    dbc,
    dcc,
    go,
    html,
    logger,
    make_subplots,
)

# Re-export filter components
from .components_filters import (
    DataFreshnessIndicator,
    DateRangeSelector,
    FilterChain,
    QualityFilter,
)

# Re-export chart components
from .components_charts import WellChartLibrary

# Re-export audit components
from .components_audit import AuditTrailDrilldown

# Re-export anomaly components
from .components_anomaly import AnomalyHighlighter

# Re-export interaction components
from .components_interactions import ChartInteractions

# Re-export orchestrator
from .components_orchestrator import InteractiveDashboardComponents


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
