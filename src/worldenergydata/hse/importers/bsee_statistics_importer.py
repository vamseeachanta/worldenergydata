# ABOUTME: Concrete importer for BSEE safety statistics database CSV data
# ABOUTME: Implements CSV parsing and field normalization for aggregated HSE statistics records

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from worldenergydata.hse.database.models import SafetyStatistic
from worldenergydata.hse.importers.base_importer import BaseImporter

from worldenergydata.common.logging import get_logger

logger = get_logger(__name__)


class BSEEStatisticsImporter(BaseImporter):
    """
    Concrete importer for BSEE safety statistics database.

    Imports aggregated HSE safety statistics from BSEE CSV files.
    Handles CSV parsing, field normalization, and data type conversion
    for quarterly and annual aggregated incident statistics.

    Usage:
        importer = BSEEStatisticsImporter(db_session, csv_file_path="statistics.csv")
        stats = importer.import_data()
        logger.info(f"Imported: {stats['imported_count']}, Skipped: {stats['skipped_count']}")
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
        Normalize raw CSV data to match SafetyStatistic database schema.

        Performs field mapping from BSEE statistics CSV format to SafetyStatistic
        database schema and converts data types as needed.

        Field Mappings:
        - report_date (string) → report_date (datetime)
        - operator_name → operator
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
            Normalized dictionary matching SafetyStatistic schema
        """
        normalized = {}

        # Required field: report_date (convert string to datetime)
        if "report_date" in raw_data:
            date_str = raw_data["report_date"]
            if isinstance(date_str, str):
                try:
                    normalized["report_date"] = datetime.strptime(
                        date_str, "%Y-%m-%d %H:%M:%S"
                    )
                except ValueError:
                    try:
                        normalized["report_date"] = datetime.strptime(
                            date_str, "%Y-%m-%d"
                        )
                    except ValueError:
                        normalized["report_date"] = date_str
            else:
                normalized["report_date"] = date_str

        # Required field: operator
        if "operator_name" in raw_data:
            normalized["operator"] = raw_data["operator_name"]

        # Optional field: facility_name
        normalized["facility_name"] = raw_data.get("facility")

        # Optional field: field_name
        normalized["field_name"] = raw_data.get("field")

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

    def validate_data(self, normalized_data: Dict[str, Any]) -> bool:
        """
        Validate normalized statistics data meets SafetyStatistic requirements.

        Overrides base validation since SafetyStatistic has different required
        fields than HSEIncident (no bsee_incident_id, incident_type, severity).

        Required fields: report_date, operator.

        Args:
            normalized_data: Normalized data dictionary

        Returns:
            True if validation passes, False otherwise
        """
        if normalized_data is None:
            self.validation_errors.append("Data is None")
            return False

        if not isinstance(normalized_data, dict):
            self.validation_errors.append(
                f"Data must be dictionary, got {type(normalized_data).__name__}"
            )
            return False

        if not normalized_data:
            self.validation_errors.append("Data is empty dictionary")
            return False

        valid = True

        # Check required fields for SafetyStatistic
        required_fields = ["report_date", "operator"]
        for field in required_fields:
            if field not in normalized_data or normalized_data[field] is None:
                self.validation_errors.append(f"Missing required field: {field}")
                valid = False

        # Validate report_date is datetime object
        if (
            "report_date" in normalized_data
            and normalized_data["report_date"] is not None
            and not isinstance(normalized_data["report_date"], datetime)
        ):
            self.validation_errors.append(
                f"report_date must be datetime object, got "
                f"{type(normalized_data['report_date']).__name__}"
            )
            valid = False

        return valid

    def is_duplicate(self, data: Dict[str, Any]) -> bool:
        """
        Check if safety statistic record already exists in database.

        Duplicate detection based on operator + report_date + facility_name
        composite key, since SafetyStatistic has no bsee_incident_id.

        Args:
            data: Normalized data dictionary

        Returns:
            True if record exists in database, False otherwise
        """
        if "operator" not in data or "report_date" not in data:
            return False

        query = self.db_session.query(SafetyStatistic).filter(
            SafetyStatistic.operator == data["operator"],
            SafetyStatistic.report_date == data["report_date"],
        )

        if data.get("facility_name") is not None:
            query = query.filter(SafetyStatistic.facility_name == data["facility_name"])
        else:
            query = query.filter(SafetyStatistic.facility_name.is_(None))

        return query.first() is not None

    def import_record(self, data: Dict[str, Any]):
        """
        Import single statistics record to database as SafetyStatistic.

        Creates a SafetyStatistic object (not HSEIncident) since this data
        represents aggregated counts rather than individual incidents.

        Args:
            data: Validated, normalized data dictionary matching
                  SafetyStatistic schema
        """
        statistic = SafetyStatistic(
            report_date=data.get("report_date"),
            operator=data.get("operator"),
            facility_name=data.get("facility_name"),
            field_name=data.get("field_name"),
            operational_period=data.get("operational_period"),
            total_incidents=data.get("total_incidents"),
            fatality_count=data.get("fatality_count"),
            lost_time_count=data.get("lost_time_count"),
            recordable_count=data.get("recordable_count"),
            near_miss_count=data.get("near_miss_count"),
            minor_count=data.get("minor_count"),
        )

        self.db_session.add(statistic)
        self.db_session.commit()

        self.imported_count += 1
