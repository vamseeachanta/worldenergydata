#!/usr/bin/env python3
"""
IMO GISIS Data Collation Script (Robust Version)
Handles CSV parsing errors and malformed data
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
print("IMO GISIS DATA COLLATION (ROBUST)")
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
        # Try reading with error handling for bad lines
        df = pd.read_csv(csv_file, on_bad_lines='skip', engine='python')
        records = len(df)
        dfs.append(df)

        file_stats.append({
            "filename": filename,
            "records": records,
            "columns": len(df.columns),
            "status": "success"
        })

        print(f"✅ {records:,} records")
    except Exception as e:
        print(f"❌ Error: {e}")
        file_stats.append({
            "filename": filename,
            "error": str(e),
            "status": "failed"
        })

print()

# Combine all dataframes
print("Combining all datasets...", end=" ")
if dfs:
    combined_df = pd.concat(dfs, ignore_index=True)
    print(f"✅ {len(combined_df):,} total records")
else:
    print("❌ No data to combine")
    exit(1)

print()

# Data quality checks
print("DATA QUALITY CHECKS")
print("-" * 80)

# Check for duplicates
if 'Reference' in combined_df.columns:
    duplicates = combined_df.duplicated(subset=['Reference']).sum()
    print(f"Duplicate records (by Reference): {duplicates:,}")
    unique_refs = combined_df['Reference'].nunique()
    print(f"Unique references: {unique_refs:,}")

# Column info
print(f"\nColumns ({len(combined_df.columns)}):")
for i, col in enumerate(combined_df.columns, 1):
    non_null = combined_df[col].notna().sum()
    pct = (non_null / len(combined_df)) * 100
    print(f"  {i}. {col}: {non_null:,} non-null ({pct:.1f}%)")

print()

# Generate statistics
print("STATISTICS")
print("-" * 80)

# By severity
if 'Casualty severity' in combined_df.columns:
    print("\nCasualties by Severity:")
    severity_counts = combined_df['Casualty severity'].value_counts()
    for severity, count in severity_counts.items():
        pct = (count / len(combined_df)) * 100
        print(f"  {severity}: {count:,} ({pct:.1f}%)")

# By event type
if 'Casualty event' in combined_df.columns:
    print("\nTop 15 Casualty Events:")
    event_counts = combined_df['Casualty event'].value_counts().head(15)
    for event, count in event_counts.items():
        if pd.notna(event) and event:
            pct = (count / len(combined_df)) * 100
            print(f"  {event}: {count:,} ({pct:.1f}%)")

# By ship type
if 'Ship types' in combined_df.columns:
    print("\nTop 15 Ship Types:")
    ship_type_counts = combined_df['Ship types'].value_counts().head(15)
    for ship_type, count in ship_type_counts.items():
        if pd.notna(ship_type) and ship_type:
            pct = (count / len(combined_df)) * 100
            print(f"  {ship_type}: {count:,} ({pct:.1f}%)")

# Parse dates and analyze by year
if 'Occurrence date and time' in combined_df.columns:
    print("\nAnalyzing by year...")
    combined_df['Occurrence date and time'] = pd.to_datetime(
        combined_df['Occurrence date and time'],
        errors='coerce'
    )
    combined_df['Year'] = combined_df['Occurrence date and time'].dt.year

    print("\nCasualties by Decade:")
    for decade in [1900, 1970, 1980, 1990, 2000, 2010, 2020]:
        decade_data = combined_df[(combined_df['Year'] >= decade) & (combined_df['Year'] < decade + 10)]
        print(f"  {decade}s: {len(decade_data):,}")

    print("\nRecent Years (2015-2025):")
    recent_years = combined_df[combined_df['Year'] >= 2015]['Year'].value_counts().sort_index()
    for year, count in recent_years.items():
        if pd.notna(year):
            print(f"  {int(year)}: {count:,}")

# Geographic distribution
if 'Location' in combined_df.columns:
    print("\nTop 10 Locations:")
    location_counts = combined_df['Location'].value_counts().head(10)
    for location, count in location_counts.items():
        if pd.notna(location) and location:
            pct = (count / len(combined_df)) * 100
            print(f"  {location}: {count:,} ({pct:.1f}%)")

# Flag states
if 'Flag Administrations' in combined_df.columns:
    print("\nTop 15 Flag Administrations:")
    flag_counts = combined_df['Flag Administrations'].value_counts().head(15)
    for flag, count in flag_counts.items():
        if pd.notna(flag) and flag:
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
    "files_processed": len([f for f in file_stats if f.get('status') == 'success']),
    "files_failed": len([f for f in file_stats if f.get('status') == 'failed']),
    "total_records": len(combined_df),
    "duplicate_records": int(duplicates) if 'Reference' in combined_df.columns else None,
    "unique_references": int(combined_df['Reference'].nunique()) if 'Reference' in combined_df.columns else None,
    "date_range": {
        "earliest": combined_df['Occurrence date and time'].min().isoformat() if 'Occurrence date and time' in combined_df.columns and pd.notna(combined_df['Occurrence date and time'].min()) else None,
        "latest": combined_df['Occurrence date and time'].max().isoformat() if 'Occurrence date and time' in combined_df.columns and pd.notna(combined_df['Occurrence date and time'].max()) else None
    },
    "columns": list(combined_df.columns),
    "file_statistics": file_stats,
    "severity_breakdown": severity_counts.to_dict() if 'Casualty severity' in combined_df.columns else {},
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
if summary['date_range']['earliest']:
    print(f"Date Range: {summary['date_range']['earliest'][:10]} to {summary['date_range']['latest'][:10]}")
print(f"Files Processed: {summary['files_processed']}/{summary['input_files']}")
print(f"Output File: {OUTPUT_FILE}")
print(f"Summary File: {SUMMARY_FILE}")
print("="*80)
