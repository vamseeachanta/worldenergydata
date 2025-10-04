"""
Constants for Marine Safety Module

Defines enumerations and constants for incident types, severity levels,
vessel types, and other categorizations.
"""

from enum import Enum, IntEnum
from typing import Dict, List, Set


class IncidentType(str, Enum):
    """Types of marine safety incidents"""

    COLLISION = "collision"
    GROUNDING = "grounding"
    FIRE = "fire"
    EXPLOSION = "explosion"
    CAPSIZING = "capsizing"
    FLOODING = "flooding"
    EQUIPMENT_FAILURE = "equipment_failure"
    STRUCTURAL_FAILURE = "structural_failure"
    LOSS_OF_PROPULSION = "loss_of_propulsion"
    LOSS_OF_CONTROL = "loss_of_control"
    PERSONNEL_INJURY = "personnel_injury"
    FATALITY = "fatality"
    POLLUTION = "pollution"
    ENVIRONMENTAL = "environmental"
    WEATHER_RELATED = "weather_related"
    NEAR_MISS = "near_miss"
    OTHER = "other"


class SeverityLevel(IntEnum):
    """Severity levels for incidents (1=lowest, 5=highest)"""

    MINIMAL = 1
    MINOR = 2
    MODERATE = 3
    SERIOUS = 4
    CATASTROPHIC = 5


class IncidentStatus(str, Enum):
    """Status of incident investigation"""

    REPORTED = "reported"
    UNDER_INVESTIGATION = "under_investigation"
    PRELIMINARY_REPORT = "preliminary_report"
    FINAL_REPORT = "final_report"
    CLOSED = "closed"
    ARCHIVED = "archived"


class VesselType(str, Enum):
    """Types of vessels involved in offshore operations"""

    # Offshore platforms
    DRILLING_RIG = "drilling_rig"
    PRODUCTION_PLATFORM = "production_platform"
    MODU = "modu"  # Mobile Offshore Drilling Unit
    FPSO = "fpso"  # Floating Production Storage and Offloading
    FSO = "fso"  # Floating Storage and Offloading
    TLP = "tlp"  # Tension Leg Platform
    SPAR_PLATFORM = "spar_platform"
    SEMISUBMERSIBLE = "semisubmersible"
    JACKUP_RIG = "jackup_rig"

    # Support vessels
    SUPPLY_VESSEL = "supply_vessel"
    ANCHOR_HANDLING = "anchor_handling"
    TUG = "tug"
    CREW_BOAT = "crew_boat"
    STANDBY_VESSEL = "standby_vessel"

    # Wind farm vessels
    WIND_TURBINE_INSTALL = "wind_turbine_install"
    CABLE_LAYER = "cable_layer"
    SERVICE_VESSEL = "service_vessel"

    # Other
    TANKER = "tanker"
    CARGO_VESSEL = "cargo_vessel"
    DIVING_SUPPORT = "diving_support"
    RESEARCH_VESSEL = "research_vessel"
    OTHER = "other"


class VesselFlag(str, Enum):
    """Common vessel flag states"""

    BAHAMAS = "BS"
    CYPRUS = "CY"
    LIBERIA = "LR"
    MALTA = "MT"
    MARSHALL_ISLANDS = "MH"
    PANAMA = "PA"
    SINGAPORE = "SG"
    UK = "GB"
    USA = "US"
    NORWAY = "NO"
    OTHER = "XX"


class WeatherCondition(str, Enum):
    """Weather conditions during incidents"""

    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    SNOW = "snow"
    FOG = "fog"
    STORM = "storm"
    HURRICANE = "hurricane"
    HIGH_WINDS = "high_winds"
    ROUGH_SEAS = "rough_seas"
    CALM = "calm"
    UNKNOWN = "unknown"


class SeaState(IntEnum):
    """Sea state (Douglas scale 0-9)"""

    CALM = 0
    SMOOTH = 1
    SLIGHT = 2
    MODERATE = 3
    ROUGH = 4
    VERY_ROUGH = 5
    HIGH = 6
    VERY_HIGH = 7
    PHENOMENAL = 8
    CONFUSED = 9


