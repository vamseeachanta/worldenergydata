"""
Well Production Dashboard module for WorldEnergyData.

Provides interactive dashboards for well production analysis with verification integration.
"""

from .api import DashboardAPI
from .cli import DashboardCLI
from .well_production import (
    FieldAggregator,
    WellDashboardConfig,
    WellMetrics,
    WellProductionDashboard,
)

__all__ = [
    "WellProductionDashboard",
    "WellDashboardConfig",
    "WellMetrics",
    "FieldAggregator",
    "DashboardAPI",
    "DashboardCLI",
]

__version__ = "1.0.0"
