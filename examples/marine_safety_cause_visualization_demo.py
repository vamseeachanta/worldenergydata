#!/usr/bin/env python3
# ABOUTME: Example script demonstrating CauseVisualizer capabilities
# ABOUTME: Generates comprehensive HTML report with all visualization types

"""
Marine Safety Cause Visualization Demo

This script demonstrates the CauseVisualizer class by creating a comprehensive
HTML report with all available visualization types. It generates sample data
and produces an interactive report following HTML reporting standards.

Usage:
    python examples/marine_safety_cause_visualization_demo.py

Output:
    reports/marine_safety_cause_analysis_demo.html
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from worldenergydata.modules.marine_safety.analysis.cause_visualizations import (
    CauseVisualizer
)
from worldenergydata.modules.marine_safety.constants import (
    CauseCategory,
    SeverityLevel
)


def generate_sample_data(num_incidents: int = 200) -> pd.DataFrame:
    """
    Generate realistic sample incident data for demonstration.

    Args:
        num_incidents: Number of sample incidents to generate

    Returns:
        DataFrame with sample incident data
    """
    np.random.seed(42)  # For reproducibility

    # Start date 2 years ago
    start_date = datetime.now() - timedelta(days=730)

    # Realistic cause distribution (weighted) - use string values directly
    causes = [
        ('human_error', 0.30),
        ('equipment_failure', 0.25),
        ('maintenance_issue', 0.15),
        ('weather', 0.10),
        ('procedural', 0.08),
        ('communication', 0.05),
        ('training', 0.04),
        ('management', 0.02),
        ('design_flaw', 0.01),
    ]

    # Realistic severity distribution - use integer values directly
    severities = [
        (1, 0.35),  # MINIMAL
        (2, 0.30),  # MINOR
        (3, 0.20),  # MODERATE
        (4, 0.10),  # SERIOUS
        (5, 0.05),  # CATASTROPHIC
    ]

    data = []
    for i in range(num_incidents):
        # Random date within 2-year period
        days_offset = np.random.randint(0, 730)
        incident_date = start_date + timedelta(days=days_offset)

        # Select cause based on weights
        cause_vals, cause_weights = zip(*causes)
        cause = np.random.choice(cause_vals, p=cause_weights)

        # Select severity based on weights
        sev_vals, sev_weights = zip(*severities)
        severity = np.random.choice(sev_vals, p=sev_weights)

        data.append({
            'incident_id': f'INC-{i+1:05d}',
            'date': incident_date,
            'cause_category': cause,  # Already a string value
            'severity': int(severity),  # Already an integer value
            'description': f'Sample incident {i+1}',
            'vessel_type': np.random.choice([
                'supply_vessel', 'platform', 'tanker', 'crew_boat'
            ]),
            'location': np.random.choice([
                'Gulf of Mexico', 'North Sea', 'Pacific Ocean'
            ]),
        })

    return pd.DataFrame(data)


def generate_hatch_maloperation_data(num_incidents: int = 80) -> pd.DataFrame:
    """
    Generate sample hatch/opening maloperation incident data.

    Args:
        num_incidents: Number of sample incidents

    Returns:
        DataFrame with hatch maloperation data
    """
    np.random.seed(43)
    start_date = datetime.now() - timedelta(days=730)

    maloperation_types = [
        ('improper_securing', 0.30),
        ('delayed_closure', 0.25),
        ('missing_fasteners', 0.20),
        ('inadequate_inspection', 0.15),
        ('structural_damage', 0.10),
    ]

    data = []
    for i in range(num_incidents):
        days_offset = np.random.randint(0, 730)
        incident_date = start_date + timedelta(days=days_offset)

        mal_types, mal_weights = zip(*maloperation_types)
        mal_type = np.random.choice(mal_types, p=mal_weights)

        data.append({
            'incident_id': f'HATCH-{i+1:04d}',
            'date': incident_date,
            'maloperation_type': mal_type,
            'severity': np.random.choice(list(SeverityLevel)),
            'hatch_location': f'Hatch #{np.random.randint(1, 6)}',
            'weather_condition': np.random.choice([
                'calm', 'moderate', 'rough_seas'
            ]),
            'consequences': np.random.choice([
                'flooding', 'near_miss', 'equipment_damage'
            ]),
        })

    return pd.DataFrame(data)


def create_html_report(output_file: Path):
    """
    Create comprehensive HTML report with all visualizations.

    Args:
        output_file: Path to save HTML report
    """
    print("Generating sample data...")
    incident_data = generate_sample_data()
    hatch_data = generate_hatch_maloperation_data()

    print("Creating visualizations...")
    visualizer = CauseVisualizer()

    # Generate all visualizations
    fig_frequency = visualizer.create_cause_frequency_chart(incident_data)
    fig_trend = visualizer.create_cause_trend_over_time(
        incident_data,
        aggregation='monthly'
    )
    fig_pie = visualizer.create_cause_proportion_pie_chart(incident_data)
    fig_heatmap = visualizer.create_cause_severity_heatmap(incident_data)
    fig_sunburst = visualizer.create_cause_hierarchy_sunburst(incident_data)
    fig_hatch = visualizer.create_hatch_maloperation_chart(hatch_data)
    fig_hatch_severity = visualizer.create_hatch_maloperation_severity_breakdown(
        hatch_data
    )
    fig_dashboard = visualizer.create_comprehensive_dashboard(incident_data)

    # Calculate summary statistics
    total_incidents = len(incident_data)
    most_common_cause = incident_data['cause_category'].mode()[0]
    avg_severity = incident_data['severity'].mean()
    recent_incidents = len(incident_data[
        incident_data['date'] >= (datetime.now() - timedelta(days=30))
    ])

    # Create HTML report
    print(f"Creating HTML report at {output_file}...")

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Marine Safety Incident Cause Analysis - Demo Report</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}

        .report-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        .report-header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}

        .report-header p {{
            font-size: 1.1em;
            opacity: 0.95;
        }}

        .report-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            padding: 20px;
            background: #f8f9fa;
        }}

        .info-item {{
            text-align: center;
            padding: 10px;
        }}

        .info-label {{
            color: #6c757d;
            font-size: 0.9em;
            margin-bottom: 5px;
        }}

        .info-value {{
            font-size: 1.3em;
            font-weight: bold;
            color: #667eea;
        }}

        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #ffffff;
        }}

        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            color: white;
            transition: transform 0.3s ease;
        }}

        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }}

        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 10px;
        }}

        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }}

        .stat-description {{
            font-size: 0.85em;
            opacity: 0.8;
        }}

        .section {{
            padding: 30px;
            border-bottom: 1px solid #e9ecef;
        }}

        .section:last-child {{
            border-bottom: none;
        }}

        .section-title {{
            font-size: 1.8em;
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}

        .plot-container {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}

        .plot-title {{
            font-size: 1.3em;
            color: #495057;
            margin-bottom: 15px;
            font-weight: 600;
        }}

        .plot-description {{
            color: #6c757d;
            margin-bottom: 20px;
            line-height: 1.6;
        }}

        .footer {{
            background: #f8f9fa;
            padding: 30px;
            text-align: center;
            color: #6c757d;
        }}

        .footer a {{
            color: #667eea;
            text-decoration: none;
        }}

        .footer a:hover {{
            text-decoration: underline;
        }}

        @media (max-width: 768px) {{
            .report-header h1 {{
                font-size: 1.8em;
            }}

            .summary-stats {{
                grid-template-columns: 1fr;
            }}

            .stat-value {{
                font-size: 2em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="report-header">
            <h1>🌊 Marine Safety Incident Cause Analysis</h1>
            <p>Interactive Visualization Demo Report</p>
        </div>

        <!-- Report Info -->
        <div class="report-info">
            <div class="info-item">
                <div class="info-label">Generated</div>
                <div class="info-value">{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Module</div>
                <div class="info-value">Marine Safety</div>
            </div>
            <div class="info-item">
                <div class="info-label">Repository</div>
                <div class="info-value">WorldEnergyData</div>
            </div>
            <div class="info-item">
                <div class="info-label">Data Period</div>
                <div class="info-value">2 Years</div>
            </div>
        </div>

        <!-- Summary Statistics -->
        <div class="summary-stats">
            <div class="stat-card">
                <div class="stat-label">Total Incidents</div>
                <div class="stat-value">{total_incidents:,}</div>
                <div class="stat-description">All incident records analyzed</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Most Common Cause</div>
                <div class="stat-value">{most_common_cause.replace('_', ' ').title()}</div>
                <div class="stat-description">Primary cause category</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Average Severity</div>
                <div class="stat-value">{avg_severity:.1f}</div>
                <div class="stat-description">Scale: 1 (minimal) to 5 (catastrophic)</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Recent Incidents</div>
                <div class="stat-value">{recent_incidents}</div>
                <div class="stat-description">Last 30 days</div>
            </div>
        </div>

        <!-- Visualizations -->
        <div class="section">
            <h2 class="section-title">📊 Cause Frequency Distribution</h2>
            <div class="plot-container">
                <div class="plot-description">
                    This interactive bar chart shows the frequency of each cause category.
                    Hover over bars to see detailed counts and percentages. The color scheme
                    is consistent across all visualizations for easy identification.
                </div>
                <div id="plot-frequency"></div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">📈 Cause Trends Over Time</h2>
            <div class="plot-container">
                <div class="plot-description">
                    Track how different cause categories trend over time. Use the range slider
                    below the chart to zoom into specific time periods. Click legend items to
                    show/hide specific causes.
                </div>
                <div id="plot-trend"></div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">🥧 Cause Category Proportions</h2>
            <div class="plot-container">
                <div class="plot-description">
                    View the relative proportion of each cause category as a pie chart.
                    The largest category is pulled out for emphasis. Hover over slices
                    for detailed percentage breakdowns.
                </div>
                <div id="plot-pie"></div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">🔥 Cause vs Severity Heatmap</h2>
            <div class="plot-container">
                <div class="plot-description">
                    This heatmap shows the cross-tabulation of cause categories and severity levels.
                    Darker colors indicate higher incident counts. Hover over cells to see exact values.
                </div>
                <div id="plot-heatmap"></div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">☀️ Hierarchical Cause Analysis</h2>
            <div class="plot-container">
                <div class="plot-description">
                    Interactive sunburst chart showing the hierarchical breakdown of causes and
                    their severity distributions. Click on segments to zoom in and explore the
                    hierarchy. Click the center to zoom back out.
                </div>
                <div id="plot-sunburst"></div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">⚓ Hatch Maloperation Analysis</h2>
            <div class="plot-container">
                <div class="plot-description">
                    Specialized analysis of hatch and opening maloperation incidents, showing
                    the distribution of different maloperation types.
                </div>
                <div id="plot-hatch"></div>
            </div>
            <div class="plot-container">
                <div class="plot-description">
                    Detailed breakdown of hatch maloperation incidents by type and severity level.
                    Grouped bars allow easy comparison of severity distributions across maloperation types.
                </div>
                <div id="plot-hatch-severity"></div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">📊 Comprehensive Dashboard</h2>
            <div class="plot-container">
                <div class="plot-description">
                    Combined dashboard showing multiple visualization types in a single view
                    for comprehensive analysis at a glance.
                </div>
                <div id="plot-dashboard"></div>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            <p><strong>WorldEnergyData - Marine Safety Analysis Module</strong></p>
            <p>Interactive visualizations powered by Plotly</p>
            <p>Generated from sample data for demonstration purposes</p>
            <p style="margin-top: 15px;">
                <a href="https://github.com/worldenergydata/worldenergydata">GitHub Repository</a> |
                <a href="../docs/HTML_REPORTING_STANDARDS.md">HTML Reporting Standards</a>
            </p>
        </div>
    </div>

    <script>
        // Render all plots
        var frequency_data = {fig_frequency.to_json()};
        Plotly.newPlot('plot-frequency', frequency_data.data, frequency_data.layout, {{responsive: true}});

        var trend_data = {fig_trend.to_json()};
        Plotly.newPlot('plot-trend', trend_data.data, trend_data.layout, {{responsive: true}});

        var pie_data = {fig_pie.to_json()};
        Plotly.newPlot('plot-pie', pie_data.data, pie_data.layout, {{responsive: true}});

        var heatmap_data = {fig_heatmap.to_json()};
        Plotly.newPlot('plot-heatmap', heatmap_data.data, heatmap_data.layout, {{responsive: true}});

        var sunburst_data = {fig_sunburst.to_json()};
        Plotly.newPlot('plot-sunburst', sunburst_data.data, sunburst_data.layout, {{responsive: true}});

        var hatch_data = {fig_hatch.to_json()};
        Plotly.newPlot('plot-hatch', hatch_data.data, hatch_data.layout, {{responsive: true}});

        var hatch_severity_data = {fig_hatch_severity.to_json()};
        Plotly.newPlot('plot-hatch-severity', hatch_severity_data.data, hatch_severity_data.layout, {{responsive: true}});

        var dashboard_data = {fig_dashboard.to_json()};
        Plotly.newPlot('plot-dashboard', dashboard_data.data, dashboard_data.layout, {{responsive: true}});
    </script>
</body>
</html>
"""

    # Write HTML file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html_content)

    print(f"\n✓ Report created successfully!")
    print(f"  Location: {output_file}")
    print(f"  Size: {output_file.stat().st_size / 1024:.1f} KB")
    print(f"\n  Open the report in your browser to view interactive visualizations.")


def main():
    """Main execution function."""
    # Set output path
    output_dir = Path(__file__).parent.parent / "reports"
    output_file = output_dir / "marine_safety_cause_analysis_demo.html"

    print("=" * 70)
    print("  Marine Safety Cause Visualization Demo")
    print("=" * 70)
    print()

    create_html_report(output_file)

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
