#!/usr/bin/env python3
"""
Import NOAA Office of Response and Restoration (OR&R) incident data.

This script imports oil spill and chemical release data from NOAA's Emergency
Response Division incident archive.

Usage:
    python scripts/import_noaa_data.py <incidents_csv> [options]

    Options:
        --limit N              Import only first N records
        --preview              Preview first 10 records without importing
        --batch-size N         Records per batch (default: 500)
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
from worldenergydata.modules.marine_safety.importers.noaa_importer import NOAAImporter


def preview_data(importer: NOAAImporter, num_records: int = 10):
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
        print(f"NOAA ID: {record.get('source_incident_id')}")
        print(f"Date: {record.get('incident_date')}")
        print(f"Type: {record.get('incident_type')}")
        print(f"Title: {record.get('title', 'N/A')}")

        if record.get('estimated_damage_usd'):
            print(f"Est. Damage: ${record.get('estimated_damage_usd'):,.2f}")

        if 'location' in record:
            loc = record['location']
            print(f"Location: {loc.get('location_name', 'Unknown')}")
            if 'latitude' in loc and 'longitude' in loc:
                print(f"  Coords: {loc['latitude']:.4f}, {loc['longitude']:.4f}")

        if 'metadata_json' in record:
            metadata = record['metadata_json']
            if 'commodity' in metadata:
                print(f"Commodity: {metadata['commodity']}")
            if 'response_measures' in metadata:
                print(f"Response: {', '.join(metadata['response_measures'])}")
            if 'max_potential_release_gallons' in metadata:
                print(f"Max Release: {metadata['max_potential_release_gallons']:,.0f} gallons")

    print(f"\n{'=' * 80}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Import NOAA Office of Response and Restoration (OR&R) incident data'
    )
    parser.add_argument(
        'incidents_file',
        help='Path to incidents.csv file'
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
        default=500,
        help='Number of records per batch (default: 500)'
    )
    parser.add_argument(
        '--db',
        default='data/modules/marine_safety/database/marine_safety.db',
        help='Database path (default: data/modules/marine_safety/database/marine_safety.db)'
    )

    args = parser.parse_args()

    # Validate file
    incidents_path = Path(args.incidents_file)
    if not incidents_path.exists():
        print(f"Error: Incidents file not found: {incidents_path}")
        sys.exit(1)

    # Setup database
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f'sqlite:///{db_path}')

    # Create tables
    Base.metadata.create_all(engine)

    # Create session
    session = Session(engine)

    # Create importer
    importer = NOAAImporter(
        source_path=incidents_path,
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
            print("IMPORTING NOAA OR&R INCIDENT DATA")
            print('=' * 80)
            print(f"\nIncidents file: {incidents_path}")
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
            from worldenergydata.modules.marine_safety.database.models import Incident, Location

            total_incidents = session.query(func.count(Incident.incident_id)).scalar()
            total_locations = session.query(func.count(Location.location_id)).scalar()

            print(f"\nDatabase totals:")
            print(f"  Incidents: {total_incidents}")
            print(f"  Locations: {total_locations}")
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
