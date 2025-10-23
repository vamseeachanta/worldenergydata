#!/usr/bin/env python3
"""
ABOUTME: Patch script to add CSV export and optimized HTML generation to generate_incident_report.py
ABOUTME: Adds performance optimizations without rewriting the entire script
"""

import re
from pathlib import Path

# Read the original script
script_path = Path(__file__).parent / 'generate_incident_report.py'
content = script_path.read_text()

# Check if already patched
if 'def export_incident_data_to_csv' in content:
    print("✓ Script already patched with CSV export functionality")
    exit(0)

print("Patching generate_incident_report.py with performance optimizations...")

# Find the location to insert the CSV export function (after analyze_fatalities)
insert_marker = 'def generate_smart_summary'
insert_pos = content.find(insert_marker)

if insert_pos == -1:
    print("ERROR: Could not find insertion point in script")
    exit(1)

# CSV export function to insert
csv_export_function = '''

def export_incident_data_to_csv(df: pd.DataFrame, incident_type: str) -> Path:
    """
    Export incident data to CSV file for client-side loading in HTML reports.

    Args:
        df: DataFrame containing incident data
        incident_type: Type of incident ('hatch', 'foundering', 'fatality')

    Returns:
        Path to created CSV file
    """
    # Create results directory
    results_dir = Path('results/modules/marine_safety')
    results_dir.mkdir(parents=True, exist_ok=True)

    # Select columns based on incident type
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
    csv_path = results_dir / csv_filename

    export_df.to_csv(csv_path, index=False, encoding='utf-8')
    logger.info(f"✓ Exported {len(export_df)} {incident_type} incidents to {csv_path}")

    return csv_path


'''

# Insert the function
content = content[:insert_pos] + csv_export_function + content[insert_pos:]

# Now modify the generate_detailed_report function to export CSV
# Find the start of the function
report_func_start = content.find('def generate_detailed_report(')
if report_func_start == -1:
    print("ERROR: Could not find generate_detailed_report function")
    exit(1)

# Find the line where we define title (after incident_types dict)
title_def_pos = content.find("title = incident_types.get(incident_type", report_func_start)
if title_def_pos == -1:
    print("ERROR: Could not find title definition in generate_detailed_report")
    exit(1)

# Find the end of the line
title_line_end = content.find('\n', title_def_pos)

# Insert CSV export call after title definition
csv_export_call = '''

    # Export incident data to CSV for optimized client-side loading
    csv_path = export_incident_data_to_csv(df, incident_type)
    csv_relative_path = f'../../results/modules/marine_safety/{incident_type}_incidents.csv'
'''

content = content[:title_line_end] + csv_export_call + content[title_line_end:]

# Add PapaParse library to HTML script imports
# Find the plotly script tag
plotly_script = content.find('<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>')
if plotly_script != -1:
    papaparse_import = '\n    <script src="https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.4.1/papaparse.min.js"></script>'
    script_end = content.find('</script>', plotly_script) + len('</script>')
    content = content[:script_end] + papaparse_import + content[script_end:]

# Write the patched content
script_path.write_text(content)

print("✓ Successfully patched generate_incident_report.py")
print("  - Added export_incident_data_to_csv() function")
print("  - Integrated CSV export into generate_detailed_report()")
print("  - Added PapaParse library for CSV loading")
print("")
print("NOTE: For full optimization, the HTML template needs manual update")
print("      to use JavaScript-based table loading and pagination.")
print("      See scripts/marine_safety/generate_optimized_report.py for the template.")
