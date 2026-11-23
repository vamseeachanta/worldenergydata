# ABOUTME: Concrete importer for BSEE incident investigation database CSV data
# ABOUTME: Implements CSV parsing and field normalization for HSE incident records

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from worldenergydata.common.logging import get_logger
from worldenergydata.hse.importers.base_importer import BaseImporter

logger = get_logger(__name__)


class BSEEIncidentsImporter(BaseImporter):
    """
    Concrete importer for BSEE incident investigation database.

    Imports HSE incident data from BSEE CSV files or web scraping sources.
    Handles CSV parsing, field normalization, and data type conversion.

    Usage:
        importer = BSEEIncidentsImporter(db_session, csv_file_path="incidents.csv")
        stats = importer.import_data()
        logger.info(f"Imported: {stats['imported_count']}, Skipped: {stats['skipped_count']}")
    """

    def __init__(self, db_session, csv_file_path: str = None):
        """
        Initialize BSEE incidents importer.

        Args:
            db_session: SQLAlchemy database session
            csv_file_path: Path to BSEE incidents CSV file (optional)
        """
        super().__init__(db_session)
        self.csv_file_path = csv_file_path

    def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Fetch raw incident data from CSV file.

        Reads BSEE incident CSV file and returns records as list of dictionaries.
        Expected CSV columns:
        - incident_id: BSEE incident identifier
        - incident_date: Date of incident (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        - operator_name: Operating company name
        - facility: Facility name (optional)
        - lease: Lease number (optional)
        - block: Block number (optional)
        - field: Field name (optional)
        - lat: Latitude as string (optional)
        - lon: Longitude as string (optional)
        - incident_type: Type of incident (injury, spill, equipment_failure, violation)
        - severity: Severity level (fatality, lost_time, recordable, near_miss, minor)
        - description: Incident description (optional)

        Returns:
            List of dictionaries containing raw CSV data

        Raises:
            FileNotFoundError: If CSV file does not exist
            ValueError: If CSV file is invalid or malformed
        """
        if not self.csv_file_path:
            raise ValueError("csv_file_path not provided")

        csv_path = Path(self.csv_file_path)

        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_file_path}")

        try:
            # Read CSV file with pandas
            df = pd.read_csv(csv_path)

            # Convert DataFrame to list of dictionaries
            records = df.to_dict("records")

            return records

        except pd.errors.EmptyDataError:
            # Empty CSV file (only headers or completely empty)
            return []
        except Exception as e:
            raise ValueError(f"Failed to parse CSV file: {e}")

    def normalize_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize raw CSV data to match database schema.

        Performs field mapping from BSEE CSV format to HSEIncident database schema
        and converts data types as needed.

        Field Mappings:
        - incident_id → bsee_incident_id
        - incident_date (string) → incident_date (datetime)
        - operator_name → operator
        - facility → facility_name
        - lease → lease_number
        - block → block_number
        - field → field_name
        - lat (string) → latitude (float)
        - lon (string) → longitude (float)
        - incident_type → incident_type (unchanged)
        - severity → severity (unchanged)
        - description → description (unchanged)

        Args:
            raw_data: Raw data dictionary from CSV

        Returns:
            Normalized dictionary matching HSEIncident schema
        """
        normalized = {}

        # Required field: bsee_incident_id
        if "incident_id" in raw_data:
            normalized["bsee_incident_id"] = raw_data["incident_id"]

        # Required field: incident_date (convert string to datetime)
        if "incident_date" in raw_data:
            date_str = raw_data["incident_date"]
            if isinstance(date_str, str):
                # Try parsing with time component first
                try:
                    normalized["incident_date"] = datetime.strptime(
                        date_str, "%Y-%m-%d %H:%M:%S"
                    )
                except ValueError:
                    # Fall back to date-only format
                    try:
                        normalized["incident_date"] = datetime.strptime(
                            date_str, "%Y-%m-%d"
                        )
                    except ValueError:
                        # If parsing fails, keep original (will fail validation)
                        normalized["incident_date"] = date_str
            else:
                # Already datetime object
                normalized["incident_date"] = date_str

        # Required field: operator
        if "operator_name" in raw_data:
            normalized["operator"] = raw_data["operator_name"]

        # Required field: incident_type
        if "incident_type" in raw_data:
            normalized["incident_type"] = raw_data["incident_type"]

        # Required field: severity
        if "severity" in raw_data:
            normalized["severity"] = raw_data["severity"]

        # Optional field: facility_name
        if "facility" in raw_data:
            normalized["facility_name"] = raw_data["facility"]
        else:
            normalized["facility_name"] = None

        # Optional field: lease_number
        if "lease" in raw_data:
            normalized["lease_number"] = raw_data["lease"]
        else:
            normalized["lease_number"] = None

        # Optional field: block_number
        if "block" in raw_data:
            normalized["block_number"] = raw_data["block"]
        else:
            normalized["block_number"] = None

        # Optional field: field_name
        if "field" in raw_data:
            normalized["field_name"] = raw_data["field"]
        else:
            normalized["field_name"] = None

        # Optional field: latitude (convert string to float)
        if "lat" in raw_data and raw_data["lat"] is not None:
            try:
                if isinstance(raw_data["lat"], str):
                    normalized["latitude"] = float(raw_data["lat"])
                else:
                    normalized["latitude"] = raw_data["lat"]
            except (ValueError, TypeError):
                normalized["latitude"] = None
        else:
            normalized["latitude"] = None

        # Optional field: longitude (convert string to float)
        if "lon" in raw_data and raw_data["lon"] is not None:
            try:
                if isinstance(raw_data["lon"], str):
                    normalized["longitude"] = float(raw_data["lon"])
                else:
                    normalized["longitude"] = raw_data["lon"]
            except (ValueError, TypeError):
                normalized["longitude"] = None
        else:
            normalized["longitude"] = None

        # Optional field: description
        if "description" in raw_data:
            normalized["description"] = raw_data["description"]
        else:
            normalized["description"] = None

        return normalized
