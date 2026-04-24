# ABOUTME: IMO GISIS (Global Integrated Shipping Information System) marine casualty data importer.
# ABOUTME: Imports marine casualties and incidents from IMO GISIS CSV
# exports per MSC-MEPC.3/Circ.4/Rev.1.

"""
IMO GISIS Data Importer

Imports marine casualty and incident data from the International Maritime Organization's
Global Integrated Shipping Information System (GISIS). Handles CSV exports from the
Marine Casualties and Incidents (MCI) module following the MSC-MEPC.3/Circ.4/Rev.1
reporting format.

Data available from 2005 onwards at gisis.imo.org (registration required).

This module serves as the main entry point and re-exports all public names
from the split sub-modules for backward compatibility.
"""

import csv
import logging
import re
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
    IncidentCause,
    IncidentDocument,
    Location,
    Vessel,
)
from worldenergydata.marine_safety.importers.base_importer import BaseImporter

# Import from split modules
from worldenergydata.marine_safety.importers.imo_mappings import (
    CASUALTY_TYPE_MAPPINGS,
    CAUSE_MAPPINGS,
    FIELD_MAPPINGS,
    SHIP_TYPE_MAPPINGS,
    STATUS_MAPPINGS,
)
from worldenergydata.marine_safety.importers.imo_normalizers import (
    FLAG_STATE_MAPPINGS,
    get_flag_state_name,
    is_flag_of_convenience,
    normalize_flag_state,
)
from worldenergydata.marine_safety.importers.imo_parser import (
    build_environmental_impact,
    build_location_description,
    calculate_severity,
    generate_title,
    map_casualty_type,
    map_ship_type,
    map_status,
    parse_contributing_factors,
    parse_position,
)
from worldenergydata.marine_safety.importers.imo_validators import (
    extract_imo_number,
    format_imo_number,
    validate_imo,
    validate_imo_number,
)
from worldenergydata.marine_safety.processors.data_cleaner import DataCleaner
from worldenergydata.marine_safety.processors.data_normalizer import (
    DataNormalizer,
)

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = [
    # Main class
    "IMOGISISImporter",
    # Validators
    "validate_imo_number",
    "validate_imo",
    "extract_imo_number",
    "format_imo_number",
    # Normalizers
    "normalize_flag_state",
    "get_flag_state_name",
    "is_flag_of_convenience",
    "FLAG_STATE_MAPPINGS",
    # Mappings
    "FIELD_MAPPINGS",
    "CASUALTY_TYPE_MAPPINGS",
    "SHIP_TYPE_MAPPINGS",
    "CAUSE_MAPPINGS",
    "STATUS_MAPPINGS",
    # Parsers
    "parse_position",
    "map_casualty_type",
    "map_ship_type",
    "map_status",
    "parse_contributing_factors",
    "build_location_description",
    "build_environmental_impact",
    "generate_title",
    "calculate_severity",
]


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

    # Class-level mappings (references to imported mappings for compatibility)
    FIELD_MAPPINGS = FIELD_MAPPINGS
    CASUALTY_TYPE_MAPPINGS = CASUALTY_TYPE_MAPPINGS
    SHIP_TYPE_MAPPINGS = SHIP_TYPE_MAPPINGS
    CAUSE_MAPPINGS = CAUSE_MAPPINGS
    STATUS_MAPPINGS = STATUS_MAPPINGS

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
        self.validate_imo_flag = validate_imo
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
            for gisis_field, our_field in FIELD_MAPPINGS.items():
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
            if "imo_number" in parsed and self.validate_imo_flag:
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
                parsed["incident_type"] = map_casualty_type(parsed["incident_type"])

            # Map vessel/ship type to VesselType enum
            if "vessel_type" in parsed:
                parsed["vessel_type"] = map_ship_type(parsed["vessel_type"])

            # Map investigation status
            if "investigation_status" in parsed:
                parsed["status"] = map_status(parsed["investigation_status"])
            else:
                parsed["status"] = IncidentStatus.REPORTED.value

            # Parse position if provided in single field
            if "position" in parsed and "latitude" not in parsed:
                lat, lon = parse_position(parsed["position"])
                if lat is not None:
                    parsed["latitude"] = lat
                if lon is not None:
                    parsed["longitude"] = lon

            # Build location description if not present
            if "location_description" not in parsed:
                parsed["location_description"] = build_location_description(parsed)

            # Extract contributing factors/causes
            if "contributing_factors" in parsed:
                parsed["cause_categories"] = parse_contributing_factors(
                    parsed["contributing_factors"]
                )

            # Build environmental impact description
            if "pollution_quantity" in parsed or "pollution_type" in parsed:
                parsed["environmental_impact"] = build_environmental_impact(parsed)

            # Generate title if not present
            if "title" not in parsed:
                parsed["title"] = generate_title(parsed)

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

            # Calculate severity based on casualties
            severity = calculate_severity(
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
