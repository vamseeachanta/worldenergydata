#!/usr/bin/env python3
"""
Analyze Marine Safety Database

Generates comprehensive statistics on the marine safety incident database,
including breakdowns by source, type, date range, geographic coverage,
and data quality.

Usage:
    python scripts/analyze_marine_safety_database.py [--db <path>]
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

import argparse
from sqlalchemy import create_engine, func, text, distinct
from sqlalchemy.orm import Session
from datetime import datetime

from worldenergydata.modules.marine_safety.database.models import (
    Incident, Location, Vessel, Company
)


def analyze_database(db_path: str):
    """Generate comprehensive database statistics."""
    engine = create_engine(f'sqlite:///{db_path}')
    session = Session(engine)

    print(f"\n{'=' * 80}")
    print("MARINE SAFETY DATABASE ANALYSIS")
    print('=' * 80)
    print(f"Database: {db_path}")
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # ========================================
    # Overall Statistics
    # ========================================
    print(f"{'=' * 80}")
    print("OVERALL STATISTICS")
    print('=' * 80)

    total_incidents = session.query(func.count(Incident.incident_id)).scalar()
    total_locations = session.query(func.count(Location.location_id)).scalar()
    total_vessels = session.query(func.count(Vessel.vessel_id)).scalar()
    total_companies = session.query(func.count(Company.company_id)).scalar()

    print(f"Total Incidents: {total_incidents:,}")
    print(f"Total Locations: {total_locations:,}")
    print(f"Total Vessels: {total_vessels:,}")
    print(f"Total Companies: {total_companies:,}")
    print()

    # ========================================
    # Incidents by Source Agency
    # ========================================
    print(f"{'=' * 80}")
    print("INCIDENTS BY SOURCE AGENCY")
    print('=' * 80)

    source_stats = session.query(
        Incident.source_agency,
        func.count(Incident.incident_id).label('count')
    ).group_by(Incident.source_agency).order_by(text('count DESC')).all()

    for source, count in source_stats:
        print(f"{source:20} {count:>10,} ({count/total_incidents*100:>6.2f}%)")
    print()

    # ========================================
    # Incidents by Type
    # ========================================
    print(f"{'=' * 80}")
    print("INCIDENTS BY TYPE")
    print('=' * 80)

    type_stats = session.query(
        Incident.incident_type,
        func.count(Incident.incident_id).label('count')
    ).group_by(Incident.incident_type).order_by(text('count DESC')).all()

    for inc_type, count in type_stats:
        print(f"{inc_type:25} {count:>10,} ({count/total_incidents*100:>6.2f}%)")
    print()

    # ========================================
    # Date Range Coverage
    # ========================================
    print(f"{'=' * 80}")
    print("DATE RANGE COVERAGE BY SOURCE")
    print('=' * 80)

    date_ranges = session.query(
        Incident.source_agency,
        func.min(Incident.incident_date).label('earliest'),
        func.max(Incident.incident_date).label('latest'),
        func.count(Incident.incident_id).label('count')
    ).group_by(Incident.source_agency).order_by(Incident.source_agency).all()

    for source, earliest, latest, count in date_ranges:
        print(f"{source:20} {earliest} to {latest}  ({count:,} incidents)")
    print()

    # ========================================
    # Geographic Coverage
    # ========================================
    print(f"{'=' * 80}")
    print("GEOGRAPHIC COVERAGE")
    print('=' * 80)

    # Count locations with coordinates
    locations_with_coords = session.query(func.count(Location.location_id)).filter(
        Location.latitude.isnot(None),
        Location.longitude.isnot(None)
    ).scalar()

    print(f"Locations with GPS coordinates: {locations_with_coords:,} ({locations_with_coords/total_locations*100:.1f}%)")
    print()

    # Top countries
    print("Top Countries (by location):")
    countries = session.query(
        Location.country_code,
        func.count(Location.location_id).label('count')
    ).filter(
        Location.country_code.isnot(None)
    ).group_by(Location.country_code).order_by(text('count DESC')).limit(10).all()

    for country, count in countries:
        print(f"  {country:5} {count:>8,}")
    print()

    # Top regions
    print("Top Regions (by location):")
    regions = session.query(
        Location.region_code,
        func.count(Location.location_id).label('count')
    ).filter(
        Location.region_code.isnot(None)
    ).group_by(Location.region_code).order_by(text('count DESC')).limit(10).all()

    for region, count in regions:
        print(f"  {region:5} {count:>8,}")
    print()

    # ========================================
    # Casualties Summary
    # ========================================
    print(f"{'=' * 80}")
    print("CASUALTIES SUMMARY")
    print('=' * 80)

    total_fatalities = session.query(func.sum(Incident.fatalities)).scalar() or 0
    total_injuries = session.query(func.sum(Incident.injuries)).scalar() or 0
    total_missing = session.query(func.sum(Incident.missing_persons)).scalar() or 0

    incidents_with_fatalities = session.query(func.count(Incident.incident_id)).filter(
        Incident.fatalities > 0
    ).scalar()

    incidents_with_injuries = session.query(func.count(Incident.incident_id)).filter(
        Incident.injuries > 0
    ).scalar()

    print(f"Total Fatalities: {total_fatalities:,}")
    print(f"Total Injuries: {total_injuries:,}")
    print(f"Total Missing: {total_missing:,}")
    print()
    print(f"Incidents with Fatalities: {incidents_with_fatalities:,} ({incidents_with_fatalities/total_incidents*100:.2f}%)")
    print(f"Incidents with Injuries: {incidents_with_injuries:,} ({incidents_with_injuries/total_incidents*100:.2f}%)")
    print()

    # Worst incidents by fatalities
    print("Worst Incidents by Fatalities (Top 10):")
    worst_incidents = session.query(
        Incident.source_agency,
        Incident.source_incident_id,
        Incident.incident_date,
        Incident.title,
        Incident.fatalities
    ).filter(
        Incident.fatalities > 0
    ).order_by(Incident.fatalities.desc()).limit(10).all()

    for source, inc_id, date, title, fatalities in worst_incidents:
        title_short = (title[:50] + '...') if title and len(title) > 50 else (title or 'N/A')
        print(f"  {fatalities:>3} deaths - {source}/{inc_id} - {date} - {title_short}")
    print()

    # ========================================
    # Pollution and Environmental Incidents
    # ========================================
    print(f"{'=' * 80}")
    print("POLLUTION AND ENVIRONMENTAL INCIDENTS")
    print('=' * 80)

    pollution_incidents = session.query(func.count(Incident.incident_id)).filter(
        Incident.incident_type == 'pollution'
    ).scalar()

    environmental_incidents = session.query(func.count(Incident.incident_id)).filter(
        Incident.incident_type == 'environmental'
    ).scalar()

    print(f"Pollution Incidents: {pollution_incidents:,} ({pollution_incidents/total_incidents*100:.2f}%)")
    print(f"Environmental Incidents: {environmental_incidents:,} ({environmental_incidents/total_incidents*100:.2f}%)")
    print()

    # Incidents with damage estimates
    incidents_with_damage = session.query(func.count(Incident.incident_id)).filter(
        Incident.estimated_damage_usd.isnot(None),
        Incident.estimated_damage_usd > 0
    ).scalar()

    total_damage = session.query(func.sum(Incident.estimated_damage_usd)).filter(
        Incident.estimated_damage_usd.isnot(None)
    ).scalar() or 0

    print(f"Incidents with Damage Estimates: {incidents_with_damage:,} ({incidents_with_damage/total_incidents*100:.2f}%)")
    print(f"Total Estimated Damage: ${total_damage:,.2f}")
    print()

    # ========================================
    # Data Quality Metrics
    # ========================================
    print(f"{'=' * 80}")
    print("DATA QUALITY METRICS")
    print('=' * 80)

    # Incidents with titles
    incidents_with_titles = session.query(func.count(Incident.incident_id)).filter(
        Incident.title.isnot(None)
    ).scalar()

    # Incidents with descriptions
    incidents_with_descriptions = session.query(func.count(Incident.incident_id)).filter(
        Incident.description.isnot(None)
    ).scalar()

    # Incidents with locations
    incidents_with_locations = session.query(func.count(Incident.incident_id)).filter(
        Incident.location_id.isnot(None)
    ).scalar()

    # Incidents with vessels
    incidents_with_vessels = session.query(func.count(Incident.incident_id)).filter(
        Incident.vessel_id.isnot(None)
    ).scalar()

    print(f"Incidents with Titles: {incidents_with_titles:,} ({incidents_with_titles/total_incidents*100:.1f}%)")
    print(f"Incidents with Descriptions: {incidents_with_descriptions:,} ({incidents_with_descriptions/total_incidents*100:.1f}%)")
    print(f"Incidents with Locations: {incidents_with_locations:,} ({incidents_with_locations/total_incidents*100:.1f}%)")
    print(f"Incidents with Vessels: {incidents_with_vessels:,} ({incidents_with_vessels/total_incidents*100:.1f}%)")
    print()

    # ========================================
    # Database Size
    # ========================================
    print(f"{'=' * 80}")
    print("DATABASE SIZE")
    print('=' * 80)

    db_file = Path(db_path)
    if db_file.exists():
        db_size_bytes = db_file.stat().st_size
        db_size_mb = db_size_bytes / (1024 * 1024)
        db_size_gb = db_size_mb / 1024

        print(f"Database File Size: {db_size_mb:.2f} MB ({db_size_gb:.3f} GB)")
        print(f"Average Size per Incident: {db_size_bytes/total_incidents:.2f} bytes")
    print()

    print(f"{'=' * 80}\n")

    session.close()


def main():
    parser = argparse.ArgumentParser(
        description='Analyze Marine Safety Database'
    )
    parser.add_argument(
        '--db',
        default='data/modules/marine_safety/database/marine_safety.db',
        help='Database path (default: data/modules/marine_safety/database/marine_safety.db)'
    )

    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: Database not found: {db_path}")
        sys.exit(1)

    analyze_database(str(db_path))


if __name__ == '__main__':
    main()
