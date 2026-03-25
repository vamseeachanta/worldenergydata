# ABOUTME: Abstract base class for BSEE HSE data importers
# ABOUTME: Provides common validation, error handling, and database persistence framework

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from worldenergydata.hse.database.models import HSEIncident


class BaseImporter(ABC):
    """
    Abstract base class for BSEE HSE data importers.

    Provides common functionality for data validation, error handling,
    duplicate detection, and database persistence across all importer implementations.

    Concrete importers must implement:
    - fetch_data(): Retrieve raw data from source (CSV, API, web scraping)
    - normalize_data(): Transform raw data to match database schema

    Usage:
        class BSEEIncidentsImporter(BaseImporter):
            def fetch_data(self):
                # Fetch from BSEE API or CSV
                return raw_data_list

            def normalize_data(self, raw_data):
                # Transform to match HSEIncident schema
                return normalized_dict

        importer = BSEEIncidentsImporter(db_session)
        stats = importer.import_data()
        print(f"Imported: {stats['imported_count']}, Skipped: {stats['skipped_count']}")
    """

    # Valid enum values
    VALID_INCIDENT_TYPES = {"injury", "spill", "equipment_failure", "violation"}
    VALID_SEVERITY_LEVELS = {
        "fatality",
        "lost_time",
        "recordable",
        "near_miss",
        "minor",
    }

    # Gulf of Mexico geographic boundaries
    GOM_LATITUDE_MIN = 18.0
    GOM_LATITUDE_MAX = 31.0
    GOM_LONGITUDE_MIN = -98.0
    GOM_LONGITUDE_MAX = -80.0

    def __init__(self, db_session: Session):
        """
        Initialize importer with database session.

        Args:
            db_session: SQLAlchemy database session for persistence
        """
        self.db_session = db_session
        self.validation_errors: List[str] = []
        self.imported_count: int = 0
        self.skipped_count: int = 0

    @abstractmethod
    def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Fetch raw data from source.

        Must be implemented by concrete importer classes.

        Returns:
            List of dictionaries containing raw data from source
        """
        pass

    @abstractmethod
    def normalize_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize raw data to match database schema.

        Must be implemented by concrete importer classes.

        Args:
            raw_data: Raw data dictionary from source

        Returns:
            Normalized dictionary matching HSEIncident schema
        """
        pass

    def validate_data(self, normalized_data: Dict[str, Any]) -> bool:
        """
        Validate normalized data meets required field and constraint requirements.

        Validation checks:
        - Data type is dictionary
        - Required fields present: bsee_incident_id, incident_date, operator, incident_type, severity
        - incident_type in valid enum values
        - severity in valid enum values
        - incident_date is datetime object
        - latitude within Gulf of Mexico range (if present)
        - longitude within Gulf of Mexico range (if present)

        Args:
            normalized_data: Normalized data dictionary

        Returns:
            True if validation passes, False otherwise
            Validation errors are accumulated in self.validation_errors
        """
        # Handle None data
        if normalized_data is None:
            self.validation_errors.append("Data is None")
            return False

        # Handle wrong data type (not dictionary)
        if not isinstance(normalized_data, dict):
            self.validation_errors.append(
                f"Data must be dictionary, got {type(normalized_data).__name__}"
            )
            return False

        # Handle empty dictionary
        if not normalized_data:
            self.validation_errors.append("Data is empty dictionary")
            return False

        valid = True

        # Check required fields
        required_fields = [
            "bsee_incident_id",
            "incident_date",
            "operator",
            "incident_type",
            "severity",
        ]
        for field in required_fields:
            if field not in normalized_data or normalized_data[field] is None:
                self.validation_errors.append(f"Missing required field: {field}")
                valid = False

        # Validate incident_type enum
        if (
            "incident_type" in normalized_data
            and normalized_data["incident_type"] is not None
        ):
            if normalized_data["incident_type"] not in self.VALID_INCIDENT_TYPES:
                self.validation_errors.append(
                    f"Invalid incident_type: {normalized_data['incident_type']}. "
                    f"Must be one of: {', '.join(self.VALID_INCIDENT_TYPES)}"
                )
                valid = False

        # Validate severity enum
        if "severity" in normalized_data and normalized_data["severity"] is not None:
            if normalized_data["severity"] not in self.VALID_SEVERITY_LEVELS:
                self.validation_errors.append(
                    f"Invalid severity: {normalized_data['severity']}. "
                    f"Must be one of: {', '.join(self.VALID_SEVERITY_LEVELS)}"
                )
                valid = False

        # Validate incident_date is datetime object
        if (
            "incident_date" in normalized_data
            and normalized_data["incident_date"] is not None
        ):
            if not isinstance(normalized_data["incident_date"], datetime):
                self.validation_errors.append(
                    f"incident_date must be datetime object, got {type(normalized_data['incident_date']).__name__}"
                )
                valid = False

        # Validate latitude within Gulf of Mexico range
        if "latitude" in normalized_data and normalized_data["latitude"] is not None:
            lat = normalized_data["latitude"]
            if lat < self.GOM_LATITUDE_MIN or lat > self.GOM_LATITUDE_MAX:
                self.validation_errors.append(
                    f"Latitude {lat} outside Gulf of Mexico range "
                    f"({self.GOM_LATITUDE_MIN} to {self.GOM_LATITUDE_MAX}°N)"
                )
                valid = False

        # Validate longitude within Gulf of Mexico range
        if "longitude" in normalized_data and normalized_data["longitude"] is not None:
            lon = normalized_data["longitude"]
            if lon < self.GOM_LONGITUDE_MIN or lon > self.GOM_LONGITUDE_MAX:
                self.validation_errors.append(
                    f"Longitude {lon} outside Gulf of Mexico range "
                    f"({self.GOM_LONGITUDE_MIN} to {self.GOM_LONGITUDE_MAX}°W)"
                )
                valid = False

        return valid

    def is_duplicate(self, data: Dict[str, Any]) -> bool:
        """
        Check if incident already exists in database.

        Duplicate detection based on unique bsee_incident_id.

        Args:
            data: Normalized data dictionary

        Returns:
            True if incident exists in database, False otherwise
        """
        if "bsee_incident_id" not in data:
            return False

        bsee_id = data["bsee_incident_id"]
        existing = (
            self.db_session.query(HSEIncident)
            .filter(HSEIncident.bsee_incident_id == bsee_id)
            .first()
        )

        return existing is not None

    def skip_duplicate(self, data: Dict[str, Any]):
        """
        Increment skipped count for duplicate incident.

        Args:
            data: Normalized data dictionary (not used, for consistency)
        """
        self.skipped_count += 1

    def import_record(self, data: Dict[str, Any]):
        """
        Import single record to database.

        Creates HSEIncident object and persists to database.
        Increments imported_count on success.

        Args:
            data: Validated, normalized data dictionary
        """
        # Create HSEIncident object
        incident = HSEIncident(
            bsee_incident_id=data.get("bsee_incident_id"),
            incident_date=data.get("incident_date"),
            operator=data.get("operator"),
            facility_name=data.get("facility_name"),
            lease_number=data.get("lease_number"),
            block_number=data.get("block_number"),
            field_name=data.get("field_name"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            incident_type=data.get("incident_type"),
            severity=data.get("severity"),
            description=data.get("description"),
            root_cause=data.get("root_cause"),
            corrective_actions=data.get("corrective_actions"),
            investigation_status=data.get("investigation_status"),
        )

        # Persist to database
        self.db_session.add(incident)
        self.db_session.commit()

        # Increment imported count
        self.imported_count += 1

    def import_data(self) -> Dict[str, int]:
        """
        Execute full import pipeline: fetch → normalize → validate → persist.

        Pipeline steps:
        1. Fetch raw data from source (fetch_data)
        2. For each record:
            a. Normalize to match schema (normalize_data)
            b. Validate required fields and constraints (validate_data)
            c. Check for duplicates (is_duplicate)
            d. Import to database if valid and not duplicate (import_record)
        3. Return import statistics

        Returns:
            Dictionary with import statistics:
            - imported_count: Number of records successfully imported
            - skipped_count: Number of duplicate records skipped
            - error_count: Number of records that failed validation
            - total_records: Total number of records processed
        """
        # Fetch raw data
        raw_data_list = self.fetch_data()
        total_records = len(raw_data_list)
        error_count = 0

        # Process each record
        for raw_data in raw_data_list:
            # Normalize data
            normalized = self.normalize_data(raw_data)

            # Validate data
            if not self.validate_data(normalized):
                error_count += 1
                continue

            # Check for duplicates
            if self.is_duplicate(normalized):
                self.skip_duplicate(normalized)
                continue

            # Import record
            self.import_record(normalized)

        # Return statistics
        return {
            "imported_count": self.imported_count,
            "skipped_count": self.skipped_count,
            "error_count": error_count,
            "total_records": total_records,
        }

    def clear_errors(self):
        """Clear validation errors list."""
        self.validation_errors = []
