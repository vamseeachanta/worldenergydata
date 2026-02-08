"""Rig fleet constants and type classification utilities."""

from __future__ import annotations

from enum import Enum


class RigType(str, Enum):
    """Offshore drilling rig type classification."""

    DRILLSHIP = "drillship"
    SEMI_SUBMERSIBLE = "semi_submersible"
    JACK_UP = "jack_up"
    PLATFORM_RIG = "platform_rig"
    TENDER_ASSISTED = "tender_assisted"
    INLAND_BARGE = "inland_barge"
    SUBMERSIBLE = "submersible"
    UNKNOWN = "unknown"


class RigStatus(str, Enum):
    """Current operational status of a rig."""

    ACTIVE = "active"
    STACKED_COLD = "stacked_cold"
    STACKED_WARM = "stacked_warm"
    UNDER_CONTRACT = "under_contract"
    AVAILABLE = "available"
    IN_TRANSIT = "in_transit"
    IN_SHIPYARD = "in_shipyard"
    SCRAPPED = "scrapped"
    UNKNOWN = "unknown"


# Known rig name patterns for heuristic classification.
# Keys are substrings to match (case-insensitive), values are RigType.
_DRILLSHIP_KEYWORDS: tuple[str, ...] = (
    "DEEPWATER",
    "DISCOVERER",
    "EXPLORER",
    "STENA",
    "PACIFIC",
    "TITANIUM",
    "TUNGSTEN",
    "VALIANT",
    "DHIRUBHAI",
    "BOLETTE",
    "WEST NEPTUNE",
)

_SEMI_SUB_KEYWORDS: tuple[str, ...] = (
    "DEVELOPMENT DRILLER",
    "OCEAN",
    "ATWOOD",
    "PAUL ROMANO",
    "CAJUN EXPRESS",
    "THUNDER HORSE",
    "Q4000",
    "HELIX",
)

_JACK_UP_KEYWORDS: tuple[str, ...] = (
    "ROWAN",
    "ENSCO",
    "SPARTAN",
    "KEY HAWAII",
    "GORILLA",
    "RALPH COFFMAN",
)

_PLATFORM_RIG_KEYWORDS: tuple[str, ...] = (
    "PLATFORM RIG",
    "PRODUCTION RIG",
)


def classify_rig_type(rig_name: str) -> RigType:
    """Classify rig type from name using known naming patterns.

    Args:
        rig_name: The rig name string from WAR or fleet data.

    Returns:
        Best-guess RigType based on name heuristics.
    """
    name_upper = rig_name.upper().strip()

    if any(kw in name_upper for kw in _DRILLSHIP_KEYWORDS):
        return RigType.DRILLSHIP
    if any(kw in name_upper for kw in _SEMI_SUB_KEYWORDS):
        return RigType.SEMI_SUBMERSIBLE
    if any(kw in name_upper for kw in _JACK_UP_KEYWORDS):
        return RigType.JACK_UP
    if any(kw in name_upper for kw in _PLATFORM_RIG_KEYWORDS):
        return RigType.PLATFORM_RIG

    return RigType.UNKNOWN
