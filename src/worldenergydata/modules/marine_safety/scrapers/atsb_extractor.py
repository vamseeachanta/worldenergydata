# ABOUTME: Data extraction logic for ATSB marine investigation scraper.
# ABOUTME: Extracts detailed investigation data from ATSB report pages.

"""
ATSB Data Extractor

Extracts detailed investigation data from ATSB report pages.
"""

import re
from typing import Any, Callable, Dict, Optional

from worldenergydata.modules.marine_safety.constants import IncidentType
from worldenergydata.modules.marine_safety.scrapers.atsb_constants import (
    AUSTRALIAN_STATES,
    INCIDENT_TYPE_MAPPING,
)
from worldenergydata.modules.marine_safety.utils.logger import get_logger

logger = get_logger(__name__)


def normalize_australian_state(state: Optional[str]) -> Optional[str]:
    """
    Normalize Australian state names to standard codes.

    Args:
        state: State name or code

    Returns:
        Normalized state code (e.g., NSW, VIC) or original if not recognized
    """
    if not state:
        return None

    state_lower = state.lower().strip()
    return AUSTRALIAN_STATES.get(state_lower, state.upper())


def extract_investigation_details(
    soup: Any,
    extract_text_fn: Callable,
) -> Dict[str, Any]:
    """
    Extract detailed investigation data from a report page.

    Args:
        soup: BeautifulSoup parsed HTML of report page
        extract_text_fn: Function to extract text from elements

    Returns:
        Dictionary of detailed investigation data
    """
    details: Dict[str, Any] = {}

    # Extract incident type/category
    incident_type = extract_text_fn(
        soup, ".field--name-field-occurrence-type, .occurrence-type"
    )
    if incident_type:
        details["incident_type"] = map_incident_type(incident_type)

    # Extract narrative/description
    narrative = extract_text_fn(soup, ".field--name-body, .narrative, .summary")
    if narrative:
        details["description"] = narrative[:5000]  # Limit length

    # Extract casualties
    fatalities_text = extract_text_fn(
        soup, ".field--name-field-fatalities, .fatalities"
    )
    if fatalities_text:
        details["fatalities"] = parse_casualty_count(fatalities_text)

    injuries_text = extract_text_fn(soup, ".field--name-field-injuries, .injuries")
    if injuries_text:
        details["injuries"] = parse_casualty_count(injuries_text)

    # Extract vessel details
    vessel_type = extract_text_fn(soup, ".field--name-field-vessel-type, .vessel-type")
    if vessel_type:
        details["vessel_type"] = vessel_type

    flag_state = extract_text_fn(soup, ".field--name-field-flag-state, .flag-state")
    if flag_state:
        details["flag_state"] = flag_state

    gross_tonnage = extract_text_fn(
        soup, ".field--name-field-gross-tonnage, .gross-tonnage"
    )
    if gross_tonnage:
        try:
            details["gross_tonnage"] = float(
                gross_tonnage.replace(",", "").replace(" ", "")
            )
        except ValueError:
            pass

    # Extract coordinates if available
    lat = extract_text_fn(soup, ".field--name-field-latitude, .latitude")
    lon = extract_text_fn(soup, ".field--name-field-longitude, .longitude")

    if lat:
        try:
            details["latitude"] = float(lat.replace(",", "."))
        except ValueError:
            pass

    if lon:
        try:
            details["longitude"] = float(lon.replace(",", "."))
        except ValueError:
            pass

    # Extract state/region
    state = extract_text_fn(soup, ".field--name-field-state, .state-territory")
    if state:
        details["state"] = normalize_australian_state(state)

    # Extract probable cause if available
    probable_cause = extract_text_fn(
        soup, ".field--name-field-probable-cause, .probable-cause, .findings"
    )
    if probable_cause:
        details["probable_cause"] = probable_cause[:5000]

    return details


def map_incident_type(incident_type: str) -> str:
    """
    Map ATSB incident type to IncidentType enum value.

    Args:
        incident_type: Incident type string from ATSB

    Returns:
        IncidentType value as string
    """
    incident_lower = incident_type.lower().strip()

    # Try exact match first
    if incident_lower in INCIDENT_TYPE_MAPPING:
        return INCIDENT_TYPE_MAPPING[incident_lower].value

    # Try partial match
    for key, value in INCIDENT_TYPE_MAPPING.items():
        if key in incident_lower or incident_lower in key:
            return value.value

    logger.warning(f"Unknown ATSB incident type: {incident_type}")
    return IncidentType.OTHER.value


def parse_casualty_count(text: str) -> int:
    """
    Parse casualty count from text.

    Args:
        text: Text containing casualty information

    Returns:
        Casualty count as integer
    """
    if not text:
        return 0

    # Try to extract number from text
    match = re.search(r"(\d+)", text)
    if match:
        return int(match.group(1))

    # Check for keywords
    text_lower = text.lower()
    if "none" in text_lower or "no " in text_lower:
        return 0

    return 0
