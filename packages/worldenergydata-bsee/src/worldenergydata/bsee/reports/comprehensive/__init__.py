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

from .aggregators import (
    BlockAggregator,
    DataAggregator,
    FieldAggregator,
    LeaseAggregator,
)
from .controller_enhanced import (
    ReportConfiguration,
    ReportController,
    ReportParameters,
    ReportType,
)
from .data_loader_enhanced import HierarchicalDataLoader
from .models import (
    Block,
    EconomicMetrics,
    Field,
    HierarchyLevel,
    Lease,
    OrganizationalUnit,
    ProductionMetrics,
    ProductionPeriod,
    Well,
    WellSummary,
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
    "LeaseAggregator",
]
