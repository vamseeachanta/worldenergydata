# ABOUTME: Bridge script to import BSEE incident investigation and INC data into HSE database
# ABOUTME: Connects file-based importers (load() -> List[Dict]) with SQLAlchemy DB persistence

"""
BSEE HSE Database Import Script

Bridges the file-based importers (BSEEIncInvImporter, BSEEINCSImporter) with the
SQLAlchemy database persistence layer.

The file-based importers produce normalized List[Dict] records via load(), but do
not persist to the database. This script:
1. Creates the database and tables if absent
2. Loads records from both importers
3. Validates each record (required fields, enum values, date types)
4. Persists valid, non-duplicate records as HSEIncident rows
5. For INC violation records, also creates ViolationIncident child records
6. Reports import statistics and date ranges

Usage:
    cd worldenergydata
    PYTHONPATH="src:../assetutilities/src" python3 scripts/import_bsee_hse_to_db.py

    # Dry run (validate only, no DB writes):
    PYTHONPATH="src:../assetutilities/src" python3 scripts/import_bsee_hse_to_db.py --dry-run

    # Summary only (show what's already in DB):
    PYTHONPATH="src:../assetutilities/src" python3 scripts/import_bsee_hse_to_db.py --summary
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add src to path if needed
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from worldenergydata.hse.database.models import (
    Base,
    HSEIncident,
    ViolationIncident,
)
from worldenergydata.hse.importers.bsee_incinv_importer import BSEEIncInvImporter
from worldenergydata.hse.importers.bsee_incs_importer import BSEEINCSImporter

# Default paths relative to project root
DEFAULT_DATA_DIR = "data/modules/hse/raw/bsee"
DEFAULT_DB_PATH = "data/modules/hse/hse_incidents.db"

# Batch size for periodic commits
BATCH_SIZE = 1000

# Valid enum values (must match BaseImporter and models.py)
VALID_INCIDENT_TYPES = {"injury", "spill", "equipment_failure", "violation"}
VALID_SEVERITY_LEVELS = {"fatality", "lost_time", "recordable", "near_miss", "minor"}


def create_db_session(db_path: str) -> Session:
    """
    Create SQLAlchemy engine and session for the HSE database.

    Creates all tables if they do not exist.

    Args:
        db_path: Path to SQLite database file.

    Returns:
        SQLAlchemy Session instance.
    """
    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"timeout": 30},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return session_factory()


def validate_record(record: Dict[str, Any]) -> Optional[str]:
    """
    Validate a normalized record has required fields and valid enum values.

    Args:
        record: Normalized record dictionary.

    Returns:
        Error message string if invalid, None if valid.
    """
    if not isinstance(record, dict) or not record:
        return "Record is not a non-empty dictionary"

    required = ["bsee_incident_id", "incident_date", "operator", "incident_type", "severity"]
    for field in required:
        if field not in record or record[field] is None:
            return f"Missing required field: {field}"

    if record["incident_type"] not in VALID_INCIDENT_TYPES:
        return f"Invalid incident_type: {record['incident_type']}"

    if record["severity"] not in VALID_SEVERITY_LEVELS:
        return f"Invalid severity: {record['severity']}"

    if not isinstance(record["incident_date"], datetime):
        return f"incident_date must be datetime, got {type(record['incident_date']).__name__}"

    return None


def load_existing_ids(session: Session) -> Set[str]:
    """
    Load all existing bsee_incident_id values from the database.

    Pre-loading into a set is much faster than per-record DB queries,
    especially for 66K+ INC records.

    Args:
        session: SQLAlchemy database session.

    Returns:
        Set of existing bsee_incident_id strings.
    """
    rows = session.query(HSEIncident.bsee_incident_id).all()
    return {r[0] for r in rows}


def import_incinv_records(
    session: Session,
    records: List[Dict[str, Any]],
    existing_ids: Set[str],
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Import incident investigation records into the database.

    Args:
        session: SQLAlchemy database session.
        records: Normalized records from BSEEIncInvImporter.load().
        existing_ids: Set of bsee_incident_id values already in DB.
        dry_run: If True, validate only without writing to DB.

    Returns:
        Dictionary with import statistics.
    """
    stats = {
        "total": len(records),
        "imported": 0,
        "skipped_duplicate": 0,
        "validation_errors": 0,
        "error_details": [],
    }

    for i, record in enumerate(records):
        # Validate
        error = validate_record(record)
        if error:
            stats["validation_errors"] += 1
            if len(stats["error_details"]) < 10:
                stats["error_details"].append(f"Row {i}: {error}")
            continue

        # Check duplicate
        if record["bsee_incident_id"] in existing_ids:
            stats["skipped_duplicate"] += 1
            continue

        if not dry_run:
            incident = HSEIncident(
                bsee_incident_id=record["bsee_incident_id"],
                incident_date=record["incident_date"],
                operator=record["operator"],
                lease_number=record.get("lease_number"),
                block_number=record.get("block_number"),
                incident_type=record["incident_type"],
                severity=record["severity"],
                description=record.get("description"),
                investigation_status=record.get("investigation_status"),
            )
            session.add(incident)
            existing_ids.add(record["bsee_incident_id"])

            # Periodic commit
            if (stats["imported"] + 1) % BATCH_SIZE == 0:
                session.commit()
                print(
                    f"  ... committed {stats['imported'] + 1} incident "
                    f"investigation records"
                )

        stats["imported"] += 1

    if not dry_run:
        session.commit()

    return stats


