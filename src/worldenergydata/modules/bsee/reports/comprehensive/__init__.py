"""
Comprehensive Report System for BSEE Data

This module provides a hierarchical reporting system for oil and gas field data,
supporting multi-level aggregation from wells to blocks with economic analysis
and multi-format export capabilities.
"""

from .controller import (
    ReportController,
    ReportConfiguration,
    ReportParameters,
    ReportType
)

from .models import (
    OrganizationalUnit,
    Well,
    Lease,
    Field,
    Block,
    WellSummary,
    ProductionMetrics,
    EconomicMetrics,
    HierarchyLevel,
    ProductionPeriod
)

__version__ = "1.0.0"
__all__ = [
    "ReportController",
    "ReportConfiguration",
    "ReportParameters",
    "ReportType",
    "OrganizationalUnit",
    "Well",
    "Lease",
    "Field",
    "Block",
    "WellSummary",
    "ProductionMetrics",
    "EconomicMetrics",
    "HierarchyLevel",
    "ProductionPeriod"
]