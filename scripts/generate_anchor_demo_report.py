#!/usr/bin/env python
"""
Generate Demo HTML Report for Anchor Field

Creates a demonstration report using Anchor field characteristics:
- 7 wells in deepwater (7,000+ ft)
- subsea20 development system
- Production from 2019-2024
- Realistic production profiles

Author: WorldEnergyData Team
Date: 2025-10-05
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.worldenergydata.modules.fdas.core.config import classify_dev_system_by_depth


def create_anchor_demo_data():
    """Create realistic demo data for Anchor field."""

    # Create 7 wells typical of Anchor field
    wells = pd.DataFrame({
        'API_WELL_NUMBER': [
            '608074150000',
            '608074150100',
            '608074150200',
            '608074150300',
            '608074150400',
            '608074150500',
            '608074150600',
        ],
        'WELL_NAME': [
            'ANCHOR-001',
            'ANCHOR-002',
            'ANCHOR-003',
            'ANCHOR-004',
            'ANCHOR-005',
            'ANCHOR-006',
            'ANCHOR-007',
        ],
        'WATER_DEPTH': [7250, 7180, 7310, 7220, 7275, 7190, 7265],
        'WELL_SPUD_DATE': [
            '2017-03-15', '2017-09-20', '2018-02-10',
            '2018-08-05', '2019-01-18', '2019-07-22', '2020-03-10'
        ],
        'TOTAL_DEPTH_DATE': [
            '2017-08-30', '2018-01-15', '2018-07-25',
            '2018-12-20', '2019-06-12', '2019-12-05', '2020-09-18'
        ],
        'BOTM_FLD_NAME_CD': 'ANCHOR',
    })

    # Add DEV_SYSTEM
    wells['DEV_SYSTEM'] = wells['WATER_DEPTH'].apply(classify_dev_system_by_depth)

    # Create production data (2019-2024)
    production_records = []
    start_date = datetime(2019, 1, 1)

    # Production profile for each well
    well_profiles = {
        '608074150000': {'first_prod': datetime(2019, 2, 1), 'peak': 25000, 'decline': 0.95},
        '608074150100': {'first_prod': datetime(2019, 3, 1), 'peak': 28000, 'decline': 0.94},
        '608074150200': {'first_prod': datetime(2019, 9, 1), 'peak': 30000, 'decline': 0.96},
        '608074150300': {'first_prod': datetime(2020, 2, 1), 'peak': 27000, 'decline': 0.95},
        '608074150400': {'first_prod': datetime(2020, 8, 1), 'peak': 32000, 'decline': 0.93},
        '608074150500': {'first_prod': datetime(2021, 3, 1), 'peak': 29000, 'decline': 0.96},
        '608074150600': {'first_prod': datetime(2021, 12, 1), 'peak': 26000, 'decline': 0.94},
    }

    # Generate monthly production
    current_date = start_date
    end_date = datetime(2024, 9, 30)

    while current_date <= end_date:
        for api, profile in well_profiles.items():
            if current_date >= profile['first_prod']:
                # Months since first production
                months = (current_date.year - profile['first_prod'].year) * 12 + \
                        (current_date.month - profile['first_prod'].month)

                # Decline curve
                oil_vol = profile['peak'] * (profile['decline'] ** months)
                gas_vol = oil_vol * np.random.uniform(0.8, 1.2)  # GOR variability
                water_vol = oil_vol * 0.15 * (1 + months * 0.02)  # Increasing water cut

                production_records.append({
                    'API_WELL_NUMBER': api,
                    'PRODUCTION_DATE': current_date.strftime('%Y-%m-%d'),
                    'OIL_VOLUME': oil_vol,
                    'GAS_VOLUME': gas_vol,
                    'WATER_VOLUME': water_vol,
                })

        current_date += timedelta(days=30)  # Approximate monthly

    production = pd.DataFrame(production_records)

    return wells, production


def generate_html_report(field_name: str, wells: pd.DataFrame,
                        production: pd.DataFrame, output_file: Path):
    """Generate comprehensive HTML report (same as generate_field_report.py)."""

    # Calculate statistics
    well_stats = {
        'total_wells': len(wells),
        'avg_water_depth': wells['WATER_DEPTH'].mean(),
        'min_water_depth': wells['WATER_DEPTH'].min(),
        'max_water_depth': wells['WATER_DEPTH'].max(),
        'dev_system_counts': wells['DEV_SYSTEM'].value_counts().to_dict(),
        'spud_date_range': (
            pd.to_datetime(wells['WELL_SPUD_DATE']).min().strftime('%Y-%m-%d'),
            pd.to_datetime(wells['WELL_SPUD_DATE']).max().strftime('%Y-%m-%d')
        ),
    }

    prod_stats = {
        'total_records': len(production),
        'total_oil': production['OIL_VOLUME'].sum(),
        'total_gas': production['GAS_VOLUME'].sum(),
        'total_water': production['WATER_VOLUME'].sum(),
        'producing_wells': production['API_WELL_NUMBER'].nunique(),
        'date_range': (
            pd.to_datetime(production['PRODUCTION_DATE']).min().strftime('%Y-%m-%d'),
            pd.to_datetime(production['PRODUCTION_DATE']).max().strftime('%Y-%m-%d')
        ),
    }

    # Monthly aggregation
    production['PROD_DATE'] = pd.to_datetime(production['PRODUCTION_DATE'])
    monthly = production.groupby(pd.Grouper(key='PROD_DATE', freq='MS'))['OIL_VOLUME'].sum()
    prod_stats['avg_monthly_oil'] = monthly.mean()
    prod_stats['peak_monthly_oil'] = monthly.max()

    # Generate HTML (same structure as generate_field_report.py)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{field_name} Field Analysis Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
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
        header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        header p {{ font-size: 1.1em; opacity: 0.9; }}
        .content {{ padding: 40px; }}
        .section {{ margin-bottom: 40px; }}
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
        tr:hover {{ background: #f9f9f9; }}
        .highlight {{
            background: #fff3cd;
            padding: 20px;
            border-left: 4px solid #ffc107;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .data-note {{
            background: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        .badge-subsea20 {{ background: #dc3545; color: white; }}
        .footer {{
            background: #f8f9fa;
            padding: 20px 40px;
            text-align: center;
            color: #666;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{field_name} Field Analysis</h1>
            <p>Deepwater Development in Green Canyon</p>
            <p style="font-size: 0.9em; margin-top: 10px;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>

        <div class="content">
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
                        <h3>Development Timeline</h3>
                        <div class="value" style="font-size: 1em;">
                            {well_stats['spud_date_range'][0]}<br>to<br>{well_stats['spud_date_range'][1]}
                        </div>
                    </div>
                </div>

                <div class="highlight">
                    <strong>Development Classification:</strong> Based on average water depth of {well_stats['avg_water_depth']:,.0f} ft,
                    this is a <strong>SUBSEA 20K</strong> deepwater development requiring advanced subsea production systems.
                </div>

                <h3 style="margin-top: 30px; margin-bottom: 15px;">All Wells</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Well Name</th>
                            <th>API Number</th>
                            <th>Water Depth (ft)</th>
                            <th>Spud Date</th>
                            <th>Completion Date</th>
                        </tr>
                    </thead>
                    <tbody>
"""

    for _, well in wells.iterrows():
        html += f"""
                        <tr>
                            <td><strong>{well['WELL_NAME']}</strong></td>
                            <td>{well['API_WELL_NUMBER']}</td>
                            <td>{well['WATER_DEPTH']:,.0f}</td>
                            <td>{well['WELL_SPUD_DATE']}</td>
                            <td>{well['TOTAL_DEPTH_DATE']}</td>
                        </tr>
"""

    html += f"""
                    </tbody>
                </table>
            </div>

            <div class="section">
                <h2>📈 Production Performance</h2>
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
                        <h3>Avg Monthly Oil</h3>
                        <div class="value">{prod_stats['avg_monthly_oil']/1e3:,.1f}<span class="unit">Mbbls</span></div>
                    </div>
                    <div class="stat-card">
                        <h3>Peak Monthly Oil</h3>
                        <div class="value">{prod_stats['peak_monthly_oil']/1e3:,.1f}<span class="unit">Mbbls</span></div>
                    </div>
                </div>

                <div class="data-note">
                    <strong>Production Period:</strong> {prod_stats['date_range'][0]} to {prod_stats['date_range'][1]}<br>
                    <strong>Total Production Records:</strong> {prod_stats['total_records']:,}<br>
                    <strong>Cumulative Oil:</strong> {prod_stats['total_oil']/1e6:,.2f} MMbbls<br>
                    <strong>Cumulative Gas:</strong> {prod_stats['total_gas']/1e6:,.2f} MMmcf
                </div>
            </div>

            <div class="section">
                <h2>🎯 Key Findings</h2>
                <ul style="margin: 20px 0; padding-left: 20px;">
                    <li><strong>Deepwater Development:</strong> Average water depth of {well_stats['avg_water_depth']:,.0f} ft
                        requires subsea 20K systems with enhanced pressure ratings</li>
                    <li><strong>Well Count:</strong> {well_stats['total_wells']} production wells drilled from
                        {well_stats['spud_date_range'][0]} to {well_stats['spud_date_range'][1]}</li>
                    <li><strong>Production History:</strong> Field has produced {prod_stats['total_oil']/1e6:,.2f} MMbbls of oil
                        since first production in {prod_stats['date_range'][0]}</li>
                    <li><strong>Current Performance:</strong> Average monthly production of {prod_stats['avg_monthly_oil']/1e3:,.1f} Mbbls/month</li>
                    <li><strong>Peak Production:</strong> Reached {prod_stats['peak_monthly_oil']/1e3:,.1f} Mbbls/month</li>
                </ul>

                <div class="highlight">
                    <strong>Note:</strong> This is a demonstration report using synthetic production data based on typical
                    Anchor field characteristics. For actual field analysis, integrate with real BSEE production data.
                </div>
            </div>
        </div>

        <div class="footer">
            <p><strong>WorldEnergyData - FDAS Module Report</strong></p>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Module Version: 1.0.0</p>
            <p style="font-size: 0.9em; margin-top: 5px;">Demonstration report with synthetic production data</p>
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
    print(f"  Development System: SUBSEA20")


def main():
    """Main execution."""
    print("="*80)
    print("Anchor Field Demo Report Generator")
    print("="*80)

    try:
        # Create demo data
        print("\nCreating Anchor field demonstration data...")
        wells, production = create_anchor_demo_data()

        print(f"Created:")
        print(f"  Wells: {len(wells)}")
        print(f"  Production records: {len(production):,}")

        # Generate report
        output_file = Path('reports/anchor_field_demo_report.html')
        generate_html_report("ANCHOR", wells, production, output_file)

        print(f"\n" + "="*80)
        print("✓ Demo report generation complete!")
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
