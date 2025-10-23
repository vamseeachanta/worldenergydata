#!/usr/bin/env python3
"""
ABOUTME: Export marine safety incident data to CSV files for optimized HTML report loading
ABOUTME: Separates data from presentation layer to reduce HTML file sizes
"""

import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def export_incident_data_to_csv(df: pd.DataFrame, incident_type: str, output_dir: Path) -> Path:
    """
    Export incident data to CSV file for client-side loading in HTML reports.

    Args:
        df: DataFrame containing incident data
        incident_type: Type of incident ('hatch', 'foundering', 'fatality')
        output_dir: Directory to save CSV files

    Returns:
        Path to created CSV file
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create clean column set based on incident type
    if incident_type == 'hatch':
        columns_to_export = [
            'incident_id', 'date', 'vessel_name', 'description',
            'severity', 'location', 'source', 'fatalities', 'injuries'
        ]
    elif incident_type == 'foundering':
        columns_to_export = [
            'incident_id', 'date', 'vessel_name', 'description',
            'fatalities', 'location', 'source', 'injuries'
        ]
    elif incident_type == 'fatality':
        columns_to_export = [
            'incident_id', 'date', 'vessel_name', 'description',
            'incident_type', 'location', 'source', 'fatalities', 'injuries'
        ]
    else:
        # Default: export all available columns
        columns_to_export = list(df.columns)

    # Select only columns that exist in the DataFrame
    available_columns = [col for col in columns_to_export if col in df.columns]
    export_df = df[available_columns].copy()

    # Convert date to string format for CSV
    if 'date' in export_df.columns:
        export_df['date'] = pd.to_datetime(export_df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
        export_df['date'] = export_df['date'].fillna('Unknown')

    # Fill missing vessel names
    if 'vessel_name' in export_df.columns:
        export_df['vessel_name'] = export_df['vessel_name'].fillna('Unknown')

    # Fill missing descriptions
    if 'description' in export_df.columns:
        export_df['description'] = export_df['description'].fillna('No description available')

    # Fill numeric columns
    for col in ['fatalities', 'injuries']:
        if col in export_df.columns:
            export_df[col] = export_df[col].fillna(0).astype(int)

    # Fill string columns
    for col in ['severity', 'location', 'source', 'incident_type']:
        if col in export_df.columns:
            export_df[col] = export_df[col].fillna('N/A')

    # Export to CSV
    csv_filename = f'{incident_type}_incidents.csv'
    csv_path = output_dir / csv_filename

    export_df.to_csv(csv_path, index=False, encoding='utf-8')
    logger.info(f"Exported {len(export_df)} {incident_type} incidents to {csv_path}")

    return csv_path


def generate_smart_summary(text: str, max_length: int = 150) -> str:
    """Generate smart summary of incident description."""
    if not text or pd.isna(text):
        return "No description available"

    text = str(text).strip()

    if len(text) <= max_length:
        return text

    # Try to break at sentence boundary
    sentences = text.split('. ')
    summary = ""
    for sentence in sentences:
        if len(summary + sentence) <= max_length - 3:
            summary += sentence + ". "
        else:
            break

    if summary:
        return summary.strip()

    # If no good sentence break, just truncate
    return text[:max_length-3] + "..."


if __name__ == "__main__":
    # Example usage
    import sys
    from pathlib import Path

    # Add src to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

    try:
        from worldenergydata.modules.marine_safety.analysis.incidents.hatch_maloperation_analysis import HatchMaloperationAnalyzer

        output_dir = Path('results/modules/marine_safety')

        # Load and analyze data
        analyzer = HatchMaloperationAnalyzer()
        all_incidents = analyzer.load_all_incidents()
        analysis = analyzer.analyze_incidents(all_incidents, use_llm=False)

        # Export to CSV
        if analysis and analysis.get('detection_details'):
            detection_df = pd.DataFrame(analysis['detection_details'])
            csv_path = export_incident_data_to_csv(detection_df, 'hatch', output_dir)
            print(f"✓ Exported hatch incidents to: {csv_path}")
        else:
            print("No hatch incidents to export")

    except ImportError as e:
        print(f"Error importing analyzer: {e}")
        print("Run this script from the project root after installing the package")
