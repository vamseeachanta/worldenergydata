# ABOUTME: Incident correlation module for linking incidents across data sources.
# ABOUTME: Provides fuzzy matching, deduplication, and cross-reference capabilities.

"""
Cross-Source Incident Correlation Engine

This package provides tools for identifying and linking related incidents across
multiple data sources (USCG, NTSB, MAIB, TSB, ATSB, IMO, etc.). Features include:

- Fuzzy vessel name matching using Levenshtein distance
- IMO number exact matching
- Geographic proximity matching using haversine formula
- Temporal proximity matching
- Combined confidence scoring
- Batch deduplication support

Example usage:
    from worldenergydata.modules.marine_safety.analysis.correlation import (
        IncidentMatcher,
        IncidentDeduplicator,
        MatchConfig
    )

    # Configure matcher
    config = MatchConfig(
        min_confidence=0.75,
        date_tolerance_days=5,
        location_threshold_km=100
    )

    # Find matches
    matcher = IncidentMatcher(config)
    matches = matcher.find_matches(incident, candidates)
"""

from .deduplicator import (
    DeduplicationMetrics,
    DeduplicationResult,
    IncidentDeduplicator,
)
from .matcher import IncidentMatcher, MatchConfig, MatchResult, MatchType

__all__ = [
    # Matcher components
    "IncidentMatcher",
    "MatchConfig",
    "MatchResult",
    "MatchType",
    # Deduplicator components
    "IncidentDeduplicator",
    "DeduplicationResult",
    "DeduplicationMetrics",
]
