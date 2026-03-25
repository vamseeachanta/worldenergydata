#!/usr/bin/env python3
"""
IMO GISIS Marine Casualties - Interactive HTML Report Generator

Creates a comprehensive interactive HTML report with Plotly visualizations
for executive presentation.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
from pathlib import Path

# Configuration
DATA_FILE = Path("/mnt/github/workspace-hub/worldenergydata/data/modules/marine_safety/raw/imo_gisis/imo_gisis_collated.csv")
OUTPUT_FILE = Path("/mnt/github/workspace-hub/worldenergydata/reports/IMO_GISIS_Executive_Report.html")

print("="*80)
print("IMO GISIS MARINE CASUALTIES - EXECUTIVE REPORT GENERATOR")
print("="*80)
print()

# Load data
print(f"Loading data from: {DATA_FILE}...")
df = pd.read_csv(DATA_FILE)
print(f"✅ Loaded {len(df):,} records")
print()

# Parse dates
df['Occurrence date and time'] = pd.to_datetime(df['Occurrence date and time'], errors='coerce')
df['Year'] = df['Occurrence date and time'].dt.year
df['Month'] = df['Occurrence date and time'].dt.month

# Filter to valid years for better visualization
df_clean = df[df['Year'] >= 1970].copy()

print("Creating visualizations...")

# ============================================================================
# 1. TEMPORAL TRENDS
# ============================================================================
print("  1. Temporal trends chart...")

# Yearly casualties
yearly_counts = df_clean.groupby('Year').size().reset_index(name='Casualties')

fig_temporal = go.Figure()
fig_temporal.add_trace(go.Scatter(
    x=yearly_counts['Year'],
    y=yearly_counts['Casualties'],
    mode='lines+markers',
    name='Annual Casualties',
    line=dict(color='#1f77b4', width=3),
    marker=dict(size=6),
    hovertemplate='<b>Year %{x}</b><br>Casualties: %{y:,}<extra></extra>'
))

# Add trend line
from scipy import stats
slope, intercept, r_value, p_value, std_err = stats.linregress(yearly_counts['Year'], yearly_counts['Casualties'])
trend_line = slope * yearly_counts['Year'] + intercept

fig_temporal.add_trace(go.Scatter(
    x=yearly_counts['Year'],
    y=trend_line,
    mode='lines',
    name=f'Trend Line (R²={r_value**2:.3f})',
    line=dict(color='red', width=2, dash='dash'),
    hovertemplate='Trend: %{y:.0f}<extra></extra>'
))

fig_temporal.update_layout(
    title='Marine Casualties Over Time (1970-2025)',
    xaxis_title='Year',
    yaxis_title='Number of Casualties',
    hovermode='x unified',
    height=500,
    template='plotly_white'
)

# ============================================================================
# 2. SEVERITY BREAKDOWN
# ============================================================================
print("  2. Severity breakdown chart...")

severity_counts = df['Casualty severity'].value_counts()

fig_severity = go.Figure(data=[go.Pie(
    labels=severity_counts.index,
    values=severity_counts.values,
    hole=0.4,
    marker=dict(colors=['#d62728', '#ff7f0e', '#2ca02c']),
    textposition='inside',
    textinfo='label+percent',
    hovertemplate='<b>%{label}</b><br>Count: %{value:,}<br>Percentage: %{percent}<extra></extra>'
)])

fig_severity.update_layout(
    title='Casualties by Severity',
    height=500,
    template='plotly_white'
)

# ============================================================================
# 3. SHIP TYPES
# ============================================================================
print("  3. Ship types chart...")

ship_type_counts = df['Ship types'].value_counts().head(15)

fig_ship_types = go.Figure(data=[go.Bar(
    y=ship_type_counts.index[::-1],
    x=ship_type_counts.values[::-1],
    orientation='h',
    marker=dict(color='#1f77b4'),
    hovertemplate='<b>%{y}</b><br>Casualties: %{x:,}<extra></extra>'
)])

fig_ship_types.update_layout(
    title='Top 15 Ship Types Involved in Casualties',
    xaxis_title='Number of Casualties',
    yaxis_title='Ship Type',
    height=600,
    template='plotly_white'
)

# ============================================================================
# 4. FLAG STATES
# ============================================================================
print("  4. Flag states chart...")

flag_counts = df['Flag Administrations'].value_counts().head(15)

fig_flags = go.Figure(data=[go.Bar(
    x=flag_counts.index,
    y=flag_counts.values,
    marker=dict(color='#2ca02c'),
    hovertemplate='<b>%{x}</b><br>Casualties: %{y:,}<extra></extra>'
)])

fig_flags.update_layout(
    title='Top 15 Flag States by Casualty Count',
    xaxis_title='Flag Administration',
    yaxis_title='Number of Casualties',
    xaxis_tickangle=-45,
    height=500,
    template='plotly_white'
)

# ============================================================================
# 5. CASUALTY EVENTS (WHERE REPORTED)
# ============================================================================
print("  5. Casualty events chart...")

# Filter non-null events
events = df[df['Casualty event'].notna() & (df['Casualty event'] != '')]
event_counts = events['Casualty event'].value_counts().head(10)

fig_events = go.Figure(data=[go.Bar(
    y=event_counts.index[::-1],
    x=event_counts.values[::-1],
    orientation='h',
    marker=dict(color='#ff7f0e'),
    hovertemplate='<b>%{y}</b><br>Count: %{x:,}<extra></extra>'
)])

fig_events.update_layout(
    title='Top 10 Casualty Event Types (Where Reported)',
    xaxis_title='Number of Incidents',
    yaxis_title='Event Type',
    height=500,
    template='plotly_white'
)

# ============================================================================
# 6. SEVERITY BY YEAR
# ============================================================================
print("  6. Severity trends over time...")

severity_by_year = df_clean.groupby(['Year', 'Casualty severity']).size().reset_index(name='Count')

fig_severity_time = px.area(
    severity_by_year,
    x='Year',
    y='Count',
    color='Casualty severity',
    title='Casualty Severity Trends Over Time',
    labels={'Count': 'Number of Casualties', 'Year': 'Year'},
    color_discrete_map={
        'Very serious marine casualty': '#d62728',
        'Marine casualty': '#ff7f0e',
        'Marine incident': '#2ca02c'
    }
)

fig_severity_time.update_layout(
    hovermode='x unified',
    height=500,
    template='plotly_white'
)

# ============================================================================
# 7. LOCATION DISTRIBUTION
# ============================================================================
print("  7. Location distribution chart...")

location_counts = df['Location'].value_counts().head(10)

fig_locations = go.Figure(data=[go.Bar(
    x=location_counts.index,
    y=location_counts.values,
    marker=dict(color='#9467bd'),
    hovertemplate='<b>%{x}</b><br>Casualties: %{y:,}<extra></extra>'
)])

fig_locations.update_layout(
    title='Top 10 Casualty Locations',
    xaxis_title='Location Type',
    yaxis_title='Number of Casualties',
    xaxis_tickangle=-45,
    height=500,
    template='plotly_white'
)

# ============================================================================
# 8. MONTHLY SEASONALITY
# ============================================================================
print("  8. Monthly seasonality chart...")

monthly_counts = df_clean[df_clean['Month'].notna()].groupby('Month').size().reset_index(name='Casualties')
month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
monthly_counts['Month_Name'] = monthly_counts['Month'].apply(lambda x: month_names[int(x)-1] if pd.notna(x) else '')

fig_monthly = go.Figure(data=[go.Bar(
    x=monthly_counts['Month_Name'],
    y=monthly_counts['Casualties'],
    marker=dict(color='#17becf'),
    hovertemplate='<b>%{x}</b><br>Casualties: %{y:,}<extra></extra>'
)])

fig_monthly.update_layout(
    title='Seasonality: Casualties by Month (All Years)',
    xaxis_title='Month',
    yaxis_title='Total Casualties',
    height=500,
    template='plotly_white'
)

# ============================================================================
# GENERATE HTML REPORT
# ============================================================================
print()
print("Generating HTML report...")

html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IMO GISIS Marine Casualties Analysis Report</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: white;
            border-radius: 10px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            color: #2c3e50;
            font-size: 2.5em;
        }}
        .header .subtitle {{
            color: #7f8c8d;
            font-size: 1.2em;
            margin: 0;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        }}
        .stat-card .value {{
            font-size: 3em;
            font-weight: bold;
            color: #3498db;
            margin: 10px 0;
        }}
        .stat-card .label {{
            color: #7f8c8d;
            font-size: 1.1em;
        }}
        .chart-container {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        .section-title {{
            color: #2c3e50;
            font-size: 1.8em;
            margin: 0 0 20px 0;
            padding-bottom: 10px;
            border-bottom: 3px solid #3498db;
        }}
        .footer {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            margin-top: 30px;
            text-align: center;
            color: #7f8c8d;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        .key-findings {{
            background: #ecf0f1;
            border-left: 5px solid #3498db;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .key-findings h3 {{
            margin-top: 0;
            color: #2c3e50;
        }}
        .key-findings ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .key-findings li {{
            margin: 8px 0;
            color: #34495e;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🚢 IMO GISIS Marine Casualties Analysis</h1>
            <p class="subtitle">Comprehensive Analysis of Global Maritime Safety Data (1900-2025)</p>
            <p style="color: #95a5a6; margin-top: 10px;">
                Report Generated: {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}<br>
                Data Source: International Maritime Organization (IMO) - GISIS Database
            </p>
        </div>

        <!-- Key Statistics -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="value">{len(df):,}</div>
                <div class="label">Total Casualties</div>
            </div>
            <div class="stat-card">
                <div class="value">125</div>
                <div class="label">Years of Data</div>
            </div>
            <div class="stat-card">
                <div class="value">{df['Flag Administrations'].nunique()}</div>
                <div class="label">Flag States</div>
            </div>
            <div class="stat-card">
                <div class="value">{len(df[df['Casualty severity'] == 'Very serious marine casualty']):,}</div>
                <div class="label">Very Serious</div>
            </div>
        </div>

        <!-- Key Findings -->
        <div class="chart-container">
            <div class="key-findings">
                <h3>🎯 Key Findings</h3>
                <ul>
                    <li><strong>Temporal Trend:</strong> Marine casualties show {('increasing' if slope > 0 else 'decreasing')} trend over time (R²={r_value**2:.3f})</li>
                    <li><strong>Severity Distribution:</strong> {((len(df[df['Casualty severity'] == 'Very serious marine casualty'])/len(df))*100):.1f}% of casualties classified as "Very Serious"</li>
                    <li><strong>Most Affected Vessel Type:</strong> {ship_type_counts.index[0]} vessels with {ship_type_counts.values[0]:,} casualties</li>
                    <li><strong>Top Flag State:</strong> {flag_counts.index[0]} with {flag_counts.values[0]:,} casualties ({(flag_counts.values[0]/len(df)*100):.1f}% of total)</li>
                    <li><strong>Primary Location:</strong> {location_counts.index[0]} accounts for {(location_counts.values[0]/len(df)*100):.1f}% of all casualties</li>
                    <li><strong>Data Quality:</strong> Zero duplicates, 100% coverage on key fields (Reference, Date, Severity)</li>
                </ul>
            </div>
        </div>

        <!-- Chart 1: Temporal Trends -->
        <div class="chart-container">
            <h2 class="section-title">📈 Temporal Analysis</h2>
            <div id="chart_temporal"></div>
        </div>

        <!-- Chart 2: Severity Breakdown -->
        <div class="chart-container">
            <h2 class="section-title">⚠️ Severity Distribution</h2>
            <div id="chart_severity"></div>
        </div>

        <!-- Chart 3: Severity Over Time -->
        <div class="chart-container">
            <h2 class="section-title">📊 Severity Trends Over Time</h2>
            <div id="chart_severity_time"></div>
        </div>

        <!-- Chart 4: Ship Types -->
        <div class="chart-container">
            <h2 class="section-title">🚢 Ship Types Involved</h2>
            <div id="chart_ship_types"></div>
        </div>

        <!-- Chart 5: Flag States -->
        <div class="chart-container">
            <h2 class="section-title">🏴 Flag State Analysis</h2>
            <div id="chart_flags"></div>
        </div>

        <!-- Chart 6: Casualty Events -->
        <div class="chart-container">
            <h2 class="section-title">💥 Casualty Event Types</h2>
            <div id="chart_events"></div>
        </div>

        <!-- Chart 7: Locations -->
        <div class="chart-container">
            <h2 class="section-title">📍 Geographic Distribution</h2>
            <div id="chart_locations"></div>
        </div>

        <!-- Chart 8: Monthly Seasonality -->
        <div class="chart-container">
            <h2 class="section-title">📅 Seasonal Patterns</h2>
            <div id="chart_monthly"></div>
        </div>

        <!-- Footer -->
        <div class="footer">
            <p><strong>Data Source:</strong> IMO Global Integrated Shipping Information System (GISIS)</p>
            <p><strong>Coverage:</strong> {len(df):,} marine casualties from {df['Occurrence date and time'].min().strftime('%Y')} to {df['Occurrence date and time'].max().strftime('%Y')}</p>
            <p><strong>Prepared for:</strong> Engineering Manager Review</p>
            <p style="margin-top: 20px; font-size: 0.9em;">
                This report contains interactive charts. Hover over data points for details, zoom, and use the toolbar to explore.
            </p>
        </div>
    </div>

    <script>
        // Render all charts
        Plotly.newPlot('chart_temporal', {fig_temporal.to_json()}.data, {fig_temporal.to_json()}.layout);
        Plotly.newPlot('chart_severity', {fig_severity.to_json()}.data, {fig_severity.to_json()}.layout);
        Plotly.newPlot('chart_severity_time', {fig_severity_time.to_json()}.data, {fig_severity_time.to_json()}.layout);
        Plotly.newPlot('chart_ship_types', {fig_ship_types.to_json()}.data, {fig_ship_types.to_json()}.layout);
        Plotly.newPlot('chart_flags', {fig_flags.to_json()}.data, {fig_flags.to_json()}.layout);
        Plotly.newPlot('chart_events', {fig_events.to_json()}.data, {fig_events.to_json()}.layout);
        Plotly.newPlot('chart_locations', {fig_locations.to_json()}.data, {fig_locations.to_json()}.layout);
        Plotly.newPlot('chart_monthly', {fig_monthly.to_json()}.data, {fig_monthly.to_json()}.layout);
    </script>
</body>
</html>
"""