class DataSource(str, Enum):
    """Source agencies for incident data"""

    BSEE = "bsee"  # Bureau of Safety and Environmental Enforcement
    USCG = "uscg"  # United States Coast Guard
    NTSB = "ntsb"  # National Transportation Safety Board
    MAIB = "maib"  # Marine Accident Investigation Branch (UK)
    TSB = "tsb"  # Transportation Safety Board (Canada)
    ATSB = "atsb"  # Australian Transport Safety Bureau
    EMSA = "emsa"  # European Maritime Safety Agency
    IMO = "imo"  # International Maritime Organization
    OTHER = "other"


class InvestigationPriority(str, Enum):
    """Priority levels for investigations"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class CauseCategory(str, Enum):
    """Categories of incident causes"""

    HUMAN_ERROR = "human_error"
    EQUIPMENT_FAILURE = "equipment_failure"
    DESIGN_FLAW = "design_flaw"
    MAINTENANCE_ISSUE = "maintenance_issue"
    WEATHER = "weather"
    ENVIRONMENTAL = "environmental"
    PROCEDURAL = "procedural"
    TRAINING = "training"
    COMMUNICATION = "communication"
    MANAGEMENT = "management"
    EXTERNAL = "external"
    MULTIPLE = "multiple"
    UNKNOWN = "unknown"


# Validation constants
MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0

# Geographic regions for offshore operations
OFFSHORE_REGIONS: Dict[str, str] = {
    "GOM": "Gulf of Mexico",
    "NA": "North Atlantic",
    "NS": "North Sea",
    "PAC": "Pacific",
    "CAR": "Caribbean",
    "MED": "Mediterranean",
    "PG": "Persian Gulf",
    "AUS": "Australia",
    "BRA": "Brazil",
    "WA": "West Africa",
    "SEA": "Southeast Asia",
}

# US Coast Guard districts
USCG_DISTRICTS: Dict[str, str] = {
    "D1": "First District (Northeast)",
    "D5": "Fifth District (Mid-Atlantic)",
    "D7": "Seventh District (Southeast)",
    "D8": "Eighth District (Gulf of Mexico)",
    "D9": "Ninth District (Great Lakes)",
    "D11": "Eleventh District (Pacific)",
    "D13": "Thirteenth District (Pacific Northwest)",
    "D14": "Fourteenth District (Hawaii/Pacific Islands)",
    "D17": "Seventeenth District (Alaska)",
}

# BSEE regions
BSEE_REGIONS: Dict[str, str] = {
    "GOM": "Gulf of Mexico",
    "PAC": "Pacific",
    "ALA": "Alaska",
}

# Data quality flags
DATA_QUALITY_FLAGS: Set[str] = {
    "verified",
    "preliminary",
    "estimated",
    "incomplete",
    "conflicting",
    "outdated",
}

# Standard file extensions for documents
ALLOWED_DOCUMENT_EXTENSIONS: Set[str] = {
    ".pdf",
    ".doc",
    ".docx",
    ".txt",
    ".csv",
    ".xls",
    ".xlsx",
    ".xml",
    ".json",
    ".html",
}

# HTTP status codes to retry
RETRYABLE_HTTP_CODES: Set[int] = {408, 429, 500, 502, 503, 504}

# Maximum lengths for text fields
MAX_LENGTHS: Dict[str, int] = {
    "incident_title": 500,
    "incident_description": 10000,
    "vessel_name": 255,
    "vessel_imo": 10,
    "company_name": 255,
    "location_name": 500,
    "url": 2048,
}

# Default values
DEFAULT_SEVERITY = SeverityLevel.MODERATE
DEFAULT_STATUS = IncidentStatus.REPORTED
DEFAULT_PRIORITY = InvestigationPriority.MEDIUM

# API endpoints (configurable, these are examples)
DATA_SOURCE_URLS: Dict[str, str] = {
    "BSEE": "https://www.bsee.gov/stats-facts/offshore-incident-statistics",
    "USCG": "https://www.dco.uscg.mil/Our-Organization/Assistant-Commandant-for-Prevention-Policy-CG-5P/Inspections-Compliance-CG-5PC-/Office-of-Investigations-Casualty-Analysis/",
    "NTSB": "https://data.ntsb.gov/carol-main-public",
    "MAIB": "https://www.gov.uk/maib-reports",
}
