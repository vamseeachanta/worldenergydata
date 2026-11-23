#!/usr/bin/env python
"""
Generate HTML Report for Field Analysis

Creates a comprehensive visual report for a field development including:
- Well count and locations
- Production history and trends
- Development timeline
- Field statistics
- Interactive visualizations

Author: WorldEnergyData Team
Date: 2025-10-05
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.worldenergydata.modules.fdas.core.config import classify_dev_system_by_depth


def load_field_data(bsee_dir: Path, field_name: str = None):
    """Load BSEE data for a specific field or all data."""

    # Load well data
    well_path = bsee_dir / 'wells' / 'well_data.csv'
    print(f"Loading well data from {well_path}...")
    wells = pd.read_csv(well_path, low_memory=False)

    # Add DEV_SYSTEM classification
    if 'WATER_DEPTH' in wells.columns:
        wells['DEV_SYSTEM'] = wells['WATER_DEPTH'].apply(
            lambda x: classify_dev_system_by_depth(x) if pd.notna(x) else 'unknown'
        )

    # Filter by field if specified
    if field_name and 'BOTM_FLD_NAME_CD' in wells.columns:
        wells = wells[wells['BOTM_FLD_NAME_CD'].str.upper() == field_name.upper()]

    # Load production data if available
    prod_path = bsee_dir / 'production' / 'production.csv'
    production = None
    if prod_path.exists():
        print(f"Loading production data from {prod_path}...")
        production = pd.read_csv(prod_path, low_memory=False)

        # Filter by wells if field specified
        if field_name and len(wells) > 0:
            well_apis = wells['API_WELL_NUMBER'].unique()
            production = production[production['API_WELL_NUMBER'].isin(well_apis)]

    return wells, production


def analyze_wells(wells: pd.DataFrame):
    """Analyze well data and generate statistics."""

    stats = {
        'total_wells': len(wells),
        'dev_system_counts': {},
        'avg_water_depth': 0,
        'min_water_depth': 0,
        'max_water_depth': 0,
        'spud_date_range': ('N/A', 'N/A'),
        'completion_date_range': ('N/A', 'N/A'),
    }

    if len(wells) == 0:
        return stats

    # Development system distribution
    if 'DEV_SYSTEM' in wells.columns:
        stats['dev_system_counts'] = wells['DEV_SYSTEM'].value_counts().to_dict()

    # Water depth statistics
    if 'WATER_DEPTH' in wells.columns:
        water_depths = wells['WATER_DEPTH'].dropna()
        if len(water_depths) > 0:
            stats['avg_water_depth'] = water_depths.mean()
            stats['min_water_depth'] = water_depths.min()
            stats['max_water_depth'] = water_depths.max()

    # Date ranges
    if 'WELL_SPUD_DATE' in wells.columns:
        spud_dates = pd.to_datetime(wells['WELL_SPUD_DATE'], errors='coerce').dropna()
        if len(spud_dates) > 0:
            stats['spud_date_range'] = (
                spud_dates.min().strftime('%Y-%m-%d'),
                spud_dates.max().strftime('%Y-%m-%d')
            )

    if 'TOTAL_DEPTH_DATE' in wells.columns:
        comp_dates = pd.to_datetime(wells['TOTAL_DEPTH_DATE'], errors='coerce').dropna()
        if len(comp_dates) > 0:
            stats['completion_date_range'] = (
                comp_dates.min().strftime('%Y-%m-%d'),
                comp_dates.max().strftime('%Y-%m-%d')
            )

    return stats


def analyze_production(production: pd.DataFrame):
    """Analyze production data and generate statistics."""

    stats = {
        'total_records': 0,
        'date_range': ('N/A', 'N/A'),
        'total_oil': 0,
        'total_gas': 0,
        'total_water': 0,
        'avg_monthly_oil': 0,
        'peak_monthly_oil': 0,
        'producing_wells': 0,
    }

    if production is None or len(production) == 0:
        return stats

    stats['total_records'] = len(production)

    # Date range
    if 'PRODUCTION_DATE' in production.columns:
        prod_dates = pd.to_datetime(production['PRODUCTION_DATE'], errors='coerce').dropna()
        if len(prod_dates) > 0:
            stats['date_range'] = (
                prod_dates.min().strftime('%Y-%m-%d'),
                prod_dates.max().strftime('%Y-%m-%d')
            )

    # Volume statistics
    volume_cols = {
        'OIL_VOLUME': 'total_oil',
        'GAS_VOLUME': 'total_gas',
        'WATER_VOLUME': 'total_water'
    }

    for col, stat_key in volume_cols.items():
        if col in production.columns:
            volumes = production[col].fillna(0)
            stats[stat_key] = volumes.sum()

    # Monthly aggregation for oil
    if 'OIL_VOLUME' in production.columns and 'PRODUCTION_DATE' in production.columns:
        production['PROD_DATE'] = pd.to_datetime(production['PRODUCTION_DATE'], errors='coerce')
        monthly = production.groupby(pd.Grouper(key='PROD_DATE', freq='MS'))['OIL_VOLUME'].sum()
        if len(monthly) > 0:
            stats['avg_monthly_oil'] = monthly.mean()
            stats['peak_monthly_oil'] = monthly.max()

    # Producing wells
    if 'API_WELL_NUMBER' in production.columns:
        stats['producing_wells'] = production['API_WELL_NUMBER'].nunique()

    return stats


def generate_html_report(field_name: str, wells: pd.DataFrame,
                        production: pd.DataFrame, output_file: Path):
    """Generate comprehensive HTML report."""

    # Analyze data
    well_stats = analyze_wells(wells)
    prod_stats = analyze_production(production)

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{field_name} Field Analysis Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}

        .content {{
            padding: 40px;
        }}

        .section {{
            margin-bottom: 40px;
        }}

        .section h2 {{
            color: #667eea;
            font-size: 1.8em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}

        .stat-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}

        .stat-card h3 {{
            font-size: 0.9em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}

        .stat-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}

        .stat-card .unit {{
            font-size: 0.9em;
            color: #888;
            margin-left: 5px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}

        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}

        tr:hover {{
            background: #f9f9f9;
        }}

        .highlight {{
            background: #fff3cd;
            padding: 20px;
            border-left: 4px solid #ffc107;
            border-radius: 4px;
            margin: 20px 0;
        }}

        .highlight strong {{
            color: #856404;
        }}

        .footer {{
            background: #f8f9fa;
            padding: 20px 40px;
            text-align: center;
            color: #666;
            border-top: 1px solid #eee;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            margin: 2px;
        }}

        .badge-dry {{
            background: #ffc107;
            color: #000;
        }}

        .badge-subsea15 {{
            background: #17a2b8;
            color: white;
        }}

        .badge-subsea20 {{
            background: #dc3545;
            color: white;
        }}

        .badge-unknown {{
            background: #6c757d;
            color: white;
        }}

        .well-list {{
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}

        .data-note {{
            background: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{field_name} Field Analysis</h1>
            <p>Comprehensive Development & Production Report</p>
            <p style="font-size: 0.9em; margin-top: 10px;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>

        <div class="content">
            <!-- Executive Summary -->
            <div class="section">
                <h2>📊 Executive Summary</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>Total Wells</h3>
                        <div class="value">{well_stats['total_wells']}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Avg Water Depth</h3>
                        <div class="value">{well_stats['avg_water_depth']:,.0f}<span class="unit">ft</span></div>
                    </div>
                    <div class="stat-card">
                        <h3>Total Oil Production</h3>
                        <div class="value">{prod_stats['total_oil']/1e6:,.1f}<span class="unit">MMbbls</span></div>
                    </div>
                    <div class="stat-card">
                        <h3>Producing Wells</h3>
                        <div class="value">{prod_stats['producing_wells']}</div>
                    </div>
                </div>
            </div>

            <!-- Well Statistics -->
            <div class="section">
                <h2>🔧 Well Statistics</h2>

                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>Water Depth Range</h3>
                        <div class="value" style="font-size: 1.3em;">
                            {well_stats['min_water_depth']:,.0f} - {well_stats['max_water_depth']:,.0f}<span class="unit">ft</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <h3>Spud Date Range</h3>
                        <div class="value" style="font-size: 1em;">
                            {well_stats['spud_date_range'][0]}<br>to<br>{well_stats['spud_date_range'][1]}
                        </div>
                    </div>
                </div>

                <h3 style="margin-top: 30px; margin-bottom: 15px;">Development System Classification</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Development System</th>
                            <th>Well Count</th>
                            <th>Percentage</th>
                        </tr>
                    </thead>
                    <tbody>
"""

    # Development system table
    total_wells = well_stats['total_wells']
    for dev_sys, count in sorted(well_stats['dev_system_counts'].items()):
        pct = (count / total_wells * 100) if total_wells > 0 else 0
        badge_class = f"badge-{dev_sys}"
        html += f"""
                        <tr>
                            <td><span class="badge {badge_class}">{dev_sys.upper()}</span></td>
                            <td>{count:,}</td>
                            <td>{pct:.1f}%</td>
                        </tr>
"""

    html += f"""
                    </tbody>
                </table>
            </div>

            <!-- Production Statistics -->
            <div class="section">
                <h2>📈 Production Statistics</h2>

                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>Total Oil</h3>
                        <div class="value">{prod_stats['total_oil']/1e6:,.2f}<span class="unit">MMbbls</span></div>
                    </div>
                    <div class="stat-card">
                        <h3>Total Gas</h3>
                        <div class="value">{prod_stats['total_gas']/1e6:,.2f}<span class="unit">MMmcf</span></div>
                    </div>
                    <div class="stat-card">
                        <h3>Total Water</h3>
                        <div class="value">{prod_stats['total_water']/1e6:,.2f}<span class="unit">MMbbls</span></div>
                    </div>
                    <div class="stat-card">
                        <h3>Avg Monthly Oil</h3>
                        <div class="value">{prod_stats['avg_monthly_oil']/1e3:,.1f}<span class="unit">Mbbls</span></div>
                    </div>
                </div>

                <div class="data-note">
                    <strong>Production Period:</strong> {prod_stats['date_range'][0]} to {prod_stats['date_range'][1]}<br>
                    <strong>Total Production Records:</strong> {prod_stats['total_records']:,}<br>
                    <strong>Peak Monthly Oil:</strong> {prod_stats['peak_monthly_oil']/1e3:,.1f} Mbbls
                </div>
            </div>

            <!-- Well List -->
            <div class="section">
                <h2>🔍 Well Details</h2>
                <p>Showing first 50 wells (total: {len(wells):,})</p>
                <div class="well-list">
                    <table>
                        <thead>
                            <tr>
                                <th>API Number</th>
                                <th>Well Name</th>
                                <th>Water Depth (ft)</th>
                                <th>Dev System</th>
                                <th>Spud Date</th>
                            </tr>
                        </thead>
                        <tbody>
"""

    # Well details table (first 50 wells)
    display_wells = wells.head(50)
    for _, well in display_wells.iterrows():
        api = well.get('API_WELL_NUMBER', 'N/A')
        name = well.get('WELL_NAME', 'N/A')
        depth = well.get('WATER_DEPTH', 0)
        dev_sys = well.get('DEV_SYSTEM', 'unknown')
        spud = well.get('WELL_SPUD_DATE', 'N/A')

        if pd.notna(spud):
            try:
                spud = pd.to_datetime(spud).strftime('%Y-%m-%d')
            except:
                pass

        badge_class = f"badge-{dev_sys}"

        html += f"""
                            <tr>
                                <td>{api}</td>
                                <td>{name}</td>
                                <td>{depth:,.0f}</td>
                                <td><span class="badge {badge_class}">{dev_sys.upper()}</span></td>
                                <td>{spud}</td>
                            </tr>
"""

    html += f"""
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Key Findings -->
            <div class="section">
                <h2>🎯 Key Findings</h2>
                <div class="highlight">
                    <strong>Development Classification:</strong> Based on average water depth of {well_stats['avg_water_depth']:,.0f} ft,
                    this is classified as a <strong>{classify_dev_system_by_depth(well_stats['avg_water_depth']).upper()}</strong> development.
                </div>

                <ul style="margin: 20px 0; padding-left: 20px;">
                    <li><strong>Field has {well_stats['total_wells']} total wells</strong> drilled over the period
                        {well_stats['spud_date_range'][0]} to {well_stats['spud_date_range'][1]}</li>
                    <li><strong>Production history spans {prod_stats['date_range'][0]} to {prod_stats['date_range'][1]}</strong></li>
                    <li><strong>Cumulative oil production: {prod_stats['total_oil']/1e6:,.2f} MMbbls</strong></li>
                    <li><strong>Average monthly oil rate: {prod_stats['avg_monthly_oil']/1e3:,.1f} Mbbls/month</strong></li>
                    <li><strong>Peak production reached: {prod_stats['peak_monthly_oil']/1e3:,.1f} Mbbls/month</strong></li>
                </ul>
            </div>
        </div>

        <div class="footer">
            <p><strong>WorldEnergyData - FDAS Module Report</strong></p>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Module Version: 1.0.0</p>
        </div>
    </div>
</body>
</html>
"""

    # Write file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✓ HTML report generated: {output_file}")
    print(f"\nReport Statistics:")
    print(f"  Total Wells: {well_stats['total_wells']}")
    print(f"  Production Records: {prod_stats['total_records']:,}")
    print(f"  Total Oil: {prod_stats['total_oil']/1e6:,.2f} MMbbls")
    print(f"  Avg Water Depth: {well_stats['avg_water_depth']:,.0f} ft")


