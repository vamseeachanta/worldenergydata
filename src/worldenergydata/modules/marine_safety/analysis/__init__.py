"""
Marine Safety Analysis Module

This package provides comprehensive statistical analysis capabilities for marine
safety incident data including cause analysis, trend identification,
cross-tabulation studies, and cross-source incident correlation.
"""

from .cause_statistics import (
    CauseStatistics,
    CrossTabulation,
    FrequencyDistribution,
    StatisticalSummary,
    TemporalTrend,
)
from .correlation import (
    DeduplicationMetrics,
    DeduplicationResult,
    IncidentDeduplicator,
    IncidentMatcher,
    MatchConfig,
    MatchResult,
    MatchType,
)
from .incidents.hatch_maloperation_analysis import HatchMaloperationAnalyzer

__all__ = [
    # Cause Statistics
    "CauseStatistics",
    "FrequencyDistribution",
    "TemporalTrend",
    "CrossTabulation",
    "StatisticalSummary",
    # Incident Analysis
    "HatchMaloperationAnalyzer",
    # Cross-Source Correlation
    "IncidentMatcher",
    "MatchConfig",
    "MatchResult",
    "MatchType",
    "IncidentDeduplicator",
    "DeduplicationResult",
    "DeduplicationMetrics",
]
