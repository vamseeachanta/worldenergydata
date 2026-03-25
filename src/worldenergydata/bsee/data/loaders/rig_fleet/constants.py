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
    LAND_RIG = "land_rig"
    WIRELINE_UNIT = "wireline_unit"
    COIL_TUBING_UNIT = "coil_tubing_unit"
    LIFT_BOAT = "lift_boat"
    SNUBBING_UNIT = "snubbing_unit"
    WORKOVER_RIG = "workover_rig"
    SUPPORT_VESSEL = "support_vessel"
    PUMPING_UNIT = "pumping_unit"
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


class DataSource(str, Enum):
    """Origin of rig fleet data."""

    BSEE_WAR = "bsee_war"
    MANUAL_OVERRIDE = "manual_override"
    XLS_HISTORICAL = "xls_historical"
    UNKNOWN = "unknown"


# Known rig name patterns for heuristic classification.
# Ordered by specificity: longer/more-specific prefixes first within each type
# to avoid ambiguous matches (e.g. "OCEAN" could be drillship or semi-sub).

_DRILLSHIP_KEYWORDS: tuple[str, ...] = (
    "NOBLE GLOBETROTTER",
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
    "COBALT",
    "BULLY",
)

_SEMI_SUB_KEYWORDS: tuple[str, ...] = (
    "DEVELOPMENT DRILLER",
    "TRANSOCEAN",
    "NAUTILUS",
    "SEDCO",
    "SCARABEO",
    "MAERSK",
    "OCEAN",
    "ATWOOD",
    "PAUL ROMANO",
    "CAJUN EXPRESS",
    "THUNDER HORSE",
    "Q4000",
    "HELIX",
)

_JACK_UP_KEYWORDS: tuple[str, ...] = (
    "KEY SINGAPORE",
    "KEY MANHATTAN",
    "KEY HAWAII",
    "CECIL PROVINE",
    "RALPH COFFMAN",
    "ROWAN",
    "ENSCO",
    "SPARTAN",
    "GORILLA",
    "HERCULES",
    "SEAHAWK",
    "SUNDOWNER",
)

_PLATFORM_RIG_KEYWORDS: tuple[str, ...] = (
    "HELMERICH & PAYNE",
    "HELMERICH &AMP; PAYNE",
    "PLATFORM RIG",
    "PRODUCTION RIG",
    "NABORS",
    "H&P",
    "PARKER",
    "FLEX RIG",
)

_INLAND_BARGE_KEYWORDS: tuple[str, ...] = (
    "INLAND",
    "BARGE",
)

_WIRELINE_KEYWORDS: tuple[str, ...] = (
    "WIRELINE",
    "SLICKLINE",
    "E-LINE",
    "ELECTRIC LINE",
    "/SL",
    "/WL",
    "/EL",
)

_COIL_TUBING_KEYWORDS: tuple[str, ...] = (
    "COIL TUBING",
    "COILED TUBING",
    "CT UNIT",
    "/CT",
)

_LIFT_BOAT_KEYWORDS: tuple[str, ...] = (
    "LIFT BOAT",
    "LIFTBOAT",
    "L.BOAT",
    "L BOAT",
)

_SNUBBING_KEYWORDS: tuple[str, ...] = (
    "SNUBBING",
    "HYDRAULIC WORKOVER",
)

_SUPPORT_VESSEL_KEYWORDS: tuple[str, ...] = (
    "ANCHOR HANDLING",
    "DIVE SUPPORT",
    "CONSTRUCTION VESSEL",
    "DIVE BOA",
    "D. BOAT",
    "DSV",
)

_PUMPING_KEYWORDS: tuple[str, ...] = (
    "PUMPING UNIT",
    "PUMP UNIT",
)

_WORKOVER_KEYWORDS: tuple[str, ...] = (
    "WORKOVER",
)


def classify_rig_type(rig_name: str) -> RigType:
    """Classify rig type from name using known naming patterns.

    Uses prefix-priority matching: checks each category's keyword list
    in order.  Place more-specific keywords earlier in each tuple to
    avoid false positives.

    Args:
        rig_name: The rig name string from WAR or fleet data.

    Returns:
        Best-guess RigType based on name heuristics.
    """
    name_upper = rig_name.upper().strip()

    # Intervention types first (most-specific to least-specific).
    if any(kw in name_upper for kw in _SNUBBING_KEYWORDS):
        return RigType.SNUBBING_UNIT
    if any(kw in name_upper for kw in _COIL_TUBING_KEYWORDS):
        return RigType.COIL_TUBING_UNIT
    if any(kw in name_upper for kw in _WIRELINE_KEYWORDS):
        return RigType.WIRELINE_UNIT
    if any(kw in name_upper for kw in _LIFT_BOAT_KEYWORDS):
        return RigType.LIFT_BOAT
    if any(kw in name_upper for kw in _SUPPORT_VESSEL_KEYWORDS):
        return RigType.SUPPORT_VESSEL
    if any(kw in name_upper for kw in _PUMPING_KEYWORDS):
        return RigType.PUMPING_UNIT
    if any(kw in name_upper for kw in _WORKOVER_KEYWORDS):
        return RigType.WORKOVER_RIG

    # Drilling rig types.
    if any(kw in name_upper for kw in _DRILLSHIP_KEYWORDS):
        return RigType.DRILLSHIP
    if any(kw in name_upper for kw in _SEMI_SUB_KEYWORDS):
        return RigType.SEMI_SUBMERSIBLE
    if any(kw in name_upper for kw in _JACK_UP_KEYWORDS):
        return RigType.JACK_UP
    if any(kw in name_upper for kw in _PLATFORM_RIG_KEYWORDS):
        return RigType.PLATFORM_RIG
    if any(kw in name_upper for kw in _INLAND_BARGE_KEYWORDS):
        return RigType.INLAND_BARGE

    return RigType.UNKNOWN
