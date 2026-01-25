#!/usr/bin/env python
"""
Import USCG MISLE Data

Script to import bulk MISLE marine casualty data into the database.

Usage:
    python scripts/import_misle_data.py <misle_file.csv> [--limit N] [--preview]
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from worldenergydata.modules.marine_safety.database.models import Base
from worldenergydata.modules.marine_safety.importers.misle_importer import MISLEImporter


def main():
    """Main import function."""
    parser = argparse.ArgumentParser(description='Import USCG MISLE marine casualty data')
    parser.add_argument('misle_file', help='Path to MISLE CSV file')
    parser.add_argument('--limit', type=int, help='Limit number of records to import')
    parser.add_argument('--preview', action='store_true', help='Preview data without importing')
    parser.add_argument('--batch-size', type=int, default=100, help='Records per batch (default: 100)')
    parser.add_argument('--db', default='data/modules/marine_safety/database/marine_safety.db',
                       help='Database path')

    args = parser.parse_args()

    print("="*80)
    print("USCG MISLE DATA IMPORT")
    print("="*80)
    print()

    # Validate source file
    source_path = Path(args.misle_file)
    if not source_path.exists():
        print(f"❌ Error: File not found: {source_path}")
        return 1

    print(f"Source file: {source_path}")
    print(f"File size: {source_path.stat().st_size:,} bytes")
    print()

    # Setup database
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{db_path}"

    print(f"Database: {db_path}")
    print()

    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)

    session = Session(engine)

    try:
        # Create importer
        importer = MISLEImporter(
            source_path=source_path,
            session=session,
            batch_size=args.batch_size,
            file_format='csv'
        )

        # Preview mode
        if args.preview:
            print("PREVIEW MODE - First 10 records")
            print("-"*80)

            previews = importer.preview_data(num_records=10)

            for idx, record in enumerate(previews, 1):
                print(f"\nRecord {idx}:")
                print(f"  Incident ID: {record.get('source_incident_id')}")
                print(f"  Date: {record.get('incident_date')}")
                print(f"  Type: {record.get('incident_type')}")
                print(f"  Location: ({record.get('latitude')}, {record.get('longitude')})")
                print(f"  Casualties: {record.get('fatalities', 0)} fatalities, "
                      f"{record.get('injuries', 0)} injuries")
                print(f"  Vessel: {record.get('vessel_name', 'N/A')}")

            print()
            print("="*80)
            print(f"✅ Preview complete - {len(previews)} records shown")
            print()
            print("To import data, run without --preview flag")
            return 0

        # Import mode
        print("IMPORT MODE")
        print("-"*80)

        if args.limit:
            print(f"Limit: {args.limit} records")
        else:
            print("Limit: None (importing all records)")

        print(f"Batch size: {args.batch_size}")
        print()
        print("Starting import...")
        print()

        # Run import
        stats = importer.import_data(limit=args.limit, skip_duplicates=True)

        # Display results
        print()
        print("="*80)
        print("IMPORT COMPLETE")
        print("="*80)
        print()
        print("Statistics:")
        print(f"  Total records processed: {stats['total_records']:,}")
        print(f"  Successfully imported: {stats['imported']:,}")
        print(f"  Skipped (invalid): {stats['skipped']:,}")
        print(f"  Duplicates: {stats['duplicates']:,}")
        print(f"  Errors: {stats['errors']:,}")
        print()

        # Calculate success rate
        if stats['total_records'] > 0:
            success_rate = (stats['imported'] / stats['total_records']) * 100
            print(f"Success rate: {success_rate:.1f}%")
            print()

        # Show database counts
        from worldenergydata.modules.marine_safety.database.models import (
            Incident, Location, Vessel
        )

        total_incidents = session.query(Incident).count()
        total_locations = session.query(Location).count()
        total_vessels = session.query(Vessel).count()

        print("Database totals:")
        print(f"  Incidents: {total_incidents:,}")
        print(f"  Locations: {total_locations:,}")
        print(f"  Vessels: {total_vessels:,}")
        print()

        print(f"Database: {db_path}")
        print()

        return 0

    except Exception as e:
        print()
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        session.close()


if __name__ == '__main__':
    sys.exit(main())
