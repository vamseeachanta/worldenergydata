"""
Comprehensive Report System for BSEE Data

This module provides a hierarchical reporting system for oil and gas field data,
supporting multi-level aggregation from wells to blocks with economic analysis
and multi-format export capabilities.

Enhanced Features:
- Direct integration with BSEE data refresh modules
- Real-time data fetching from binary files
- Block and lease-level data aggregation
- Production data from multiple sources
"""

from .controller_enhanced import (
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

from .data_loader_enhanced import HierarchicalDataLoader

from .aggregators import (
    DataAggregator,
    BlockAggregator,
    FieldAggregator,
    LeaseAggregator
)

__version__ = "1.1.0"
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
    "ProductionPeriod",
    "HierarchicalDataLoader",
    "DataAggregator",
    "BlockAggregator",
    "FieldAggregator",
    "LeaseAggregator"
]