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
from worldenergydata.common.data_resolver import get_module_data_safe
from worldenergydata.hse.database.models import Base, HSEIncident

logger = get_logger(__name__)

# Default database URL (SQLite)
DEFAULT_DB_URL = f"sqlite:///{get_module_data_safe('hse') / 'hse_incidents.db'}"

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

# Degree of injury mapping for accident_injury records.
# CSV data contains numeric codes (1, 2, 3) per OSHA data dictionary.
# Text variants included for robustness (e.g. if data format changes).
DEGREE_SEVERITY = {
    # Numeric codes (actual CSV values)
    "1": "fatality",
    "2": "lost_time",
    "3": "recordable",
    "0": "near_miss",
    # Text variants (from osha_accident_lookup2.csv DEGR codes)
    "Fatality": "fatality",
    "Hospitalized injury": "lost_time",
    "Non Hospitalized injury": "recordable",
    "Non-hospitalized injury": "recordable",
    "Amputation": "lost_time",
}


# Map CSV column names to lookup2 accident_code prefixes
INJURY_FIELD_LOOKUP_CODES = {
    "nature_of_inj": "IN",
    "part_of_body": "BD",
    "src_of_injury": "SO",
    "evn_factor": "EN",
    "hum_factor": "HU",
    "occ_code": "OCC",
    "degree_of_inj": "DEGR",
}

# Human-readable labels for description building
INJURY_FIELD_LABELS = {
    "nature_of_inj": "Nature",
    "part_of_body": "Body part",
    "src_of_injury": "Source",
    "event_type": "Event",
}


def _load_accident_lookups(
    lookup_path: Path,
) -> Dict[str, Dict[str, str]]:
    """Load osha_accident_lookup2.csv into nested dict {code: {number: value}}.

    Args:
        lookup_path: Path to osha_accident_lookup2.csv.

    Returns:
        Dict mapping accident_code -> {accident_number -> accident_value}.
    """
    if not lookup_path.exists():
        logger.warning("Lookup file not found: %s", lookup_path)
        return {}

    df = pd.read_csv(lookup_path, dtype=str, encoding="latin-1")
    col_map = {c: c.strip().strip('"').lower() for c in df.columns}
    df = df.rename(columns=col_map)

    lookups: Dict[str, Dict[str, str]] = {}
    for _, row in df.iterrows():
        code = (_safe_str(row.get("accident_code")) or "").strip('"')
        number = (_safe_str(row.get("accident_number")) or "").strip('"')
        value = (_safe_str(row.get("accident_value")) or "").strip('"')
        if code and number:
            if code not in lookups:
                lookups[code] = {}
            lookups[code][number] = value

    return lookups


def _decode_field(
    lookups: Dict[str, Dict[str, str]],
    field_name: str,
    raw_value: Optional[str],
) -> Optional[str]:
    """Decode a numeric field using lookup table.

    Returns decoded text if found, raw value if no lookup, None if empty.
    """
    if raw_value is None:
        return None
    code = INJURY_FIELD_LOOKUP_CODES.get(field_name)
    if code and code in lookups:
        decoded = lookups[code].get(raw_value)
        if decoded:
            return decoded
    return raw_value


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

        # Load accident lookup table for decoding numeric fields
        lookup_path = self.data_dir / "osha_accident_lookup2.csv"
        self._lookups = _load_accident_lookups(lookup_path)

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

        # Build description from injury detail fields (decoded via lookup table)
        desc_parts = []
        for field, label in INJURY_FIELD_LABELS.items():
            raw = _safe_str(row.get(field))
            if raw:
                decoded = _decode_field(self._lookups, field, raw)
                desc_parts.append(f"{label}: {decoded}")

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
