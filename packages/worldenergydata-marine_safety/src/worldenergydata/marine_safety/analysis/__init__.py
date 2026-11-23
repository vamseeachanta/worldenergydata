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
from .incidents.hatch_maloperation_analysis import HatchMaloperationAnalyzer

# Correlation subpackage requires rapidfuzz (optional dependency).
# Use lazy imports so the rest of the analysis module remains usable without it.
try:
    from .correlation import (
        DeduplicationMetrics,
        DeduplicationResult,
        IncidentDeduplicator,
        IncidentMatcher,
        MatchConfig,
        MatchResult,
        MatchType,
    )

    _HAS_CORRELATION = True
except ImportError:
    _HAS_CORRELATION = False

__all__ = [
    # Cause Statistics
    "CauseStatistics",
    "FrequencyDistribution",
    "TemporalTrend",
    "CrossTabulation",
    "StatisticalSummary",
    # Incident Analysis
    "HatchMaloperationAnalyzer",
]

if _HAS_CORRELATION:
    __all__ += [
        # Cross-Source Correlation
        "IncidentMatcher",
        "MatchConfig",
        "MatchResult",
        "MatchType",
        "IncidentDeduplicator",
        "DeduplicationResult",
        "DeduplicationMetrics",
    ]
