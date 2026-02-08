# ABOUTME: OSHA enforcement data importer for HSE incident database
# ABOUTME: Reads downloaded OSHA CSVs and maps to HSEIncident model schema

"""
OSHA Enforcement Data Importer

Reads OSHA inspection, violation, accident, and accident injury CSVs
(previously downloaded by OSHAAcquirer) and persists records to the
HSE incident database.

Column mappings:
    - activity_nr -> bsee_incident_id (prefixed with "OSHA-")
    - open_date -> incident_date
    - estab_name -> facility_name
    - site_state + site_city -> description location context
    - naics_code -> stored in description
    - Inspection type mapped to incident_type and severity

Usage:
    from worldenergydata.hse.importers.osha_importer import OSHAImporter

    importer = OSHAImporter(db_session=session, data_dir="data/modules/hse/raw/osha")
    stats = importer.import_data()

    # CLI
    uv run python -m worldenergydata.hse.importers.osha_importer \\
        --data-dir data/modules/hse/raw/osha
"""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from worldenergydata.common import get_logger
from worldenergydata.hse.database.models import Base, HSEIncident

logger = get_logger(__name__)

# Default database URL (SQLite)
DEFAULT_DB_URL = "sqlite:///data/modules/hse/hse_incidents.db"

# OSHA inspection type to severity mapping
INSPECTION_TYPE_SEVERITY = {
    "A": "fatality",  # Accident (fatality/catastrophe)
    "B": "recordable",  # Complaint
    "C": "minor",  # Referral
    "D": "minor",  # Monitoring
    "E": "minor",  # Variance
    "F": "near_miss",  # Follow-up
    "G": "minor",  # Unprogrammed related
    "H": "minor",  # Planned
    "I": "minor",  # Unprogrammed other
    "J": "recordable",  # Programmed related
    "K": "minor",  # Programmed other
    "L": "minor",  # Programmed
}

# OSHA violation type to incident_type mapping
VIOLATION_TYPE_MAP = {
    "S": "violation",  # Serious
    "W": "violation",  # Willful
    "R": "violation",  # Repeat
    "O": "violation",  # Other-than-serious
    "U": "violation",  # Unclassified
}

# Degree of injury mapping for accident_injury records
DEGREE_SEVERITY = {
    "Fatality": "fatality",
    "Hospitalized injury": "lost_time",
    "Amputation": "lost_time",
    "Non-hospitalized injury": "recordable",
}


def _safe_str(value: Any) -> Optional[str]:
    """Convert value to stripped string, returning None for NaN/empty."""
    if pd.isna(value):
        return None
    result = str(value).strip()
    return result if result else None


def _safe_float(value: Any) -> Optional[float]:
    """Convert value to float, returning None for non-numeric values."""
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _parse_date(value: Any) -> Optional[datetime]:
    """Parse date from various formats."""
    if pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    try:
        return pd.to_datetime(value).to_pydatetime()
    except (ValueError, TypeError):
        return None


