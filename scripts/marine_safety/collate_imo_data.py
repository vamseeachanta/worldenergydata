#!/usr/bin/env python3
"""
IMO GISIS Data Collation Script

Combines multiple IMO GISIS CSV files into a single standardized dataset
and generates comprehensive statistics.
"""

import pandas as pd
import glob
import json
from pathlib import Path
from datetime import datetime

# Configuration
INPUT_DIR = Path("/mnt/github/workspace-hub/worldenergydata/data/modules/marine_safety/raw/imo_gisis")
OUTPUT_FILE = INPUT_DIR / "imo_gisis_collated.csv"
SUMMARY_FILE = INPUT_DIR / "collation_summary.json"

print("="*80)
print("IMO GISIS DATA COLLATION")
print("="*80)
print()

# Find all GISIS CSV files
csv_files = sorted(glob.glob(str(INPUT_DIR / "GISIS-MCIR-*.csv")))

print(f"Found {len(csv_files)} CSV files:")
for file in csv_files:
    print(f"  - {Path(file).name}")
print()

# Read and combine all files
dfs = []
file_stats = []

for csv_file in csv_files:
    filename = Path(csv_file).name
    print(f"Reading: {filename}...", end=" ")

    try:
        df = pd.read_csv(csv_file)
        records = len(df)
        dfs.append(df)

        file_stats.append({
            "filename": filename,
            "records": records,
            "columns": len(df.columns)
        })

        print(f"✅ {records:,} records")
    except Exception as e:
        print(f"❌ Error: {e}")
        file_stats.append({
            "filename": filename,
            "error": str(e)
        })

print()

# Combine all dataframes
print("Combining all datasets...", end=" ")
combined_df = pd.concat(dfs, ignore_index=True)
print(f"✅ {len(combined_df):,} total records")
print()

# Data quality checks
print("DATA QUALITY CHECKS")
print("-" * 80)

# Check for duplicates
duplicates = combined_df.duplicated(subset=['Reference']).sum()
print(f"Duplicate records (by Reference): {duplicates:,}")

# Missing values
print(f"\nMissing values by column:")
missing = combined_df.isnull().sum()
for col, count in missing[missing > 0].items():
    pct = (count / len(combined_df)) * 100
    print(f"  {col}: {count:,} ({pct:.1f}%)")

print()

# Generate statistics
print("STATISTICS")
print("-" * 80)

# By severity
print("\nCasualties by Severity:")
severity_counts = combined_df['Casualty severity'].value_counts()
for severity, count in severity_counts.items():
    pct = (count / len(combined_df)) * 100
    print(f"  {severity}: {count:,} ({pct:.1f}%)")

# By event type
print("\nTop 10 Casualty Events:")
event_counts = combined_df['Casualty event'].value_counts().head(10)
for event, count in event_counts.items():
    pct = (count / len(combined_df)) * 100
    print(f"  {event}: {count:,} ({pct:.1f}%)")

# By ship type
print("\nTop 10 Ship Types:")
ship_type_counts = combined_df['Ship types'].value_counts().head(10)
for ship_type, count in ship_type_counts.items():
    pct = (count / len(combined_df)) * 100
    print(f"  {ship_type}: {count:,} ({pct:.1f}%)")

# Parse dates and analyze by year
print("\nAnalyzing by year...")
combined_df['Occurrence date and time'] = pd.to_datetime(
    combined_df['Occurrence date and time'],
    errors='coerce'
)
combined_df['Year'] = combined_df['Occurrence date and time'].dt.year

print("\nCasualties by Year (Top 20):")
year_counts = combined_df['Year'].value_counts().sort_index(ascending=False).head(20)
for year, count in year_counts.items():
    if pd.notna(year):
        print(f"  {int(year)}: {count:,}")

# Geographic distribution
print("\nTop 10 Locations:")
location_counts = combined_df['Location'].value_counts().head(10)
for location, count in location_counts.items():
    pct = (count / len(combined_df)) * 100
    print(f"  {location}: {count:,} ({pct:.1f}%)")

# Flag states
print("\nTop 10 Flag Administrations:")
# Split multiple flags if needed
flag_counts = combined_df['Flag Administrations'].value_counts().head(10)
for flag, count in flag_counts.items():
    pct = (count / len(combined_df)) * 100
    print(f"  {flag}: {count:,} ({pct:.1f}%)")

print()

# Save collated data
print("SAVING RESULTS")
print("-" * 80)

print(f"Writing collated dataset to: {OUTPUT_FILE}...", end=" ")
combined_df.to_csv(OUTPUT_FILE, index=False)
file_size = OUTPUT_FILE.stat().st_size / (1024 * 1024)
print(f"✅ {file_size:.2f} MB")

# Generate summary
summary = {
    "collation_date": datetime.now().isoformat(),
    "input_files": len(csv_files),
    "total_records": len(combined_df),
    "duplicate_records": int(duplicates),
    "unique_references": combined_df['Reference'].nunique(),
    "date_range": {
        "earliest": combined_df['Occurrence date and time'].min().isoformat() if pd.notna(combined_df['Occurrence date and time'].min()) else None,
        "latest": combined_df['Occurrence date and time'].max().isoformat() if pd.notna(combined_df['Occurrence date and time'].max()) else None
    },
    "columns": list(combined_df.columns),
    "file_statistics": file_stats,
    "severity_breakdown": severity_counts.to_dict(),
    "top_events": event_counts.head(10).to_dict(),
    "top_ship_types": ship_type_counts.head(10).to_dict(),
    "yearly_totals": {int(k): int(v) for k, v in year_counts.items() if pd.notna(k)},
    "output_file": str(OUTPUT_FILE),
    "output_size_mb": round(file_size, 2)
}

print(f"Writing summary to: {SUMMARY_FILE}...", end=" ")
with open(SUMMARY_FILE, 'w') as f:
    json.dump(summary, f, indent=2)
print("✅")

print()
print("="*80)
print("✅ COLLATION COMPLETE")
print("="*80)
print(f"Total Records: {len(combined_df):,}")
print(f"Date Range: {summary['date_range']['earliest']} to {summary['date_range']['latest']}")
print(f"Output File: {OUTPUT_FILE}")
print(f"Summary File: {SUMMARY_FILE}")
print("="*80)
