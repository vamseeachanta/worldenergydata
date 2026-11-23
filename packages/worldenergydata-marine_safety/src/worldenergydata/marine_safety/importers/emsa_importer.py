# ABOUTME: European Maritime Safety Agency (EMSA) EMCIP data importer stub.
# ABOUTME: Placeholder for importing marine casualty data from the
# European Marine Casualty Information Platform.

"""
EMSA EMCIP Data Importer (Stub)

Stub implementation for importing European Marine Casualty Information Platform
(EMCIP) data from the European Maritime Safety Agency (EMSA).

DATA ACCESS REQUIREMENTS:
-------------------------
EMCIP data access is restricted. To obtain data:

1. **Public Dashboard**: Basic statistics available at:
   https://portal.emsa.europa.eu/emcip-public

2. **Institutional Access**: Full dataset requires:
   - EU Member State maritime administration credentials
   - Academic research agreements with EMSA
   - Data sharing agreements under Directive 2009/18/EC

3. **Contact Information**:
   - EMSA: emsa.europa.eu/contact.html
   - EMCIP Technical Support: emcip-support@emsa.europa.eu

4. **Data Request Process**:
   a. Submit formal data request to EMSA
   b. Specify research purpose and scope
   c. Sign data protection agreement
   d. Receive access credentials (typically 4-8 weeks)

EMCIP DATA FORMAT:
-----------------
EMCIP uses a harmonized taxonomy based on:
- IMO MSC-MEPC.3/Circ.3 (Casualty Investigation Code)
- CASMET (Casualty Statistics and Methodology) taxonomy
- Directive 2009/18/EC reporting requirements

Key EMCIP tables/entities:
- Occurrence (incident record)
- Event (specific events within occurrence)
- Ship (vessel information)
- Person (affected persons)
- Environment (conditions)
- Cause/Factor (contributing factors)

SUPPORTED IMPORT FORMATS (when implemented):
- CSV exports from EMCIP Extract
- JSON API responses (if API access granted)
- XML EMCIP interchange format
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy.orm import Session

from worldenergydata.marine_safety.constants import (
    DataSource,
    IncidentStatus,
    IncidentType,
    VesselType,
)
from worldenergydata.marine_safety.importers.base_importer import BaseImporter

logger = logging.getLogger(__name__)


class EMSAImporter(BaseImporter):
    """
    Importer for European Maritime Safety Agency EMCIP data.

    This is a stub implementation. Full functionality requires:
    1. Institutional access credentials from EMSA
    2. Data sharing agreement
    3. EMCIP data export files

    The EMCIP (European Marine Casualty Information Platform) contains
    harmonized marine casualty data from all EU member states, collected
    under Directive 2009/18/EC.

    Supported data formats (when fully implemented):
    - emcip_extract.csv: Standard EMCIP export format
    - emcip_api.json: EMCIP API JSON response
    - emcip_interchange.xml: EMCIP XML interchange format

    Example usage:
        # Note: Will raise NotImplementedError until access is configured
        importer = EMSAImporter(
            source_path=Path("emcip_extract.csv"),
            session=db_session,
            member_state="all",  # or specific state code
        )
        stats = importer.import_data()
    """

    # EMCIP field mappings to internal field names
    # Based on EMCIP taxonomy and CASMET standards
    FIELD_MAPPINGS: Dict[str, str] = {
        # Primary identifiers
        "OCCURRENCE_ID": "source_incident_id",
        "EMCIP_ID": "source_incident_id",
        "CASUALTY_ID": "source_incident_id",
        "NATIONAL_REFERENCE": "national_reference",
        "IMO_CASUALTY_ID": "imo_casualty_id",
        # Date/time fields
        "OCCURRENCE_DATE": "incident_date",
        "OCCURRENCE_TIME": "incident_time",
        "DATE_OF_OCCURRENCE": "incident_date",
        "TIME_OF_OCCURRENCE": "incident_time",
        "UTC_DATE": "incident_date_utc",
        "UTC_TIME": "incident_time_utc",
        "LOCAL_DATE": "incident_date",
        "LOCAL_TIME": "incident_time",
        # Occurrence classification
        "OCCURRENCE_SEVERITY": "severity_level",
        "CASUALTY_CATEGORY": "casualty_category",
        "OCCURRENCE_TYPE": "incident_type",
        "EVENT_TYPE": "event_type",
        "MAIN_EVENT": "main_event",
        "INITIAL_EVENT": "initial_event",
        # Location fields
        "LATITUDE": "latitude",
        "LONGITUDE": "longitude",
        "OCCURRENCE_LOCATION": "location_description",
        "LOCATION_TYPE": "location_type",
        "COASTAL_STATE": "coastal_state",
        "FLAG_STATE": "flag_state",
        "PORT_OF_DEPARTURE": "port_departure",
        "PORT_OF_DESTINATION": "port_destination",
        "PORT_OF_ACCIDENT": "port_accident",
        "SEA_AREA": "sea_area",
        "TERRITORIAL_WATERS": "territorial_waters",
        # Vessel fields (EMCIP Ship entity)
        "SHIP_NAME": "vessel_name",
        "VESSEL_NAME": "vessel_name",
        "IMO_NUMBER": "imo_number",
        "CALL_SIGN": "call_sign",
        "MMSI": "mmsi",
        "SHIP_TYPE": "vessel_type",
        "SHIP_CATEGORY": "vessel_category",
        "GROSS_TONNAGE": "gross_tonnage",
        "DEADWEIGHT": "deadweight",
        "LENGTH_OVERALL": "length_overall",
        "YEAR_OF_BUILD": "year_built",
        "CLASSIFICATION_SOCIETY": "classification_society",
        "PORT_OF_REGISTRY": "port_of_registry",
        # Casualty data (EMCIP Person entity)
        "FATALITIES": "fatalities",
        "DEATHS": "fatalities",
        "INJURIES": "injuries",
        "SERIOUS_INJURIES": "serious_injuries",
        "MISSING_PERSONS": "missing_persons",
        "CREW_FATALITIES": "crew_fatalities",
        "PASSENGER_FATALITIES": "passenger_fatalities",
        "OTHER_FATALITIES": "other_fatalities",
        "TOTAL_ON_BOARD": "total_on_board",
        "CREW_COUNT": "crew_count",
        "PASSENGER_COUNT": "passenger_count",
        # Environmental impact
        "POLLUTION_TYPE": "pollution_type",
        "OIL_SPILL_VOLUME": "oil_spill_volume",
        "POLLUTION_CATEGORY": "pollution_category",
        "CARGO_LOST": "cargo_lost",
        # Investigation status
        "INVESTIGATION_STATUS": "investigation_status",
        "INVESTIGATION_FLAG": "investigation_flag",
        "SAFETY_INVESTIGATION": "safety_investigation",
        "FINAL_REPORT_DATE": "final_report_date",
        "REPORT_URL": "report_url",
        # Environmental conditions
        "WEATHER_CONDITION": "weather_condition",
        "WIND_FORCE": "wind_force",
        "WIND_DIRECTION": "wind_direction",
        "SEA_STATE": "sea_state",
        "VISIBILITY": "visibility",
        "NATURAL_LIGHT": "natural_light",
        # Contributing factors (EMCIP Cause/Factor entity)
        "CONTRIBUTING_FACTOR_L1": "contributing_factor_l1",
        "CONTRIBUTING_FACTOR_L2": "contributing_factor_l2",
        "CONTRIBUTING_FACTOR_L3": "contributing_factor_l3",
        "CAUSAL_CHAIN": "causal_chain",
        # Narrative fields
        "SHORT_DESCRIPTION": "title",
        "OCCURRENCE_DESCRIPTION": "description",
        "SYNOPSIS": "synopsis",
        "SAFETY_ISSUES": "safety_issues",
        "SAFETY_RECOMMENDATIONS": "safety_recommendations",
        # Metadata
        "REPORTING_STATE": "reporting_state",
        "INVESTIGATING_STATE": "investigating_state",
        "DATA_PROVIDER": "data_provider",
        "LAST_UPDATE": "last_update",
        "QUALITY_FLAG": "quality_flag",
    }

    # EU Member State codes to ISO 3166-1 alpha-2
    # Used for normalizing EMCIP member state references
    EU_MEMBER_STATE_CODES: Dict[str, str] = {
        # EU27 + UK (historical data)
        "AT": "AT",  # Austria (landlocked, but regulates Danube)
        "BE": "BE",  # Belgium
        "BG": "BG",  # Bulgaria
        "CY": "CY",  # Cyprus
        "CZ": "CZ",  # Czech Republic (landlocked)
        "DE": "DE",  # Germany
        "DK": "DK",  # Denmark
        "EE": "EE",  # Estonia
        "EL": "GR",  # Greece (EMCIP uses EL)
        "GR": "GR",  # Greece (standard ISO)
        "ES": "ES",  # Spain
        "FI": "FI",  # Finland
        "FR": "FR",  # France
        "HR": "HR",  # Croatia
        "HU": "HU",  # Hungary (landlocked)
        "IE": "IE",  # Ireland
        "IT": "IT",  # Italy
        "LT": "LT",  # Lithuania
        "LU": "LU",  # Luxembourg (landlocked)
        "LV": "LV",  # Latvia
        "MT": "MT",  # Malta
        "NL": "NL",  # Netherlands
        "PL": "PL",  # Poland
        "PT": "PT",  # Portugal
        "RO": "RO",  # Romania
        "SE": "SE",  # Sweden
        "SI": "SI",  # Slovenia
        "SK": "SK",  # Slovakia (landlocked)
        "UK": "GB",  # United Kingdom (historical)
        "GB": "GB",  # United Kingdom
        # EEA countries also reporting to EMCIP
        "NO": "NO",  # Norway
        "IS": "IS",  # Iceland
        # Full names (for flexible parsing)
        "austria": "AT",
        "belgium": "BE",
        "bulgaria": "BG",
        "cyprus": "CY",
        "czech republic": "CZ",
        "czechia": "CZ",
        "germany": "DE",
        "denmark": "DK",
        "estonia": "EE",
        "greece": "GR",
        "spain": "ES",
        "finland": "FI",
        "france": "FR",
        "croatia": "HR",
        "hungary": "HU",
        "ireland": "IE",
        "italy": "IT",
        "lithuania": "LT",
        "luxembourg": "LU",
        "latvia": "LV",
        "malta": "MT",
        "netherlands": "NL",
        "poland": "PL",
        "portugal": "PT",
        "romania": "RO",
        "sweden": "SE",
        "slovenia": "SI",
        "slovakia": "SK",
        "united kingdom": "GB",
        "norway": "NO",
        "iceland": "IS",
    }

    # EMCIP casualty category mappings
    # Based on IMO MSC-MEPC.3/Circ.3 and Directive 2009/18/EC
    CASUALTY_CATEGORY_MAPPINGS: Dict[str, str] = {
        # Very Serious Marine Casualty
        "very serious marine casualty": "catastrophic",
        "vsmc": "catastrophic",
        "total loss": "catastrophic",
        "loss of ship": "catastrophic",
        "loss of life": "catastrophic",
        # Serious Marine Casualty
        "serious marine casualty": "serious",
        "smc": "serious",
        "constructive total loss": "serious",
        "major structural damage": "serious",
        "serious pollution": "serious",
        # Marine Casualty
        "marine casualty": "moderate",
        "casualty": "moderate",
        "mc": "moderate",
        # Marine Incident
        "marine incident": "minor",
        "incident": "minor",
        "mi": "minor",
        "hazardous incident": "minor",
    }

    # EMCIP occurrence type to IncidentType enum mappings
    # Based on CASMET taxonomy
    OCCURRENCE_TYPE_MAPPINGS: Dict[str, str] = {
        # Contact/Collision events
        "collision": IncidentType.COLLISION.value,
        "collision with vessel": IncidentType.COLLISION.value,
        "collision at sea": IncidentType.COLLISION.value,
        "contact": IncidentType.COLLISION.value,
        "contact with object": IncidentType.COLLISION.value,
        "allision": IncidentType.COLLISION.value,
        "striking": IncidentType.COLLISION.value,
        # Grounding
        "grounding": IncidentType.GROUNDING.value,
        "stranding": IncidentType.GROUNDING.value,
        "aground": IncidentType.GROUNDING.value,
        "running aground": IncidentType.GROUNDING.value,
        # Fire/Explosion
        "fire": IncidentType.FIRE.value,
        "explosion": IncidentType.EXPLOSION.value,
        "fire/explosion": IncidentType.FIRE.value,
        "engine room fire": IncidentType.FIRE.value,
        "cargo fire": IncidentType.FIRE.value,
        # Flooding/Capsizing/Sinking
        "flooding": IncidentType.FLOODING.value,
        "foundering": IncidentType.FLOODING.value,
        "sinking": IncidentType.FLOODING.value,
        "capsizing": IncidentType.CAPSIZING.value,
        "capsize": IncidentType.CAPSIZING.value,
        "listing": IncidentType.FLOODING.value,
        "loss of stability": IncidentType.CAPSIZING.value,
        # Equipment/Structural
        "machinery failure": IncidentType.EQUIPMENT_FAILURE.value,
        "equipment failure": IncidentType.EQUIPMENT_FAILURE.value,
        "hull failure": IncidentType.STRUCTURAL_FAILURE.value,
        "structural failure": IncidentType.STRUCTURAL_FAILURE.value,
        "loss of propulsion": IncidentType.LOSS_OF_PROPULSION.value,
        "loss of steering": IncidentType.LOSS_OF_CONTROL.value,
        "loss of power": IncidentType.EQUIPMENT_FAILURE.value,
        # Personnel
        "occupational accident": IncidentType.PERSONNEL_INJURY.value,
        "person overboard": IncidentType.PERSONNEL_INJURY.value,
        "man overboard": IncidentType.PERSONNEL_INJURY.value,
        "fall overboard": IncidentType.PERSONNEL_INJURY.value,
        "injury": IncidentType.PERSONNEL_INJURY.value,
        "death": IncidentType.FATALITY.value,
        "fatality": IncidentType.FATALITY.value,
        # Environmental
        "pollution": IncidentType.POLLUTION.value,
        "oil pollution": IncidentType.POLLUTION.value,
        "cargo damage": IncidentType.ENVIRONMENTAL.value,
        "dangerous goods": IncidentType.ENVIRONMENTAL.value,
        # Weather-related
        "heavy weather damage": IncidentType.WEATHER_RELATED.value,
        "parametric rolling": IncidentType.WEATHER_RELATED.value,
        # Other
        "near miss": IncidentType.NEAR_MISS.value,
        "hazardous occurrence": IncidentType.NEAR_MISS.value,
        "other": IncidentType.OTHER.value,
    }

    # EMCIP ship type to VesselType enum mappings
    SHIP_TYPE_MAPPINGS: Dict[str, str] = {
        # Offshore vessels
        "offshore drilling unit": VesselType.DRILLING_RIG.value,
        "drilling rig": VesselType.DRILLING_RIG.value,
        "modu": VesselType.MODU.value,
        "mobile offshore drilling unit": VesselType.MODU.value,
        "fpso": VesselType.FPSO.value,
        "production platform": VesselType.PRODUCTION_PLATFORM.value,
        "offshore supply vessel": VesselType.SUPPLY_VESSEL.value,
        "osv": VesselType.SUPPLY_VESSEL.value,
        "platform supply vessel": VesselType.SUPPLY_VESSEL.value,
        "psv": VesselType.SUPPLY_VESSEL.value,
        "anchor handling tug": VesselType.ANCHOR_HANDLING.value,
        "ahts": VesselType.ANCHOR_HANDLING.value,
        "offshore support vessel": VesselType.SUPPLY_VESSEL.value,
        # Tankers
        "oil tanker": VesselType.TANKER.value,
        "tanker": VesselType.TANKER.value,
        "chemical tanker": VesselType.TANKER.value,
        "product tanker": VesselType.TANKER.value,
        "lng carrier": VesselType.TANKER.value,
        "lpg carrier": VesselType.TANKER.value,
        "gas carrier": VesselType.TANKER.value,
        # Cargo
        "general cargo": VesselType.CARGO_VESSEL.value,
        "cargo ship": VesselType.CARGO_VESSEL.value,
        "bulk carrier": VesselType.CARGO_VESSEL.value,
        "container ship": VesselType.CARGO_VESSEL.value,
        "containership": VesselType.CARGO_VESSEL.value,
        "ro-ro cargo": VesselType.CARGO_VESSEL.value,
        "reefer": VesselType.CARGO_VESSEL.value,
        "refrigerated cargo": VesselType.CARGO_VESSEL.value,
        # Other vessel types
        "tug": VesselType.TUG.value,
        "tugboat": VesselType.TUG.value,
        "towing vessel": VesselType.TUG.value,
        "research vessel": VesselType.RESEARCH_VESSEL.value,
        "survey vessel": VesselType.RESEARCH_VESSEL.value,
        "diving support vessel": VesselType.DIVING_SUPPORT.value,
        "dsv": VesselType.DIVING_SUPPORT.value,
        "cable layer": VesselType.CABLE_LAYER.value,
        "cable ship": VesselType.CABLE_LAYER.value,
        # Passenger vessels
        "passenger ship": VesselType.OTHER.value,
        "ro-ro passenger": VesselType.OTHER.value,
        "ferry": VesselType.OTHER.value,
        "cruise ship": VesselType.OTHER.value,
        # Fishing
        "fishing vessel": VesselType.OTHER.value,
        "fishing": VesselType.OTHER.value,
        "trawler": VesselType.OTHER.value,
    }

    # Investigation status mappings
    STATUS_MAPPINGS: Dict[str, str] = {
        "reported": IncidentStatus.REPORTED.value,
        "notification": IncidentStatus.REPORTED.value,
        "under investigation": IncidentStatus.UNDER_INVESTIGATION.value,
        "ongoing": IncidentStatus.UNDER_INVESTIGATION.value,
        "in progress": IncidentStatus.UNDER_INVESTIGATION.value,
        "preliminary": IncidentStatus.PRELIMINARY_REPORT.value,
        "interim report": IncidentStatus.PRELIMINARY_REPORT.value,
        "final": IncidentStatus.FINAL_REPORT.value,
        "final report": IncidentStatus.FINAL_REPORT.value,
        "closed": IncidentStatus.CLOSED.value,
        "no investigation": IncidentStatus.CLOSED.value,
        "archived": IncidentStatus.ARCHIVED.value,
    }

    def __init__(
        self,
        source_path: Path,
        session: Session,
        batch_size: int = 100,
        file_format: str = "auto",
        member_state: str = "all",
        credentials: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize EMSA EMCIP importer.

        Args:
            source_path: Path to EMCIP export file (CSV, JSON, or XML)
            session: Database session
            batch_size: Records per batch for database commits
            file_format: Format of source file ('csv', 'json', 'xml', or 'auto')
            member_state: Filter by EU member state code ('all' or 2-letter code)
            credentials: Optional EMCIP API credentials dict with keys:
                        'username', 'password', 'api_key'

        Raises:
            NotImplementedError: This is a stub - full implementation pending
                                EMCIP data access agreement
        """
        super().__init__(source_path, session, batch_size)

        # Auto-detect format from file extension
        if file_format == "auto":
            suffix = source_path.suffix.lower()
            if suffix == ".json":
                self.file_format = "json"
            elif suffix == ".csv":
                self.file_format = "csv"
            elif suffix == ".xml":
                self.file_format = "xml"
            else:
                self.file_format = "csv"  # Default assumption
        else:
            self.file_format = file_format

        # Normalize member state filter
        self.member_state = self._normalize_member_state(member_state)

        # Store credentials (not currently used - stub)
        self.credentials = credentials or {}

        # Caches for performance
        self._location_cache: Dict[str, int] = {}
        self._vessel_cache: Dict[str, int] = {}

        logger.info(
            f"Initialized EMSAImporter (format={self.file_format}, "
            f"member_state={self.member_state})"
        )
        logger.warning(
            "EMSA importer is a stub implementation. "
            "Full functionality requires EMCIP data access credentials."
        )

    def _normalize_member_state(self, state: str) -> Optional[str]:
        """
        Normalize member state code to ISO 3166-1 alpha-2.

        Args:
            state: Member state code or name, or 'all' for no filter

        Returns:
            Normalized 2-letter code or None for 'all'
        """
        if not state or state.lower() == "all":
            return None

        state_lookup = state.lower().strip()

        if state_lookup in self.EU_MEMBER_STATE_CODES:
            return self.EU_MEMBER_STATE_CODES[state_lookup]

        # Check if already a valid 2-letter code (uppercase)
        state_upper = state.upper().strip()
        if len(state_upper) == 2 and state_upper in self.EU_MEMBER_STATE_CODES.values():
            return state_upper

        logger.warning(f"Unknown EU member state: {state}")
        return state_upper if len(state_upper) == 2 else None

    def read_source(self) -> Generator[Dict[str, Any], None, None]:
        """
        Read records from EMCIP export file.

        This method is not yet implemented. EMCIP data requires
        institutional access credentials.

        Yields:
            Raw record dictionaries from EMCIP export

        Raises:
            NotImplementedError: EMCIP data access not configured
        """
        raise NotImplementedError(
            "EMSA EMCIP data import requires institutional access.\n\n"
            "To obtain access:\n"
            "1. Visit: https://portal.emsa.europa.eu/emcip-public\n"
            "2. Contact: emcip-support@emsa.europa.eu\n"
            "3. Submit data access request under Directive 2009/18/EC\n\n"
            "Once access is granted, provide EMCIP export files to this importer.\n"
            "Supported formats: CSV, JSON, XML"
        )

    def parse_record(self, raw_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse raw EMCIP record into standardized format.

        Applies EMCIP field mappings and normalizations for:
        - CASMET taxonomy compliance
        - EU member state code normalization
        - IMO casualty classification alignment

        Args:
            raw_record: Raw record from EMCIP export

        Returns:
            Parsed record dictionary or None if invalid

        Raises:
            NotImplementedError: EMCIP data access not configured
        """
        raise NotImplementedError(
            "EMSA EMCIP record parsing not implemented.\n"
            "Requires EMCIP data samples to validate field mappings.\n"
            "Contact emcip-support@emsa.europa.eu for data access."
        )

    def map_to_model(self, parsed_record: Dict[str, Any]) -> Optional[Any]:
        """
        Map parsed EMCIP record to database model.

        Creates Incident, Vessel, and Location entities following
        EMCIP taxonomy standards.

        Args:
            parsed_record: Normalized record dictionary

        Returns:
            Incident model instance or None

        Raises:
            NotImplementedError: EMCIP data access not configured
        """
        raise NotImplementedError(
            "EMSA EMCIP model mapping not implemented.\n"
            "Requires validation against EMCIP data schema.\n"
            "See: EMCIP Data Exchange Format specification"
        )

    def validate_credentials(self) -> bool:
        """
        Validate EMCIP access credentials.

        Checks if provided credentials can authenticate with EMCIP system.

        Returns:
            True if credentials are valid, False otherwise

        Raises:
            NotImplementedError: EMCIP API access not implemented
        """
        raise NotImplementedError(
            "EMCIP credential validation not implemented.\n"
            "EMCIP API access requires institutional agreement.\n"
            "Contact EMSA for API documentation."
        )

    def fetch_from_api(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        member_state: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch records directly from EMCIP API.

        Retrieves marine casualty records within date range.

        Args:
            start_date: Start of date range (default: 1 year ago)
            end_date: End of date range (default: today)
            member_state: Filter by member state (default: self.member_state)

        Returns:
            List of raw EMCIP records

        Raises:
            NotImplementedError: EMCIP API access not implemented
        """
        raise NotImplementedError(
            "EMCIP API fetch not implemented.\n"
            "Direct API access requires:\n"
            "1. Institutional access agreement\n"
            "2. API credentials from EMSA\n"
            "3. Compliance with data protection requirements\n\n"
            "Alternative: Request data export from EMCIP portal"
        )

    def get_supported_member_states(self) -> List[str]:
        """
        Get list of EU member states supported by EMCIP.

        Returns:
            List of 2-letter ISO country codes
        """
        # Return unique values from member state mappings
        return sorted(set(self.EU_MEMBER_STATE_CODES.values()))

    def _map_occurrence_type(self, occurrence_type: str) -> str:
        """
        Map EMCIP occurrence type to IncidentType enum value.

        Uses CASMET taxonomy mappings.

        Args:
            occurrence_type: EMCIP occurrence/event type string

        Returns:
            IncidentType enum value string
        """
        if not occurrence_type:
            return IncidentType.OTHER.value

        type_lower = occurrence_type.lower().strip()

        # Try exact match
        if type_lower in self.OCCURRENCE_TYPE_MAPPINGS:
            return self.OCCURRENCE_TYPE_MAPPINGS[type_lower]

        # Try partial match
        for key, value in self.OCCURRENCE_TYPE_MAPPINGS.items():
            if key in type_lower or type_lower in key:
                return value

        logger.debug(f"Unknown EMCIP occurrence type: {occurrence_type}")
        return IncidentType.OTHER.value

    def _map_ship_type(self, ship_type: str) -> str:
        """
        Map EMCIP ship type to VesselType enum value.

        Args:
            ship_type: EMCIP ship type/category string

        Returns:
            VesselType enum value string
        """
        if not ship_type:
            return VesselType.OTHER.value

        type_lower = ship_type.lower().strip()

        # Try exact match
        if type_lower in self.SHIP_TYPE_MAPPINGS:
            return self.SHIP_TYPE_MAPPINGS[type_lower]

        # Try partial match
        for key, value in self.SHIP_TYPE_MAPPINGS.items():
            if key in type_lower:
                return value

        logger.debug(f"Unknown EMCIP ship type: {ship_type}")
        return VesselType.OTHER.value

    def _map_casualty_category(self, category: str) -> str:
        """
        Map EMCIP casualty category to severity string.

        Based on IMO casualty classification:
        - Very Serious Marine Casualty (VSMC)
        - Serious Marine Casualty (SMC)
        - Marine Casualty (MC)
        - Marine Incident (MI)

        Args:
            category: EMCIP casualty category string

        Returns:
            Severity level string
        """
        if not category:
            return "unknown"

        cat_lower = category.lower().strip()

        if cat_lower in self.CASUALTY_CATEGORY_MAPPINGS:
            return self.CASUALTY_CATEGORY_MAPPINGS[cat_lower]

        # Try partial match
        for key, value in self.CASUALTY_CATEGORY_MAPPINGS.items():
            if key in cat_lower:
                return value

        return "unknown"

    def _map_investigation_status(self, status: str) -> str:
        """
        Map EMCIP investigation status to IncidentStatus enum value.

        Args:
            status: EMCIP investigation status string

        Returns:
            IncidentStatus enum value string
        """
        if not status:
            return IncidentStatus.REPORTED.value

        status_lower = status.lower().strip()

        if status_lower in self.STATUS_MAPPINGS:
            return self.STATUS_MAPPINGS[status_lower]

        # Try partial match
        for key, value in self.STATUS_MAPPINGS.items():
            if key in status_lower:
                return value

        return IncidentStatus.REPORTED.value

    def preview_data(self, num_records: int = 5) -> List[Dict[str, Any]]:
        """
        Preview first N records without importing.

        Useful for validating file format and field mappings.

        Args:
            num_records: Number of records to preview

        Returns:
            List of parsed records

        Raises:
            NotImplementedError: EMCIP data access not configured
        """
        raise NotImplementedError(
            "EMCIP data preview not available.\n"
            "Provide EMCIP export file to enable preview functionality."
        )

    def get_field_statistics(self, max_records: int = 1000) -> Dict[str, Any]:
        """
        Analyze source file to get field statistics.

        Useful for understanding data completeness.

        Args:
            max_records: Maximum records to analyze

        Returns:
            Dictionary with field statistics

        Raises:
            NotImplementedError: EMCIP data access not configured
        """
        raise NotImplementedError(
            "EMCIP field statistics not available.\n"
            "Provide EMCIP export file to enable analysis."
        )

    def is_duplicate(self, model_instance: Any) -> bool:
        """
        Check if EMCIP record already exists in database.

        Uses source_agency (EMSA) + source_incident_id as unique key.

        Args:
            model_instance: Incident model instance to check

        Returns:
            True if duplicate exists, False otherwise
        """
        from worldenergydata.marine_safety.database.models import Incident

        existing = (
            self.session.query(Incident)
            .filter(
                Incident.source_agency == DataSource.EMSA.value,
                Incident.source_incident_id == model_instance.source_incident_id,
            )
            .first()
        )

        return existing is not None

    def clear_caches(self) -> None:
        """Clear location and vessel caches."""
        self._location_cache.clear()
        self._vessel_cache.clear()
        logger.debug("Cleared EMSA importer caches")

    @staticmethod
    def get_emcip_info() -> Dict[str, Any]:
        """
        Get information about EMCIP data platform.

        Returns:
            Dictionary with EMCIP access information
        """
        return {
            "name": "European Marine Casualty Information Platform (EMCIP)",
            "organization": "European Maritime Safety Agency (EMSA)",
            "website": "https://emsa.europa.eu",
            "portal": "https://portal.emsa.europa.eu/emcip-public",
            "support_email": "emcip-support@emsa.europa.eu",
            "legal_basis": "Directive 2009/18/EC",
            "taxonomy": "CASMET (Casualty Statistics and Methodology)",
            "imo_alignment": "MSC-MEPC.3/Circ.3",
            "access_types": {
                "public": "Basic statistics and trends via public dashboard",
                "institutional": "Full dataset via member state authorities",
                "research": "Academic access via data sharing agreement",
            },
            "data_coverage": {
                "temporal": "2011-present",
                "geographic": "EU/EEA waters and EU-flagged vessels worldwide",
                "vessel_types": "All commercial vessels, fishing vessels >15m",
            },
            "update_frequency": "Continuous (real-time reporting by member states)",
        }
