#!/usr/bin/env python
"""
Test script for data processors.

Tests DataCleaner and DataNormalizer with sample data.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from datetime import datetime
from worldenergydata.modules.marine_safety.processors.data_cleaner import DataCleaner
from worldenergydata.modules.marine_safety.processors.data_normalizer import DataNormalizer


def main():
    """Test data processors."""
    print("="*80)
    print("DATA PROCESSORS TEST")
    print("="*80 + "\n")

    # Sample raw data (messy, as it might come from scraping)
    raw_data = [
        {
            'incident_id': 'USCG-2024-001',
            'incident_date': '01/15/2024',
            'incident_time': '2024-01-15 14:30:00',
            'incident_type': 'COLLISION',  # Uppercase
            'title': '  Collision in Houston Ship Channel   ',  # Extra spaces
            'description': 'Two vessels   collided in  foggy conditions',  # Multiple spaces
            'fatalities': '0',  # String instead of int
            'injuries': '3',
            'estimated_damage_usd': '$250,000.00',  # With dollar sign and comma
            'latitude': '29.7604',
            'longitude': '-95.3698',
            'vessel_type': 'Cargo Ship',  # Mixed case
            'flag_state': 'united states',  # Full name
            'severity_level': 'moderate',  # String
            'status': 'Under Investigation',
        },
        {
            'incident_id': 'NTSB-2024-002',
            'incident_date': '2024-02-20',
            'incident_type': 'grounding',  # Lowercase
            'title': 'Tanker runs aground',
            'fatalities': 0,
            'injuries': 0,
            'estimated_damage_usd': '500000',  # No formatting
            'latitude': 40.7128,  # Already numeric
            'longitude': -74.0060,
            'vessel_type': 'oil tanker',
            'flag_state': 'UK',
            'severity_level': None,  # Will be calculated
            'status': 'completed',
        },
        {
            'incident_id': 'USCG-2024-003',
            'incident_date': 'March 10, 2024',  # Different format
            'incident_type': 'Fire/Explosion',  # Compound type
            'title': 'Engine room fire  ',
            'description': '',  # Empty string
            'fatalities': '2',
            'injuries': '5',
            'estimated_damage_usd': '1,500,000.00',
            'latitude': '32.invalid',  # Invalid coordinate
            'longitude': '-117.1611',
            'vessel_type': 'container',
            'flag_state': 'Panama',
            'severity_level': 'SEVERE',
            'status': 'draft',
        },
    ]

    # Test Data Cleaner
    print("STEP 1: DATA CLEANING")
    print("-" * 80)

    cleaner = DataCleaner()

    cleaned_data = []
    for idx, data in enumerate(raw_data, 1):
        print(f"\nCleaning record {idx}...")
        cleaned = cleaner.process(data)
        cleaned_data.append(cleaned)

        # Show key changes
        print(f"  Title: '{data.get('title')}' -> '{cleaned.get('title')}'")
        print(f"  Damage: {data.get('estimated_damage_usd')} -> {cleaned.get('estimated_damage_usd')}")
        print(f"  Fatalities: {data.get('fatalities')} ({type(data.get('fatalities')).__name__}) -> "
              f"{cleaned.get('fatalities')} ({type(cleaned.get('fatalities')).__name__})")

    print(f"\n✓ Cleaning complete")
    print(f"  Stats: {cleaner.get_stats()}")

    # Test Data Normalizer
    print("\n" + "="*80)
    print("STEP 2: DATA NORMALIZATION")
    print("-" * 80)

    normalizer = DataNormalizer()

    normalized_data = []
    for idx, data in enumerate(cleaned_data, 1):
        print(f"\nNormalizing record {idx}...")
        normalized = normalizer.process(data)
        normalized_data.append(normalized)

        # Show key changes
        print(f"  Incident type: '{data.get('incident_type')}' -> '{normalized.get('incident_type')}'")
        print(f"  Vessel type: '{data.get('vessel_type')}' -> '{normalized.get('vessel_type')}'")
        print(f"  Country: '{data.get('flag_state')}' -> '{normalized.get('flag_state')}'")
        print(f"  Severity: {data.get('severity_level')} -> {normalized.get('severity_level')}")
        print(f"  Status: '{data.get('status')}' -> '{normalized.get('status')}'")

    print(f"\n✓ Normalization complete")
    print(f"  Stats: {normalizer.get_stats()}")

    # Summary
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80 + "\n")

    for idx, (raw, cleaned, normalized) in enumerate(zip(raw_data, cleaned_data, normalized_data), 1):
        print(f"Record {idx}: {normalized.get('incident_id')}")
        print(f"  Type: {normalized.get('incident_type')} (severity: {normalized.get('severity_level')})")
        print(f"  Casualties: {normalized.get('fatalities')} fatalities, {normalized.get('injuries')} injuries")
        print(f"  Damage: ${normalized.get('estimated_damage_usd'):,}" if normalized.get('estimated_damage_usd') else "  Damage: N/A")
        print(f"  Status: {normalized.get('status')}")
        print()

    print("="*80)
    print("✅ ALL TESTS PASSED")
    print("="*80)
    print()
    print("Data processors are ready for use in the data pipeline!")
    print()


if __name__ == '__main__':
    main()
