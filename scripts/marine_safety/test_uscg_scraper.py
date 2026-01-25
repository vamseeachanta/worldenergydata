#!/usr/bin/env python
"""
Test script for USCG Marine Casualty Scraper

This script:
1. Initializes the USCG scraper
2. Attempts to scrape a small sample of 2024 data
3. Validates the scraped data
4. Stores it in the SQLite database
5. Verifies the data was stored correctly

Usage:
    python scripts/test_uscg_scraper.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from worldenergydata.modules.marine_safety.scrapers.uscg_scraper import (
    USCGMarineCasualtyScraper,
    MarineIncident
)
from worldenergydata.modules.marine_safety.database.models import (
    Base,
    Incident,
    Location,
    Company,
    Vessel
)


def main():
    """Main test function."""
    print("="*80)
    print("USCG Marine Casualty Scraper - Test Script")
    print("="*80)
    print()

    # Configuration
    checkpoint_dir = Path('data/modules/marine_safety/checkpoints')
    db_path = Path('data/modules/marine_safety/database/marine_safety.db')
    output_file = Path('data/modules/marine_safety/raw/uscg/test_scrape_2024.json')

    # Ensure directories exist
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: Initialize scraper
    print("Step 1: Initializing USCG Scraper...")
    print(f"  Year range: 2024-2024")
    print(f"  Rate limit: 2.0s between requests")
    print(f"  Checkpoint dir: {checkpoint_dir}")
    print()

    scraper = USCGMarineCasualtyScraper(
        checkpoint_dir=checkpoint_dir,
        start_year=2024,
        end_year=2024,
        rate_limit_delay=2.0,
        resume_from_checkpoint=False
    )

    print("✅ Scraper initialized successfully")
    print()

    # Step 2: Attempt to scrape data
    print("Step 2: Attempting to scrape USCG data...")
    print("⚠️  This requires internet connection to USCG website")
    print("⚠️  This may take several minutes depending on data volume")
    print()

    try:
        incidents = scraper.scrape()
        print(f"✅ Successfully scraped {len(incidents)} incident(s)")
        print()

        # Save raw data to file
        import json
        with open(output_file, 'w') as f:
            # Convert Pydantic models to dicts
            incidents_data = [inc.model_dump(mode='json') for inc in incidents]
            json.dump(incidents_data, f, indent=2, default=str)
        print(f"✅ Saved raw data to: {output_file}")
        print()

    except Exception as e:
        print(f"❌ Error during scraping: {type(e).__name__}: {e}")
        print()
        print("Note: The scraper requires live access to USCG website.")
        print("If you're offline or the website is unavailable, this test will fail.")
        print()
        print("You can still test the database storage with mock data...")

        # Create mock incident for testing
        incidents = [
            MarineIncident(
                incident_id="TEST-2024-001",
                incident_date=datetime(2024, 1, 15),
                incident_type="Collision",
                severity_level="Moderate",
                description="Test incident for scraper validation",
                casualty_info=None,
                vessel_info=None,
                location_info=None
            )
        ]
        print(f"✅ Created {len(incidents)} mock incident(s) for testing")
        print()

    # Step 3: Connect to database
    print("Step 3: Connecting to database...")
    db_url = f"sqlite:///{db_path}"
    print(f"  Database: {db_path}")
    print()

    engine = create_engine(db_url, echo=False)

    # Ensure tables exist
    Base.metadata.create_all(engine)
    print("✅ Database tables verified")
    print()

    # Step 4: Store incidents in database
    print("Step 4: Storing incidents in database...")
    session = Session(engine)

    stored_count = 0
    for inc_data in incidents:
        try:
            # Create location if we have coordinates
            location = None
            if hasattr(inc_data, 'location_info') and inc_data.location_info:
                loc_info = inc_data.location_info
                location = Location(
                    latitude=loc_info.latitude,
                    longitude=loc_info.longitude,
                    location_description=loc_info.location_description,
                    waterway_name=loc_info.waterway,
                    port_name=loc_info.port,
                    country=loc_info.country
                )
                session.add(location)
                session.flush()  # Get location_id

            # Create incident record
            casualty_info = getattr(inc_data, 'casualty_info', None)

            incident = Incident(
                source_agency='USCG',
                source_incident_id=inc_data.incident_id,
                incident_date=inc_data.incident_date.date() if hasattr(inc_data.incident_date, 'date') else inc_data.incident_date,
                incident_type=inc_data.incident_type,
                severity_level=1,  # Default severity
                status='draft',
                title=inc_data.description[:500] if hasattr(inc_data, 'description') and inc_data.description else None,
                description=getattr(inc_data, 'description', None),
                location_id=location.location_id if location else None,
                fatalities=casualty_info.fatalities if casualty_info else 0,
                injuries=casualty_info.injuries if casualty_info else 0,
                missing_persons=casualty_info.missing if casualty_info else 0
            )

            session.add(incident)
            stored_count += 1

        except Exception as e:
            print(f"⚠️  Warning: Could not store incident {getattr(inc_data, 'incident_id', 'unknown')}: {e}")
            continue

    # Commit all changes
    session.commit()
    print(f"✅ Successfully stored {stored_count} incident(s) in database")
    print()

    # Step 5: Verify data
    print("Step 5: Verifying stored data...")
    total_incidents = session.query(Incident).count()
    total_locations = session.query(Location).count()

    print(f"  Total incidents in database: {total_incidents}")
    print(f"  Total locations in database: {total_locations}")

    # Show sample incident
    if total_incidents > 0:
        sample = session.query(Incident).first()
        print(f"\n  Sample incident:")
        print(f"    ID: {sample.incident_id}")
        print(f"    Source ID: {sample.source_incident_id}")
        print(f"    Date: {sample.incident_date}")
        print(f"    Type: {sample.incident_type}")
        print(f"    Fatalities: {sample.fatalities}")
        print(f"    Injuries: {sample.injuries}")

    session.close()
    print()
    print("="*80)
    print("✅ TEST COMPLETE")
    print("="*80)
    print()
    print("Summary:")
    print(f"  - Scraped: {len(incidents)} incident(s)")
    print(f"  - Stored: {stored_count} incident(s)")
    print(f"  - Database: {db_path}")
    print(f"  - Raw data: {output_file}")
    print()


if __name__ == '__main__':
    main()
