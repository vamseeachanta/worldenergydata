# ABOUTME: NTSB (National Transportation Safety Board) marine incident data importer.
# ABOUTME: Imports marine accident investigation data from NTSB CAROL database exports.

"""
NTSB Data Importer

Imports NTSB (National Transportation Safety Board) marine accident investigation
data into the marine safety database. Handles CSV exports from the CAROL database.
"""

import csv
import logging
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy.orm import Session

from worldenergydata.modules.marine_safety.constants import (
    DataSource,
    IncidentStatus,
    IncidentType,
    VesselType,
)
from worldenergydata.modules.marine_safety.database.models import (
    Incident,
    Location,
    Vessel,
)
from worldenergydata.modules.marine_safety.importers.base_importer import BaseImporter
from worldenergydata.modules.marine_safety.processors.data_cleaner import DataCleaner
from worldenergydata.modules.marine_safety.processors.data_normalizer import (
    DataNormalizer,
)

logger = logging.getLogger(__name__)


class NTSBImporter(BaseImporter):
    """
    Imports NTSB marine accident investigation data.

    Expected source format: CSV export from NTSB CAROL database
    Filters for marine mode investigations only.

    Expected fields (CAROL database):
    - NTSB ID (e.g., MAR20AB001)
    - Mode (Marine, Aviation, etc.)
    - Event Date
    - Accident Type
    - Location (City, State, Country, Lat/Lon)
    - Vessel Name/Type
    - Fatalities/Injuries
    - Investigation Status
    - Probable Cause
    """

    # NTSB field name mappings to internal field names
    FIELD_MAPPINGS: Dict[str, str] = {
        # Primary identifiers
        "NTSB_ID": "source_incident_id",
        "NTSBID": "source_incident_id",
        "NTSB_NUMBER": "source_incident_id",
        "NTSB_NO": "source_incident_id",
        "ACCIDENT_NUMBER": "source_incident_id",
        "MKEY": "source_incident_id",
        # Date/time fields
        "EVENT_DATE": "incident_date",
        "EVENTDATE": "incident_date",
        "DATE": "incident_date",
        "ACCIDENT_DATE": "incident_date",
        "EVENT_TIME": "incident_time",
        "EVENTTIME": "incident_time",
        "TIME": "incident_time",
        # Incident type
        "ACCIDENT_TYPE": "incident_type",
        "ACCIDENTTYPE": "incident_type",
        "TYPE": "incident_type",
        "EVENT_TYPE": "incident_type",
        "EVENTTYPE": "incident_type",
        # Location fields
        "LATITUDE": "latitude",
        "LAT": "latitude",
        "LONGITUDE": "longitude",
        "LON": "longitude",
        "LONG": "longitude",
        "CITY": "city",
        "STATE": "state",
        "COUNTRY": "country",
        "LOCATION": "location_description",
        "LOCATION_DESCRIPTION": "location_description",
        "WATER_BODY": "water_body",
        "WATERBODY": "water_body",
        # Vessel fields
        "VESSEL_NAME": "vessel_name",
        "VESSELNAME": "vessel_name",
        "VESSEL_TYPE": "vessel_type",
        "VESSELTYPE": "vessel_type",
        "IMO_NUMBER": "imo_number",
        "IMONUMBER": "imo_number",
        "FLAG": "flag_state",
        "FLAG_STATE": "flag_state",
        "FLAGSTATE": "flag_state",
        "GROSS_TONNAGE": "gross_tonnage",
        "GROSSTONNAGE": "gross_tonnage",
        "YEAR_BUILT": "year_built",
        "YEARBUILT": "year_built",
        # Casualty data
        "FATALITIES": "fatalities",
        "DEATHS": "fatalities",
        "FATAL": "fatalities",
        "TOTAL_FATAL": "fatalities",
        "INJURIES": "injuries",
        "INJURED": "injuries",
        "TOTAL_INJURIES": "injuries",
        "MISSING": "missing_persons",
        "MISSING_PERSONS": "missing_persons",
        # Investigation data
        "STATUS": "investigation_status",
        "INVESTIGATION_STATUS": "investigation_status",
        "PROBABLE_CAUSE": "description",
        "PROBABLECAUSE": "description",
        "NARRATIVE": "description",
        "SYNOPSIS": "description",
        # Damage
        "DAMAGE_USD": "estimated_damage_usd",
        "DAMAGE": "estimated_damage_usd",
        "PROPERTY_DAMAGE": "estimated_damage_usd",
        # Mode (used for filtering)
        "MODE": "mode",
        "TRANSPORTATION_MODE": "mode",
    }

    # NTSB accident type mappings to IncidentType enum values
    ACCIDENT_TYPE_MAPPINGS: Dict[str, str] = {
        # Collision types
        "collision": IncidentType.COLLISION.value,
        "collision with vessel": IncidentType.COLLISION.value,
        "collision with object": IncidentType.COLLISION.value,
        "allision": IncidentType.COLLISION.value,
        "contact": IncidentType.COLLISION.value,
        "striking": IncidentType.COLLISION.value,
        # Grounding
        "grounding": IncidentType.GROUNDING.value,
        "stranding": IncidentType.GROUNDING.value,
        "aground": IncidentType.GROUNDING.value,
        "ran aground": IncidentType.GROUNDING.value,
        # Fire/Explosion
        "fire": IncidentType.FIRE.value,
        "explosion": IncidentType.EXPLOSION.value,
        "fire/explosion": IncidentType.FIRE.value,
        "fire and explosion": IncidentType.FIRE.value,
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
        "fatality": IncidentType.FATALITY.value,
        # Environmental
        "pollution": IncidentType.POLLUTION.value,
        "oil spill": IncidentType.POLLUTION.value,
        "discharge": IncidentType.POLLUTION.value,
        "environmental": IncidentType.ENVIRONMENTAL.value,
        "hazmat": IncidentType.POLLUTION.value,
        # Weather
        "weather": IncidentType.WEATHER_RELATED.value,
        "heavy weather": IncidentType.WEATHER_RELATED.value,
        "storm": IncidentType.WEATHER_RELATED.value,
    }

    # NTSB vessel type mappings to VesselType enum values
    VESSEL_TYPE_MAPPINGS: Dict[str, str] = {
        # Offshore vessels
        "drilling rig": VesselType.DRILLING_RIG.value,
        "modu": VesselType.MODU.value,
        "mobile offshore": VesselType.MODU.value,
        "platform": VesselType.PRODUCTION_PLATFORM.value,
        "fpso": VesselType.FPSO.value,
        "semisubmersible": VesselType.SEMISUBMERSIBLE.value,
        "jackup": VesselType.JACKUP_RIG.value,
        # Support vessels
        "supply vessel": VesselType.SUPPLY_VESSEL.value,
        "osv": VesselType.SUPPLY_VESSEL.value,
        "offshore supply": VesselType.SUPPLY_VESSEL.value,
        "anchor handling": VesselType.ANCHOR_HANDLING.value,
        "ahts": VesselType.ANCHOR_HANDLING.value,
        "tug": VesselType.TUG.value,
        "tugboat": VesselType.TUG.value,
        "towboat": VesselType.TUG.value,
        "push boat": VesselType.TUG.value,
        "crew boat": VesselType.CREW_BOAT.value,
        "crewboat": VesselType.CREW_BOAT.value,
        "standby vessel": VesselType.STANDBY_VESSEL.value,
        # Cargo vessels
        "tanker": VesselType.TANKER.value,
        "oil tanker": VesselType.TANKER.value,
        "chemical tanker": VesselType.TANKER.value,
        "cargo": VesselType.CARGO_VESSEL.value,
        "cargo vessel": VesselType.CARGO_VESSEL.value,
        "cargo ship": VesselType.CARGO_VESSEL.value,
        "container": VesselType.CARGO_VESSEL.value,
        "container ship": VesselType.CARGO_VESSEL.value,
        "bulk carrier": VesselType.CARGO_VESSEL.value,
        "freighter": VesselType.CARGO_VESSEL.value,
        "barge": VesselType.CARGO_VESSEL.value,
        # Research/Diving
        "research vessel": VesselType.RESEARCH_VESSEL.value,
        "research": VesselType.RESEARCH_VESSEL.value,
        "diving support": VesselType.DIVING_SUPPORT.value,
        "dive support": VesselType.DIVING_SUPPORT.value,
        # Wind farm
        "cable layer": VesselType.CABLE_LAYER.value,
        "cable ship": VesselType.CABLE_LAYER.value,
        "service vessel": VesselType.SERVICE_VESSEL.value,
    }

    # NTSB investigation status mappings
    STATUS_MAPPINGS: Dict[str, str] = {
        "open": IncidentStatus.UNDER_INVESTIGATION.value,
        "in progress": IncidentStatus.UNDER_INVESTIGATION.value,
        "under investigation": IncidentStatus.UNDER_INVESTIGATION.value,
        "preliminary": IncidentStatus.PRELIMINARY_REPORT.value,
        "probable cause": IncidentStatus.FINAL_REPORT.value,
        "complete": IncidentStatus.FINAL_REPORT.value,
        "completed": IncidentStatus.FINAL_REPORT.value,
        "final": IncidentStatus.FINAL_REPORT.value,
        "closed": IncidentStatus.CLOSED.value,
        "archived": IncidentStatus.ARCHIVED.value,
    }

    def __init__(
        self,
        source_path: Path,
        session: Session,
        batch_size: int = 100,
        file_format: str = "csv",
        marine_only: bool = True,
    ):
        """
        Initialize NTSB importer.

        Args:
            source_path: Path to NTSB CAROL export file
            session: Database session
            batch_size: Records per batch
            file_format: Format of source file ('csv')
            marine_only: If True, filter for marine mode only
        """
        super().__init__(source_path, session, batch_size)

        self.file_format = file_format
        self.marine_only = marine_only
        self.cleaner = DataCleaner()
        self.normalizer = DataNormalizer()

        # Caches for performance optimization
        self._location_cache: Dict[str, int] = {}
        self._vessel_cache: Dict[str, int] = {}

        logger.info(f"Initialized NTSBImporter (marine_only={marine_only})")

    def read_source(self) -> Generator[Dict[str, Any], None, None]:
        """
        Read records from NTSB CSV file.

        Yields:
            Raw record dictionaries (filtered for marine mode if enabled)
        """
        if self.file_format == "csv":
            yield from self._read_csv()
        else:
            raise NotImplementedError(f"Format '{self.file_format}' not yet supported")

    def _read_csv(self) -> Generator[Dict[str, Any], None, None]:
        """Read records from CSV file, filtering for marine mode."""
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

                    # Filter for marine mode if enabled
                    if self.marine_only:
                        mode = normalized_row.get("MODE", "").lower()
                        transportation_mode = normalized_row.get(
                            "TRANSPORTATION_MODE", ""
                        ).lower()

                        # Skip non-marine records
                        if mode and mode not in ("marine", "mar"):
                            if transportation_mode not in ("marine", "mar"):
                                continue

                        # Also check NTSB ID prefix (MAR for marine)
                        ntsb_id = self._get_ntsb_id(normalized_row)
                        if ntsb_id and not ntsb_id.upper().startswith("MAR"):
                            if mode not in ("marine", "mar"):
                                continue

                    yield normalized_row

        except FileNotFoundError:
            logger.error(f"Source file not found: {self.source_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
            raise

    def _get_ntsb_id(self, row: Dict[str, Any]) -> Optional[str]:
        """Extract NTSB ID from row using various possible field names."""
        for field in [
            "NTSB_ID",
            "NTSBID",
            "NTSB_NUMBER",
            "NTSB_NO",
            "ACCIDENT_NUMBER",
            "MKEY",
        ]:
            if field in row and row[field]:
                return str(row[field]).strip()
        return None

    def parse_record(self, raw_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse raw NTSB record into standardized format.

        Args:
            raw_record: Raw record from NTSB file

        Returns:
            Parsed record dictionary or None if invalid
        """
        try:
            parsed: Dict[str, Any] = {}

            # Map fields using field mappings
            for ntsb_field, our_field in self.FIELD_MAPPINGS.items():
                if ntsb_field in raw_record:
                    value = raw_record[ntsb_field]
                    if value and str(value).strip():
                        parsed[our_field] = value

            # Ensure we have required fields
            if "source_incident_id" not in parsed:
                logger.warning("Record missing NTSB ID, skipping")
                return None

            if "incident_date" not in parsed:
                logger.warning(
                    f"Record {parsed.get('source_incident_id')} missing date, skipping"
                )
                return None

            # Set source agency
            parsed["source_agency"] = DataSource.NTSB.value

            # Map accident type to IncidentType enum
            if "incident_type" in parsed:
                parsed["incident_type"] = self._map_accident_type(
                    parsed["incident_type"]
                )

            # Map vessel type to VesselType enum
            if "vessel_type" in parsed:
                parsed["vessel_type"] = self._map_vessel_type(parsed["vessel_type"])

            # Map investigation status
            if "investigation_status" in parsed:
                parsed["status"] = self._map_status(parsed["investigation_status"])

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

    def _map_accident_type(self, accident_type: str) -> str:
        """Map NTSB accident type to IncidentType enum value."""
        if not accident_type:
            return IncidentType.OTHER.value

        accident_lower = accident_type.lower().strip()

        # Try exact match
        if accident_lower in self.ACCIDENT_TYPE_MAPPINGS:
            return self.ACCIDENT_TYPE_MAPPINGS[accident_lower]

        # Try partial match
        for key, value in self.ACCIDENT_TYPE_MAPPINGS.items():
            if key in accident_lower or accident_lower in key:
                return value

        logger.warning(f"Unknown NTSB accident type: {accident_type}")
        return IncidentType.OTHER.value

    def _map_vessel_type(self, vessel_type: str) -> str:
        """Map NTSB vessel type to VesselType enum value."""
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

        logger.warning(f"Unknown NTSB vessel type: {vessel_type}")
        return VesselType.OTHER.value

    def _map_status(self, status: str) -> str:
        """Map NTSB investigation status to IncidentStatus enum value."""
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

        logger.warning(f"Unknown NTSB status: {status}")
        return IncidentStatus.REPORTED.value

    def _build_location_description(self, parsed: Dict[str, Any]) -> Optional[str]:
        """Build location description from city, state, country fields."""
        parts = []

        if parsed.get("water_body"):
            parts.append(parsed["water_body"])

        if parsed.get("city"):
            parts.append(parsed["city"])

        if parsed.get("state"):
            parts.append(parsed["state"])

        if parsed.get("country"):
            parts.append(parsed["country"])

        return ", ".join(parts) if parts else None

    def _generate_title(self, parsed: Dict[str, Any]) -> str:
        """Generate incident title from available fields."""
        vessel_name = parsed.get("vessel_name", "Unknown Vessel")
        incident_type = parsed.get("incident_type", "incident")
        ntsb_id = parsed.get("source_incident_id", "")

        # Format incident type for display
        incident_display = incident_type.replace("_", " ").title()

        return f"{incident_display} - {vessel_name} ({ntsb_id})"

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
                source_agency=DataSource.NTSB.value,
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
                # NTSB data is generally high quality
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
            country_code=record.get("country", "USA"),
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
        logger.info(f"Previewing first {num_records} NTSB records...")

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
        stats = {"total_records_analyzed": total_records, "fields": {}}

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