class OSHAImporter:
    """
    Importer for OSHA enforcement data into HSE incident database.

    Reads CSV files downloaded by OSHAAcquirer and maps columns to the
    HSEIncident model. Handles inspections, violations, accidents, and
    accident injury records.

    Attributes:
        db_session: SQLAlchemy database session.
        data_dir: Path to directory containing OSHA CSV files.
    """

    def __init__(
        self,
        db_session: Session,
        data_dir: str,
        use_filtered: bool = True,
    ):
        """
        Initialize the OSHA importer.

        Args:
            db_session: SQLAlchemy database session for persistence.
            data_dir: Path to directory containing OSHA CSV files.
            use_filtered: If True, prefer filtered oil & gas CSVs when available.
        """
        self.db_session = db_session
        self.data_dir = Path(data_dir)
        self.use_filtered = use_filtered
        self.imported_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.validation_errors: List[str] = []

    def import_data(self) -> Dict[str, int]:
        """
        Execute full import pipeline for all OSHA datasets.

        Processes inspection, accident, and accident_injury CSVs
        (violations are linked to inspections, not imported separately
        as standalone incidents).

        Returns:
            Dictionary with import statistics:
            - imported_count: Records successfully imported
            - skipped_count: Duplicate records skipped
            - error_count: Records that failed validation
            - total_records: Total records processed
        """
        total_records = 0

        # Import inspections (primary dataset)
        inspection_path = self._resolve_path("osha_inspection")
        if inspection_path and inspection_path.exists():
            count = self._import_inspections(inspection_path)
            total_records += count
            logger.info("Processed %d inspection records", count)

        # Import accidents
        accident_path = self._resolve_path("osha_accident")
        if accident_path and accident_path.exists():
            count = self._import_accidents(accident_path)
            total_records += count
            logger.info("Processed %d accident records", count)

        # Import accident injuries
        injury_path = self._resolve_path("osha_accident_injury")
        if injury_path and injury_path.exists():
            count = self._import_accident_injuries(injury_path)
            total_records += count
            logger.info("Processed %d accident injury records", count)

        self.db_session.commit()

        logger.info(
            "OSHA import complete: %d imported, %d skipped, %d errors, %d total",
            self.imported_count,
            self.skipped_count,
            self.error_count,
            total_records,
        )

        return {
            "imported_count": self.imported_count,
            "skipped_count": self.skipped_count,
            "error_count": self.error_count,
            "total_records": total_records,
        }

    def _resolve_path(self, dataset_name: str) -> Optional[Path]:
        """
        Resolve the CSV path, preferring filtered version if available.

        Args:
            dataset_name: Base name of the dataset (e.g., 'osha_inspection').

        Returns:
            Path to the CSV file, or None if not found.
        """
        if self.use_filtered:
            filtered = self.data_dir / "filtered" / f"{dataset_name}_oil_gas.csv"
            if filtered.exists():
                logger.info("Using filtered dataset: %s", filtered)
                return filtered

        # Fallback to unfiltered
        unfiltered = self.data_dir / f"{dataset_name}.csv"
        if unfiltered.exists():
            return unfiltered

        logger.warning("Dataset not found: %s", dataset_name)
        return None

    def _import_inspections(self, path: Path) -> int:
        """
        Import OSHA inspection records.

        Maps inspection fields to HSEIncident:
        - activity_nr -> bsee_incident_id (prefixed "OSHA-INSP-")
        - open_date -> incident_date
        - estab_name -> facility_name
        - insp_type -> severity mapping
        - site_city, site_state -> description

        Args:
            path: Path to the inspection CSV file.

        Returns:
            Number of records processed.
        """
        logger.info("Importing inspections from %s", path)
        count = 0

        for chunk in pd.read_csv(
            path,
            dtype=str,
            chunksize=50_000,
            low_memory=False,
            encoding="latin-1",
        ):
            col_map = {c: c.lower() for c in chunk.columns}
            df = chunk.rename(columns=col_map)

            for _, row in df.iterrows():
                count += 1
                try:
                    normalized = self._normalize_inspection(row)
                except Exception as exc:
                    logger.debug("Inspection normalization error: %s", exc)
                    self.error_count += 1
                    continue

                if normalized is None:
                    self.error_count += 1
                    continue

                if self._is_duplicate(normalized["bsee_incident_id"]):
                    self.skipped_count += 1
                    continue

                self._persist(normalized)

            # Commit per chunk for memory efficiency
            self.db_session.commit()

        return count

    def _import_accidents(self, path: Path) -> int:
        """
        Import OSHA accident records.

        Maps accident fields to HSEIncident with incident_type='injury'.

        Args:
            path: Path to the accident CSV file.

        Returns:
            Number of records processed.
        """
        logger.info("Importing accidents from %s", path)
        count = 0

        for chunk in pd.read_csv(
            path,
            dtype=str,
            chunksize=50_000,
            low_memory=False,
            encoding="latin-1",
        ):
            col_map = {c: c.lower() for c in chunk.columns}
            df = chunk.rename(columns=col_map)

            for _, row in df.iterrows():
                count += 1
                try:
                    normalized = self._normalize_accident(row)
                except Exception as exc:
                    logger.debug("Accident normalization error: %s", exc)
                    self.error_count += 1
                    continue

                if normalized is None:
                    self.error_count += 1
                    continue

                if self._is_duplicate(normalized["bsee_incident_id"]):
                    self.skipped_count += 1
                    continue

                self._persist(normalized)

            self.db_session.commit()

        return count

    def _import_accident_injuries(self, path: Path) -> int:
        """
        Import OSHA accident injury records.

        Maps injury details to HSEIncident with appropriate severity.

        Args:
            path: Path to the accident_injury CSV file.

        Returns:
            Number of records processed.
        """
        logger.info("Importing accident injuries from %s", path)
        count = 0

        for chunk in pd.read_csv(
            path,
            dtype=str,
            chunksize=50_000,
            low_memory=False,
            encoding="latin-1",
        ):
            col_map = {c: c.lower() for c in chunk.columns}
            df = chunk.rename(columns=col_map)

            for _, row in df.iterrows():
                count += 1
                try:
                    normalized = self._normalize_accident_injury(row)
                except Exception as exc:
                    logger.debug("Injury normalization error: %s", exc)
                    self.error_count += 1
                    continue

                if normalized is None:
                    self.error_count += 1
                    continue

                if self._is_duplicate(normalized["bsee_incident_id"]):
                    self.skipped_count += 1
                    continue

                self._persist(normalized)

            self.db_session.commit()

        return count

    def _normalize_inspection(self, row: pd.Series) -> Optional[Dict[str, Any]]:
        """
        Normalize an OSHA inspection row to HSEIncident schema.

        Args:
            row: pandas Series with lowercase column names.

        Returns:
            Normalized dictionary, or None if required fields missing.
        """
        activity_nr = _safe_str(row.get("activity_nr"))
        if activity_nr is None:
            return None

        incident_id = f"OSHA-INSP-{activity_nr}"
        open_date = _parse_date(row.get("open_date"))
        if open_date is None:
            return None

        estab_name = _safe_str(row.get("estab_name"))
        if estab_name is None:
            estab_name = "Unknown Establishment"

        # Map inspection type to severity
        insp_type = _safe_str(row.get("insp_type")) or ""
        severity = INSPECTION_TYPE_SEVERITY.get(insp_type.upper(), "minor")

        # Build description from location and NAICS
        site_city = _safe_str(row.get("site_city")) or ""
        site_state = _safe_str(row.get("site_state")) or ""
        naics = _safe_str(row.get("naics_code")) or ""
        sic = _safe_str(row.get("sic_code")) or ""

        desc_parts = []
        if site_city or site_state:
            desc_parts.append(f"Location: {site_city}, {site_state}")
        if naics:
            desc_parts.append(f"NAICS: {naics}")
        if sic:
            desc_parts.append(f"SIC: {sic}")

        description = "; ".join(desc_parts) if desc_parts else None

        return {
            "bsee_incident_id": incident_id,
            "incident_date": open_date,
            "operator": estab_name,
            "facility_name": estab_name,
            "incident_type": "violation",
            "severity": severity,
            "description": description,
        }

    def _normalize_accident(self, row: pd.Series) -> Optional[Dict[str, Any]]:
        """
        Normalize an OSHA accident row to HSEIncident schema.

        Args:
            row: pandas Series with lowercase column names.

        Returns:
            Normalized dictionary, or None if required fields missing.
        """
        # Try summary_nr first, then activity_nr
        summary_nr = _safe_str(row.get("summary_nr"))
        if summary_nr is None:
            summary_nr = _safe_str(row.get("activity_nr"))
        if summary_nr is None:
            return None

        incident_id = f"OSHA-ACC-{summary_nr}"

        # Try various date columns
        event_date = _parse_date(row.get("event_date"))
        if event_date is None:
            event_date = _parse_date(row.get("open_date"))
        if event_date is None:
            return None

        estab_name = _safe_str(row.get("estab_name"))
        if estab_name is None:
            estab_name = "Unknown Establishment"

        # Build description
        desc_parts = []
        event_desc = _safe_str(row.get("event_desc"))
        if event_desc:
            desc_parts.append(event_desc)

        site_city = _safe_str(row.get("site_city")) or ""
        site_state = _safe_str(row.get("site_state")) or ""
        if site_city or site_state:
            desc_parts.append(f"Location: {site_city}, {site_state}")

        description = "; ".join(desc_parts) if desc_parts else None

        return {
            "bsee_incident_id": incident_id,
            "incident_date": event_date,
            "operator": estab_name,
            "facility_name": estab_name,
            "incident_type": "injury",
            "severity": "recordable",
            "description": description,
        }

    def _normalize_accident_injury(self, row: pd.Series) -> Optional[Dict[str, Any]]:
        """
        Normalize an OSHA accident injury row to HSEIncident schema.

        Args:
            row: pandas Series with lowercase column names.

        Returns:
            Normalized dictionary, or None if required fields missing.
        """
        rel_insp_nr = _safe_str(row.get("rel_insp_nr"))
        if rel_insp_nr is None:
            rel_insp_nr = _safe_str(row.get("summary_nr"))
        if rel_insp_nr is None:
            return None

        # Use a combination of inspection number and row index for uniqueness
        age = _safe_str(row.get("age")) or "0"
        sex = _safe_str(row.get("sex")) or "U"
        incident_id = f"OSHA-INJ-{rel_insp_nr}-{age}-{sex}"

        # Try event_date from related accident
        event_date = _parse_date(row.get("event_date"))
        if event_date is None:
            return None

        # Map degree of injury to severity
        degree = _safe_str(row.get("degree_of_inj")) or ""
        severity = DEGREE_SEVERITY.get(degree, "recordable")

        # Build description from injury nature
        desc_parts = []
        nature = _safe_str(row.get("nature_of_inj"))
        if nature:
            desc_parts.append(f"Nature: {nature}")
        body_part = _safe_str(row.get("part_of_body"))
        if body_part:
            desc_parts.append(f"Body part: {body_part}")
        event_type = _safe_str(row.get("event_type"))
        if event_type:
            desc_parts.append(f"Event: {event_type}")
        source = _safe_str(row.get("environ_factor"))
        if source:
            desc_parts.append(f"Environment: {source}")

        description = "; ".join(desc_parts) if desc_parts else None

        return {
            "bsee_incident_id": incident_id,
            "incident_date": event_date,
            "operator": "OSHA Accident Report",
            "facility_name": None,
            "incident_type": "injury",
            "severity": severity,
            "description": description,
        }

    def _is_duplicate(self, bsee_incident_id: str) -> bool:
        """
        Check if a record with this ID already exists.

        Args:
            bsee_incident_id: Unique incident identifier.

        Returns:
            True if the record already exists in the database.
        """
        existing = (
            self.db_session.query(HSEIncident.id)
            .filter(HSEIncident.bsee_incident_id == bsee_incident_id)
            .first()
        )
        return existing is not None

    def _persist(self, data: Dict[str, Any]) -> None:
        """
        Create an HSEIncident record and add to the session.

        Args:
            data: Validated, normalized data dictionary.
        """
        incident = HSEIncident(
            bsee_incident_id=data["bsee_incident_id"],
            incident_date=data["incident_date"],
            operator=data["operator"],
            facility_name=data.get("facility_name"),
            incident_type=data["incident_type"],
            severity=data["severity"],
            description=data.get("description"),
        )
        self.db_session.add(incident)
        self.imported_count += 1


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Import OSHA enforcement data into HSE database",
    )
    parser.add_argument(
        "--data-dir",
        required=True,
        help="Directory containing downloaded OSHA CSV files",
    )
    parser.add_argument(
        "--db-url",
        default=DEFAULT_DB_URL,
        help=f"Database URL (default: {DEFAULT_DB_URL})",
    )
    parser.add_argument(
        "--no-filtered",
        action="store_true",
        default=False,
        help="Use unfiltered CSVs instead of filtered oil & gas data",
    )
    return parser


def main(argv: Optional[list] = None) -> None:
    """CLI entry point for OSHA data import."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Set up database
    engine = create_engine(args.db_url, echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    try:
        importer = OSHAImporter(
            db_session=session,
            data_dir=args.data_dir,
            use_filtered=not args.no_filtered,
        )
        stats = importer.import_data()

        logger.info("Import statistics:")
        for key, value in stats.items():
            logger.info("  %s: %d", key, value)
    except Exception as exc:
        logger.error("Import failed: %s", exc)
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
