"""
Visualization components for comprehensive reports.

Provides charts, maps, and interactive dashboards.
"""

from .production_charts import ProductionChart, ChartConfig
from .well_performance_charts import WellPerformanceChart, PerformanceMetrics
from .economic_charts import EconomicChart, EconomicMetrics
from .geographic_charts import GeographicChart, WellLocation, FieldBoundary
from .dashboard_builder import DashboardBuilder, DashboardConfig, ChartConfig as DashboardChartConfig

__all__ = [
    'ProductionChart',
    'WellPerformanceChart', 
    'EconomicChart',
    'GeographicChart',
    'DashboardBuilder',
    'ChartConfig',
    'PerformanceMetrics',
    'EconomicMetrics',
    'WellLocation',
    'FieldBoundary',
    'DashboardConfig',
    'DashboardChartConfig'
]

# Version info
__version__ = '1.0.0'