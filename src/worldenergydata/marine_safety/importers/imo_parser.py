# ABOUTME: Parsing utilities for IMO GISIS data transformation.
# ABOUTME: Handles position parsing, contributing factors extraction, and field mapping.

"""
IMO GISIS Data Parser

Provides parsing functions for transforming raw IMO GISIS data:
- Position string parsing (decimal, DMS formats)
- Contributing factors extraction
- Field mapping and type conversion
- Location and environmental impact description building
"""

import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from worldenergydata.marine_safety.constants import (
    CauseCategory,
    IncidentStatus,
    IncidentType,
    VesselType,
)
from worldenergydata.marine_safety.importers.imo_mappings import (
    CASUALTY_TYPE_MAPPINGS,
    CAUSE_MAPPINGS,
    SHIP_TYPE_MAPPINGS,
    STATUS_MAPPINGS,
)

logger = logging.getLogger(__name__)


def parse_position(position: str) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    """
    Parse position string into latitude and longitude.

    Handles various formats:
    - "12.345, -67.890" (decimal)
    - "12 30 N, 067 45 W" (degrees minutes)
    - "12 30 45 N, 067 45 30 W" (degrees minutes seconds)

    Args:
        position: Position string

    Returns:
        Tuple of (latitude, longitude) as Decimals, or (None, None)
    """
    if not position:
        return None, None

    position = position.strip()

    # Try decimal format first
    decimal_pattern = r"(-?\d+\.?\d*)\s*[,;]\s*(-?\d+\.?\d*)"
    match = re.match(decimal_pattern, position)
    if match:
        try:
            lat = Decimal(match.group(1))
            lon = Decimal(match.group(2))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
        except (ValueError, InvalidOperation):
            pass

    # Try DMS format: 12 30 45 N, 067 45 30 W
    dms_pattern = (
        r"(\d+)\s*[°\s]\s*(\d+)\s*[\''\s]?\s*(\d*\.?\d*)?\s*[\"″\s]?\s*([NS])\s*"
        r"[,;]?\s*"
        r"(\d+)\s*[°\s]\s*(\d+)\s*[\''\s]?\s*(\d*\.?\d*)?\s*[\"″\s]?\s*([EW])"
    )
    match = re.search(dms_pattern, position, re.IGNORECASE)
    if match:
        try:
            lat_deg = int(match.group(1))
            lat_min = int(match.group(2))
            lat_sec = float(match.group(3) or 0)
            lat_dir = match.group(4).upper()

            lon_deg = int(match.group(5))
            lon_min = int(match.group(6))
            lon_sec = float(match.group(7) or 0)
            lon_dir = match.group(8).upper()

            lat = Decimal(str(lat_deg + lat_min / 60 + lat_sec / 3600))
            lon = Decimal(str(lon_deg + lon_min / 60 + lon_sec / 3600))

            if lat_dir == "S":
                lat = -lat
            if lon_dir == "W":
                lon = -lon

            return lat, lon
        except (ValueError, InvalidOperation):
            pass

    logger.debug(f"Could not parse position: {position}")
    return None, None


def map_casualty_type(casualty_type: str) -> str:
    """
    Map IMO GISIS casualty type to IncidentType enum value.

    Args:
        casualty_type: Raw casualty type string from GISIS

    Returns:
        IncidentType enum value string
    """
    if not casualty_type:
        return IncidentType.OTHER.value

    casualty_lower = casualty_type.lower().strip()

    # Try exact match
    if casualty_lower in CASUALTY_TYPE_MAPPINGS:
        return CASUALTY_TYPE_MAPPINGS[casualty_lower]

    # Try partial match
    for key, value in CASUALTY_TYPE_MAPPINGS.items():
        if key in casualty_lower or casualty_lower in key:
            return value

    logger.debug(f"Unknown IMO casualty type: {casualty_type}")
    return IncidentType.OTHER.value


def map_ship_type(ship_type: str) -> str:
    """
    Map IMO GISIS ship type to VesselType enum value.

    Args:
        ship_type: Raw ship type string from GISIS

    Returns:
        VesselType enum value string
    """
    if not ship_type:
        return VesselType.OTHER.value

    ship_lower = ship_type.lower().strip()

    # Try exact match
    if ship_lower in SHIP_TYPE_MAPPINGS:
        return SHIP_TYPE_MAPPINGS[ship_lower]

    # Try partial match
    for key, value in SHIP_TYPE_MAPPINGS.items():
        if key in ship_lower:
            return value

    logger.debug(f"Unknown IMO ship type: {ship_type}")
    return VesselType.OTHER.value