def import_incs_records(
    session: Session,
    records: List[Dict[str, Any]],
    existing_ids: Set[str],
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Import INC (Incidents of Non-Compliance) records into the database.

    Each INC record creates an HSEIncident (type=violation) and a
    ViolationIncident child record with violation-specific fields.

    Args:
        session: SQLAlchemy database session.
        records: Normalized records from BSEEINCSImporter.load().
        existing_ids: Set of bsee_incident_id values already in DB.
        dry_run: If True, validate only without writing to DB.

    Returns:
        Dictionary with import statistics.
    """
    stats = {
        "total": len(records),
        "imported": 0,
        "skipped_duplicate": 0,
        "validation_errors": 0,
        "violation_records": 0,
        "error_details": [],
    }

    for i, record in enumerate(records):
        # Validate
        error = validate_record(record)
        if error:
            stats["validation_errors"] += 1
            if len(stats["error_details"]) < 10:
                stats["error_details"].append(f"Row {i}: {error}")
            continue

        # Check duplicate
        if record["bsee_incident_id"] in existing_ids:
            stats["skipped_duplicate"] += 1
            continue

        if not dry_run:
            incident = HSEIncident(
                bsee_incident_id=record["bsee_incident_id"],
                incident_date=record["incident_date"],
                operator=record["operator"],
                incident_type=record["incident_type"],
                severity=record["severity"],
                description=record.get("description"),
            )
            session.add(incident)
            session.flush()  # Get the incident ID for FK

            violation = ViolationIncident(
                hse_incident_id=incident.id,
                inc_number=record.get("inc_number"),
                violation_type=record.get("violation_type"),
            )
            session.add(violation)
            existing_ids.add(record["bsee_incident_id"])
            stats["violation_records"] += 1

            # Periodic commit
            if (stats["imported"] + 1) % BATCH_SIZE == 0:
                session.commit()
                print(f"  ... committed {stats['imported'] + 1} INC records")

        else:
            stats["violation_records"] += 1

        stats["imported"] += 1

    if not dry_run:
        session.commit()

    return stats


def print_db_summary(session: Session) -> None:
    """Print current database record counts and date ranges."""
    print("\n=== Database Summary ===")

    total = session.query(HSEIncident).count()
    print(f"HSE Incidents total: {total}")

    if total > 0:
        for itype in ["injury", "spill", "equipment_failure", "violation"]:
            count = (
                session.query(HSEIncident)
                .filter(HSEIncident.incident_type == itype)
                .count()
            )
            if count > 0:
                print(f"  {itype}: {count}")

        min_date = session.query(
            HSEIncident.incident_date
        ).order_by(HSEIncident.incident_date.asc()).first()
        max_date = session.query(
            HSEIncident.incident_date
        ).order_by(HSEIncident.incident_date.desc()).first()
        if min_date and max_date:
            print(f"  Date range: {min_date[0]} to {max_date[0]}")

        incinv_count = (
            session.query(HSEIncident)
            .filter(HSEIncident.bsee_incident_id.like("INCINV-%"))
            .count()
        )
        inc_count = (
            session.query(HSEIncident)
            .filter(HSEIncident.bsee_incident_id.like("INC-%"))
            .count()
        )
        print(f"  Incident investigations (INCINV-*): {incinv_count}")
        print(f"  Incidents of Non-Compliance (INC-*): {inc_count}")

    violation_count = session.query(ViolationIncident).count()
    print(f"Violation Incidents (child records): {violation_count}")
    print("")


def main() -> None:
    """Main entry point for BSEE HSE database import."""
    parser = argparse.ArgumentParser(
        description="Import BSEE incident investigation and INC data into HSE database",
    )
    parser.add_argument(
        "--data-dir",
        default=DEFAULT_DATA_DIR,
        help=f"BSEE raw data directory (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--db-path",
        default=DEFAULT_DB_PATH,
        help=f"SQLite database path (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate records without writing to database",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show current database contents and exit",
    )
    parser.add_argument(
        "--skip-incinv",
        action="store_true",
        help="Skip incident investigation import",
    )
    parser.add_argument(
        "--skip-incs",
        action="store_true",
        help="Skip INCs import",
    )
    args = parser.parse_args()

    print("=== BSEE HSE Database Import ===")
    print(f"Data directory: {args.data_dir}")
    print(f"Database: {args.db_path}")
    if args.dry_run:
        print("MODE: Dry run (no database writes)")
    print(f"Started: {datetime.now().isoformat()}")
    print("")

    session = create_db_session(args.db_path)

    if args.summary:
        print_db_summary(session)
        session.close()
        return

    # Pre-load existing IDs for fast duplicate checking
    existing_ids = load_existing_ids(session)
    print(f"Existing records in DB: {len(existing_ids)}")
    print("")

    # Phase 1: Import incident investigations
    if not args.skip_incinv:
        print("--- Phase 1: Incident Investigations ---")
        t0 = time.time()
        incinv_importer = BSEEIncInvImporter(data_dir=args.data_dir)
        incinv_records = incinv_importer.load()
        print(f"Loaded {len(incinv_records)} incident investigation records")

        incinv_stats = import_incinv_records(
            session, incinv_records, existing_ids, dry_run=args.dry_run
        )
        elapsed = time.time() - t0
        print(f"Results ({elapsed:.1f}s):")
        print(f"  Imported: {incinv_stats['imported']}")
        print(f"  Skipped (duplicate): {incinv_stats['skipped_duplicate']}")
        print(f"  Validation errors: {incinv_stats['validation_errors']}")
        if incinv_stats["error_details"]:
            print("  Error samples:")
            for err in incinv_stats["error_details"]:
                print(f"    {err}")

        if incinv_records:
            dates = [
                r["incident_date"]
                for r in incinv_records
                if r.get("incident_date")
            ]
            if dates:
                print(f"  Date range: {min(dates)} to {max(dates)}")
        print("")

    # Phase 2: Import INCs
    if not args.skip_incs:
        print("--- Phase 2: Incidents of Non-Compliance (INCs) ---")
        t0 = time.time()
        incs_importer = BSEEINCSImporter(data_dir=args.data_dir)
        incs_records = incs_importer.load()
        print(f"Loaded {len(incs_records)} INC violation records")

        incs_stats = import_incs_records(
            session, incs_records, existing_ids, dry_run=args.dry_run
        )
        elapsed = time.time() - t0
        print(f"Results ({elapsed:.1f}s):")
        print(f"  Imported: {incs_stats['imported']}")
        print(f"  Violation child records: {incs_stats['violation_records']}")
        print(f"  Skipped (duplicate): {incs_stats['skipped_duplicate']}")
        print(f"  Validation errors: {incs_stats['validation_errors']}")
        if incs_stats["error_details"]:
            print("  Error samples:")
            for err in incs_stats["error_details"]:
                print(f"    {err}")

        if incs_records:
            dates = [
                r["incident_date"]
                for r in incs_records
                if r.get("incident_date")
            ]
            if dates:
                print(f"  Date range: {min(dates)} to {max(dates)}")
        print("")

    # Print final database summary
    print_db_summary(session)

    session.close()
    print(f"Finished: {datetime.now().isoformat()}")
    print("=== Import complete ===")


if __name__ == "__main__":
    main()
