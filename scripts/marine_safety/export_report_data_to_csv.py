#!/usr/bin/env python3
"""
ABOUTME: Export marine safety incident data to CSV files from analysis results
ABOUTME: Creates lightweight CSV files for optimized HTML report loading
"""

import pandas as pd
from pathlib import Path
import sys
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Export incident data to CSV files."""
    logger.info("="*60)
    logger.info("Marine Safety Incident Data Export to CSV")
    logger.info("="*60)

    # Import after adding to path
    from scripts.marine_safety.generate_incident_report import load_incident_data, analyze_hatch_incidents

    # Create output directory
    results_dir = Path('results/modules/marine_safety')
    results_dir.mkdir(parents=True, exist_ok=True)

    # Load incident data
    logger.info("Loading incident data from databases...")
    data = load_incident_data(None)

    # Export each incident type to CSV
    for incident_type in ['hatch', 'foundering', 'fatality']:
        if incident_type not in data or data[incident_type].empty:
            logger.warning(f"No data available for {incident_type} incidents")
            continue

        df = data[incident_type]

        # Select relevant columns based on incident type
        if incident_type == 'hatch':
            columns = ['incident_id', 'date', 'vessel_name', 'description', 'severity', 'location', 'source', 'fatalities', 'injuries']
        elif incident_type == 'foundering':
            columns = ['incident_id', 'date', 'vessel_name', 'description', 'fatalities', 'location', 'source', 'injuries']
        elif incident_type == 'fatality':
            columns = ['incident_id', 'date', 'vessel_name', 'description', 'incident_type', 'location', 'source', 'fatalities', 'injuries']
        else:
            columns = list(df.columns)

        # Select available columns
        available_columns = [col for col in columns if col in df.columns]
        export_df = df[available_columns].copy()

        # Clean and format data
        if 'date' in export_df.columns:
            export_df['date'] = pd.to_datetime(export_df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
            export_df['date'] = export_df['date'].fillna('Unknown')

        if 'vessel_name' in export_df.columns:
            export_df['vessel_name'] = export_df['vessel_name'].fillna('Unknown')

        if 'description' in export_df.columns:
            export_df['description'] = export_df['description'].fillna('No description available')
            # Truncate very long descriptions to reduce CSV size
            export_df['description'] = export_df['description'].str[:2000]

        for col in ['fatalities', 'injuries']:
            if col in export_df.columns:
                export_df[col] = export_df[col].fillna(0).astype(int)

        for col in ['severity', 'location', 'source', 'incident_type']:
            if col in export_df.columns:
                export_df[col] = export_df[col].fillna('N/A')

        # For hatch incidents, filter to only detected incidents
        if incident_type == 'hatch':
            logger.info(f"Analyzing hatch incidents to filter detections...")
            analysis = analyze_hatch_incidents(df, use_llm=False)
            if analysis and analysis.get('detection_details'):
                detected_df = pd.DataFrame(analysis['detection_details'])
                # Match detected incidents with full data
                detected_ids = set(detected_df['incident_id'].values)
                export_df = export_df[export_df['incident_id'].isin(detected_ids)]
                logger.info(f"Filtered to {len(export_df)} detected hatch incidents")

        # Export to CSV
        csv_path = results_dir / f'{incident_type}_incidents.csv'
        export_df.to_csv(csv_path, index=False, encoding='utf-8')

        file_size_mb = csv_path.stat().st_size / (1024 * 1024)
        logger.info(f"✓ Exported {len(export_df)} {incident_type} incidents to {csv_path} ({file_size_mb:.2f} MB)")

    logger.info("")
    logger.info("="*60)
    logger.info("CSV Export Complete!")
    logger.info("="*60)
    logger.info(f"CSV files saved to: {results_dir}/")
    logger.info("")
    logger.info("These CSV files can be used for:")
    logger.info("  - Optimized HTML report loading (via JavaScript)")
    logger.info("  - Data analysis in Excel/Python/R")
    logger.info("  - Integration with other systems")
    logger.info("")


if __name__ == '__main__':
    main()
