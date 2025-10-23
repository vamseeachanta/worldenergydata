#!/usr/bin/env python3
"""
ABOUTME: Marine safety incident analysis report generator
ABOUTME: Creates executive summary and detailed HTML reports with interactive visualizations

This script analyzes marine safety incidents including hatch maloperation, founderings,
and fatalities, then generates professional HTML reports suitable for supervisor presentation.
"""

import argparse
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime
import sys
import os
import logging
import json

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

try:
    from worldenergydata.modules.marine_safety.analysis.incidents.hatch_maloperation_analysis import HatchMaloperationAnalyzer
    ANALYZER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import HatchMaloperationAnalyzer: {e}")
    ANALYZER_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def load_incident_data(input_dir: Path):
    """Load all incident CSV files from real data sources."""
    data = {}
    all_incidents = []

    logger.info("Loading real incident data from multiple sources...")

    # 1. Load Canadian TSB occurrence data
    try:
        tsb_file = Path('data/modules/marine_safety/raw/canadian_tsb/occurrence.csv')
        if tsb_file.exists():
            logger.info(f"Loading Canadian TSB data from {tsb_file}")
            tsb_df = pd.read_csv(tsb_file, encoding='utf-8-sig', low_memory=False)

            # Normalize schema
            tsb_normalized = pd.DataFrame({
                'incident_id': tsb_df['OccID'] if 'OccID' in tsb_df else '',
                'date': pd.to_datetime(tsb_df['OccDate'], errors='coerce') if 'OccDate' in tsb_df else None,
                'vessel_name': '',  # Not in TSB occurrence table
                'description': tsb_df['Summary'] if 'Summary' in tsb_df else '',
                'severity': tsb_df['OccClassDisplayEng'] if 'OccClassDisplayEng' in tsb_df else 'Unknown',
                'location': tsb_df['ProvinceDisplayEng'] if 'ProvinceDisplayEng' in tsb_df else '',
                'fatalities': tsb_df['TotalDeaths'] if 'TotalDeaths' in tsb_df else 0,
                'injuries': (tsb_df['TotalMinorInjuries'].fillna(0) +
                           tsb_df['TotalSeriousInjuries'].fillna(0)) if 'TotalMinorInjuries' in tsb_df else 0,
                'incident_type': tsb_df['AccIncTypeDisplayEng'] if 'AccIncTypeDisplayEng' in tsb_df else '',
                'source': 'Canadian TSB'
            })
            all_incidents.append(tsb_normalized)
            logger.info(f"Loaded {len(tsb_normalized)} Canadian TSB incidents")
    except Exception as e:
        logger.error(f"Error loading Canadian TSB data: {e}")

    # 2. Load DLP Historical accidents data
    try:
        dlp_file = Path('data/modules/marine_safety/raw/dlp_historical/Accidents_1995-2012.csv')
        if dlp_file.exists():
            logger.info(f"Loading DLP Historical data from {dlp_file}")
            dlp_df = pd.read_csv(dlp_file, encoding='utf-8-sig', low_memory=False)

            # Normalize schema
            dlp_normalized = pd.DataFrame({
                'incident_id': dlp_df['BARDID'] if 'BARDID' in dlp_df else '',
                'date': pd.to_datetime(dlp_df['Date'], errors='coerce') if 'Date' in dlp_df else None,
                'vessel_name': '',  # Not in accidents table
                'description': dlp_df['Redactednarrative'] if 'Redactednarrative' in dlp_df else '',
                'severity': 'Unknown',
                'location': (dlp_df['NameofBodyofWater'].fillna('') + ', ' +
                           dlp_df['State'].fillna('')) if 'NameofBodyofWater' in dlp_df else '',
                'fatalities': dlp_df['Numberdeaths'].fillna(0) if 'Numberdeaths' in dlp_df else 0,
                'injuries': dlp_df['Numberinjured'].fillna(0) if 'Numberinjured' in dlp_df else 0,
                'incident_type': dlp_df['AccidentEvent1'] if 'AccidentEvent1' in dlp_df else '',
                'source': 'DLP Historical'
            })
            all_incidents.append(dlp_normalized)
            logger.info(f"Loaded {len(dlp_normalized)} DLP Historical incidents")
    except Exception as e:
        logger.error(f"Error loading DLP Historical data: {e}")

    # 3. Load IMO GISIS data (use collated file if available)
    try:
        imo_file = Path('data/modules/marine_safety/raw/imo_gisis/imo_gisis_collated.csv')
        if imo_file.exists():
            logger.info(f"Loading IMO GISIS data from {imo_file}")
            imo_df = pd.read_csv(imo_file, encoding='utf-8-sig', low_memory=False)

            # Normalize schema
            imo_normalized = pd.DataFrame({
                'incident_id': imo_df['Reference'] if 'Reference' in imo_df else '',
                'date': pd.to_datetime(imo_df['Occurrence date and time'], errors='coerce') if 'Occurrence date and time' in imo_df else None,
                'vessel_name': imo_df['Ships involved'] if 'Ships involved' in imo_df else '',
                'description': imo_df['Casualty event'] if 'Casualty event' in imo_df else '',
                'severity': imo_df['Casualty severity'] if 'Casualty severity' in imo_df else 'Unknown',
                'location': imo_df['Place'] if 'Place' in imo_df else '',
                'fatalities': 0,  # Not directly available in IMO data
                'injuries': 0,  # Not directly available in IMO data
                'incident_type': imo_df['Casualty event'] if 'Casualty event' in imo_df else '',
                'source': 'IMO GISIS'
            })
            all_incidents.append(imo_normalized)
            logger.info(f"Loaded {len(imo_normalized)} IMO GISIS incidents")
    except Exception as e:
        logger.error(f"Error loading IMO GISIS data: {e}")

    # Combine all incidents
    if all_incidents:
        combined_df = pd.concat(all_incidents, ignore_index=True)
        logger.info(f"Combined total: {len(combined_df)} incidents from all sources")

        # Remove rows with no description
        combined_df = combined_df[combined_df['description'].notna() & (combined_df['description'] != '')]
        logger.info(f"After removing empty descriptions: {len(combined_df)} incidents")

        # Separate into incident types (will be detected by LLM/regex later)
        data['all_incidents'] = combined_df
        data['hatch'] = combined_df  # Will filter in analysis
        data['foundering'] = combined_df[combined_df['incident_type'].str.contains('founder|capsize|sinking', case=False, na=False)]
        data['fatality'] = combined_df[combined_df['fatalities'] > 0]

        logger.info(f"Potential foundering incidents: {len(data['foundering'])}")
        logger.info(f"Fatal incidents: {len(data['fatality'])}")
    else:
        logger.warning("No incident data loaded")
        data['hatch'] = pd.DataFrame()
        data['foundering'] = pd.DataFrame()
        data['fatality'] = pd.DataFrame()

    return data


