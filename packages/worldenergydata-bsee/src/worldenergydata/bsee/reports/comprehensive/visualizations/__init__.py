"""
Visualization components for comprehensive reports.

Provides charts, maps, and interactive dashboards.
"""

from .dashboard_builder import ChartConfig as DashboardChartConfig
from .dashboard_builder import (
    DashboardBuilder,
    DashboardConfig,
)
from .economic_charts import EconomicChart, EconomicMetrics
from .geographic_charts import FieldBoundary, GeographicChart, WellLocation
from .production_charts import ChartConfig, ProductionChart
from .well_performance_charts import PerformanceMetrics, WellPerformanceChart

__all__ = [
    "ProductionChart",
    "WellPerformanceChart",
    "EconomicChart",
    "GeographicChart",
    "DashboardBuilder",
    "ChartConfig",
    "PerformanceMetrics",
    "EconomicMetrics",
    "WellLocation",
    "FieldBoundary",
    "DashboardConfig",
    "DashboardChartConfig",
]

# Version info
__version__ = "1.0.0"