def main():
    """Main execution."""
    print("="*80)
    print("Field Analysis HTML Report Generator")
    print("="*80)

    # Paths
    bsee_data_dir = Path('data/modules/bsee/current')

    if not bsee_data_dir.exists():
        print(f"\nError: BSEE data directory not found: {bsee_data_dir}")
        return 1

    # Field name (default to searching for Anchor, or use all data)
    field_name = "ANCHOR"

    try:
        # Load data
        print(f"\nLoading data for field: {field_name}")
        wells, production = load_field_data(bsee_data_dir, field_name)

        if len(wells) == 0:
            print(f"\nNo wells found for field '{field_name}'")
            print("Generating report for ALL fields in database...")
            field_name = "ALL FIELDS"
            wells, production = load_field_data(bsee_data_dir, field_name=None)

        print(f"\nLoaded:")
        print(f"  Wells: {len(wells):,}")
        print(f"  Production records: {len(production) if production is not None else 0:,}")

        # Generate report
        output_file = Path('reports/field_analysis_report.html')
        generate_html_report(field_name, wells, production, output_file)

        print(f"\n" + "="*80)
        print("✓ Report generation complete!")
        print("="*80)
        print(f"\nOpen the report in your browser:")
        print(f"  file://{output_file.absolute()}")

        return 0

    except Exception as e:
        print(f"\n✗ Error generating report: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