def analyze_hatch_incidents(df: pd.DataFrame, use_llm: bool = False):
    """Analyze hatch maloperation incidents using LLM or regex detection."""
    if df.empty:
        return {
            'total': 0,
            'detected': 0,
            'by_severity': {},
            'by_month': {},
            'detection_method': 'none'
        }

    results = {
        'total': len(df),
        'detected': 0,
        'true_positives': 0,
        'false_positives': 0,
        'true_negatives': 0,
        'false_negatives': 0,
        'by_severity': {},
        'by_month': {},
        'detection_details': [],
        'detection_method': 'llm' if use_llm else 'regex'
    }

    if not ANALYZER_AVAILABLE:
        logger.warning("HatchMaloperationAnalyzer not available, skipping detailed analysis")
        results['detection_method'] = 'unavailable'
        return results

    # Initialize analyzer
    try:
        analyzer = HatchMaloperationAnalyzer(
            use_llm=use_llm,
            llm_confidence_threshold=0.7,
            fallback_to_regex=True
        )
        logger.info(f"Initialized analyzer with LLM={use_llm}")
    except Exception as e:
        logger.error(f"Failed to initialize analyzer: {e}")
        results['detection_method'] = 'error'
        return results

    # Analyze each incident
    logger.info(f"Analyzing {len(df)} incidents for hatch maloperation...")
    for idx, row in df.iterrows():
        if idx > 0 and idx % 10000 == 0:
            logger.info(f"  Processed {idx}/{len(df)} incidents, detected {results['detected']} hatch incidents so far")

        incident = {
            'description': row['description'],
            'incident_id': row['incident_id']
        }

        # Get detailed detection results
        result = analyzer.is_hatch_maloperation_incident(incident, return_details=True)

        is_detected = result['is_hatch_incident']

        # Update statistics
        if is_detected:
            results['detected'] += 1

            # Store detection details for detected hatch incidents
            details = {
                'incident_id': row['incident_id'],
                'detected': is_detected,
                'method': result.get('detection_method', 'unknown'),
                'confidence': result.get('llm_confidence', 0.0),
                'severity': row.get('severity', 'Unknown'),
                'date': row['date'],
                'source': row.get('source', 'Unknown'),
                'description': row['description'][:200]  # Truncate for display
            }
            results['detection_details'].append(details)

            # By severity
            severity = row.get('severity', 'Unknown')
            if severity not in results['by_severity']:
                results['by_severity'][severity] = 0
            if is_detected:
                results['by_severity'][severity] += 1

            # By month
            month = row['date'].strftime('%Y-%m')
            if month not in results['by_month']:
                results['by_month'][month] = 0
            if is_detected:
                results['by_month'][month] += 1

    # Calculate detection statistics
    stats = analyzer.get_detection_statistics()
    results['stats'] = stats

    return results


