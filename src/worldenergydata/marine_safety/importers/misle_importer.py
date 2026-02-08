"""
MISLE Data Importer

Imports USCG MISLE (Marine Information for Safety and Law Enforcement)
database files into the marine safety database.
"""

import csv
import logging
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy.orm import Session

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


class MISLEImporter(BaseImporter):
    """
    Imports USCG MISLE marine casualty data.

    Expected source format: CSV or Access database export
    Expected fields (may vary):
    - Case number / Incident ID
    - Incident date/time
    - Location (lat/lon or description)
    - Incident type
    - Vessel information
    - Casualties (fatalities, injuries)
    - Damage estimates
    - Investigation details
    """

    # MISLE field name mappings (adjust based on actual file structure)
    FIELD_MAPPINGS = {
        "CASENUMBER": "source_incident_id",
        "CASE_NUMBER": "source_incident_id",
        "INCIDENT_ID": "source_incident_id",
        "ACTIVITY_DATE": "incident_date",
        "INCIDENT_DATE": "incident_date",
        "DATE": "incident_date",
        "ACTIVITY_TIME": "incident_time",
        "INCIDENT_TIME": "incident_time",
        "TIME": "incident_time",
        "LATITUDE": "latitude",
        "LAT": "latitude",
        "LONGITUDE": "longitude",
        "LON": "longitude",
        "LONG": "longitude",
        "INCIDENT_TYPE": "incident_type",
        "TYPE": "incident_type",
        "ACTIVITY_TYPE": "incident_type",
        "FATALITIES": "fatalities",
        "DEATHS": "fatalities",
        "INJURIES": "injuries",
        "INJURED": "injuries",
        "MISSING": "missing_persons",
        "VESSEL_NAME": "vessel_name",
        "VESSEL_TYPE": "vessel_type",
        "IMO_NUMBER": "imo_number",
        "FLAG": "flag_state",
        "FLAG_STATE": "flag_state",
        "DAMAGE_USD": "estimated_damage_usd",
        "DAMAGE": "estimated_damage_usd",
        "PROPERTY_DAMAGE": "estimated_damage_usd",
    }

    def __init__(
        self,
        source_path: Path,
        session: Session,
        batch_size: int = 100,
        file_format: str = "csv",
    ):
        """
        Initialize MISLE importer.

        Args:
            source_path: Path to MISLE data file
            session: Database session
            batch_size: Records per batch
            file_format: Format of source file ('csv', 'access', 'excel')
        """
        super().__init__(source_path, session, batch_size)

        self.file_format = file_format
        self.cleaner = DataCleaner()
        self.normalizer = DataNormalizer()

        # Cache for lookups
        self._location_cache = {}
        self._vessel_cache = {}
        self._company_cache = {}

    def read_source(self) -> Generator[Dict[str, Any], None, None]:
        """
        Read records from MISLE CSV file.

        Yields:
            Raw record dictionaries
        """
        if self.file_format == "csv":
            yield from self._read_csv()
        else:
            raise NotImplementedError(f"Format '{self.file_format}' not yet supported")

    def _read_csv(self) -> Generator[Dict[str, Any], None, None]:
        """Read CSV file."""
        try:
            with open(self.source_path, "r", encoding="utf-8-sig") as f:
                # Try comma first, then tab
                sample = f.read(4096)
                f.seek(0)

                delimiter = "," if "," in sample else "\t"

                reader = csv.DictReader(f, delimiter=delimiter)

                for row in reader:
                    # Convert to uppercase keys for mapping, skip None keys
                    normalized_row = {
                        k.upper().strip(): v for k, v in row.items() if k is not None
                    }
                    yield normalized_row

        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
            raise

    def parse_record(self, raw_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse raw MISLE record into standardized format.

        Args:
            raw_record: Raw record from MISLE file

        Returns:
            Parsed record dictionary or None
        """
        try:
            parsed = {}

            # Map fields using field mappings
            for misle_field, our_field in self.FIELD_MAPPINGS.items():
                if misle_field in raw_record:
                    value = raw_record[misle_field]
                    if value and str(value).strip():  # Not empty
                        parsed[our_field] = value

            # Ensure we have minimum required fields
            if "source_incident_id" not in parsed:
                logger.warning("Record missing incident ID, skipping")
                return None

            if "incident_date" not in parsed:
                logger.warning(
                    f"Record {parsed.get('source_incident_id')} missing date, skipping"
                )
                return None

            # Add source agency
            parsed["source_agency"] = "USCG"

            # Clean the data
            parsed = self.cleaner.process(parsed)

            # Normalize the data
            parsed = self.normalizer.process(parsed)

            return parsed

        except Exception as e:
            logger.error(f"Error parsing record: {e}")
            return None

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
            company_id = (
                None  # Company data usually not in MISLE, set later if available
            )

            # Create incident
            incident = Incident(
                source_agency=parsed_record.get("source_agency", "USCG"),
                source_incident_id=parsed_record["source_incident_id"],
                incident_date=parsed_record["incident_date"],
                incident_time=parsed_record.get("incident_time"),
                incident_type=parsed_record.get("incident_type", "other"),
                severity_level=parsed_record.get("severity_level", 2),
                status=parsed_record.get("status", "reported"),
                title=parsed_record.get("title"),
                description=parsed_record.get("description"),
                vessel_id=vessel_id,
                company_id=company_id,
                location_id=location_id,
                fatalities=parsed_record.get("fatalities", 0),
                injuries=parsed_record.get("injuries", 0),
                missing_persons=parsed_record.get("missing_persons", 0),
                estimated_damage_usd=parsed_record.get("estimated_damage_usd"),
                data_quality_score=Decimal("0.75"),  # MISLE data is reasonably reliable
            )

            return incident

        except Exception as e:
            logger.error(f"Error mapping to model: {e}")
            return None

    def _get_or_create_location(self, record: Dict[str, Any]) -> Optional[int]:
        """Get or create location entity."""
        lat = record.get("latitude")
        lon = record.get("longitude")

        if not lat or not lon:
            return None

        # Check cache
        cache_key = f"{lat},{lon}"
        if cache_key in self._location_cache:
            return self._location_cache[cache_key]

        # Check database
        existing = (
            self.session.query(Location)
            .filter(Location.latitude == lat, Location.longitude == lon)
            .first()
        )

        if existing:
            self._location_cache[cache_key] = existing.location_id
            return existing.location_id

        # Create new
        location = Location(
            latitude=lat,
            longitude=lon,
            location_name=record.get("location_description"),
            country_code=record.get("country_code", "USA"),
        )
        self.session.add(location)
        self.session.flush()

        self._location_cache[cache_key] = location.location_id
        return location.location_id

    def _get_or_create_vessel(self, record: Dict[str, Any]) -> Optional[int]:
        """Get or create vessel entity."""
        vessel_name = record.get("vessel_name")
        imo_number = record.get("imo_number")

        if not vessel_name and not imo_number:
            return None

        # Check cache by IMO
        if imo_number and imo_number in self._vessel_cache:
            return self._vessel_cache[imo_number]

        # Check database
        if imo_number:
            existing = (
                self.session.query(Vessel)
                .filter(Vessel.imo_number == imo_number)
                .first()
            )

            if existing:
                self._vessel_cache[imo_number] = existing.vessel_id
                return existing.vessel_id

        # Create new
        vessel = Vessel(
            vessel_name=vessel_name or f"Unknown ({imo_number})",
            vessel_type=record.get("vessel_type", "other"),
            imo_number=imo_number,
            flag_state=record.get("flag_state"),
        )
        self.session.add(vessel)
        self.session.flush()

        if imo_number:
            self._vessel_cache[imo_number] = vessel.vessel_id

        return vessel.vessel_id

    def is_duplicate(self, incident: Incident) -> bool:
        """
        Check if incident already exists.

        Args:
            incident: Incident model instance

        Returns:
            True if duplicate, False otherwise
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

        Args:
            num_records: Number of records to preview

        Returns:
            List of parsed records
        """
        logger.info(f"Previewing first {num_records} records...")

        previews = []
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
