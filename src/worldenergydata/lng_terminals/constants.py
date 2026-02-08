"""
Constants for the LNG Terminals Module.

Defines enumerations and constants for terminal types, functions, statuses,
pipeline classifications, data source reliability, and geographic regions
used across the LNG terminals data pipeline.
"""

from enum import Enum
from typing import Set


class TerminalType(str, Enum):
    """Physical configuration of an LNG terminal facility."""

    ONSHORE_IMPORT = "onshore_import"
    ONSHORE_EXPORT = "onshore_export"
    FSRU = "fsru"
    FLNG = "flng"
    ONSHORE_LIQUEFACTION = "onshore_liquefaction"


class TerminalFunction(str, Enum):
    """Operational direction of LNG flow through a terminal."""

    IMPORT = "import"
    EXPORT = "export"
    BIDIRECTIONAL = "bidirectional"


class TerminalStatus(str, Enum):
    """Lifecycle status of a terminal facility."""

    OPERATIONAL = "operational"
    UNDER_CONSTRUCTION = "under_construction"
    PLANNED = "planned"
    PROPOSED = "proposed"
    DECOMMISSIONED = "decommissioned"
    MOTHBALLED = "mothballed"


class PipelineType(str, Enum):
    """Classification of pipelines connected to an LNG terminal."""

    FEED_GAS = "feed_gas"
    LNG_TRANSFER = "lng_transfer"
    LNG_LOADING = "lng_loading"
    BOIL_OFF_GAS = "boil_off_gas"
    SEND_OUT = "send_out"
    PROCESS = "process"
    CONDENSATE = "condensate"


class SourceReliability(str, Enum):
    """Confidence level assigned to a data source."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Region(str, Enum):
    """Geographic regions for LNG terminal classification.

    Each member's value is a human-readable display name suitable for
    reports and UI labels.
    """

    NORTH_AMERICA = "North America"
    SOUTH_AMERICA = "South America"
    EUROPE = "Europe"
    MIDDLE_EAST = "Middle East"
    AFRICA = "Africa"
    ASIA_PACIFIC = "Asia Pacific"
    OCEANIA = "Oceania"


class RefreshMode(str, Enum):
    """Controls how collectors handle cached versus fresh data.

    Members:
        FULL: Discard any cached data and re-fetch everything from the source.
        INCREMENTAL: Fetch only records updated since the last successful run.
        CACHE_FIRST: Return cached data if it exists and has not expired;
            otherwise fetch from the source.
        FORCE_CACHE: Always return cached data (error if no cache exists).
    """

    FULL = "full"
    INCREMENTAL = "incremental"
    CACHE_FIRST = "cache_first"
    FORCE_CACHE = "force_cache"


# ---------------------------------------------------------------------------
# Scalar constants
# ---------------------------------------------------------------------------

RETRYABLE_HTTP_CODES: Set[int] = {500, 502, 503, 504}
"""HTTP status codes that warrant an automatic retry."""

MAX_PIPELINES_PER_TERMINAL: int = 8
"""Upper bound on the number of pipelines associated with a single terminal."""