def generate_smart_summary(description: str, max_length: int = 150) -> str:
    """
    Generate an intelligent summary from incident description.
    Extracts key information: what happened, where, vessel, outcome.
    """
    if not description or pd.isna(description):
        return "No description available"

    desc = str(description).strip()

    # If description is short enough, return as-is
    if len(desc) <= max_length:
        return desc

    # Extract key phrases and information
    import re

    # Try to extract vessel name if mentioned
    vessel_match = re.search(r'(?:vessel|ship|boat|MV|M/V|F/V)\s+["\']?([A-Z][A-Za-z0-9\s-]+)["\']?', desc, re.IGNORECASE)
    vessel = vessel_match.group(1).strip() if vessel_match else None

    # Try to extract location
    location_match = re.search(r'(?:in|at|near|off|on)\s+([A-Z][A-Za-z\s,]+?)(?:\.|,|\s+(?:when|during|the|and|with))', desc)
    location = location_match.group(1).strip() if location_match else None

    # Key incident indicators
    incident_keywords = {
        'hatch': ['hatch', 'opening', 'door', 'cover', 'access', 'seal', 'closure'],
        'flooding': ['flood', 'water', 'ingress', 'leak', 'breach'],
        'capsize': ['capsize', 'overturn', 'roll', 'list'],
        'founder': ['founder', 'sink', 'sank', 'submerge'],
        'fire': ['fire', 'explosion', 'burn', 'smoke'],
        'collision': ['collision', 'collide', 'struck', 'hit', 'contact'],
        'grounding': ['ground', 'aground', 'strand'],
        'injury': ['injur', 'fatal', 'death', 'killed', 'crew member'],
        'mechanical': ['engine', 'propulsion', 'machinery', 'equipment', 'failure']
    }

    desc_lower = desc.lower()
    detected_types = []
    for incident_type, keywords in incident_keywords.items():
        if any(kw in desc_lower for kw in keywords):
            detected_types.append(incident_type)

    # Build smart summary
    parts = []

    if detected_types:
        parts.append(detected_types[0].capitalize())

    if vessel:
        parts.append(f"on {vessel}")

    if location:
        parts.append(f"at {location}")

    # Extract outcome/result if mentioned
    outcome_patterns = [
        r'result(?:ed|ing)?\s+in\s+([^.;]+)',
        r'caus(?:ed|ing)\s+([^.;]+)',
        r'led\s+to\s+([^.;]+)',
        r'(\d+\s+(?:crew|person|people|death|fatal|injur))',
    ]

    for pattern in outcome_patterns:
        outcome_match = re.search(pattern, desc, re.IGNORECASE)
        if outcome_match:
            outcome = outcome_match.group(1).strip()[:50]
            parts.append(f"- {outcome}")
            break

    if parts:
        summary = ' '.join(parts)
        if len(summary) <= max_length:
            return summary
        else:
            return summary[:max_length-3] + "..."

    # Fallback: Return first sentence or first max_length chars
    sentences = re.split(r'[.!?]+\s+', desc)
    if sentences and len(sentences[0]) <= max_length:
        return sentences[0] + "."

    return desc[:max_length-3] + "..."


def analyze_founderings(df: pd.DataFrame):
    """Analyze foundering incidents."""
    if df.empty:
        return {'total': 0, 'total_fatalities': 0, 'by_month': {}, 'avg_fatalities': 0}

    results = {
        'total': len(df),
        'total_fatalities': df['fatalities'].sum(),
        'avg_fatalities': df['fatalities'].mean(),
        'by_month': {},
        'by_fatality_range': {'0': 0, '1-2': 0, '3-5': 0, '6+': 0}
    }

    # By month
    df['month'] = df['date'].dt.to_period('M').astype(str)
    monthly = df.groupby('month').agg({
        'incident_id': 'count',
        'fatalities': 'sum'
    }).to_dict('index')
    results['by_month'] = monthly

    # By fatality range
    for _, row in df.iterrows():
        deaths = row['fatalities']
        if deaths == 0:
            results['by_fatality_range']['0'] += 1
        elif deaths <= 2:
            results['by_fatality_range']['1-2'] += 1
        elif deaths <= 5:
            results['by_fatality_range']['3-5'] += 1
        else:
            results['by_fatality_range']['6+'] += 1

    return results


def analyze_fatalities(df: pd.DataFrame):
    """Analyze fatality incidents."""
    if df.empty:
        return {'total': 0, 'total_deaths': 0, 'by_cause': {}, 'by_month': {}, 'by_source': {}}

    results = {
        'total': len(df),
        'total_deaths': int(df['fatalities'].sum()),
        'by_cause': {},
        'by_month': {},
        'by_source': {}
    }

    # By cause of death (if available in data)
    if 'cause_of_death' in df.columns:
        cause_counts = df['cause_of_death'].value_counts().to_dict()
        results['by_cause'] = cause_counts
    else:
        # Group by incident type as proxy for cause
        if 'incident_type' in df.columns:
            cause_counts = df['incident_type'].value_counts().head(10).to_dict()
            results['by_cause'] = cause_counts

    # By data source
    if 'source' in df.columns:
        source_counts = df.groupby('source').agg({
            'incident_id': 'count',
            'fatalities': 'sum'
        }).to_dict('index')
        results['by_source'] = source_counts

    # By month
    df_copy = df.copy()
    df_copy['month'] = df_copy['date'].dt.to_period('M').astype(str)
    monthly = df_copy.groupby('month').agg({
        'incident_id': 'count',
        'fatalities': 'sum'
    }).to_dict('index')
    results['by_month'] = monthly

    return results


