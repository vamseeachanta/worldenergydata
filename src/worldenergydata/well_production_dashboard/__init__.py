"""
Well Production Dashboard module for WorldEnergyData.

Provides interactive dashboards for well production analysis with verification integration.
"""
from .well_production import (
    WellProductionDashboard,
    WellDashboardConfig,
    WellMetrics,
    FieldAggregator
)
from .api import DashboardAPI
from .cli import DashboardCLI

__all__ = [
    'WellProductionDashboard',
    'WellDashboardConfig',
    'WellMetrics',
    'FieldAggregator',
    'DashboardAPI',
    'DashboardCLI'
]

__version__ = '1.0.0'