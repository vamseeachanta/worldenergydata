"""
Marine Safety Analysis Module

This package provides comprehensive statistical analysis capabilities for marine
safety incident data including cause analysis, trend identification, and
cross-tabulation studies.

Note: cause_statistics and cause_report are in the flat namespace
(worldenergydata.marine_safety.analysis.*). This re-exports them for
backward compatibility.
"""

from worldenergydata.marine_safety.analysis.cause_report import (
    CauseAnalysisReport,
    ReportFilters,
)
from worldenergydata.marine_safety.analysis.cause_statistics import (
    CauseStatistics,
    CrossTabulation,
    FrequencyDistribution,
    StatisticalSummary,
    TemporalTrend,
)

from .incidents.hatch_maloperation_analysis import HatchMaloperationAnalyzer

__all__ = [
    "CauseAnalysisReport",
    "CauseStatistics",
    "CrossTabulation",
    "FrequencyDistribution",
    "HatchMaloperationAnalyzer",
    "ReportFilters",
    "StatisticalSummary",
    "TemporalTrend",
]