def map_status(status: str) -> str:
    """
    Map IMO investigation status to IncidentStatus enum value.

    Args:
        status: Raw status string from GISIS

    Returns:
        IncidentStatus enum value string
    """
    if not status:
        return IncidentStatus.REPORTED.value

    status_lower = status.lower().strip()

    # Try exact match
    if status_lower in STATUS_MAPPINGS:
        return STATUS_MAPPINGS[status_lower]

    # Try partial match
    for key, value in STATUS_MAPPINGS.items():
        if key in status_lower:
            return value

    logger.debug(f"Unknown IMO status: {status}")
    return IncidentStatus.REPORTED.value


def parse_contributing_factors(factors: str) -> List[str]:
    """
    Parse contributing factors string into list of CauseCategory values.

    Args:
        factors: Contributing factors string (may be comma/semicolon separated)

    Returns:
        List of CauseCategory enum values
    """
    if not factors:
        return []

    # Split by common delimiters
    factor_list = re.split(r"[,;/]", factors)
    cause_categories: List[str] = []

    for factor in factor_list:
        factor_lower = factor.lower().strip()
        if not factor_lower:
            continue

        # Try exact match
        if factor_lower in CAUSE_MAPPINGS:
            cause = CAUSE_MAPPINGS[factor_lower]
            if cause not in cause_categories:
                cause_categories.append(cause)
            continue

        # Try partial match
        matched = False
        for key, value in CAUSE_MAPPINGS.items():
            if key in factor_lower:
                if value not in cause_categories:
                    cause_categories.append(value)
                matched = True
                break

        if not matched:
            # Default to unknown
            if CauseCategory.UNKNOWN.value not in cause_categories:
                cause_categories.append(CauseCategory.UNKNOWN.value)

    return cause_categories


def build_location_description(parsed: Dict[str, Any]) -> Optional[str]:
    """
    Build location description from available location fields.

    Args:
        parsed: Parsed record containing location fields

    Returns:
        Combined location description or None
    """
    parts = []

    if parsed.get("area"):
        parts.append(parsed["area"])

    if parsed.get("waters"):
        parts.append(parsed["waters"])

    if parsed.get("investigating_state"):
        parts.append(f"Waters of {parsed['investigating_state']}")

    return ", ".join(parts) if parts else None


def build_environmental_impact(parsed: Dict[str, Any]) -> str:
    """
    Build environmental impact description from pollution fields.

    Args:
        parsed: Parsed record containing pollution fields

    Returns:
        Environmental impact description string
    """
    parts = []

    if parsed.get("pollution_type"):
        parts.append(f"Type: {parsed['pollution_type']}")

    if parsed.get("pollution_quantity"):
        parts.append(f"Quantity: {parsed['pollution_quantity']}")

    return "; ".join(parts) if parts else ""


def generate_title(parsed: Dict[str, Any]) -> str:
    """
    Generate incident title from available fields.

    Args:
        parsed: Parsed record containing incident fields

    Returns:
        Generated incident title
    """
    vessel_name = parsed.get("vessel_name", "Unknown Vessel")
    incident_type = parsed.get("incident_type", "incident")
    imo_number = parsed.get("imo_number", "")

    # Format incident type for display
    incident_display = incident_type.replace("_", " ").title()

    if imo_number:
        return f"{incident_display} - {vessel_name} (IMO {imo_number})"
    return f"{incident_display} - {vessel_name}"


def calculate_severity(fatalities: int, injuries: int, missing: int) -> int:
    """
    Calculate severity level based on casualties following IMO guidelines.

    IMO categorizes casualties as:
    - Very serious casualty: loss of ship, loss of life, severe pollution
    - Serious casualty: fire, collision, grounding with significant damage
    - Less serious casualty: other incidents

    Args:
        fatalities: Number of fatalities
        injuries: Number of injuries
        missing: Number of missing persons

    Returns:
        Severity level (1=minimal, 2=minor, 3=moderate, 4=serious, 5=catastrophic)
    """
    total_severe = fatalities + missing

    if total_severe >= 10:
        return 5  # Catastrophic (very serious)
    elif total_severe >= 5:
        return 4  # Serious
    elif total_severe >= 1:
        return 3  # Moderate (serious)
    elif injuries >= 10:
        return 3  # Moderate
    elif injuries >= 1:
        return 2  # Minor
    return 1  # Minimal
