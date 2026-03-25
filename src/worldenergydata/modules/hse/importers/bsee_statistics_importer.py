# ABOUTME: Concrete importer for BSEE safety statistics database CSV data
# ABOUTME: Implements CSV parsing and field normalization for aggregated HSE statistics records

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from worldenergydata.modules.hse.importers.base_importer import BaseImporter


class BSEEStatisticsImporter(BaseImporter):
    """
    Concrete importer for BSEE safety statistics database.

    Imports aggregated HSE safety statistics from BSEE CSV files.
    Handles CSV parsing, field normalization, and data type conversion
    for quarterly and annual aggregated incident statistics.

    Usage:
        importer = BSEEStatisticsImporter(db_session, csv_file_path="statistics.csv")
        stats = importer.import_data()
        print(f"Imported: {stats['imported_count']}, Skipped: {stats['skipped_count']}")
    """

    def __init__(self, db_session, csv_file_path: str = None):
        """
        Initialize BSEE statistics importer.

        Args:
            db_session: SQLAlchemy database session
            csv_file_path: Path to BSEE statistics CSV file (optional)
        """
        super().__init__(db_session)
        self.csv_file_path = csv_file_path

    def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Fetch raw statistics data from CSV file.

        Reads BSEE statistics CSV file and returns records as list of dictionaries.
        Expected CSV columns:
        - incident_id: BSEE incident identifier
        - report_date: Date of statistical report (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        - operator_name: Operating company name
        - severity: Severity level (fatality, lost_time, recordable, near_miss, minor)
        - facility: Facility name (optional)
        - field: Field name (optional)
        - operational_period: Days operating in quarter (integer as string, optional)
        - total_incidents: Total incident count (integer as string, optional)
        - fatality_count: Number of fatalities (integer as string, optional)
        - lost_time_count: Number of lost time incidents (integer as string, optional)
        - recordable_count: Number of recordable incidents (integer as string, optional)
        - near_miss_count: Number of near miss incidents (integer as string, optional)
        - minor_count: Number of minor incidents (integer as string, optional)

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

        Performs field mapping from BSEE statistics CSV format to HSEIncident
        database schema and converts data types as needed.

        Field Mappings:
        - incident_id → bsee_incident_id
        - report_date (string) → incident_date (datetime)
        - operator_name → operator
        - incident_type → automatically set to 'equipment_failure'
        - severity → severity (unchanged)
        - facility → facility_name
        - field → field_name
        - operational_period (string) → operational_period (integer)
        - total_incidents (string) → total_incidents (integer)
        - fatality_count (string) → fatality_count (integer)
        - lost_time_count (string) → lost_time_count (integer)
        - recordable_count (string) → recordable_count (integer)
        - near_miss_count (string) → near_miss_count (integer)
        - minor_count (string) → minor_count (integer)

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
        if "report_date" in raw_data:
            date_str = raw_data["report_date"]
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

        # Required field: incident_type (automatically set to 'equipment_failure')
        normalized["incident_type"] = "equipment_failure"

        # Required field: severity
        if "severity" in raw_data:
            normalized["severity"] = raw_data["severity"]

        # Optional field: facility_name
        if "facility" in raw_data:
            normalized["facility_name"] = raw_data["facility"]
        else:
            normalized["facility_name"] = None

        # Optional field: field_name
        if "field" in raw_data:
            normalized["field_name"] = raw_data["field"]
        else:
            normalized["field_name"] = None

        # Optional field: operational_period (convert string to integer)
        if (
            "operational_period" in raw_data
            and raw_data["operational_period"] is not None
        ):
            try:
                if isinstance(raw_data["operational_period"], str):
                    normalized["operational_period"] = int(
                        raw_data["operational_period"]
                    )
                else:
                    normalized["operational_period"] = raw_data["operational_period"]
            except (ValueError, TypeError):
                normalized["operational_period"] = None
        else:
            normalized["operational_period"] = None

        # Optional field: total_incidents (convert string to integer)
        if "total_incidents" in raw_data and raw_data["total_incidents"] is not None:
            try:
                if isinstance(raw_data["total_incidents"], str):
                    normalized["total_incidents"] = int(raw_data["total_incidents"])
                else:
                    normalized["total_incidents"] = raw_data["total_incidents"]
            except (ValueError, TypeError):
                normalized["total_incidents"] = None
        else:
            normalized["total_incidents"] = None

        # Optional field: fatality_count (convert string to integer)
        if "fatality_count" in raw_data and raw_data["fatality_count"] is not None:
            try:
                if isinstance(raw_data["fatality_count"], str):
                    normalized["fatality_count"] = int(raw_data["fatality_count"])
                else:
                    normalized["fatality_count"] = raw_data["fatality_count"]
            except (ValueError, TypeError):
                normalized["fatality_count"] = None
        else:
            normalized["fatality_count"] = None

        # Optional field: lost_time_count (convert string to integer)
        if "lost_time_count" in raw_data and raw_data["lost_time_count"] is not None:
            try:
                if isinstance(raw_data["lost_time_count"], str):
                    normalized["lost_time_count"] = int(raw_data["lost_time_count"])
                else:
                    normalized["lost_time_count"] = raw_data["lost_time_count"]
            except (ValueError, TypeError):
                normalized["lost_time_count"] = None
        else:
            normalized["lost_time_count"] = None

        # Optional field: recordable_count (convert string to integer)
        if "recordable_count" in raw_data and raw_data["recordable_count"] is not None:
            try:
                if isinstance(raw_data["recordable_count"], str):
                    normalized["recordable_count"] = int(raw_data["recordable_count"])
                else:
                    normalized["recordable_count"] = raw_data["recordable_count"]
            except (ValueError, TypeError):
                normalized["recordable_count"] = None
        else:
            normalized["recordable_count"] = None

        # Optional field: near_miss_count (convert string to integer)
        if "near_miss_count" in raw_data and raw_data["near_miss_count"] is not None:
            try:
                if isinstance(raw_data["near_miss_count"], str):
                    normalized["near_miss_count"] = int(raw_data["near_miss_count"])
                else:
                    normalized["near_miss_count"] = raw_data["near_miss_count"]
            except (ValueError, TypeError):
                normalized["near_miss_count"] = None
        else:
            normalized["near_miss_count"] = None

        # Optional field: minor_count (convert string to integer)
        if "minor_count" in raw_data and raw_data["minor_count"] is not None:
            try:
                if isinstance(raw_data["minor_count"], str):
                    normalized["minor_count"] = int(raw_data["minor_count"])
                else:
                    normalized["minor_count"] = raw_data["minor_count"]
            except (ValueError, TypeError):
                normalized["minor_count"] = None
        else:
            normalized["minor_count"] = None

        return normalized