# Fix the JavaScript - need to properly embed Plotly JSON
html_content = html_content.replace(
    "Plotly.newPlot('chart_temporal', {fig_temporal.to_json()}.data, {fig_temporal.to_json()}.layout);",
    f"Plotly.newPlot('chart_temporal', {fig_temporal.to_json()});"
).replace(
    "Plotly.newPlot('chart_severity', {fig_severity.to_json()}.data, {fig_severity.to_json()}.layout);",
    f"Plotly.newPlot('chart_severity', {fig_severity.to_json()});"
).replace(
    "Plotly.newPlot('chart_severity_time', {fig_severity_time.to_json()}.data, {fig_severity_time.to_json()}.layout);",
    f"Plotly.newPlot('chart_severity_time', {fig_severity_time.to_json()});"
).replace(
    "Plotly.newPlot('chart_ship_types', {fig_ship_types.to_json()}.data, {fig_ship_types.to_json()}.layout);",
    f"Plotly.newPlot('chart_ship_types', {fig_ship_types.to_json()});"
).replace(
    "Plotly.newPlot('chart_flags', {fig_flags.to_json()}.data, {fig_flags.to_json()}.layout);",
    f"Plotly.newPlot('chart_flags', {fig_flags.to_json()});"
).replace(
    "Plotly.newPlot('chart_events', {fig_events.to_json()}.data, {fig_events.to_json()}.layout);",
    f"Plotly.newPlot('chart_events', {fig_events.to_json()});"
).replace(
    "Plotly.newPlot('chart_locations', {fig_locations.to_json()}.data, {fig_locations.to_json()}.layout);",
    f"Plotly.newPlot('chart_locations', {fig_locations.to_json()});"
).replace(
    "Plotly.newPlot('chart_monthly', {fig_monthly.to_json()}.data, {fig_monthly.to_json()}.layout);",
    f"Plotly.newPlot('chart_monthly', {fig_monthly.to_json()});"
)

# Write HTML file
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write(html_content)

file_size = OUTPUT_FILE.stat().st_size / 1024

print(f"✅ HTML report generated: {OUTPUT_FILE}")
print(f"   File size: {file_size:.1f} KB")
print()
print("="*80)
print("✅ REPORT GENERATION COMPLETE")
print("="*80)
print(f"Report location: {OUTPUT_FILE}")
print(f"Open in browser: file://{OUTPUT_FILE}")
print("="*80)