def create_hatch_visualizations(df: pd.DataFrame, analysis: dict):
    """Create interactive visualizations for hatch incidents."""
    figs = []

    if df.empty or analysis['detected'] == 0:
        return figs

    # Create dataframe from detection details
    if not analysis.get('detection_details'):
        return figs

    detected_df = pd.DataFrame(analysis['detection_details'])

    # 1. Detection by severity
    if analysis['by_severity']:
        severity_fig = go.Figure(data=[
            go.Bar(
                x=list(analysis['by_severity'].keys()),
                y=list(analysis['by_severity'].values()),
                marker_color=['#ff4444', '#ff9944', '#ffdd44'],
                text=list(analysis['by_severity'].values()),
                textposition='outside'
            )
        ])
        severity_fig.update_layout(
            title='Hatch Maloperation Incidents by Severity',
            xaxis_title='Severity Level',
            yaxis_title='Number of Incidents',
            template='plotly_white',
            height=400
        )
        figs.append(('severity', severity_fig))

    # 2. Trend over time
    if not detected_df.empty:
        detected_df['month'] = detected_df['date'].dt.to_period('M').astype(str)
        monthly_counts = detected_df.groupby('month').size().reset_index(name='count')

        trend_fig = go.Figure(data=[
            go.Scatter(
                x=monthly_counts['month'],
                y=monthly_counts['count'],
                mode='lines+markers',
                line=dict(color='#ff4444', width=3),
                marker=dict(size=10),
                name='Incidents'
            )
        ])
        trend_fig.update_layout(
            title='Hatch Maloperation Incidents - Monthly Trend',
            xaxis_title='Month',
            yaxis_title='Number of Incidents',
            template='plotly_white',
            height=400
        )
        figs.append(('trend', trend_fig))

    # 3. Detection method breakdown (if using LLM)
    if 'stats' in analysis and analysis['detection_method'] == 'llm':
        stats = analysis['stats']
        method_fig = go.Figure(data=[
            go.Pie(
                labels=['LLM Detection', 'Regex Detection', 'Hybrid Detection'],
                values=[
                    stats.get('llm_detections', 0),
                    stats.get('regex_detections', 0),
                    stats.get('hybrid_detections', 0)
                ],
                marker_colors=['#4444ff', '#ff4444', '#44ff44'],
                hole=0.4
            )
        ])
        method_fig.update_layout(
            title='Detection Method Distribution',
            template='plotly_white',
            height=400
        )
        figs.append(('methods', method_fig))

    return figs


def create_foundering_visualizations(df: pd.DataFrame, analysis: dict):
    """Create interactive visualizations for foundering incidents."""
    figs = []

    if df.empty:
        return figs

    # 1. Fatalities by incident
    fatality_fig = go.Figure(data=[
        go.Bar(
            x=df['vessel_name'],
            y=df['fatalities'],
            marker_color=df['fatalities'].apply(
                lambda x: '#44ff44' if x == 0 else '#ffdd44' if x <= 2 else '#ff9944' if x <= 5 else '#ff4444'
            ),
            text=df['fatalities'],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Fatalities: %{y}<extra></extra>'
        )
    ])
    fatality_fig.update_layout(
        title='Fatalities per Foundering Incident',
        xaxis_title='Vessel',
        yaxis_title='Number of Fatalities',
        template='plotly_white',
        height=500,
        xaxis_tickangle=-45
    )
    figs.append(('fatalities', fatality_fig))

    # 2. Monthly trend
    df['month'] = df['date'].dt.to_period('M').astype(str)
    monthly = df.groupby('month').agg({
        'incident_id': 'count',
        'fatalities': 'sum'
    }).reset_index()
    monthly.columns = ['month', 'incidents', 'fatalities']

    trend_fig = make_subplots(specs=[[{"secondary_y": True}]])
    trend_fig.add_trace(
        go.Bar(x=monthly['month'], y=monthly['incidents'], name='Incidents', marker_color='#4444ff'),
        secondary_y=False
    )
    trend_fig.add_trace(
        go.Scatter(x=monthly['month'], y=monthly['fatalities'], name='Fatalities',
                  mode='lines+markers', line=dict(color='#ff4444', width=3)),
        secondary_y=True
    )
    trend_fig.update_layout(
        title='Foundering Incidents and Fatalities - Monthly Trend',
        template='plotly_white',
        height=400
    )
    trend_fig.update_xaxes(title_text='Month')
    trend_fig.update_yaxes(title_text='Number of Incidents', secondary_y=False)
    trend_fig.update_yaxes(title_text='Total Fatalities', secondary_y=True)
    figs.append(('trend', trend_fig))

    return figs


def create_fatality_visualizations(df: pd.DataFrame, analysis: dict):
    """Create interactive visualizations for fatality incidents."""
    figs = []

    if df.empty:
        return figs

    # 1. Fatalities by cause
    cause_fig = go.Figure(data=[
        go.Bar(
            x=list(analysis['by_cause'].keys()),
            y=list(analysis['by_cause'].values()),
            marker_color='#ff4444',
            text=list(analysis['by_cause'].values()),
            textposition='outside'
        )
    ])
    cause_fig.update_layout(
        title='Fatalities by Cause of Death',
        xaxis_title='Cause of Death',
        yaxis_title='Number of Incidents',
        template='plotly_white',
        height=500,
        xaxis_tickangle=-45
    )
    figs.append(('causes', cause_fig))

    # 2. Monthly trend
    df['month'] = df['date'].dt.to_period('M').astype(str)
    monthly = df.groupby('month').agg({
        'incident_id': 'count',
        'fatalities': 'sum'
    }).reset_index()
    monthly.columns = ['month', 'incidents', 'total_fatalities']

    trend_fig = make_subplots(specs=[[{"secondary_y": True}]])
    trend_fig.add_trace(
        go.Bar(x=monthly['month'], y=monthly['incidents'], name='Incidents', marker_color='#4444ff'),
        secondary_y=False
    )
    trend_fig.add_trace(
        go.Scatter(x=monthly['month'], y=monthly['total_fatalities'], name='Total Fatalities',
                  mode='lines+markers', line=dict(color='#ff4444', width=3)),
        secondary_y=True
    )
    trend_fig.update_layout(
        title='Fatality Incidents - Monthly Trend',
        template='plotly_white',
        height=400
    )
    trend_fig.update_xaxes(title_text='Month')
    trend_fig.update_yaxes(title_text='Number of Incidents', secondary_y=False)
    trend_fig.update_yaxes(title_text='Total Fatalities', secondary_y=True)
    figs.append(('trend', trend_fig))

    return figs


