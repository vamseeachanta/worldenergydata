#!/usr/bin/env python
"""Simple test with mock marine incident data."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

from worldenergydata.modules.marine_safety.database.models import (
    Base, Incident, Location, Company, Vessel
)


def main():
    """Test database with simple mock data."""
    print("="*80)
    print("MARINE SAFETY DATABASE - SIMPLE MOCK DATA TEST")
    print("="*80 + "\n")

    # Setup
    db_path = Path('data/modules/marine_safety/database/marine_safety.db')
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    session = Session(engine)

    try:
        print("Creating mock data...\n")

        # Create company
        company = Company(
            company_name="Test Maritime Inc",
            country="USA",
            company_type="Shipping",
            is_active=True
        )
        session.add(company)
        session.flush()
        print(f"✓ Created company: {company.company_name}")

        # Create vessel
        vessel = Vessel(
            vessel_name="M/V Test Ship",
            vessel_type="cargo",
            imo_number="1234567",
            flag_state="USA",
            year_built=2020,
            gross_tonnage=Decimal("25000"),
            company_id=company.company_id
        )
        session.add(vessel)
        session.flush()
        print(f"✓ Created vessel: {vessel.vessel_name}")

        # Create location
        location = Location(
            location_name="Houston Ship Channel",
            latitude=Decimal("29.7604"),
            longitude=Decimal("-95.3698"),
            country_code="USA",
            region_code="TX"
        )
        session.add(location)
        session.flush()
        print(f"✓ Created location: {location.location_name}")

        # Create incidents
        incidents = [
            Incident(
                source_agency="USCG",
                source_incident_id="USCG-2024-001",
                incident_date=date(2024, 1, 15),
                incident_type="Collision",
                severity_level=2,
                status="under_investigation",
                title="Collision in Houston Ship Channel",
                description="Two vessels collided in foggy conditions",
                vessel_id=vessel.vessel_id,
                company_id=company.company_id,
                location_id=location.location_id,
                fatalities=0,
                injuries=3,
                estimated_damage_usd=Decimal("250000"),
                data_quality_score=Decimal("0.85")
            ),
            Incident(
                source_agency="USCG",
                source_incident_id="USCG-2024-002",
                incident_date=date(2024, 2, 20),
                incident_type="Grounding",
                severity_level=1,
                status="completed",
                title="Grounding incident",
                vessel_id=vessel.vessel_id,
                location_id=location.location_id,
                fatalities=0,
                injuries=0,
                estimated_damage_usd=Decimal("500000"),
                data_quality_score=Decimal("0.92")
            ),
            Incident(
                source_agency="NTSB",
                source_incident_id="NTSB-2024-001",
                incident_date=date(2024, 3, 10),
                incident_type="Fire",
                severity_level=3,
                status="draft",
                title="Engine room fire",
                vessel_id=vessel.vessel_id,
                fatalities=0,
                injuries=2,
                estimated_damage_usd=Decimal("1500000")
            )
        ]

        for inc in incidents:
            session.add(inc)

        session.commit()
        print(f"✓ Created {len(incidents)} incidents\n")

        # Verify
        print("="*80)
        print("VERIFICATION")
        print("="*80 + "\n")

        print(f"Companies: {session.query(Company).count()}")
        print(f"Vessels: {session.query(Vessel).count()}")
        print(f"Locations: {session.query(Location).count()}")
        print(f"Incidents: {session.query(Incident).count()}\n")

        # Show sample
        sample = session.query(Incident).first()
        print("Sample Incident:")
        print(f"  ID: {sample.incident_id}")
        print(f"  Source: {sample.source_agency} - {sample.source_incident_id}")
        print(f"  Date: {sample.incident_date}")
        print(f"  Type: {sample.incident_type}")
        print(f"  Title: {sample.title}")
        print(f"  Casualties: {sample.fatalities} fatalities, {sample.injuries} injuries")
        print(f"  Damage: ${sample.estimated_damage_usd:,}" if sample.estimated_damage_usd else "  Damage: N/A")
        print()

        # Statistics
        print("Statistics:")
        type_counts = session.query(
            Incident.incident_type,
            func.count(Incident.incident_id)
        ).group_by(Incident.incident_type).all()

        for itype, count in type_counts:
            print(f"  {itype}: {count}")

        total_damage = session.query(func.sum(Incident.estimated_damage_usd)).scalar() or 0
        print(f"\nTotal damage: ${total_damage:,}\n")

        print("="*80)
        print("✅ SUCCESS - Database working correctly!")
        print("="*80)
        print(f"\nDatabase: {db_path}")
        print()

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()


if __name__ == '__main__':
    main()
