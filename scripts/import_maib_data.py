#!/usr/bin/env python3
"""
Import UK MAIB Marine Occurrence Data

This script imports marine incident data from the UK Marine Accident Investigation Branch (MAIB).

Usage:
    python scripts/import_maib_data.py \\
        data/modules/marine_safety/raw/uk_maib/maib_occurrences.csv \\
        --vessels data/modules/marine_safety/raw/uk_maib/maib_vessels.csv \\
        --persons data/modules/marine_safety/raw/uk_maib/maib_affected_persons.csv \\
        --batch-size 1000 \\
        --limit 1000

Arguments:
    occurrences_file: Path to maib_occurrences.csv file
    --vessels: Path to maib_vessels.csv file (optional)
    --persons: Path to maib_affected_persons.csv file (optional)
    --batch-size: Number of records to process per batch (default: 1000)
    --limit: Maximum number of records to import (default: None - all records)
    --preview: Preview first N records without importing (default: 5)
    --db: Database URL (default: from environment or sqlite)
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from worldenergydata.modules.marine_safety.importers.maib_importer import MAIBImporter
from worldenergydata.modules.marine_safety.database.models import Base, Incident
from worldenergydata.modules.marine_safety.database.db_manager import DatabaseManager


def preview_data(occurrences_file: Path, vessels_file: Path = None, num_records: int = 5):
    """Preview data without importing."""
    print(f"\n{'='*80}")
    print(f"PREVIEW MODE - First {num_records} records from {occurrences_file}")
    print(f"{'='*80}\n")

    # Use SQLite for preview - simpler approach
    import os
    import tempfile
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)

    # Use simpler approach - direct SQLAlchemy engine
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(f'sqlite:///{temp_db.name}')
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()

    try:
        importer = MAIBImporter(
            occurrences_file=occurrences_file,
            vessels_file=vessels_file,
            session=session,
            batch_size=10
        )

        count = 0
        for raw_record in importer.read_source():
            parsed = importer.parse_record(raw_record)
            if parsed:
                print(f"\nRecord {count + 1}:")
                print(f"  Source ID: {parsed.get('source_incident_id')}")
                print(f"  Date: {parsed.get('incident_date')}")
                print(f"  Type: {parsed.get('incident_type')}")
                print(f"  Casualties: {parsed.get('fatalities')} deaths, {parsed.get('injuries')} injuries")
                print(f"  Description: {parsed.get('description', '')[:100]}...")

                if 'location' in parsed:
                    loc = parsed['location']
                    print(f"  Location: {loc.get('coastal_state', 'Unknown')}")
                    if loc.get('latitude') and loc.get('longitude'):
                        print(f"    Coordinates: {loc['latitude']:.4f}, {loc['longitude']:.4f}")

                if 'vessel' in parsed:
                    ves = parsed['vessel']
                    print(f"  Vessel Type: {ves.get('ship_type_l1', 'Unknown')}")
                    print(f"  Flag: {ves.get('flag_state', 'Unknown')}")

                count += 1
                if count >= num_records:
                    break

        print(f"\n{'='*80}")
        print(f"Preview complete - {count} records shown")
        print(f"{'='*80}\n")

    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description='Import UK MAIB marine occurrence data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        'occurrences_file',
        type=Path,
        help='Path to maib_occurrences.csv file'
    )
    parser.add_argument(
        '--vessels',
        type=Path,
        help='Path to maib_vessels.csv file'
    )
    parser.add_argument(
        '--persons',
        type=Path,
        help='Path to maib_affected_persons.csv file'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Number of records per batch (default: 1000)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum records to import (default: all)'
    )
    parser.add_argument(
        '--preview',
        type=int,
        nargs='?',
        const=5,
        help='Preview N records without importing (default: 5)'
    )
    parser.add_argument(
        '--db',
        type=str,
        help='Database URL (default: from environment)'
    )

    args = parser.parse_args()

    # Validate files
    if not args.occurrences_file.exists():
        print(f"Error: Occurrences file not found: {args.occurrences_file}")
        sys.exit(1)

    if args.vessels and not args.vessels.exists():
        print(f"Error: Vessels file not found: {args.vessels}")
        sys.exit(1)

    if args.persons and not args.persons.exists():
        print(f"Error: Persons file not found: {args.persons}")
        sys.exit(1)

    # Preview mode
    if args.preview is not None:
        preview_data(args.occurrences_file, args.vessels, args.preview)
        return

    # Setup database
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    if args.db:
        db_url = args.db
    else:
        # Default to SQLite
        db_url = 'sqlite:///data/modules/marine_safety/marine_safety.db'

    print(f"Database: {db_url}\n")

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()

    try:
        print(f"\n{'='*80}")
        print("UK MAIB MARINE OCCURRENCE IMPORT")
        print(f"{'='*80}")
        print(f"\nSource file: {args.occurrences_file}")
        if args.vessels:
            print(f"Vessels file: {args.vessels}")
        if args.persons:
            print(f"Persons file: {args.persons}")
        print(f"Batch size: {args.batch_size}")
        if args.limit:
            print(f"Limit: {args.limit} records")
        print()

        # Create importer
        importer = MAIBImporter(
            occurrences_file=args.occurrences_file,
            vessels_file=args.vessels,
            persons_file=args.persons,
            session=session,
            batch_size=args.batch_size
        )

        # Import data
        print("Starting import...")
        stats = importer.import_data(limit=args.limit)

        # Print results
        print(f"\n{'='*80}")
        print("IMPORT COMPLETE")
        print(f"{'='*80}")
        print(f"Total records processed: {stats['total_records']:,}")
        print(f"Successfully imported: {stats['imported']:,}")
        print(f"Duplicates skipped: {stats['duplicates']:,}")
        print(f"Records skipped: {stats['skipped']:,}")
        print(f"Errors: {stats['errors']:,}")
        print(f"\nSuccess rate: {(stats['imported'] / stats['total_records'] * 100):.1f}%")
        print(f"{'='*80}\n")

        # Print database stats
        total_incidents = session.query(Incident).count()
        maib_incidents = session.query(Incident).filter(
            Incident.source_agency == 'MAIB_UK'
        ).count()
        print(f"Total incidents in database: {total_incidents:,}")
        print(f"MAIB incidents: {maib_incidents:,}")
        print()

    except Exception as e:
        print(f"\nError during import: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == '__main__':
    main()
