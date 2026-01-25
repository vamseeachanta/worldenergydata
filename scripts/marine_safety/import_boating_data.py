#!/usr/bin/env python3
"""
Import USCG Boating Accident Report Database (BARD) data.

This script imports recreational boating accident data from the Data Liberation
Project's converted CSV files (1995-2012 USCG BARD data).

Usage:
    python scripts/import_boating_data.py <accidents_csv> [options]

    Options:
        --vessels <file>       Path to Vessels.csv
        --deaths <file>        Path to Deaths.csv
        --injuries <file>      Path to Injuries.csv
        --limit N              Import only first N records
        --preview              Preview first 10 records without importing
        --batch-size N         Records per batch (default: 100)
        --db <path>            Database path (default: data/modules/marine_safety/database/marine_safety.db)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from worldenergydata.modules.marine_safety.database.models import Base
from worldenergydata.modules.marine_safety.importers.boating_importer import BoatingImporter


def preview_data(importer: BoatingImporter, num_records: int = 10):
    """Preview first N records without importing."""
    print(f"\n{'=' * 80}")
    print(f"PREVIEW: First {num_records} records")
    print('=' * 80)

    previews = []
    for i, record in enumerate(importer.read_source()):
        if i >= num_records:
            break

        parsed = importer.parse_record(record)
        if parsed:
            previews.append(parsed)

    for i, record in enumerate(previews, 1):
        print(f"\n--- Record {i} ---")
        print(f"BARD ID: {record.get('source_incident_id')}")
        print(f"Date: {record.get('incident_date')}")
        print(f"Type: {record.get('incident_type')}")
        print(f"Fatalities: {record.get('fatalities', 0)}")
        print(f"Injuries: {record.get('injuries', 0)}")
        print(f"Damage: ${record.get('estimated_damage_usd', 0):,.2f}" if record.get('estimated_damage_usd') else "Damage: N/A")

        if 'location' in record:
            loc = record['location']
            print(f"Location: {loc.get('city', 'Unknown')}, {loc.get('state_code', 'Unknown')}")

        if 'vessel' in record:
            vessel = record['vessel']
            print(f"Vessel: {vessel.get('vessel_name', 'Unknown')} ({vessel.get('vessel_type', 'unknown')})")

    print(f"\n{'=' * 80}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Import USCG Boating Accident Report Database (BARD) data'
    )
    parser.add_argument(
        'accidents_file',
        help='Path to Accidents.csv file'
    )
    parser.add_argument(
        '--vessels',
        help='Path to Vessels.csv file'
    )
    parser.add_argument(
        '--deaths',
        help='Path to Deaths.csv file'
    )
    parser.add_argument(
        '--injuries',
        help='Path to Injuries.csv file'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of records to import'
    )
    parser.add_argument(
        '--preview',
        action='store_true',
        help='Preview data without importing'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of records per batch (default: 100)'
    )
    parser.add_argument(
        '--db',
        default='data/modules/marine_safety/database/marine_safety.db',
        help='Database path (default: data/modules/marine_safety/database/marine_safety.db)'
    )

    args = parser.parse_args()

    # Validate files
    accidents_path = Path(args.accidents_file)
    if not accidents_path.exists():
        print(f"Error: Accidents file not found: {accidents_path}")
        sys.exit(1)

    vessels_path = Path(args.vessels) if args.vessels else None
    deaths_path = Path(args.deaths) if args.deaths else None
    injuries_path = Path(args.injuries) if args.injuries else None

    # Setup database
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f'sqlite:///{db_path}')

    # Create tables
    Base.metadata.create_all(engine)

    # Create session
    session = Session(engine)

    # Create importer
    importer = BoatingImporter(
        accidents_file=accidents_path,
        vessels_file=vessels_path,
        deaths_file=deaths_path,
        injuries_file=injuries_path,
        session=session,
        batch_size=args.batch_size
    )

    try:
        if args.preview:
            # Preview mode
            preview_data(importer, num_records=10)
        else:
            # Import mode
            print(f"\n{'=' * 80}")
            print("IMPORTING BOATING ACCIDENT DATA")
            print('=' * 80)
            print(f"\nAccidents file: {accidents_path}")
            if vessels_path:
                print(f"Vessels file: {vessels_path}")
            if deaths_path:
                print(f"Deaths file: {deaths_path}")
            if injuries_path:
                print(f"Injuries file: {injuries_path}")
            print(f"Database: {db_path}")
            print(f"Batch size: {args.batch_size}")
            if args.limit:
                print(f"Limit: {args.limit} records")
            print()

            # Import data
            stats = importer.import_data(
                limit=args.limit,
                skip_duplicates=True
            )

            # Print results
            print(f"\n{'=' * 80}")
            print("IMPORT COMPLETE")
            print('=' * 80)
            print(f"\nStatistics:")
            print(f"  Total records processed: {stats['total_records']}")
            print(f"  Successfully imported: {stats['imported']}")
            print(f"  Skipped (invalid): {stats['skipped']}")
            print(f"  Duplicates: {stats['duplicates']}")
            print(f"  Errors: {stats['errors']}")
            print(f"\nSuccess rate: {stats['imported'] / stats['total_records'] * 100:.1f}%")

            # Database totals
            from sqlalchemy import func
            from worldenergydata.modules.marine_safety.database.models import Incident, Location, Vessel

            total_incidents = session.query(func.count(Incident.incident_id)).scalar()
            total_locations = session.query(func.count(Location.location_id)).scalar()
            total_vessels = session.query(func.count(Vessel.vessel_id)).scalar()

            print(f"\nDatabase totals:")
            print(f"  Incidents: {total_incidents}")
            print(f"  Locations: {total_locations}")
            print(f"  Vessels: {total_vessels}")
            print()

    except KeyboardInterrupt:
        print("\n\nImport interrupted by user")
        session.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError during import: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        sys.exit(1)
    finally:
        session.close()


if __name__ == '__main__':
    main()
