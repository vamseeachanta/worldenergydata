# ABOUTME: Concrete importer for BSEE civil penalties database CSV data
# ABOUTME: Implements CSV parsing and field normalization for HSE violation/penalty records

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from worldenergydata.common.logging import get_logger
from worldenergydata.hse.database.models import HSEIncident, ViolationIncident
from worldenergydata.hse.importers.base_importer import BaseImporter

logger = get_logger(__name__)


class BSEEPenaltiesImporter(BaseImporter):
    """
    Concrete importer for BSEE civil penalties database.

    Imports HSE violation and penalty data from BSEE CSV files.
    Handles CSV parsing, field normalization, and data type conversion
    for regulatory violations and civil penalties.

    Usage:
        importer = BSEEPenaltiesImporter(db_session, csv_file_path="penalties.csv")
        stats = importer.import_data()
        logger.info(f"Imported: {stats['imported_count']}, Skipped: {stats['skipped_count']}")
    """

    def __init__(self, db_session, csv_file_path: str = None):
        """
        Initialize BSEE penalties importer.

        Args:
            db_session: SQLAlchemy database session
            csv_file_path: Path to BSEE penalties CSV file (optional)
        """
        super().__init__(db_session)
        self.csv_file_path = csv_file_path

    def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Fetch raw penalty data from CSV file.

        Reads BSEE penalties CSV file and returns records as list of dictionaries.
        Expected CSV columns:
        - incident_id: BSEE incident identifier
        - incident_date: Date of incident (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        - operator_name: Operating company name
        - severity: Severity level (fatality, lost_time, recordable, near_miss, minor)
        - inc_number: INC (Incident of Non-Compliance) number (optional)
        - violation_type: Type of regulatory violation (optional)
        - regulation_cited: Regulation citation (e.g., "30 CFR 250.188") (optional)
        - penalty_amount: Civil penalty amount in dollars (optional)
        - penalty_status: Penalty status (proposed, assessed, paid, appealed) (optional)
        - compliance_deadline: Deadline for compliance (YYYY-MM-DD) (optional)
        - compliance_achieved: Whether compliance was achieved (True/False) (optional)

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

        Performs field mapping from BSEE penalties CSV format to HSEIncident
        and ViolationIncident database schema and converts data types as needed.

        Field Mappings:
        - incident_id → bsee_incident_id
        - incident_date (string) → incident_date (datetime)
        - operator_name → operator
        - incident_type → automatically set to 'violation'
        - severity → severity (unchanged)
        - inc_number → inc_number
        - violation_type → violation_type
        - regulation_cited → regulation_cited
        - penalty_amount (string) → penalty_amount (float)
        - penalty_status → penalty_status (unchanged)
        - compliance_deadline (string) → compliance_deadline (datetime)
        - compliance_achieved (string) → compliance_achieved (boolean)

        Args:
            raw_data: Raw data dictionary from CSV

        Returns:
            Normalized dictionary matching HSEIncident and ViolationIncident schema
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

        # Required field: incident_type (automatically set to 'violation')
        normalized["incident_type"] = "violation"

        # Required field: severity
        if "severity" in raw_data:
            normalized["severity"] = raw_data["severity"]

        # Optional field: inc_number (INC number)
        normalized["inc_number"] = raw_data.get("inc_number")

        # Optional field: violation_type
        normalized["violation_type"] = raw_data.get("violation_type")

        # Optional field: regulation_cited
        normalized["regulation_cited"] = raw_data.get("regulation_cited")

        # Optional field: penalty_amount (convert string to float)
        if "penalty_amount" in raw_data and raw_data["penalty_amount"] is not None:
            try:
                if isinstance(raw_data["penalty_amount"], str):
                    normalized["penalty_amount"] = float(raw_data["penalty_amount"])
                else:
                    normalized["penalty_amount"] = raw_data["penalty_amount"]
            except (ValueError, TypeError):
                normalized["penalty_amount"] = None
        else:
            normalized["penalty_amount"] = None

        # Optional field: penalty_status
        normalized["penalty_status"] = raw_data.get("penalty_status")

        # Optional field: compliance_deadline (convert string to datetime)
        if (
            "compliance_deadline" in raw_data
            and raw_data["compliance_deadline"] is not None
        ):
            deadline_str = raw_data["compliance_deadline"]
            if isinstance(deadline_str, str):
                # Try parsing with time component first
                try:
                    normalized["compliance_deadline"] = datetime.strptime(
                        deadline_str, "%Y-%m-%d %H:%M:%S"
                    )
                except ValueError:
                    # Fall back to date-only format
                    try:
                        normalized["compliance_deadline"] = datetime.strptime(
                            deadline_str, "%Y-%m-%d"
                        )
                    except ValueError:
                        # If parsing fails, set to None
                        normalized["compliance_deadline"] = None
            else:
                # Already datetime object
                normalized["compliance_deadline"] = deadline_str
        else:
            normalized["compliance_deadline"] = None

        # Optional field: compliance_achieved (convert string to boolean)
        if (
            "compliance_achieved" in raw_data
            and raw_data["compliance_achieved"] is not None
        ):
            achieved_str = raw_data["compliance_achieved"]
            if isinstance(achieved_str, str):
                # Parse 'True'/'False' strings to boolean
                normalized["compliance_achieved"] = achieved_str == "True"
            else:
                # Already boolean or other type
                normalized["compliance_achieved"] = achieved_str
        else:
            normalized["compliance_achieved"] = None

        return normalized

    def import_record(self, data: Dict[str, Any]):
        """
        Import single penalty/violation record to database.

        Creates both an HSEIncident base record and a linked ViolationIncident
        child record to persist violation-specific fields (inc_number,
        violation_type, regulation_cited, penalty_amount, penalty_status,
        compliance_deadline, compliance_achieved).

        Args:
            data: Validated, normalized data dictionary containing both
                  HSEIncident and ViolationIncident fields
        """
        # Create HSEIncident base record
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

        self.db_session.add(incident)
        self.db_session.flush()  # Flush to get the generated incident.id

        # Create ViolationIncident child record with violation-specific fields
        violation = ViolationIncident(
            hse_incident_id=incident.id,
            inc_number=data.get("inc_number"),
            violation_type=data.get("violation_type"),
            regulation_cited=data.get("regulation_cited"),
            penalty_amount=data.get("penalty_amount"),
            penalty_status=data.get("penalty_status"),
            compliance_deadline=data.get("compliance_deadline"),
            compliance_achieved=data.get("compliance_achieved"),
        )

        self.db_session.add(violation)
        self.db_session.commit()

        self.imported_count += 1
