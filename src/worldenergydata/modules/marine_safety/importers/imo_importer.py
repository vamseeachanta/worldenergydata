# ABOUTME: IMO GISIS (Global Integrated Shipping Information System) marine casualty data importer.
# ABOUTME: Imports marine casualties and incidents from IMO GISIS CSV exports per MSC-MEPC.3/Circ.4/Rev.1.

"""
IMO GISIS Data Importer

Imports marine casualty and incident data from the International Maritime Organization's
Global Integrated Shipping Information System (GISIS). Handles CSV exports from the
Marine Casualties and Incidents (MCI) module following the MSC-MEPC.3/Circ.4/Rev.1
reporting format.

Data available from 2005 onwards at gisis.imo.org (registration required).
"""

import csv
import logging
import re
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from sqlalchemy.orm import Session

from worldenergydata.modules.marine_safety.constants import (
    CauseCategory,
    DataSource,
    IncidentStatus,
    IncidentType,
    VesselType,
)
from worldenergydata.modules.marine_safety.database.models import (
    Incident,
    IncidentCause,
    IncidentDocument,
    Location,
    Vessel,
)
from worldenergydata.modules.marine_safety.importers.base_importer import BaseImporter
from worldenergydata.modules.marine_safety.processors.data_cleaner import DataCleaner
from worldenergydata.modules.marine_safety.processors.data_normalizer import (
    DataNormalizer,
)

logger = logging.getLogger(__name__)


def validate_imo_number(imo_number: str) -> Tuple[bool, Optional[str]]:
    """
    Validate IMO ship identification number using checksum algorithm.

    IMO numbers are 7 digits with the last digit being a check digit.
    The check digit is calculated as: sum of (digit * position) mod 10
    where position starts at 7 for the first digit.

    Args:
        imo_number: The IMO number to validate (with or without 'IMO' prefix)

    Returns:
        Tuple of (is_valid, cleaned_number) where cleaned_number is
        the 7-digit IMO number without prefix, or None if invalid
    """
    if not imo_number:
        return False, None

    # Remove IMO prefix and whitespace
    cleaned = str(imo_number).upper().strip()
    cleaned = re.sub(r"^IMO\s*", "", cleaned)
    cleaned = re.sub(r"[^0-9]", "", cleaned)

    # Must be exactly 7 digits
    if len(cleaned) != 7:
        return False, None

    try:
        # Calculate checksum: sum of (digit * position) for first 6 digits
        # Position starts at 7 and decreases
        checksum = 0
        for i, digit in enumerate(cleaned[:6]):
            checksum += int(digit) * (7 - i)

        # Check digit is the ones place of the checksum
        expected_check = checksum % 10
        actual_check = int(cleaned[6])

        if expected_check == actual_check:
            return True, cleaned
        else:
            logger.debug(
                f"IMO checksum mismatch for {imo_number}: "
                f"expected {expected_check}, got {actual_check}"
            )
            return False, cleaned  # Return cleaned even if checksum fails

    except (ValueError, IndexError):
        return False, None


def normalize_flag_state(flag_state: Optional[str]) -> Optional[str]:
    """
    Normalize flag state to ISO 2-letter country code.

    Handles various IMO GISIS flag state formats including:
    - Full country names
    - ISO 2-letter codes
    - ISO 3-letter codes
    - Common variations and misspellings

    Args:
        flag_state: Raw flag state string from GISIS

    Returns:
        ISO 2-letter country code or original string if not found
    """
    if not flag_state:
        return None

    flag_lower = flag_state.lower().strip()

    # Comprehensive flag state mappings (name/code -> ISO 2-letter)
    flag_mappings = {
        # Major flag states
        "panama": "PA",
        "pan": "PA",
        "liberia": "LR",
        "lbr": "LR",
        "marshall islands": "MH",
        "mhl": "MH",
        "hong kong": "HK",
        "hkg": "HK",
        "hong kong, china": "HK",
        "singapore": "SG",
        "sgp": "SG",
        "malta": "MT",
        "mlt": "MT",
        "bahamas": "BS",
        "bhs": "BS",
        "china": "CN",
        "chn": "CN",
        "greece": "GR",
        "grc": "GR",
        "japan": "JP",
        "jpn": "JP",
        "norway": "NO",
        "nor": "NO",
        "cyprus": "CY",
        "cyp": "CY",
        "united kingdom": "GB",
        "uk": "GB",
        "gbr": "GB",
        "great britain": "GB",
        "united states": "US",
        "usa": "US",
        "us": "US",
        "united states of america": "US",
        "denmark": "DK",
        "dnk": "DK",
        "italy": "IT",
        "ita": "IT",
        "netherlands": "NL",
        "nld": "NL",
        "germany": "DE",
        "deu": "DE",
        "france": "FR",
        "fra": "FR",
        "south korea": "KR",
        "korea": "KR",
        "kor": "KR",
        "republic of korea": "KR",
        "india": "IN",
        "ind": "IN",
        "indonesia": "ID",
        "idn": "ID",
        "turkey": "TR",
        "tur": "TR",
        "russia": "RU",
        "rus": "RU",
        "russian federation": "RU",
        "brazil": "BR",
        "bra": "BR",
        "antigua and barbuda": "AG",
        "atg": "AG",
        "bermuda": "BM",
        "bmu": "BM",
        "cayman islands": "KY",
        "cym": "KY",
        "isle of man": "IM",
        "imn": "IM",
        "gibraltar": "GI",
        "gib": "GI",
        "portugal": "PT",
        "prt": "PT",
        "madeira": "PT",
        "spain": "ES",
        "esp": "ES",
        "belgium": "BE",
        "bel": "BE",
        "canada": "CA",
        "can": "CA",
        "australia": "AU",
        "aus": "AU",
        "new zealand": "NZ",
        "nzl": "NZ",
        "philippines": "PH",
        "phl": "PH",
        "vietnam": "VN",
        "vnm": "VN",
        "thailand": "TH",
        "tha": "TH",
        "malaysia": "MY",
        "mys": "MY",
        "saudi arabia": "SA",
        "sau": "SA",
        "united arab emirates": "AE",
        "uae": "AE",
        "are": "AE",
        "egypt": "EG",
        "egy": "EG",
        "south africa": "ZA",
        "zaf": "ZA",
        "nigeria": "NG",
        "nga": "NG",
        "mexico": "MX",
        "mex": "MX",
        "argentina": "AR",
        "arg": "AR",
        "chile": "CL",
        "chl": "CL",
        "peru": "PE",
        "per": "PE",
        "venezuela": "VE",
        "ven": "VE",
        "colombia": "CO",
        "col": "CO",
        "ecuador": "EC",
        "ecu": "EC",
        # Flags of convenience - additional
        "vanuatu": "VU",
        "vut": "VU",
        "tuvalu": "TV",
        "tuv": "TV",
        "st vincent": "VC",
        "st vincent and the grenadines": "VC",
        "vct": "VC",
        "belize": "BZ",
        "blz": "BZ",
        "cambodia": "KH",
        "khm": "KH",
        "mongolia": "MN",
        "mng": "MN",
        "palau": "PW",
        "plw": "PW",
        "comoros": "KM",
        "com": "KM",
        "togo": "TG",
        "tgo": "TG",
        "tanzania": "TZ",
        "tza": "TZ",
        "sierra leone": "SL",
        "sle": "SL",
        "moldova": "MD",
        "mda": "MD",
        "georgia": "GE",
        "geo": "GE",
    }

    if flag_lower in flag_mappings:
        return flag_mappings[flag_lower]

    # If already 2-letter code, return uppercase
    if len(flag_state) == 2:
        return flag_state.upper()

    # If 3-letter code in mappings, return
    if flag_lower in flag_mappings:
        return flag_mappings[flag_lower]

    logger.debug(f"Unknown flag state: {flag_state}")
    return flag_state.upper()[:2] if len(flag_state) >= 2 else flag_state