def generate_executive_summary(data: dict, analyses: dict, output_dir: Path, use_llm: bool):
    """Generate executive summary HTML report."""

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Marine Safety Incident Analysis - Executive Summary</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .header p {{
            margin: 10px 0 0 0;
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h3 {{
            margin: 0 0 15px 0;
            color: #1e3c72;
            font-size: 1.2em;
        }}
        .card .number {{
            font-size: 3em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .card .label {{
            color: #666;
            font-size: 0.9em;
        }}
        .card.critical .number {{ color: #ff4444; }}
        .card.warning .number {{ color: #ff9944; }}
        .card.info .number {{ color: #4444ff; }}
        .card.success .number {{ color: #44ff44; }}

        .section {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #1e3c72;
            border-bottom: 3px solid #1e3c72;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        .key-findings {{
            background: #fff8e1;
            border-left: 5px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
        }}
        .key-findings h3 {{
            margin-top: 0;
            color: #f57c00;
        }}
        .key-findings ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .recommendations {{
            background: #e8f5e9;
            border-left: 5px solid #4caf50;
            padding: 15px;
            margin: 20px 0;
        }}
        .recommendations h3 {{
            margin-top: 0;
            color: #2e7d32;
        }}
        .badge {{
            display: inline-block;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 0.85em;
            font-weight: bold;
            margin-right: 5px;
        }}
        .badge.llm {{
            background: #4444ff;
            color: white;
        }}
        .badge.regex {{
            background: #ff9944;
            color: white;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #1e3c72;
            color: white;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚢 Marine Safety Incident Analysis</h1>
        <p>Executive Summary Report</p>
        <p>Generated: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}</p>
        <p>Analysis Method: <span class="badge {'llm' if use_llm else 'regex'}">{'LLM-Enhanced Detection' if use_llm else 'Regex Pattern Matching'}</span></p>
    </div>

    <div class="summary-cards">
        <div class="card critical">
            <h3>Hatch Maloperation</h3>
            <div class="number">{analyses['hatch']['detected']}</div>
            <div class="label">Incidents Detected</div>
        </div>
        <div class="card critical">
            <h3>Foundering Events</h3>
            <div class="number">{analyses['foundering']['total']}</div>
            <div class="label">Total Incidents</div>
        </div>
        <div class="card critical">
            <h3>Fatalities</h3>
            <div class="number">{analyses['fatality']['total_deaths']}</div>
            <div class="label">Total Deaths</div>
        </div>
        <div class="card warning">
            <h3>Foundering Deaths</h3>
            <div class="number">{analyses['foundering']['total_fatalities']}</div>
            <div class="label">Lives Lost at Sea</div>
        </div>
    </div>

    <div class="section">
        <h2>📊 Hatch Maloperation Analysis</h2>
        <p>Analysis of incidents involving hatch and opening malfunctions using {'LLM-based semantic detection' if use_llm else 'regex pattern matching'}.</p>

        <div class="key-findings">
            <h3>Key Findings</h3>
            <ul>
                <li><strong>{analyses['hatch']['detected']}</strong> hatch maloperation incidents detected out of {analyses['hatch']['total']} total incidents analyzed</li>
"""

    if 'stats' in analyses['hatch'] and use_llm:
        stats = analyses['hatch']['stats']
        html += f"""
                <li><strong>Detection Methods:</strong>
                    <ul>
                        <li>LLM-based: {stats.get('llm_detections', 0)} incidents ({stats.get('llm_percentage', 0):.1f}%)</li>
                        <li>Regex-based: {stats.get('regex_detections', 0)} incidents ({stats.get('regex_percentage', 0):.1f}%)</li>
                        <li>Hybrid (both): {stats.get('hybrid_detections', 0)} incidents ({stats.get('hybrid_percentage', 0):.1f}%)</li>
                    </ul>
                </li>
"""

    if analyses['hatch']['by_severity']:
        html += f"""
                <li><strong>By Severity:</strong>
                    <ul>
"""
        for severity, count in sorted(analyses['hatch']['by_severity'].items(), key=lambda x: x[1], reverse=True):
            html += f"                        <li>{severity}: {count} incidents</li>\n"
        html += """
                    </ul>
                </li>
"""

    # Calculate detection accuracy if we have true/false positives/negatives
    if analyses['hatch']['total'] > 0:
        tp = analyses['hatch'].get('true_positives', 0)
        tn = analyses['hatch'].get('true_negatives', 0)
        fp = analyses['hatch'].get('false_positives', 0)
        fn = analyses['hatch'].get('false_negatives', 0)

        total_actual_hatch = tp + fn
        total_non_hatch = tn + fp

        if total_actual_hatch > 0:
            recall = (tp / total_actual_hatch) * 100
            precision = (tp / (tp + fp)) * 100 if (tp + fp) > 0 else 0

            html += f"""
                <li><strong>Detection Accuracy:</strong>
                    <ul>
                        <li>Precision: {precision:.1f}% ({tp} true positives, {fp} false positives)</li>
                        <li>Recall: {recall:.1f}% ({tp} detected, {fn} missed)</li>
                    </ul>
                </li>
"""

    html += """
            </ul>
        </div>

        <div class="recommendations">
            <h3>Recommendations</h3>
            <ul>
                <li><strong>Immediate:</strong> Implement mandatory hatch closure verification procedures before departure</li>
                <li><strong>Short-term:</strong> Conduct comprehensive training on watertight integrity maintenance</li>
                <li><strong>Long-term:</strong> Install automated hatch monitoring systems with bridge alarms</li>
            </ul>
        </div>
    </div>

    <div class="section">
        <h2>⚓ Foundering Incident Analysis</h2>
        <p>Analysis of vessel foundering events and associated fatalities.</p>

        <div class="key-findings">
            <h3>Key Findings</h3>
            <ul>
"""

    html += f"""
                <li><strong>{analyses['foundering']['total']}</strong> foundering incidents recorded</li>
                <li><strong>{analyses['foundering']['total_fatalities']}</strong> total fatalities from founderings</li>
                <li><strong>{analyses['foundering']['avg_fatalities']:.1f}</strong> average fatalities per foundering incident</li>
"""

    if analyses['foundering']['by_fatality_range']:
        html += """
                <li><strong>Fatality Distribution:</strong>
                    <ul>
"""
        for range_label, count in analyses['foundering']['by_fatality_range'].items():
            html += f"                        <li>{range_label} fatalities: {count} incidents</li>\n"
        html += """
                    </ul>
                </li>
"""

    html += """
            </ul>
        </div>

        <div class="recommendations">
            <h3>Recommendations</h3>
            <ul>
                <li><strong>Immediate:</strong> Review and enhance emergency evacuation procedures</li>
                <li><strong>Short-term:</strong> Conduct lifeboat and life raft drills more frequently</li>
                <li><strong>Long-term:</strong> Implement real-time stability monitoring systems</li>
            </ul>
        </div>
    </div>

    <div class="section">
        <h2>💀 Fatality Incident Analysis</h2>
        <p>Analysis of fatal incidents aboard vessels.</p>

        <div class="key-findings">
            <h3>Key Findings</h3>
            <ul>
"""

    html += f"""
                <li><strong>{analyses['fatality']['total']}</strong> fatal incidents recorded</li>
                <li><strong>{analyses['fatality']['total_deaths']}</strong> total fatalities</li>
"""

    if analyses['fatality']['by_cause']:
        html += """
                <li><strong>Leading Causes of Death:</strong>
                    <ul>
"""
        sorted_causes = sorted(analyses['fatality']['by_cause'].items(), key=lambda x: x[1], reverse=True)
        for cause, count in sorted_causes[:5]:  # Top 5 causes
            html += f"                        <li>{cause}: {count} incidents</li>\n"
        html += """
                    </ul>
                </li>
"""

    html += """
            </ul>
        </div>

        <div class="recommendations">
            <h3>Recommendations</h3>
            <ul>
                <li><strong>Immediate:</strong> Reinforce confined space entry procedures and permit systems</li>
                <li><strong>Short-term:</strong> Implement comprehensive safety equipment audits</li>
                <li><strong>Long-term:</strong> Develop predictive safety analytics program</li>
            </ul>
        </div>
    </div>

    <div class="section">
        <h2>📈 Detailed Reports</h2>
        <p>For detailed analysis including interactive visualizations, please refer to the following reports:</p>
        <ul>
            <li><a href="hatch_analysis.html">Hatch Maloperation Analysis Report</a></li>
            <li><a href="foundering_analysis.html">Foundering Incident Analysis Report</a></li>
            <li><a href="fatality_analysis.html">Fatality Incident Analysis Report</a></li>
        </ul>
    </div>

    <div class="footer">
        <p>This report was generated automatically using {'LLM-enhanced incident detection' if use_llm else 'regex-based pattern matching'}.</p>
        <p>WorldEnergyData Marine Safety Analysis Module v2.0.0</p>
    </div>
</body>
</html>
"""

    output_file = output_dir / 'executive_summary.html'
    output_file.write_text(html)
    logger.info(f"Executive summary saved to {output_file}")


def generate_detailed_report(incident_type: str, df: pd.DataFrame, analysis: dict,
                            visualizations: list, output_dir: Path, use_llm: bool):
    """Generate detailed HTML report for specific incident type."""

    title_map = {
        'hatch': 'Hatch Maloperation Incidents',
        'foundering': 'Foundering Incidents',
        'fatality': 'Fatality Incidents'
    }

    title = title_map.get(incident_type, 'Incident Analysis')

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Detailed Analysis</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .section {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #1e3c72;
            border-bottom: 3px solid #1e3c72;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        .plot-container {{
            margin: 30px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #1e3c72;
            color: white;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}

        /* Enhanced description styles */
        .description-cell {{
            max-width: 600px;
            position: relative;
        }}

        .description-summary {{
            font-size: 0.95em;
            color: #333;
            line-height: 1.4;
        }}

        .view-full-btn {{
            display: inline-block;
            margin-left: 8px;
            padding: 3px 10px;
            font-size: 0.75em;
            background: #2a5298;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.2s;
        }}

        .view-full-btn:hover {{
            background: #1e3c72;
        }}

        /* Tooltip for hover */
        .description-cell[title] {{
            cursor: help;
        }}

        /* Modal for full description */
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0,0,0,0.75);
            animation: fadeIn 0.3s;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}

        .modal-content {{
            background-color: white;
            margin: 3% auto;
            padding: 0;
            border-radius: 12px;
            max-width: 900px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            animation: slideIn 0.3s;
        }}

        @keyframes slideIn {{
            from {{
                transform: translateY(-50px);
                opacity: 0;
            }}
            to {{
                transform: translateY(0);
                opacity: 1;
            }}
        }}

        .modal-header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 25px 30px;
            border-radius: 12px 12px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .modal-header h2 {{
            margin: 0;
            font-size: 1.8em;
        }}

        .close {{
            color: white;
            font-size: 40px;
            font-weight: bold;
            cursor: pointer;
            transition: color 0.2s, transform 0.2s;
            line-height: 1;
        }}

        .close:hover {{
            color: #ff6b6b;
            transform: scale(1.1);
        }}

        .modal-body {{
            padding: 30px;
            line-height: 1.8;
            font-size: 1.05em;
            color: #444;
        }}

        .incident-meta {{
            background: #f0f4f8;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 25px;
            border-left: 4px solid #2a5298;
        }}

        .incident-meta p {{
            margin: 8px 0;
            font-size: 0.95em;
        }}

        .incident-meta strong {{
            color: #1e3c72;
            margin-right: 10px;
            min-width: 100px;
            display: inline-block;
        }}

        .incident-description {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }}

        .incident-description h3 {{
            color: #1e3c72;
            margin-top: 0;
            margin-bottom: 15px;
            font-size: 1.2em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p>Detailed Analysis Report</p>
        <p>Generated: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}</p>
    </div>

    <!-- Modal for full incident details -->
    <div id="incidentModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Incident Details</h2>
                <span class="close" onclick="closeModal()">&times;</span>
            </div>
            <div class="modal-body" id="modalBodyContent">
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Interactive Visualizations</h2>
"""

    # Add visualizations
    for viz_name, fig in visualizations:
        html += f'        <div class="plot-container" id="plot-{viz_name}"></div>\n'

    html += """
    </div>

    <div class="section">
        <h2>Incident Details</h2>
        <table>
            <thead>
                <tr>
"""

    # Add table headers based on incident type
    if incident_type == 'hatch':
        html += """
                    <th>Incident ID</th>
                    <th>Date</th>
                    <th>Vessel</th>
                    <th>Description</th>
                    <th>Severity</th>
"""
    elif incident_type == 'foundering':
        html += """
                    <th>Incident ID</th>
                    <th>Date</th>
                    <th>Vessel</th>
                    <th>Description</th>
                    <th>Fatalities</th>
"""
    elif incident_type == 'fatality':
        html += """
                    <th>Incident ID</th>
                    <th>Date</th>
                    <th>Vessel</th>
                    <th>Description</th>
                    <th>Cause of Death</th>
"""

    html += """
                </tr>
            </thead>
            <tbody>
"""

    # Add table rows with enhanced descriptions
    for idx, row in df.iterrows():
        html += "                <tr>\n"
        html += f"                    <td>{row['incident_id']}</td>\n"

        # Handle null dates
        date_str = row['date'].strftime('%Y-%m-%d') if pd.notna(row['date']) else 'Unknown'
        html += f"                    <td>{date_str}</td>\n"

        # Handle missing vessel names
        vessel = row.get('vessel_name', '') if pd.notna(row.get('vessel_name')) else ''
        html += f"                    <td>{vessel if vessel else 'Unknown'}</td>\n"

        # Enhanced description with smart summary and modal
        full_description = str(row['description']) if pd.notna(row['description']) else 'No description available'
        smart_summary = generate_smart_summary(full_description, max_length=150)

        # Escape HTML characters for tooltip and modal
        full_desc_escaped = full_description.replace('"', '&quot;').replace("'", "&#39;").replace('<', '&lt;').replace('>', '&gt;')
        summary_escaped = smart_summary.replace('"', '&quot;').replace("'", "&#39;")

        # Build incident data for modal as a JavaScript object literal
        import json
        incident_data = {
            'id': str(row['incident_id']),
            'date': date_str,
            'vessel': vessel if vessel else 'Unknown',
            'description': full_desc_escaped,
            'severity': str(row.get('severity', 'N/A')),
            'location': str(row.get('location', 'Unknown')),
            'fatalities': str(int(row['fatalities'])) if pd.notna(row.get('fatalities')) else '0',
            'injuries': str(int(row.get('injuries', 0))) if pd.notna(row.get('injuries')) else '0',
            'source': str(row.get('source', 'Unknown'))
        }

        # Convert to JSON string for JavaScript
        incident_json = json.dumps(incident_data)

        html += f'''                    <td class="description-cell" title="{full_desc_escaped[:500]}...">
                        <div class="description-summary">{summary_escaped}</div>
                        <button class="view-full-btn" onclick='showIncidentDetails({incident_json})'>View Full Details</button>
                    </td>\n'''

        if incident_type == 'hatch':
            html += f"                    <td>{row.get('severity', 'N/A')}</td>\n"
        elif incident_type == 'foundering':
            fatalities = int(row['fatalities']) if pd.notna(row.get('fatalities')) else 0
            html += f"                    <td>{fatalities}</td>\n"
        elif incident_type == 'fatality':
            # Use incident_type as proxy for cause since cause_of_death column doesn't exist in real data
            cause = row.get('incident_type', 'Unknown') if 'incident_type' in row else 'Unknown'
            html += f"                    <td>{cause}</td>\n"

        html += "                </tr>\n"

    html += """
            </tbody>
        </table>
    </div>

    <script>
"""

    # Add visualization scripts
    for viz_name, fig in visualizations:
        plot_json = fig.to_json()
        html += f"""
        Plotly.newPlot('plot-{viz_name}', {plot_json});
"""

    # Add modal JavaScript functions
    html += """

        // Modal functions for incident details
        function showIncidentDetails(incident) {
            const modal = document.getElementById('incidentModal');
            const modalBody = document.getElementById('modalBodyContent');

            // Build modal content with incident details
            modalBody.innerHTML = `
                <div class="incident-meta">
                    <p><strong>Incident ID:</strong> ${{incident.id}}</p>
                    <p><strong>Date:</strong> ${{incident.date}}</p>
                    <p><strong>Vessel:</strong> ${{incident.vessel}}</p>
                    <p><strong>Location:</strong> ${{incident.location}}</p>
                    <p><strong>Data Source:</strong> ${{incident.source}}</p>
                    <p><strong>Severity:</strong> ${{incident.severity}}</p>
                    <p><strong>Fatalities:</strong> ${{incident.fatalities}} | <strong>Injuries:</strong> ${{incident.injuries}}</p>
                </div>
                <div class="incident-description">
                    <h3>Full Incident Description</h3>
                    <p>${{incident.description}}</p>
                </div>
            `;

            modal.style.display = 'block';
        }

        function closeModal() {
            const modal = document.getElementById('incidentModal');
            modal.style.display = 'none';
        }

        // Close modal when clicking outside of it
        window.onclick = function(event) {
            const modal = document.getElementById('incidentModal');
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        }}

        // Close modal with Escape key
        document.addEventListener('keydown', function(event) {{
            if (event.key === 'Escape') {{
                closeModal();
            }}
        }});
    </script>
</body>
</html>
"""

    output_file = output_dir / f'{incident_type}_analysis.html'
    output_file.write_text(html)
    logger.info(f"Detailed report saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Generate marine safety incident reports')
    parser.add_argument('--input-dir', type=Path, required=False, default=None,
                       help='Directory containing incident CSV files (optional, uses real data by default)')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Directory for output reports')
    parser.add_argument('--use-llm', type=str, default='false',
                       help='Use LLM-based detection (true/false)')

    args = parser.parse_args()

    # Convert use_llm string to boolean
    use_llm = args.use_llm.lower() in ('true', 'yes', '1')

    logger.info("="*60)
    logger.info("Marine Safety Incident Analysis Report Generator")
    logger.info("="*60)
    logger.info(f"Data source: Real incident databases (Canadian TSB, DLP Historical, IMO GISIS)")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"LLM detection: {use_llm}")
    logger.info("")

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Load data (input_dir is now ignored, loads from hardcoded real data sources)
    logger.info("Loading incident data from real databases...")
    data = load_incident_data(args.input_dir)

    # Analyze incidents
    logger.info("Analyzing incidents...")
    analyses = {
        'hatch': analyze_hatch_incidents(data['hatch'], use_llm),
        'foundering': analyze_founderings(data['foundering']),
        'fatality': analyze_fatalities(data['fatality'])
    }

    # Generate visualizations
    logger.info("Creating visualizations...")
    visualizations = {
        'hatch': create_hatch_visualizations(data['hatch'], analyses['hatch']),
        'foundering': create_foundering_visualizations(data['foundering'], analyses['foundering']),
        'fatality': create_fatality_visualizations(data['fatality'], analyses['fatality'])
    }

    # Generate reports
    logger.info("Generating reports...")
    generate_executive_summary(data, analyses, args.output_dir, use_llm)

    for incident_type in ['hatch', 'foundering', 'fatality']:
        if not data[incident_type].empty:
            generate_detailed_report(
                incident_type,
                data[incident_type],
                analyses[incident_type],
                visualizations[incident_type],
                args.output_dir,
                use_llm
            )

    logger.info("")
    logger.info("="*60)
    logger.info("Report generation complete!")
    logger.info("="*60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
