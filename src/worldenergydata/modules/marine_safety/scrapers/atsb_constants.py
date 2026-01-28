# ABOUTME: Constants and mappings for ATSB marine investigation scraper.
# ABOUTME: Includes state codes, incident type mappings, and validation patterns.

"""
ATSB Scraper Constants

Mappings, patterns, and constants for the Australian Transport Safety Bureau scraper.
"""

import re
from typing import Dict

from worldenergydata.modules.marine_safety.constants import IncidentStatus, IncidentType

# ATSB Investigation ID pattern: e.g., MO-2022-001, 342-MO-2021-001
ATSB_ID_PATTERN = re.compile(
    r"^(?:\d{3}-)?(?:MO|MR)-?\d{4}-?\d{3}$",
    re.IGNORECASE,
)

# Australian state codes mapping
AUSTRALIAN_STATES: Dict[str, str] = {
    "nsw": "NSW",
    "new south wales": "NSW",
    "vic": "VIC",
    "victoria": "VIC",
    "qld": "QLD",
    "queensland": "QLD",
    "wa": "WA",
    "western australia": "WA",
    "sa": "SA",
    "south australia": "SA",
    "tas": "TAS",
    "tasmania": "TAS",
    "nt": "NT",
    "northern territory": "NT",
    "act": "ACT",
    "australian capital territory": "ACT",
}

# Incident type mapping from ATSB categories
INCIDENT_TYPE_MAPPING: Dict[str, IncidentType] = {
    "collision": IncidentType.COLLISION,
    "contact": IncidentType.COLLISION,
    "striking": IncidentType.COLLISION,
    "grounding": IncidentType.GROUNDING,
    "stranding": IncidentType.GROUNDING,
    "fire": IncidentType.FIRE,
    "explosion": IncidentType.EXPLOSION,
    "capsizing": IncidentType.CAPSIZING,
    "capsize": IncidentType.CAPSIZING,
    "flooding": IncidentType.FLOODING,
    "foundering": IncidentType.FLOODING,
    "sinking": IncidentType.CAPSIZING,
    "structural failure": IncidentType.STRUCTURAL_FAILURE,
    "hull failure": IncidentType.STRUCTURAL_FAILURE,
    "equipment failure": IncidentType.EQUIPMENT_FAILURE,
    "machinery failure": IncidentType.EQUIPMENT_FAILURE,
    "loss of propulsion": IncidentType.LOSS_OF_PROPULSION,
    "propulsion failure": IncidentType.LOSS_OF_PROPULSION,
    "loss of steering": IncidentType.LOSS_OF_CONTROL,
    "loss of control": IncidentType.LOSS_OF_CONTROL,
    "man overboard": IncidentType.PERSONNEL_INJURY,
    "person overboard": IncidentType.PERSONNEL_INJURY,
    "fall overboard": IncidentType.PERSONNEL_INJURY,
    "injury": IncidentType.PERSONNEL_INJURY,
    "fatality": IncidentType.FATALITY,
    "death": IncidentType.FATALITY,
    "pollution": IncidentType.POLLUTION,
    "oil spill": IncidentType.POLLUTION,
    "environmental": IncidentType.ENVIRONMENTAL,
    "weather": IncidentType.WEATHER_RELATED,
    "heavy weather": IncidentType.WEATHER_RELATED,
    "storm": IncidentType.WEATHER_RELATED,
    "cyclone": IncidentType.WEATHER_RELATED,
}

# Status mapping from ATSB investigation status
STATUS_MAPPING: Dict[str, IncidentStatus] = {
    "active": IncidentStatus.UNDER_INVESTIGATION,
    "open": IncidentStatus.UNDER_INVESTIGATION,
    "preliminary": IncidentStatus.PRELIMINARY_REPORT,
    "interim": IncidentStatus.PRELIMINARY_REPORT,
    "final": IncidentStatus.FINAL_REPORT,
    "completed": IncidentStatus.FINAL_REPORT,
    "closed": IncidentStatus.CLOSED,
}

# ATSB URLs
BASE_URL = "https://www.atsb.gov.au"
MARINE_URL = "/publications/investigation_reports/marine"
PDF_BASE_URL = "https://www.atsb.gov.au/publications"

# Default minimum date (ATSB marine data available from ~2003)
DEFAULT_MIN_DATE_YEAR = 2003
DEFAULT_MIN_DATE_MONTH = 1
DEFAULT_MIN_DATE_DAY = 1

# Pagination defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGES = 100  # Safety limit
