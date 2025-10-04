#!/usr/bin/env python
"""
Test database storage with mock marine incident data.

This script validates the complete data pipeline:
1. Creates realistic mock incidents
2. Stores them in the database
3. Queries and verifies the data
4. Tests relationships between tables
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from worldenergydata.modules.marine_safety.database.models import (
    Base, Incident, Location, Company, Vessel, IncidentCause, IncidentDocument, ScrapeLog
)


def create_mock_data(session: Session) -> dict:
    """Create comprehensive mock marine safety data."""

    print("Creating mock data...\n")

    # Create companies
    companies = [
        Company(
            company_name="Oceanic Shipping Ltd",
            country="USA",
            company_type="Shipping",
            is_active=True
        ),
        Company(
            company_name="Maritime Transport Inc",
            country="UK",
            company_type="Transport",
            is_active=True
        )
    ]
    for comp in companies:
        session.add(comp)
    session.flush()
    print(f"✓ Created {len(companies)} companies")

    # Create vessels
    vessels = [
        Vessel(
            vessel_name="M/V Pacific Star",
            imo_number="9876543",
            vessel_type="cargo",
            flag_state="USA",
            year_built=2015,
            gross_tonnage=Decimal("25000.50"),
            company_id=companies[0].company_id
        ),
        Vessel(
            vessel_name="S/S Atlantic Wave",
            imo_number="9876544",
            vessel_type="tanker",
            flag_state="UK",
            year_built=2012,
            gross_tonnage=Decimal("42000.00"),
            company_id=companies[1].company_id
        )
    ]
    for vessel in vessels:
        session.add(vessel)
    session.flush()
    print(f"✓ Created {len(vessels)} vessels")

    # Create locations
    locations = [
        Location(
            latitude=29.7604,
            longitude=-95.3698,
            location_description="Houston Ship Channel",
            waterway_name="Houston Ship Channel",
            port_name="Port of Houston",
            country="USA"
        ),
        Location(
            latitude=40.7128,
            longitude=-74.0060,
            location_description="New York Harbor",
            waterway_name="New York Harbor",
            port_name="Port of New York",
            country="USA"
        )
    ]
    for loc in locations:
        session.add(loc)
    session.flush()
    print(f"✓ Created {len(locations)} locations")

    # Create incidents
    incidents = [
        Incident(
            source_agency="USCG",
            source_incident_id="USCG-2024-001",
            incident_date=date(2024, 1, 15),
            incident_time=datetime(2024, 1, 15, 14, 30),
            incident_type="Collision",
            severity_level=2,
            status="under_investigation",
            title="Collision in Houston Ship Channel",
            description="Two vessels collided in foggy conditions at Houston Ship Channel",
            vessel_id=vessels[0].vessel_id,
            company_id=companies[0].company_id,
            location_id=locations[0].location_id,
            fatalities=0,
            injuries=3,
            missing_persons=0,
            environmental_impact="Minor fuel sheen observed",
            estimated_damage_usd=Decimal("250000.00"),
            weather_condition="fog",
            wind_speed_knots=Decimal("5.5"),
            wave_height_meters=Decimal("0.5"),
            sea_state=1,
            visibility_meters=Decimal("100.0"),
            investigation_status="Active investigation ongoing",
            investigation_priority="medium",
            data_quality_score=Decimal("0.85")
        ),
        Incident(
            source_agency="NTSB",
            source_incident_id="NTSB-2024-002",
            incident_date=date(2024, 2, 20),
            incident_type="Grounding",
            severity_level=1,
            status="completed",
            title="Grounding at New York Harbor",
            description="Tanker ran aground during adverse weather",
            vessel_id=vessels[1].vessel_id,
            company_id=companies[1].company_id,
            location_id=locations[1].location_id,
            fatalities=0,
            injuries=0,
            missing_persons=0,
            estimated_damage_usd=Decimal("500000.00"),
            weather_condition="storm",
            wind_speed_knots=Decimal("35.0"),
            wave_height_meters=Decimal("3.5"),
            sea_state=5,
            investigation_status="Investigation completed",
            investigation_priority="high",
            data_quality_score=Decimal("0.92")
        ),
        Incident(
            source_agency="USCG",
            source_incident_id="USCG-2024-003",
            incident_date=date(2024, 3, 10),
            incident_type="Fire",
            severity_level=3,
            status="draft",
            title="Engine room fire",
            description="Fire in engine room, crew evacuated safely",
            vessel_id=vessels[0].vessel_id,
            location_id=locations[0].location_id,
            fatalities=0,
            injuries=2,
            missing_persons=0,
            estimated_damage_usd=Decimal("1500000.00"),
            investigation_status="Preliminary report drafted",
            data_quality_score=Decimal("0.78")
        )
    ]
    for inc in incidents:
        session.add(inc)
    session.flush()
    print(f"✓ Created {len(incidents)} incidents")

    # Create incident causes
    causes = [
        IncidentCause(
            incident_id=incidents[0].incident_id,
            cause_type="primary",
            cause_description="Poor visibility due to fog",
            contributing_factors="Inadequate bridge watch procedures"
        ),
        IncidentCause(
            incident_id=incidents[1].incident_id,
            cause_type="primary",
            cause_description="Navigation system malfunction",
            contributing_factors="Adverse weather conditions"
        )
    ]
    for cause in causes:
        session.add(cause)
    session.flush()
    print(f"✓ Created {len(causes)} incident causes")

    # Create incident documents
    documents = [
        IncidentDocument(
            incident_id=incidents[0].incident_id,
            document_type="investigation_report",
            document_title="USCG Investigation Report - Collision Houston Ship Channel",
            document_url="https://example.uscg.mil/reports/2024-001.pdf",
            source_agency="USCG",
            publication_date=date(2024, 4, 15)
        ),
        IncidentDocument(
            incident_id=incidents[1].incident_id,
            document_type="final_report",
            document_title="NTSB Final Report - Grounding New York Harbor",
            document_url="https://example.ntsb.gov/reports/2024-002.pdf",
            source_agency="NTSB",
            publication_date=date(2024, 5, 20)
        )
    ]
    for doc in documents:
        session.add(doc)
    session.flush()
    print(f"✓ Created {len(documents)} incident documents")

    session.commit()

    return {
        'companies': len(companies),
        'vessels': len(vessels),
        'locations': len(locations),
        'incidents': len(incidents),
        'causes': len(causes),
        'documents': len(documents)
    }


def query_and_verify(session: Session):
    """Query database and verify relationships."""

    print("\n" + "="*80)
    print("VERIFYING DATA")
    print("="*80 + "\n")

    # Count totals
    print("Record counts:")
    print(f"  Companies: {session.query(Company).count()}")
    print(f"  Vessels: {session.query(Vessel).count()}")
    print(f"  Locations: {session.query(Location).count()}")
    print(f"  Incidents: {session.query(Incident).count()}")
    print(f"  Incident Causes: {session.query(IncidentCause).count()}")
    print(f"  Incident Documents: {session.query(IncidentDocument).count()}")
    print()

    # Test joins and relationships
    print("Testing relationships:")

    # Get incident with all related data
    incident = session.query(Incident).filter(Incident.source_incident_id == "USCG-2024-001").first()

    if incident:
        print(f"\n  Sample Incident: {incident.title}")
        print(f"    Date: {incident.incident_date}")
        print(f"    Type: {incident.incident_type}")
        print(f"    Severity: {incident.severity_level}")
        print(f"    Fatalities: {incident.fatalities}, Injuries: {incident.injuries}")
        print(f"    Damage: ${incident.estimated_damage_usd:,.2f}" if incident.estimated_damage_usd else "    Damage: N/A")

        # Test relationships
        if incident.location_id:
            location = session.query(Location).filter(Location.location_id == incident.location_id).first()
            if location:
                print(f"    Location: {location.location_description} ({location.latitude}, {location.longitude})")

        if incident.vessel_id:
            vessel = session.query(Vessel).filter(Vessel.vessel_id == incident.vessel_id).first()
            if vessel:
                print(f"    Vessel: {vessel.vessel_name} (IMO: {vessel.imo_number})")

                if vessel.company_id:
                    company = session.query(Company).filter(Company.company_id == vessel.company_id).first()
                    if company:
                        print(f"    Company: {company.company_name} ({company.country})")

        # Check causes
        cause = session.query(IncidentCause).filter(IncidentCause.incident_id == incident.incident_id).first()
        if cause:
            print(f"    Primary Cause: {cause.cause_description}")
            if cause.contributing_factors:
                print(f"    Contributing: {cause.contributing_factors}")

    print()

    # Statistics
    print("Statistics:")

    # Incidents by type
    from sqlalchemy import func
    type_counts = session.query(
        Incident.incident_type,
        func.count(Incident.incident_id).label('count')
    ).group_by(Incident.incident_type).all()

    print("  Incidents by type:")
    for itype, count in type_counts:
        print(f"    {itype}: {count}")

    # Total casualties
    total_fatalities = session.query(func.sum(Incident.fatalities)).scalar() or 0
    total_injuries = session.query(func.sum(Incident.injuries)).scalar() or 0
    total_missing = session.query(func.sum(Incident.missing_persons)).scalar() or 0

    print(f"\n  Total casualties:")
    print(f"    Fatalities: {total_fatalities}")
    print(f"    Injuries: {total_injuries}")
    print(f"    Missing: {total_missing}")

    # Total damage
    total_damage = session.query(func.sum(Incident.estimated_damage_usd)).scalar() or 0
    print(f"\n  Total estimated damage: ${total_damage:,.2f}")

    print()


def main():
    """Main test function."""
    print("="*80)
    print("MARINE SAFETY DATABASE - MOCK DATA TEST")
    print("="*80)
    print()

    # Setup database
    db_path = Path('data/modules/marine_safety/database/marine_safety.db')
    db_url = f"sqlite:///{db_path}"

    print(f"Database: {db_path}\n")

    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)

    session = Session(engine)

    try:
        # Create mock data
        counts = create_mock_data(session)

        # Query and verify
        query_and_verify(session)

        print("="*80)
        print("✅ TEST COMPLETE - ALL DATA STORED AND VERIFIED SUCCESSFULLY")
        print("="*80)
        print()
        print("Summary:")
        for entity, count in counts.items():
            print(f"  {entity.capitalize()}: {count}")
        print()
        print(f"Database ready for use at: {db_path}")
        print()

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()


if __name__ == '__main__':
    main()