class IMOGISISImporter(BaseImporter):
    """
    Imports IMO GISIS Marine Casualties and Incidents (MCI) data.

    Expected source format: CSV export from GISIS MCI module
    Data fields follow MSC-MEPC.3/Circ.4/Rev.1 reporting format.

    Key features:
    - IMO number validation with checksum verification
    - Flag state normalization to ISO codes
    - Comprehensive casualty type mappings
    - Investigation report URL tracking
    - Contributing factor extraction
    """

    # IMO GISIS field name mappings to internal field names
    FIELD_MAPPINGS: Dict[str, str] = {
        # Ship identification
        "IMO_NUMBER": "imo_number",
        "IMO NUMBER": "imo_number",
        "IMO NO": "imo_number",
        "IMO NO.": "imo_number",
        "IMONUMBER": "imo_number",
        "SHIP_NAME": "vessel_name",
        "SHIP NAME": "vessel_name",
        "VESSEL_NAME": "vessel_name",
        "VESSEL NAME": "vessel_name",
        "NAME_OF_SHIP": "vessel_name",
        "NAME OF SHIP": "vessel_name",
        # Ship details
        "FLAG_STATE": "flag_state",
        "FLAG STATE": "flag_state",
        "FLAG": "flag_state",
        "SHIP_TYPE": "vessel_type",
        "SHIP TYPE": "vessel_type",
        "TYPE_OF_SHIP": "vessel_type",
        "TYPE OF SHIP": "vessel_type",
        "VESSEL_TYPE": "vessel_type",
        "GROSS_TONNAGE": "gross_tonnage",
        "GROSS TONNAGE": "gross_tonnage",
        "GT": "gross_tonnage",
        "YEAR_OF_BUILD": "year_built",
        "YEAR OF BUILD": "year_built",
        "YEAR_BUILT": "year_built",
        "BUILT": "year_built",
        "CLASSIFICATION_SOCIETY": "classification_society",
        "CLASSIFICATION SOCIETY": "classification_society",
        "CLASS": "classification_society",
        # Incident date/time/location
        "DATE_OF_OCCURRENCE": "incident_date",
        "DATE OF OCCURRENCE": "incident_date",
        "OCCURRENCE_DATE": "incident_date",
        "INCIDENT_DATE": "incident_date",
        "EVENT_DATE": "incident_date",
        "DATE": "incident_date",
        "TIME_OF_OCCURRENCE": "incident_time",
        "TIME OF OCCURRENCE": "incident_time",
        "TIME": "incident_time",
        "LATITUDE": "latitude",
        "LAT": "latitude",
        "LONGITUDE": "longitude",
        "LON": "longitude",
        "LONG": "longitude",
        "POSITION": "position",
        "LOCATION": "location_description",
        "PLACE_OF_OCCURRENCE": "location_description",
        "PLACE OF OCCURRENCE": "location_description",
        "AREA": "area",
        "WATERS": "waters",
        # Casualty classification
        "NATURE_OF_CASUALTY": "incident_type",
        "NATURE OF CASUALTY": "incident_type",
        "CASUALTY_TYPE": "incident_type",
        "CASUALTY TYPE": "incident_type",
        "TYPE_OF_CASUALTY": "incident_type",
        "TYPE OF CASUALTY": "incident_type",
        "CATEGORY": "casualty_category",
        "CASUALTY_CATEGORY": "casualty_category",
        "CASUALTY CATEGORY": "casualty_category",
        "SEVERITY": "severity",
        "SEVERITY_CLASSIFICATION": "severity",
        # Summary and description
        "SUMMARY_OF_EVENTS": "description",
        "SUMMARY OF EVENTS": "description",
        "SUMMARY": "description",
        "NARRATIVE": "description",
        "DESCRIPTION": "description",
        "SYNOPSIS": "description",
        "BRIEF_DESCRIPTION": "description",
        # Casualties
        "FATALITIES": "fatalities",
        "DEATHS": "fatalities",
        "NUMBER_OF_DEATHS": "fatalities",
        "NUMBER OF DEATHS": "fatalities",
        "INJURIES": "injuries",
        "INJURED": "injuries",
        "NUMBER_OF_INJURIES": "injuries",
        "NUMBER OF INJURIES": "injuries",
        "MISSING_PERSONS": "missing_persons",
        "MISSING PERSONS": "missing_persons",
        "MISSING": "missing_persons",
        "NUMBER_MISSING": "missing_persons",
        # Environmental impact
        "POLLUTION_QUANTITY": "pollution_quantity",
        "POLLUTION QUANTITY": "pollution_quantity",
        "OIL_SPILL": "pollution_quantity",
        "OIL SPILL": "pollution_quantity",
        "POLLUTION_TYPE": "pollution_type",
        "POLLUTION TYPE": "pollution_type",
        "ENVIRONMENTAL_IMPACT": "environmental_impact",
        "ENVIRONMENTAL IMPACT": "environmental_impact",
        # Contributing factors and causes
        "CONTRIBUTING_FACTORS": "contributing_factors",
        "CONTRIBUTING FACTORS": "contributing_factors",
        "FACTORS": "contributing_factors",
        "PROBABLE_CAUSE": "probable_cause",
        "PROBABLE CAUSE": "probable_cause",
        "CAUSE": "probable_cause",
        "ROOT_CAUSE": "root_cause",
        "ROOT CAUSE": "root_cause",
        # Investigation details
        "INVESTIGATION_REPORT_URL": "report_url",
        "INVESTIGATION REPORT URL": "report_url",
        "REPORT_URL": "report_url",
        "REPORT URL": "report_url",
        "REPORT_LINK": "report_url",
        "INVESTIGATION_STATUS": "investigation_status",
        "INVESTIGATION STATUS": "investigation_status",
        "STATUS": "investigation_status",
        "INVESTIGATING_STATE": "investigating_state",
        "INVESTIGATING STATE": "investigating_state",
        "LEAD_INVESTIGATING_STATE": "investigating_state",
        # Reference numbers
        "GISIS_REFERENCE": "source_incident_id",
        "GISIS REFERENCE": "source_incident_id",
        "REFERENCE_NUMBER": "source_incident_id",
        "REFERENCE NUMBER": "source_incident_id",
        "REFERENCE": "source_incident_id",
        "MCI_REFERENCE": "source_incident_id",
        "CASUALTY_ID": "source_incident_id",
        "CASUALTY ID": "source_incident_id",
        "ID": "source_incident_id",
    }

    # IMO casualty type mappings to IncidentType enum values
    CASUALTY_TYPE_MAPPINGS: Dict[str, str] = {
        # Collision categories
        "collision": IncidentType.COLLISION.value,
        "collision between ships": IncidentType.COLLISION.value,
        "collision with another ship": IncidentType.COLLISION.value,
        "contact": IncidentType.COLLISION.value,
        "contact with fixed object": IncidentType.COLLISION.value,
        "contact with floating object": IncidentType.COLLISION.value,
        "striking": IncidentType.COLLISION.value,
        "allision": IncidentType.COLLISION.value,
        # Grounding
        "grounding": IncidentType.GROUNDING.value,
        "stranding": IncidentType.GROUNDING.value,
        "grounding/stranding": IncidentType.GROUNDING.value,
        "ran aground": IncidentType.GROUNDING.value,
        # Fire and explosion
        "fire": IncidentType.FIRE.value,
        "fire on board": IncidentType.FIRE.value,
        "explosion": IncidentType.EXPLOSION.value,
        "fire/explosion": IncidentType.FIRE.value,
        "fire and explosion": IncidentType.FIRE.value,
        "fire and/or explosion": IncidentType.FIRE.value,
        # Flooding and structural
        "flooding": IncidentType.FLOODING.value,
        "hull failure": IncidentType.STRUCTURAL_FAILURE.value,
        "structural failure": IncidentType.STRUCTURAL_FAILURE.value,
        "foundering": IncidentType.FLOODING.value,
        "sinking": IncidentType.FLOODING.value,
        "loss of watertight integrity": IncidentType.FLOODING.value,
        "capsizing": IncidentType.CAPSIZING.value,
        "capsize": IncidentType.CAPSIZING.value,
        "listing": IncidentType.FLOODING.value,
        "loss of stability": IncidentType.CAPSIZING.value,
        # Equipment and machinery
        "equipment failure": IncidentType.EQUIPMENT_FAILURE.value,
        "machinery failure": IncidentType.EQUIPMENT_FAILURE.value,
        "machinery damage": IncidentType.EQUIPMENT_FAILURE.value,
        "loss of propulsion": IncidentType.LOSS_OF_PROPULSION.value,
        "propulsion failure": IncidentType.LOSS_OF_PROPULSION.value,
        "engine failure": IncidentType.LOSS_OF_PROPULSION.value,
        "loss of steering": IncidentType.LOSS_OF_CONTROL.value,
        "steering failure": IncidentType.LOSS_OF_CONTROL.value,
        "loss of control": IncidentType.LOSS_OF_CONTROL.value,
        "loss of electrical power": IncidentType.EQUIPMENT_FAILURE.value,
        "blackout": IncidentType.EQUIPMENT_FAILURE.value,
        # Personnel casualties
        "occupational accident": IncidentType.PERSONNEL_INJURY.value,
        "personnel injury": IncidentType.PERSONNEL_INJURY.value,
        "injury": IncidentType.PERSONNEL_INJURY.value,
        "man overboard": IncidentType.PERSONNEL_INJURY.value,
        "person overboard": IncidentType.PERSONNEL_INJURY.value,
        "fall overboard": IncidentType.PERSONNEL_INJURY.value,
        "fatality": IncidentType.FATALITY.value,
        "death": IncidentType.FATALITY.value,
        "loss of life": IncidentType.FATALITY.value,
        # Environmental
        "pollution": IncidentType.POLLUTION.value,
        "marine pollution": IncidentType.POLLUTION.value,
        "oil pollution": IncidentType.POLLUTION.value,
        "discharge": IncidentType.POLLUTION.value,
        "oil spill": IncidentType.POLLUTION.value,
        "chemical spill": IncidentType.POLLUTION.value,
        # Weather related
        "heavy weather damage": IncidentType.WEATHER_RELATED.value,
        "weather damage": IncidentType.WEATHER_RELATED.value,
        "parametric rolling": IncidentType.WEATHER_RELATED.value,
        "cargo shift": IncidentType.WEATHER_RELATED.value,
        # Near miss / hazardous
        "near miss": IncidentType.NEAR_MISS.value,
        "hazardous incident": IncidentType.NEAR_MISS.value,
        "marine incident": IncidentType.OTHER.value,
        "other": IncidentType.OTHER.value,
    }

    # IMO ship type mappings to VesselType enum values
    SHIP_TYPE_MAPPINGS: Dict[str, str] = {
        # Tankers
        "oil tanker": VesselType.TANKER.value,
        "crude oil tanker": VesselType.TANKER.value,
        "product tanker": VesselType.TANKER.value,
        "chemical tanker": VesselType.TANKER.value,
        "chemical/oil products tanker": VesselType.TANKER.value,
        "lpg tanker": VesselType.TANKER.value,
        "lng tanker": VesselType.TANKER.value,
        "gas carrier": VesselType.TANKER.value,
        "tanker": VesselType.TANKER.value,
        # Cargo vessels
        "bulk carrier": VesselType.CARGO_VESSEL.value,
        "bulker": VesselType.CARGO_VESSEL.value,
        "general cargo": VesselType.CARGO_VESSEL.value,
        "general cargo ship": VesselType.CARGO_VESSEL.value,
        "cargo ship": VesselType.CARGO_VESSEL.value,
        "container ship": VesselType.CARGO_VESSEL.value,
        "containership": VesselType.CARGO_VESSEL.value,
        "container": VesselType.CARGO_VESSEL.value,
        "ro-ro cargo": VesselType.CARGO_VESSEL.value,
        "roro": VesselType.CARGO_VESSEL.value,
        "roll-on/roll-off": VesselType.CARGO_VESSEL.value,
        "reefer": VesselType.CARGO_VESSEL.value,
        "refrigerated cargo": VesselType.CARGO_VESSEL.value,
        "heavy lift": VesselType.CARGO_VESSEL.value,
        "barge": VesselType.CARGO_VESSEL.value,
        "deck cargo ship": VesselType.CARGO_VESSEL.value,
        # Offshore - drilling
        "drilling rig": VesselType.DRILLING_RIG.value,
        "drilling ship": VesselType.DRILLING_RIG.value,
        "drill ship": VesselType.DRILLING_RIG.value,
        "drillship": VesselType.DRILLING_RIG.value,
        "mobile offshore drilling unit": VesselType.MODU.value,
        "modu": VesselType.MODU.value,
        "semi-submersible": VesselType.SEMISUBMERSIBLE.value,
        "semisubmersible": VesselType.SEMISUBMERSIBLE.value,
        "semi-submersible drilling rig": VesselType.SEMISUBMERSIBLE.value,
        "jack-up": VesselType.JACKUP_RIG.value,
        "jackup": VesselType.JACKUP_RIG.value,
        "jack-up rig": VesselType.JACKUP_RIG.value,
        # Offshore - production
        "fpso": VesselType.FPSO.value,
        "floating production storage offloading": VesselType.FPSO.value,
        "fso": VesselType.FSO.value,
        "floating storage": VesselType.FSO.value,
        "flng": VesselType.FPSO.value,
        "production platform": VesselType.PRODUCTION_PLATFORM.value,
        "platform": VesselType.PRODUCTION_PLATFORM.value,
        "fixed platform": VesselType.PRODUCTION_PLATFORM.value,
        "tlp": VesselType.TLP.value,
        "tension leg platform": VesselType.TLP.value,
        "spar": VesselType.SPAR_PLATFORM.value,
        "spar platform": VesselType.SPAR_PLATFORM.value,
        # Support vessels
        "offshore supply vessel": VesselType.SUPPLY_VESSEL.value,
        "osv": VesselType.SUPPLY_VESSEL.value,
        "supply vessel": VesselType.SUPPLY_VESSEL.value,
        "platform supply vessel": VesselType.SUPPLY_VESSEL.value,
        "psv": VesselType.SUPPLY_VESSEL.value,
        "anchor handling tug supply": VesselType.ANCHOR_HANDLING.value,
        "ahts": VesselType.ANCHOR_HANDLING.value,
        "anchor handling": VesselType.ANCHOR_HANDLING.value,
        "anchor handler": VesselType.ANCHOR_HANDLING.value,
        "tug": VesselType.TUG.value,
        "tugboat": VesselType.TUG.value,
        "towboat": VesselType.TUG.value,
        "harbour tug": VesselType.TUG.value,
        "ocean tug": VesselType.TUG.value,
        "push tug": VesselType.TUG.value,
        "crew boat": VesselType.CREW_BOAT.value,
        "crewboat": VesselType.CREW_BOAT.value,
        "crew transfer vessel": VesselType.CREW_BOAT.value,
        "ctv": VesselType.CREW_BOAT.value,
        "standby vessel": VesselType.STANDBY_VESSEL.value,
        "standby safety vessel": VesselType.STANDBY_VESSEL.value,
        # Wind farm vessels
        "wind turbine installation vessel": VesselType.WIND_TURBINE_INSTALL.value,
        "wtiv": VesselType.WIND_TURBINE_INSTALL.value,
        "wind installation": VesselType.WIND_TURBINE_INSTALL.value,
        "cable layer": VesselType.CABLE_LAYER.value,
        "cable laying vessel": VesselType.CABLE_LAYER.value,
        "cable ship": VesselType.CABLE_LAYER.value,
        "service operation vessel": VesselType.SERVICE_VESSEL.value,
        "sov": VesselType.SERVICE_VESSEL.value,
        # Research and diving
        "research vessel": VesselType.RESEARCH_VESSEL.value,
        "research ship": VesselType.RESEARCH_VESSEL.value,
        "survey vessel": VesselType.RESEARCH_VESSEL.value,
        "diving support vessel": VesselType.DIVING_SUPPORT.value,
        "dsv": VesselType.DIVING_SUPPORT.value,
        "diving vessel": VesselType.DIVING_SUPPORT.value,
    }

    # Contributing factor mappings to CauseCategory enum
    CAUSE_MAPPINGS: Dict[str, str] = {
        # Human error
        "human error": CauseCategory.HUMAN_ERROR.value,
        "human factor": CauseCategory.HUMAN_ERROR.value,
        "human element": CauseCategory.HUMAN_ERROR.value,
        "operator error": CauseCategory.HUMAN_ERROR.value,
        "navigation error": CauseCategory.HUMAN_ERROR.value,
        "watchkeeping": CauseCategory.HUMAN_ERROR.value,
        "fatigue": CauseCategory.HUMAN_ERROR.value,
        "situational awareness": CauseCategory.HUMAN_ERROR.value,
        "bridge resource management": CauseCategory.HUMAN_ERROR.value,
        # Equipment
        "equipment failure": CauseCategory.EQUIPMENT_FAILURE.value,
        "machinery failure": CauseCategory.EQUIPMENT_FAILURE.value,
        "mechanical failure": CauseCategory.EQUIPMENT_FAILURE.value,
        "technical failure": CauseCategory.EQUIPMENT_FAILURE.value,
        # Design
        "design deficiency": CauseCategory.DESIGN_FLAW.value,
        "design flaw": CauseCategory.DESIGN_FLAW.value,
        "structural design": CauseCategory.DESIGN_FLAW.value,
        "construction defect": CauseCategory.DESIGN_FLAW.value,
        # Maintenance
        "maintenance": CauseCategory.MAINTENANCE_ISSUE.value,
        "maintenance failure": CauseCategory.MAINTENANCE_ISSUE.value,
        "lack of maintenance": CauseCategory.MAINTENANCE_ISSUE.value,
        "poor maintenance": CauseCategory.MAINTENANCE_ISSUE.value,
        "inadequate maintenance": CauseCategory.MAINTENANCE_ISSUE.value,
        # Weather
        "weather": CauseCategory.WEATHER.value,
        "heavy weather": CauseCategory.WEATHER.value,
        "adverse weather": CauseCategory.WEATHER.value,
        "storm": CauseCategory.WEATHER.value,
        # Environmental
        "environmental": CauseCategory.ENVIRONMENTAL.value,
        "sea state": CauseCategory.ENVIRONMENTAL.value,
        "visibility": CauseCategory.ENVIRONMENTAL.value,
        "current": CauseCategory.ENVIRONMENTAL.value,
        "tide": CauseCategory.ENVIRONMENTAL.value,
        # Procedural
        "procedural": CauseCategory.PROCEDURAL.value,
        "procedure": CauseCategory.PROCEDURAL.value,
        "sms": CauseCategory.PROCEDURAL.value,
        "safety management": CauseCategory.PROCEDURAL.value,
        "non-compliance": CauseCategory.PROCEDURAL.value,
        # Training
        "training": CauseCategory.TRAINING.value,
        "inadequate training": CauseCategory.TRAINING.value,
        "lack of training": CauseCategory.TRAINING.value,
        "competence": CauseCategory.TRAINING.value,
        "certification": CauseCategory.TRAINING.value,
        # Communication
        "communication": CauseCategory.COMMUNICATION.value,
        "communication failure": CauseCategory.COMMUNICATION.value,
        "language barrier": CauseCategory.COMMUNICATION.value,
        "miscommunication": CauseCategory.COMMUNICATION.value,
        "vts": CauseCategory.COMMUNICATION.value,
        # Management
        "management": CauseCategory.MANAGEMENT.value,
        "shore management": CauseCategory.MANAGEMENT.value,
        "company policy": CauseCategory.MANAGEMENT.value,
        "commercial pressure": CauseCategory.MANAGEMENT.value,
        "manning": CauseCategory.MANAGEMENT.value,
        "crew fatigue": CauseCategory.MANAGEMENT.value,
        # External
        "external": CauseCategory.EXTERNAL.value,
        "third party": CauseCategory.EXTERNAL.value,
        "other vessel": CauseCategory.EXTERNAL.value,
        "shore side": CauseCategory.EXTERNAL.value,
    }

    # Investigation status mappings
    STATUS_MAPPINGS: Dict[str, str] = {
        "completed": IncidentStatus.FINAL_REPORT.value,
        "complete": IncidentStatus.FINAL_REPORT.value,
        "final report published": IncidentStatus.FINAL_REPORT.value,
        "final report": IncidentStatus.FINAL_REPORT.value,
        "published": IncidentStatus.FINAL_REPORT.value,
        "preliminary report": IncidentStatus.PRELIMINARY_REPORT.value,
        "preliminary": IncidentStatus.PRELIMINARY_REPORT.value,
        "ongoing": IncidentStatus.UNDER_INVESTIGATION.value,
        "in progress": IncidentStatus.UNDER_INVESTIGATION.value,
        "under investigation": IncidentStatus.UNDER_INVESTIGATION.value,
        "investigating": IncidentStatus.UNDER_INVESTIGATION.value,
        "reported": IncidentStatus.REPORTED.value,
        "notified": IncidentStatus.REPORTED.value,
        "closed": IncidentStatus.CLOSED.value,
        "archived": IncidentStatus.ARCHIVED.value,
        "no investigation": IncidentStatus.CLOSED.value,
    }

    def __init__(
        self,
        source_path: Path,
        session: Session,
        batch_size: int = 100,
        file_format: str = "csv",
        validate_imo: bool = True,
        strict_imo_validation: bool = False,
    ):
        """
        Initialize IMO GISIS importer.

        Args:
            source_path: Path to GISIS CSV export file
            session: Database session
            batch_size: Records per batch
            file_format: Format of source file ('csv')
            validate_imo: Whether to validate IMO numbers
            strict_imo_validation: If True, reject records with invalid IMO checksums
        """
        super().__init__(source_path, session, batch_size)

        self.file_format = file_format
        self.validate_imo = validate_imo
        self.strict_imo_validation = strict_imo_validation
        self.cleaner = DataCleaner()
        self.normalizer = DataNormalizer()

        # Caches for performance optimization
        self._location_cache: Dict[str, int] = {}
        self._vessel_cache: Dict[str, int] = {}

        # Track IMO validation stats
        self.imo_stats = {
            "valid": 0,
            "invalid_checksum": 0,
            "invalid_format": 0,
            "missing": 0,
        }

        logger.info(
            f"Initialized IMOGISISImporter "
            f"(validate_imo={validate_imo}, strict={strict_imo_validation})"
        )

    def read_source(self) -> Generator[Dict[str, Any], None, None]:
        """
        Read records from IMO GISIS CSV file.

        Yields:
            Raw record dictionaries from GISIS export
        """
        if self.file_format == "csv":
            yield from self._read_csv()
        else:
            raise NotImplementedError(f"Format '{self.file_format}' not yet supported")

    def _read_csv(self) -> Generator[Dict[str, Any], None, None]:
        """Read records from CSV file exported from GISIS."""
        try:
            with open(self.source_path, "r", encoding="utf-8-sig") as f:
                # Detect delimiter (GISIS exports may use comma, semicolon, or tab)
                sample = f.read(8192)
                f.seek(0)

                # Count potential delimiters
                delimiters = [",", ";", "\t"]
                delimiter_counts = {d: sample.count(d) for d in delimiters}
                delimiter = max(delimiter_counts, key=delimiter_counts.get)

                reader = csv.DictReader(f, delimiter=delimiter)

                for row in reader:
                    # Normalize keys - handle various header formats
                    normalized_row = {}
                    for k, v in row.items():
                        if k is not None:
                            # Normalize key: uppercase, remove extra spaces
                            clean_key = k.upper().strip()
                            clean_key = re.sub(r"\s+", " ", clean_key)
                            clean_key = clean_key.replace(".", "")
                            normalized_row[clean_key] = v

                    yield normalized_row

        except FileNotFoundError:
            logger.error(f"Source file not found: {self.source_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
            raise

    def parse_record(self, raw_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse raw IMO GISIS record into standardized format.

        Args:
            raw_record: Raw record from GISIS file

        Returns:
            Parsed record dictionary or None if invalid
        """
        try:
            parsed: Dict[str, Any] = {}

            # Map fields using field mappings
            for gisis_field, our_field in self.FIELD_MAPPINGS.items():
                if gisis_field in raw_record:
                    value = raw_record[gisis_field]
                    if value and str(value).strip():
                        parsed[our_field] = value

            # Must have incident date
            if "incident_date" not in parsed:
                logger.warning("Record missing incident date, skipping")
                return None

            # Generate source_incident_id if not present
            if "source_incident_id" not in parsed:
                # Create ID from date + IMO number or vessel name
                date_part = str(parsed.get("incident_date", "")).replace("-", "")[:8]
                vessel_part = parsed.get("imo_number") or parsed.get(
                    "vessel_name", "UNKNOWN"
                )
                parsed["source_incident_id"] = f"IMO-{date_part}-{vessel_part}"

            # Set source agency
            parsed["source_agency"] = DataSource.IMO.value

            # Validate and normalize IMO number
            if "imo_number" in parsed and self.validate_imo:
                is_valid, cleaned_imo = validate_imo_number(parsed["imo_number"])
                if is_valid:
                    parsed["imo_number"] = cleaned_imo
                    self.imo_stats["valid"] += 1
                elif cleaned_imo:
                    self.imo_stats["invalid_checksum"] += 1
                    if self.strict_imo_validation:
                        logger.warning(
                            f"Invalid IMO checksum: {parsed['imo_number']}, skipping"
                        )
                        return None
                    parsed["imo_number"] = cleaned_imo
                else:
                    self.imo_stats["invalid_format"] += 1
                    del parsed["imo_number"]
            elif "imo_number" not in parsed:
                self.imo_stats["missing"] += 1

            # Normalize flag state
            if "flag_state" in parsed:
                parsed["flag_state"] = normalize_flag_state(parsed["flag_state"])

            # Map casualty type to IncidentType enum
            if "incident_type" in parsed:
                parsed["incident_type"] = self._map_casualty_type(
                    parsed["incident_type"]
                )

            # Map vessel/ship type to VesselType enum
            if "vessel_type" in parsed:
                parsed["vessel_type"] = self._map_ship_type(parsed["vessel_type"])

            # Map investigation status
            if "investigation_status" in parsed:
                parsed["status"] = self._map_status(parsed["investigation_status"])
            else:
                parsed["status"] = IncidentStatus.REPORTED.value

            # Parse position if provided in single field
            if "position" in parsed and "latitude" not in parsed:
                lat, lon = self._parse_position(parsed["position"])
                if lat is not None:
                    parsed["latitude"] = lat
                if lon is not None:
                    parsed["longitude"] = lon

            # Build location description if not present
            if "location_description" not in parsed:
                parsed["location_description"] = self._build_location_description(
                    parsed
                )

            # Extract contributing factors/causes
            if "contributing_factors" in parsed:
                parsed["cause_categories"] = self._parse_contributing_factors(
                    parsed["contributing_factors"]
                )

            # Build environmental impact description
            if "pollution_quantity" in parsed or "pollution_type" in parsed:
                parsed["environmental_impact"] = self._build_environmental_impact(
                    parsed
                )

            # Generate title if not present
            if "title" not in parsed:
                parsed["title"] = self._generate_title(parsed)

            # Clean the data
            parsed = self.cleaner.process(parsed)

            # Normalize the data
            parsed = self.normalizer.process(parsed)

            return parsed

        except Exception as e:
            logger.error(f"Error parsing record: {e}")
            return None

    def _map_casualty_type(self, casualty_type: str) -> str:
        """Map IMO GISIS casualty type to IncidentType enum value."""
        if not casualty_type:
            return IncidentType.OTHER.value

        casualty_lower = casualty_type.lower().strip()

        # Try exact match
        if casualty_lower in self.CASUALTY_TYPE_MAPPINGS:
            return self.CASUALTY_TYPE_MAPPINGS[casualty_lower]

        # Try partial match
        for key, value in self.CASUALTY_TYPE_MAPPINGS.items():
            if key in casualty_lower or casualty_lower in key:
                return value

        logger.debug(f"Unknown IMO casualty type: {casualty_type}")
        return IncidentType.OTHER.value

    def _map_ship_type(self, ship_type: str) -> str:
        """Map IMO GISIS ship type to VesselType enum value."""
        if not ship_type:
            return VesselType.OTHER.value

        ship_lower = ship_type.lower().strip()

        # Try exact match
        if ship_lower in self.SHIP_TYPE_MAPPINGS:
            return self.SHIP_TYPE_MAPPINGS[ship_lower]

        # Try partial match
        for key, value in self.SHIP_TYPE_MAPPINGS.items():
            if key in ship_lower:
                return value

        logger.debug(f"Unknown IMO ship type: {ship_type}")
        return VesselType.OTHER.value

    def _map_status(self, status: str) -> str:
        """Map IMO investigation status to IncidentStatus enum value."""
        if not status:
            return IncidentStatus.REPORTED.value

        status_lower = status.lower().strip()

        # Try exact match
        if status_lower in self.STATUS_MAPPINGS:
            return self.STATUS_MAPPINGS[status_lower]

        # Try partial match
        for key, value in self.STATUS_MAPPINGS.items():
            if key in status_lower:
                return value

        logger.debug(f"Unknown IMO status: {status}")
        return IncidentStatus.REPORTED.value

    def _parse_position(
        self, position: str
    ) -> Tuple[Optional[Decimal], Optional[Decimal]]:
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
            r"(\d+)\s*[°\s]\s*(\d+)\s*[\'′\s]?\s*(\d*\.?\d*)?\s*[\"″\s]?\s*([NS])\s*"
            r"[,;]?\s*"
            r"(\d+)\s*[°\s]\s*(\d+)\s*[\'′\s]?\s*(\d*\.?\d*)?\s*[\"″\s]?\s*([EW])"
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

    def _build_location_description(self, parsed: Dict[str, Any]) -> Optional[str]:
        """Build location description from available location fields."""
        parts = []

        if parsed.get("area"):
            parts.append(parsed["area"])

        if parsed.get("waters"):
            parts.append(parsed["waters"])

        if parsed.get("investigating_state"):
            parts.append(f"Waters of {parsed['investigating_state']}")

        return ", ".join(parts) if parts else None

    def _parse_contributing_factors(self, factors: str) -> List[str]:
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
        cause_categories = []

        for factor in factor_list:
            factor_lower = factor.lower().strip()
            if not factor_lower:
                continue

            # Try exact match
            if factor_lower in self.CAUSE_MAPPINGS:
                cause = self.CAUSE_MAPPINGS[factor_lower]
                if cause not in cause_categories:
                    cause_categories.append(cause)
                continue

            # Try partial match
            matched = False
            for key, value in self.CAUSE_MAPPINGS.items():
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

    def _build_environmental_impact(self, parsed: Dict[str, Any]) -> str:
        """Build environmental impact description from pollution fields."""
        parts = []

        if parsed.get("pollution_type"):
            parts.append(f"Type: {parsed['pollution_type']}")

        if parsed.get("pollution_quantity"):
            parts.append(f"Quantity: {parsed['pollution_quantity']}")

        return "; ".join(parts) if parts else ""

    def _generate_title(self, parsed: Dict[str, Any]) -> str:
        """Generate incident title from available fields."""
        vessel_name = parsed.get("vessel_name", "Unknown Vessel")
        incident_type = parsed.get("incident_type", "incident")
        imo_number = parsed.get("imo_number", "")

        # Format incident type for display
        incident_display = incident_type.replace("_", " ").title()

        if imo_number:
            return f"{incident_display} - {vessel_name} (IMO {imo_number})"
        return f"{incident_display} - {vessel_name}"

    def map_to_model(self, parsed_record: Dict[str, Any]) -> Optional[Incident]:
        """
        Map parsed record to Incident model.

        Args:
            parsed_record: Cleaned and normalized record

        Returns:
            Incident model instance or None
        """
        try:
            # Get or create related entities
            location_id = self._get_or_create_location(parsed_record)
            vessel_id = self._get_or_create_vessel(parsed_record)

            # Calculate severity based on casualties
            severity = self._calculate_severity(
                parsed_record.get("fatalities", 0),
                parsed_record.get("injuries", 0),
                parsed_record.get("missing_persons", 0),
            )

            # Determine incident status
            status = parsed_record.get("status", IncidentStatus.REPORTED.value)

            # Create incident
            incident = Incident(
                source_agency=DataSource.IMO.value,
                source_incident_id=parsed_record["source_incident_id"],
                incident_date=parsed_record["incident_date"],
                incident_time=parsed_record.get("incident_time"),
                incident_type=parsed_record.get(
                    "incident_type", IncidentType.OTHER.value
                ),
                severity_level=severity,
                status=status,
                title=parsed_record.get("title"),
                description=parsed_record.get("description"),
                vessel_id=vessel_id,
                company_id=None,
                location_id=location_id,
                fatalities=parsed_record.get("fatalities", 0),
                injuries=parsed_record.get("injuries", 0),
                missing_persons=parsed_record.get("missing_persons", 0),
                environmental_impact=parsed_record.get("environmental_impact"),
                estimated_damage_usd=parsed_record.get("estimated_damage_usd"),
                investigation_status=parsed_record.get("investigation_status"),
                # IMO GISIS data is generally high quality official data
                data_quality_score=Decimal("0.90"),
            )

            return incident

        except Exception as e:
            logger.error(f"Error mapping to model: {e}")
            return None

    def _calculate_severity(self, fatalities: int, injuries: int, missing: int) -> int:
        """
        Calculate severity level based on casualties following IMO guidelines.

        IMO categorizes casualties as:
        - Very serious casualty: loss of ship, loss of life, severe pollution
        - Serious casualty: fire, collision, grounding with significant damage
        - Less serious casualty: other incidents

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

    def _get_or_create_location(self, record: Dict[str, Any]) -> Optional[int]:
        """
        Get existing location or create new one.

        Args:
            record: Parsed record containing location fields

        Returns:
            Location ID or None
        """
        lat = record.get("latitude")
        lon = record.get("longitude")
        location_desc = record.get("location_description")

        # Need at least coordinates or description
        if not lat and not lon and not location_desc:
            return None

        # Build cache key
        cache_key = f"{lat},{lon},{location_desc}"
        if cache_key in self._location_cache:
            return self._location_cache[cache_key]

        # Check database for existing location with coordinates
        if lat and lon:
            existing = (
                self.session.query(Location)
                .filter(Location.latitude == lat, Location.longitude == lon)
                .first()
            )

            if existing:
                self._location_cache[cache_key] = existing.location_id
                return existing.location_id

        # Create new location
        location = Location(
            latitude=lat,
            longitude=lon,
            location_name=location_desc,
            country_code=record.get("flag_state"),  # Use flag state as proxy
            region_code=record.get("area"),
        )
        self.session.add(location)
        self.session.flush()

        self._location_cache[cache_key] = location.location_id
        return location.location_id

    def _get_or_create_vessel(self, record: Dict[str, Any]) -> Optional[int]:
        """
        Get existing vessel or create new one.

        IMO number is the preferred unique identifier.

        Args:
            record: Parsed record containing vessel fields

        Returns:
            Vessel ID or None
        """
        vessel_name = record.get("vessel_name")
        imo_number = record.get("imo_number")

        # Need at least name or IMO
        if not vessel_name and not imo_number:
            return None

        # Build cache key - IMO number preferred
        cache_key = imo_number if imo_number else vessel_name
        if cache_key in self._vessel_cache:
            return self._vessel_cache[cache_key]

        # Check database for existing vessel by IMO number
        if imo_number:
            existing = (
                self.session.query(Vessel)
                .filter(Vessel.imo_number == imo_number)
                .first()
            )

            if existing:
                self._vessel_cache[cache_key] = existing.vessel_id
                return existing.vessel_id

        # Create new vessel
        vessel = Vessel(
            vessel_name=vessel_name or f"Unknown (IMO {imo_number})",
            vessel_type=record.get("vessel_type", VesselType.OTHER.value),
            imo_number=imo_number,
            flag_state=record.get("flag_state"),
            gross_tonnage=record.get("gross_tonnage"),
            year_built=record.get("year_built"),
        )
        self.session.add(vessel)
        self.session.flush()

        self._vessel_cache[cache_key] = vessel.vessel_id
        return vessel.vessel_id

    def is_duplicate(self, incident: Incident) -> bool:
        """
        Check if incident already exists in database.

        Uses source_agency + source_incident_id as unique key.

        Args:
            incident: Incident model instance to check

        Returns:
            True if duplicate exists, False otherwise
        """
        existing = (
            self.session.query(Incident)
            .filter(
                Incident.source_agency == incident.source_agency,
                Incident.source_incident_id == incident.source_incident_id,
            )
            .first()
        )

        return existing is not None

    def create_incident_causes(
        self,
        incident_id: int,
        cause_categories: List[str],
        raw_factors: Optional[str] = None,
    ) -> List[IncidentCause]:
        """
        Create IncidentCause records for an incident.

        Args:
            incident_id: ID of the incident
            cause_categories: List of CauseCategory enum values
            raw_factors: Original contributing factors text

        Returns:
            List of created IncidentCause objects
        """
        causes = []
        is_primary = True  # First cause is primary

        for category in cause_categories:
            cause = IncidentCause(
                incident_id=incident_id,
                cause_category=category,
                cause_description=raw_factors if is_primary else None,
                is_primary=is_primary,
            )
            causes.append(cause)
            is_primary = False

        return causes

    def create_incident_document(
        self, incident_id: int, report_url: str, doc_type: str = "investigation_report"
    ) -> Optional[IncidentDocument]:
        """
        Create IncidentDocument record for investigation report.

        Args:
            incident_id: ID of the incident
            report_url: URL to the investigation report
            doc_type: Document type

        Returns:
            IncidentDocument object or None if URL invalid
        """
        if not report_url or not report_url.strip():
            return None

        return IncidentDocument(
            incident_id=incident_id,
            document_type=doc_type,
            document_title="IMO Investigation Report",
            document_url=report_url.strip(),
        )

    def preview_data(self, num_records: int = 5) -> List[Dict[str, Any]]:
        """
        Preview first N records without importing.

        Useful for validating field mappings before full import.

        Args:
            num_records: Number of records to preview

        Returns:
            List of parsed records
        """
        logger.info(f"Previewing first {num_records} IMO GISIS records...")

        previews: List[Dict[str, Any]] = []
        count = 0

        for raw_record in self.read_source():
            parsed = self.parse_record(raw_record)
            if parsed:
                previews.append(parsed)
                count += 1

            if count >= num_records:
                break

        logger.info(f"Preview complete: {len(previews)} records")
        return previews

    def get_field_statistics(self, max_records: int = 1000) -> Dict[str, Any]:
        """
        Analyze source file to get field statistics.

        Useful for understanding data completeness before import.

        Args:
            max_records: Maximum records to analyze

        Returns:
            Dictionary with field statistics
        """
        logger.info(f"Analyzing field statistics (max {max_records} records)...")

        field_counts: Dict[str, int] = {}
        total_records = 0

        for raw_record in self.read_source():
            total_records += 1

            for field, value in raw_record.items():
                if value and str(value).strip():
                    field_counts[field] = field_counts.get(field, 0) + 1

            if total_records >= max_records:
                break

        # Calculate percentages
        stats = {
            "total_records_analyzed": total_records,
            "fields": {},
            "imo_validation": self.imo_stats.copy(),
        }

        for field, count in sorted(field_counts.items()):
            stats["fields"][field] = {
                "count": count,
                "percentage": round(count / total_records * 100, 1),
            }

        return stats

    def get_imo_validation_stats(self) -> Dict[str, int]:
        """
        Get IMO number validation statistics.

        Returns:
            Dictionary with validation counts
        """
        return self.imo_stats.copy()

    def clear_caches(self) -> None:
        """Clear location and vessel caches."""
        self._location_cache.clear()
        self._vessel_cache.clear()
        logger.debug("Cleared importer caches")


# Convenience function for IMO number validation
def validate_imo(imo_number: str) -> bool:
    """
    Validate an IMO number.

    Args:
        imo_number: IMO number to validate

    Returns:
        True if valid, False otherwise
    """
    is_valid, _ = validate_imo_number(imo_number)
    return is_valid
