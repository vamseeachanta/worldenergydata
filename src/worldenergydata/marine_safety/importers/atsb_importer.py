# ABOUTME: Australian Transport Safety Bureau (ATSB) marine incident data importer.
# ABOUTME: Imports marine accident investigation data from ATSB exports with Australian location normalization.

"""
ATSB Data Importer

Imports ATSB (Australian Transport Safety Bureau) marine accident investigation
data into the marine safety database. Handles JSON/CSV exports from ATSB scraper
and published datasets.
"""

import csv
import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy.orm import Session

from worldenergydata.marine_safety.constants import (
    DataSource,
    IncidentStatus,
    IncidentType,
    VesselType,
)
from worldenergydata.marine_safety.database.models import (
    Incident,
    Location,
    Vessel,
)
from worldenergydata.marine_safety.importers.base_importer import BaseImporter
from worldenergydata.marine_safety.processors.data_cleaner import DataCleaner
from worldenergydata.marine_safety.processors.data_normalizer import (
    DataNormalizer,
)

logger = logging.getLogger(__name__)


class ATSBImporter(BaseImporter):
    """
    Imports ATSB marine accident investigation data.

    Expected source formats:
    - JSON export from ATSB scraper
    - CSV export from ATSB datasets

    Handles Australian-specific:
    - State code normalization (NSW, VIC, QLD, etc.)
    - Southern hemisphere coordinates
    - ATSB investigation number formats

    Expected fields (ATSB format):
    - ATSB Investigation Number (e.g., MO-2022-001)
    - Investigation Status
    - Occurrence Date
    - Location (with Australian state codes)
    - Vessel Name/Type
    - Fatalities/Injuries
    - Occurrence Category
    """

    # ATSB field name mappings to internal field names
    FIELD_MAPPINGS: Dict[str, str] = {
        # Primary identifiers
        "ATSB_ID": "source_incident_id",
        "ATSB_INVESTIGATION_NUMBER": "source_incident_id",
        "INVESTIGATION_NUMBER": "source_incident_id",
        "REPORT_NUMBER": "source_incident_id",
        "SOURCE_ID": "source_incident_id",
        "atsb_id": "source_incident_id",
        "source_id": "source_incident_id",
        # Date/time fields
        "OCCURRENCE_DATE": "incident_date",
        "EVENT_DATE": "incident_date",
        "DATE": "incident_date",
        "event_date": "incident_date",
        "OCCURRENCE_TIME": "incident_time",
        "EVENT_TIME": "incident_time",
        # Incident type
        "OCCURRENCE_CATEGORY": "incident_type",
        "OCCURRENCE_TYPE": "incident_type",
        "INCIDENT_TYPE": "incident_type",
        "EVENT_TYPE": "incident_type",
        "incident_type": "incident_type",
        # Location fields
        "LATITUDE": "latitude",
        "LAT": "latitude",
        "LONGITUDE": "longitude",
        "LON": "longitude",
        "LONG": "longitude",
        "STATE": "state",
        "STATE_TERRITORY": "state",
        "REGION": "region",
        "LOCATION": "location_description",
        "LOCATION_DESCRIPTION": "location_description",
        "WATER_BODY": "water_body",
        "AUSTRALIAN_WATERS": "australian_waters",
        # Vessel fields
        "VESSEL_NAME": "vessel_name",
        "VESSEL_TYPE": "vessel_type",
        "FLAG_STATE": "flag_state",
        "FLAG": "flag_state",
        "GROSS_TONNAGE": "gross_tonnage",
        "YEAR_BUILT": "year_built",
        "IMO_NUMBER": "imo_number",
        "CALL_SIGN": "call_sign",
        # Casualty data
        "FATALITIES": "fatalities",
        "FATAL": "fatalities",
        "DEATHS": "fatalities",
        "INJURIES": "injuries",
        "INJURED": "injuries",
        "SERIOUS_INJURIES": "serious_injuries",
        "MISSING": "missing_persons",
        "MISSING_PERSONS": "missing_persons",
        # Investigation data
        "STATUS": "investigation_status",
        "INVESTIGATION_STATUS": "investigation_status",
        "PROBABLE_CAUSE": "description",
        "FINDINGS": "description",
        "SAFETY_MESSAGE": "safety_message",
        "NARRATIVE": "description",
        "SYNOPSIS": "description",
        # Titles and descriptions
        "TITLE": "title",
        "REPORT_TITLE": "title",
        "description": "description",
        # URLs
        "PDF_URL": "pdf_url",
        "REPORT_URL": "report_url",
        "pdf_url": "pdf_url",
        "report_url": "report_url",
    }

    # Australian state codes mapping
    AUSTRALIAN_STATES: Dict[str, str] = {
        # Standard abbreviations
        "nsw": "NSW",
        "vic": "VIC",
        "qld": "QLD",
        "wa": "WA",
        "sa": "SA",
        "tas": "TAS",
        "nt": "NT",
        "act": "ACT",
        # Full names
        "new south wales": "NSW",
        "victoria": "VIC",
        "queensland": "QLD",
        "western australia": "WA",
        "south australia": "SA",
        "tasmania": "TAS",
        "northern territory": "NT",
        "australian capital territory": "ACT",
        # Variations
        "n.s.w.": "NSW",
        "v.i.c.": "VIC",
        "q.l.d.": "QLD",
        "w.a.": "WA",
        "s.a.": "SA",
        "n.t.": "NT",
        "a.c.t.": "ACT",
    }

    # ATSB occurrence type mappings to IncidentType enum values
    OCCURRENCE_TYPE_MAPPINGS: Dict[str, str] = {
        # Collision types
        "collision": IncidentType.COLLISION.value,
        "collision with vessel": IncidentType.COLLISION.value,
        "collision with object": IncidentType.COLLISION.value,
        "contact": IncidentType.COLLISION.value,
        "striking": IncidentType.COLLISION.value,
        "allision": IncidentType.COLLISION.value,
        # Grounding
        "grounding": IncidentType.GROUNDING.value,
        "stranding": IncidentType.GROUNDING.value,
        "aground": IncidentType.GROUNDING.value,
        # Fire/Explosion
        "fire": IncidentType.FIRE.value,
        "explosion": IncidentType.EXPLOSION.value,
        "fire/explosion": IncidentType.FIRE.value,
        # Flooding/Capsizing
        "flooding": IncidentType.FLOODING.value,
        "foundering": IncidentType.FLOODING.value,
        "sinking": IncidentType.FLOODING.value,
        "capsizing": IncidentType.CAPSIZING.value,
        "capsize": IncidentType.CAPSIZING.value,
        "overturn": IncidentType.CAPSIZING.value,
        "listing": IncidentType.FLOODING.value,
        # Equipment/Structural
        "equipment failure": IncidentType.EQUIPMENT_FAILURE.value,
        "material failure": IncidentType.EQUIPMENT_FAILURE.value,
        "machinery failure": IncidentType.EQUIPMENT_FAILURE.value,
        "structural failure": IncidentType.STRUCTURAL_FAILURE.value,
        "hull failure": IncidentType.STRUCTURAL_FAILURE.value,
        "loss of propulsion": IncidentType.LOSS_OF_PROPULSION.value,
        "propulsion failure": IncidentType.LOSS_OF_PROPULSION.value,
        "loss of steering": IncidentType.LOSS_OF_CONTROL.value,
        "loss of control": IncidentType.LOSS_OF_CONTROL.value,
        # Personnel incidents
        "man overboard": IncidentType.PERSONNEL_INJURY.value,
        "person overboard": IncidentType.PERSONNEL_INJURY.value,
        "fall overboard": IncidentType.PERSONNEL_INJURY.value,
        "injury": IncidentType.PERSONNEL_INJURY.value,
        "personnel injury": IncidentType.PERSONNEL_INJURY.value,
        "occupational injury": IncidentType.PERSONNEL_INJURY.value,
        "fatality": IncidentType.FATALITY.value,
        "death": IncidentType.FATALITY.value,
        # Environmental
        "pollution": IncidentType.POLLUTION.value,
        "oil spill": IncidentType.POLLUTION.value,
        "marine pollution": IncidentType.POLLUTION.value,
        "environmental": IncidentType.ENVIRONMENTAL.value,
        # Weather
        "weather": IncidentType.WEATHER_RELATED.value,
        "heavy weather": IncidentType.WEATHER_RELATED.value,
        "storm": IncidentType.WEATHER_RELATED.value,
        "cyclone": IncidentType.WEATHER_RELATED.value,
        "tropical cyclone": IncidentType.WEATHER_RELATED.value,
    }

    # ATSB vessel type mappings to VesselType enum values
    VESSEL_TYPE_MAPPINGS: Dict[str, str] = {
        # Offshore vessels
        "drilling rig": VesselType.DRILLING_RIG.value,
        "modu": VesselType.MODU.value,
        "mobile offshore": VesselType.MODU.value,
        "platform": VesselType.PRODUCTION_PLATFORM.value,
        "fpso": VesselType.FPSO.value,
        "semisubmersible": VesselType.SEMISUBMERSIBLE.value,
        "semi-submersible": VesselType.SEMISUBMERSIBLE.value,
        "jackup": VesselType.JACKUP_RIG.value,
        "jack-up": VesselType.JACKUP_RIG.value,
        # Support vessels
        "supply vessel": VesselType.SUPPLY_VESSEL.value,
        "offshore supply vessel": VesselType.SUPPLY_VESSEL.value,
        "osv": VesselType.SUPPLY_VESSEL.value,
        "anchor handling": VesselType.ANCHOR_HANDLING.value,
        "ahts": VesselType.ANCHOR_HANDLING.value,
        "tug": VesselType.TUG.value,
        "tugboat": VesselType.TUG.value,
        "tow boat": VesselType.TUG.value,
        "crew boat": VesselType.CREW_BOAT.value,
        "crewboat": VesselType.CREW_BOAT.value,
        "standby vessel": VesselType.STANDBY_VESSEL.value,
        "emergency response": VesselType.STANDBY_VESSEL.value,
        # Cargo vessels
        "tanker": VesselType.TANKER.value,
        "oil tanker": VesselType.TANKER.value,
        "chemical tanker": VesselType.TANKER.value,
        "product tanker": VesselType.TANKER.value,
        "cargo": VesselType.CARGO_VESSEL.value,
        "cargo vessel": VesselType.CARGO_VESSEL.value,
        "cargo ship": VesselType.CARGO_VESSEL.value,
        "general cargo": VesselType.CARGO_VESSEL.value,
        "container": VesselType.CARGO_VESSEL.value,
        "container ship": VesselType.CARGO_VESSEL.value,
        "containership": VesselType.CARGO_VESSEL.value,
        "bulk carrier": VesselType.CARGO_VESSEL.value,
        "bulker": VesselType.CARGO_VESSEL.value,
        "freighter": VesselType.CARGO_VESSEL.value,
        "barge": VesselType.CARGO_VESSEL.value,
        # Research/Diving
        "research vessel": VesselType.RESEARCH_VESSEL.value,
        "research": VesselType.RESEARCH_VESSEL.value,
        "survey vessel": VesselType.RESEARCH_VESSEL.value,
        "diving support": VesselType.DIVING_SUPPORT.value,
        "dive support": VesselType.DIVING_SUPPORT.value,
        "diving support vessel": VesselType.DIVING_SUPPORT.value,
        # Australian specific
        "prawn trawler": VesselType.OTHER.value,
        "fishing vessel": VesselType.OTHER.value,
        "fishing": VesselType.OTHER.value,
        "trawler": VesselType.OTHER.value,
        "passenger ferry": VesselType.OTHER.value,
        "ferry": VesselType.OTHER.value,
        "passenger vessel": VesselType.OTHER.value,
        "cruise ship": VesselType.OTHER.value,
        "yacht": VesselType.OTHER.value,
        "sailing vessel": VesselType.OTHER.value,
        "recreational": VesselType.OTHER.value,
    }

    # ATSB investigation status mappings
    STATUS_MAPPINGS: Dict[str, str] = {
        "active": IncidentStatus.UNDER_INVESTIGATION.value,
        "open": IncidentStatus.UNDER_INVESTIGATION.value,
        "in progress": IncidentStatus.UNDER_INVESTIGATION.value,
        "under investigation": IncidentStatus.UNDER_INVESTIGATION.value,
        "preliminary": IncidentStatus.PRELIMINARY_REPORT.value,
        "interim": IncidentStatus.PRELIMINARY_REPORT.value,
        "draft": IncidentStatus.PRELIMINARY_REPORT.value,
        "final": IncidentStatus.FINAL_REPORT.value,
        "final report": IncidentStatus.FINAL_REPORT.value,
        "complete": IncidentStatus.FINAL_REPORT.value,
        "completed": IncidentStatus.FINAL_REPORT.value,
        "closed": IncidentStatus.CLOSED.value,
        "archived": IncidentStatus.ARCHIVED.value,
        "no further action": IncidentStatus.CLOSED.value,
    }

    def __init__(
        self,
        source_path: Path,
        session: Session,
        batch_size: int = 100,
        file_format: str = "auto",
    ):
        """
        Initialize ATSB importer.

        Args:
            source_path: Path to ATSB export file (JSON or CSV)
            session: Database session
            batch_size: Records per batch
            file_format: Format of source file ('json', 'csv', or 'auto' for detection)
        """
        super().__init__(source_path, session, batch_size)

        # Auto-detect format from extension if needed
        if file_format == "auto":
            suffix = source_path.suffix.lower()
            if suffix == ".json":
                self.file_format = "json"
            elif suffix == ".csv":
                self.file_format = "csv"
            else:
                raise ValueError(f"Cannot auto-detect format for {suffix} files")
        else:
            self.file_format = file_format

        self.cleaner = DataCleaner()
        self.normalizer = DataNormalizer()

        # Caches for performance optimization
        self._location_cache: Dict[str, int] = {}
        self._vessel_cache: Dict[str, int] = {}

        logger.info(f"Initialized ATSBImporter (format={self.file_format})")

    def read_source(self) -> Generator[Dict[str, Any], None, None]:
        """
        Read records from ATSB export file.

        Yields:
            Raw record dictionaries
        """
        if self.file_format == "json":
            yield from self._read_json()
        elif self.file_format == "csv":
            yield from self._read_csv()
        else:
            raise NotImplementedError(f"Format '{self.file_format}' not supported")

    def _read_json(self) -> Generator[Dict[str, Any], None, None]:
        """Read records from JSON file."""
        try:
            with open(self.source_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Handle both list format and dict with 'data' key
            if isinstance(data, list):
                records = data
            elif isinstance(data, dict):
                records = data.get("data", data.get("investigations", [data]))
            else:
                records = [data]

            for record in records:
                yield record

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {self.source_path}: {e}")
            raise
        except FileNotFoundError:
            logger.error(f"Source file not found: {self.source_path}")
            raise

    def _read_csv(self) -> Generator[Dict[str, Any], None, None]:
        """Read records from CSV file."""
        try:
            with open(self.source_path, "r", encoding="utf-8-sig") as f:
                # Detect delimiter
                sample = f.read(4096)
                f.seek(0)
                delimiter = "," if "," in sample else "\t"

                reader = csv.DictReader(f, delimiter=delimiter)

                for row in reader:
                    # Normalize keys to uppercase for consistent mapping
                    normalized_row = {
                        k.upper().strip(): v for k, v in row.items() if k is not None
                    }
                    yield normalized_row

        except FileNotFoundError:
            logger.error(f"Source file not found: {self.source_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
            raise

    def _get_atsb_id(self, row: Dict[str, Any]) -> Optional[str]:
        """Extract ATSB ID from row using various possible field names."""
        for field in [
            "ATSB_ID",
            "ATSB_INVESTIGATION_NUMBER",
            "INVESTIGATION_NUMBER",
            "REPORT_NUMBER",
            "SOURCE_ID",
            "atsb_id",
            "source_id",
        ]:
            # Try both original and uppercase
            for key in [field, field.upper()]:
                if key in row and row[key]:
                    return str(row[key]).strip()
        return None

    def parse_record(self, raw_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse raw ATSB record into standardized format.

        Args:
            raw_record: Raw record from ATSB file

        Returns:
            Parsed record dictionary or None if invalid
        """
        try:
            parsed: Dict[str, Any] = {}

            # Handle nested structure from scraper JSON
            if "location" in raw_record and isinstance(raw_record["location"], dict):
                parsed = self._parse_nested_record(raw_record)
            else:
                parsed = self._parse_flat_record(raw_record)

            # Ensure we have required fields
            if "source_incident_id" not in parsed:
                atsb_id = self._get_atsb_id(raw_record)
                if atsb_id:
                    parsed["source_incident_id"] = atsb_id
                else:
                    logger.warning("Record missing ATSB ID, skipping")
                    return None

            if "incident_date" not in parsed:
                logger.warning(
                    f"Record {parsed.get('source_incident_id')} missing date, skipping"
                )
                return None

            # Set source agency
            parsed["source_agency"] = DataSource.ATSB.value

            # Map occurrence type to IncidentType enum
            if "incident_type" in parsed:
                parsed["incident_type"] = self._map_occurrence_type(
                    parsed["incident_type"]
                )

            # Map vessel type to VesselType enum
            if "vessel_type" in parsed:
                parsed["vessel_type"] = self._map_vessel_type(parsed["vessel_type"])

            # Map investigation status
            if "investigation_status" in parsed:
                parsed["status"] = self._map_status(parsed["investigation_status"])

            # Normalize Australian state
            if "state" in parsed:
                parsed["state"] = self._normalize_state(parsed["state"])

            # Build location description if not present
            if "location_description" not in parsed:
                parsed["location_description"] = self._build_location_description(
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

    def _parse_nested_record(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """Parse nested record structure from scraper JSON."""
        parsed: Dict[str, Any] = {}

        # Extract top-level fields
        parsed["source_incident_id"] = raw_record.get("source_id", "")
        parsed["incident_date"] = raw_record.get("event_date")
        parsed["incident_type"] = raw_record.get("incident_type")
        parsed["investigation_status"] = raw_record.get("status")
        parsed["title"] = raw_record.get("title")
        parsed["description"] = raw_record.get("description")
        parsed["probable_cause"] = raw_record.get("probable_cause")
        parsed["report_url"] = raw_record.get("report_url")
        parsed["pdf_url"] = raw_record.get("pdf_url")

        # Extract location
        location = raw_record.get("location", {})
        if location:
            parsed["latitude"] = location.get("latitude")
            parsed["longitude"] = location.get("longitude")
            parsed["state"] = location.get("state")
            parsed["location_description"] = location.get("description")
            parsed["city"] = location.get("city")

        # Extract vessel
        vessel = raw_record.get("vessel", {})
        if vessel:
            parsed["vessel_name"] = vessel.get("name")
            parsed["vessel_type"] = vessel.get("type")
            parsed["flag_state"] = vessel.get("flag")
            parsed["gross_tonnage"] = vessel.get("gross_tonnage")

        # Extract casualties
        casualties = raw_record.get("casualties", {})
        if casualties:
            parsed["fatalities"] = casualties.get("fatalities", 0)
            parsed["injuries"] = casualties.get("injuries", 0)
            parsed["missing_persons"] = casualties.get("missing", 0)

        return parsed

    def _parse_flat_record(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """Parse flat record structure from CSV."""
        parsed: Dict[str, Any] = {}

        # Map fields using field mappings
        for source_field, our_field in self.FIELD_MAPPINGS.items():
            # Check both original and uppercase versions
            for key in [source_field, source_field.upper(), source_field.lower()]:
                if key in raw_record:
                    value = raw_record[key]
                    if value and str(value).strip():
                        parsed[our_field] = value
                    break

        return parsed

    def _normalize_state(self, state: Optional[str]) -> Optional[str]:
        """
        Normalize Australian state to standard code.

        Args:
            state: State name or code

        Returns:
            Normalized state code (NSW, VIC, etc.) or original if not recognized
        """
        if not state:
            return None

        state_lower = state.lower().strip()

        if state_lower in self.AUSTRALIAN_STATES:
            return self.AUSTRALIAN_STATES[state_lower]

        # Return uppercase if already looks like a code
        if len(state) <= 3:
            return state.upper()

        return state

    def _map_occurrence_type(self, occurrence_type: str) -> str:
        """Map ATSB occurrence type to IncidentType enum value."""
        if not occurrence_type:
            return IncidentType.OTHER.value

        occurrence_lower = occurrence_type.lower().strip()

        # Try exact match
        if occurrence_lower in self.OCCURRENCE_TYPE_MAPPINGS:
            return self.OCCURRENCE_TYPE_MAPPINGS[occurrence_lower]

        # Try partial match
        for key, value in self.OCCURRENCE_TYPE_MAPPINGS.items():
            if key in occurrence_lower or occurrence_lower in key:
                return value

        logger.warning(f"Unknown ATSB occurrence type: {occurrence_type}")
        return IncidentType.OTHER.value

    def _map_vessel_type(self, vessel_type: str) -> str:
        """Map ATSB vessel type to VesselType enum value."""
        if not vessel_type:
            return VesselType.OTHER.value

        vessel_lower = vessel_type.lower().strip()

        # Try exact match
        if vessel_lower in self.VESSEL_TYPE_MAPPINGS:
            return self.VESSEL_TYPE_MAPPINGS[vessel_lower]

        # Try partial match
        for key, value in self.VESSEL_TYPE_MAPPINGS.items():
            if key in vessel_lower:
                return value

        logger.warning(f"Unknown ATSB vessel type: {vessel_type}")
        return VesselType.OTHER.value

    def _map_status(self, status: str) -> str:
        """Map ATSB investigation status to IncidentStatus enum value."""
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

        logger.warning(f"Unknown ATSB status: {status}")
        return IncidentStatus.REPORTED.value

    def _build_location_description(self, parsed: Dict[str, Any]) -> Optional[str]:
        """Build location description from component fields."""
        parts = []

        if parsed.get("water_body"):
            parts.append(parsed["water_body"])

        if parsed.get("city"):
            parts.append(parsed["city"])

        if parsed.get("state"):
            parts.append(parsed["state"])

        # Always add Australia for context
        if parts:
            parts.append("Australia")

        return ", ".join(parts) if parts else "Australian waters"

    def _generate_title(self, parsed: Dict[str, Any]) -> str:
        """Generate incident title from available fields."""
        vessel_name = parsed.get("vessel_name", "Unknown Vessel")
        incident_type = parsed.get("incident_type", "incident")
        atsb_id = parsed.get("source_incident_id", "")

        # Format incident type for display
        incident_display = incident_type.replace("_", " ").title()

        return f"{incident_display} - {vessel_name} ({atsb_id})"

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
                source_agency=DataSource.ATSB.value,
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
                estimated_damage_usd=parsed_record.get("estimated_damage_usd"),
                investigation_status=parsed_record.get("investigation_status"),
                # ATSB data is generally high quality
                data_quality_score=Decimal("0.85"),
            )

            return incident

        except Exception as e:
            logger.error(f"Error mapping to model: {e}")
            return None

    def _calculate_severity(self, fatalities: int, injuries: int, missing: int) -> int:
        """
        Calculate severity level based on casualties.

        Returns:
            Severity level (1=minimal, 2=minor, 3=moderate, 4=serious, 5=catastrophic)
        """
        total_severe = fatalities + missing

        if total_severe >= 10:
            return 5  # Catastrophic
        elif total_severe >= 5:
            return 4  # Serious
        elif total_severe >= 1:
            return 3  # Moderate
        elif injuries >= 10:
            return 3  # Moderate
        elif injuries >= 1:
            return 2  # Minor

        return 1  # Minimal

    def _get_or_create_location(self, record: Dict[str, Any]) -> Optional[int]:
        """
        Get existing location or create new one.

        Uses caching for performance optimization.

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
            country_code="AUS",  # Australia
            region_code=record.get("state"),
        )
        self.session.add(location)
        self.session.flush()

        self._location_cache[cache_key] = location.location_id
        return location.location_id

    def _get_or_create_vessel(self, record: Dict[str, Any]) -> Optional[int]:
        """
        Get existing vessel or create new one.

        Uses caching for performance optimization.

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

        # Build cache key
        cache_key = imo_number if imo_number else vessel_name
        if cache_key in self._vessel_cache:
            return self._vessel_cache[cache_key]

        # Check database for existing vessel
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
            vessel_name=vessel_name or f"Unknown ({imo_number})",
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

    def preview_data(self, num_records: int = 5) -> List[Dict[str, Any]]:
        """
        Preview first N records without importing.

        Useful for validating field mappings before full import.

        Args:
            num_records: Number of records to preview

        Returns:
            List of parsed records
        """
        logger.info(f"Previewing first {num_records} ATSB records...")

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
        state_counts: Dict[str, int] = {}

        for raw_record in self.read_source():
            total_records += 1

            # Count all fields
            for field, value in raw_record.items():
                if value and str(value).strip():
                    field_counts[field] = field_counts.get(field, 0) + 1

            # Track Australian states
            for field in ["STATE", "STATE_TERRITORY", "state"]:
                if field in raw_record and raw_record[field]:
                    state = self._normalize_state(str(raw_record[field]))
                    if state:
                        state_counts[state] = state_counts.get(state, 0) + 1

            if total_records >= max_records:
                break

        # Calculate percentages
        stats = {
            "total_records_analyzed": total_records,
            "fields": {},
            "australian_states": state_counts,
        }

        for field, count in sorted(field_counts.items()):
            stats["fields"][field] = {
                "count": count,
                "percentage": round(count / total_records * 100, 1),
            }

        return stats

    def clear_caches(self) -> None:
        """Clear location and vessel caches."""
        self._location_cache.clear()
        self._vessel_cache.clear()
        logger.debug("Cleared importer caches")
