"""
Create visualization prototypes for field-level and well-level data
Based on go-by report analysis
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json

def create_field_level_visualizations():
    """Create field-level visualization prototypes"""
    
    # Sample data based on go-by reports
    fields = ['Jack', 'Julia', 'St. Malo', 'Stones']
    water_depths = [6965, 7087, 7037, 9576]
    well_counts = [11, 7, 16, 16]
    avg_construction_days = [120, 110, 125, 140]
    
    # Create subplots for field comparisons
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Field Water Depths', 'Well Count by Field', 
                       'Average Construction Days', 'Field Complexity Index'),
        specs=[[{'type': 'bar'}, {'type': 'bar'}],
               [{'type': 'bar'}, {'type': 'scatter'}]]
    )
    
    # Water depth comparison
    fig.add_trace(
        go.Bar(x=fields, y=water_depths, name='Water Depth (ft)',
               marker_color='lightblue'),
        row=1, col=1
    )
    
    # Well count comparison
    fig.add_trace(
        go.Bar(x=fields, y=well_counts, name='Number of Wells',
               marker_color='green'),
        row=1, col=2
    )
    
    # Construction days comparison
    fig.add_trace(
        go.Bar(x=fields, y=avg_construction_days, name='Avg Days',
               marker_color='orange'),
        row=2, col=1
    )
    
    # Complexity index (water depth vs construction days)
    fig.add_trace(
        go.Scatter(x=water_depths, y=avg_construction_days, 
                  mode='markers+text', text=fields,
                  textposition='top center',
                  marker=dict(size=15, color=well_counts, 
                            colorscale='Viridis', showscale=True,
                            colorbar=dict(title="Wells"))),
        row=2, col=2
    )
    
    fig.update_layout(
        title_text="Field-Level Data Visualizations",
        height=700,
        showlegend=False
    )
    
    # Save the figure
    output_path = Path("tests/modules/bsee/analysis/comprehensive-report-system/results")
    output_path.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path / "field_level_visualizations.html"))
    
    print(f"Field-level visualizations saved to: {output_path / 'field_level_visualizations.html'}")
    
    return fig

def create_well_level_visualizations():
    """Create well-level visualization prototypes"""
    
    # Generate sample well timeline data
    np.random.seed(42)
    
    # Sample wells from Jack field
    well_names = ['PS001', 'PS002', 'PS003', 'PS004', 'PS005', 
                 'PS006', 'PS007', 'PS008']
    
    # Generate sample dates
    base_date = datetime(2010, 1, 1)
    spud_dates = [base_date + timedelta(days=int(x)) 
                 for x in np.random.uniform(0, 3650, len(well_names))]
    
    construction_days = np.random.uniform(90, 150, len(well_names))
    completion_days = np.random.uniform(20, 50, len(well_names))
    
    # Create Gantt chart for well timeline
    fig = go.Figure()
    
    for i, well in enumerate(well_names):
        start_date = spud_dates[i]
        construction_end = start_date + timedelta(days=int(construction_days[i]))
        completion_end = construction_end + timedelta(days=int(completion_days[i]))
        
        # Construction phase
        fig.add_trace(go.Scatter(
            x=[start_date, construction_end],
            y=[well, well],
            mode='lines',
            line=dict(color='blue', width=10),
            name='Construction',
            showlegend=(i==0),
            hovertext=f'{well}: Construction ({int(construction_days[i])} days)'
        ))
        
        # Completion phase
        fig.add_trace(go.Scatter(
            x=[construction_end, completion_end],
            y=[well, well],
            mode='lines',
            line=dict(color='green', width=10),
            name='Completion',
            showlegend=(i==0),
            hovertext=f'{well}: Completion ({int(completion_days[i])} days)'
        ))
    
    fig.update_layout(
        title="Well Construction and Completion Timeline",
        xaxis_title="Date",
        yaxis_title="Well",
        height=500,
        hovermode='closest'
    )
    
    # Save the timeline
    output_path = Path("tests/modules/bsee/analysis/comprehensive-report-system/results")
    fig.write_html(str(output_path / "well_timeline_visualization.html"))
    
    print(f"Well timeline saved to: {output_path / 'well_timeline_visualization.html'}")
    
    # Create well performance comparison
    fig2 = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Well Construction Days Distribution', 
                       'Construction vs Completion Days'),
        specs=[[{'type': 'box'}, {'type': 'scatter'}]]
    )
    
    # Box plot of construction days
    fig2.add_trace(
        go.Box(y=construction_days, name='Construction Days',
               marker_color='lightblue'),
        row=1, col=1
    )
    
    # Scatter plot of construction vs completion
    fig2.add_trace(
        go.Scatter(x=construction_days, y=completion_days,
                  mode='markers+text', text=well_names,
                  textposition='top center',
                  marker=dict(size=10, color='red')),
        row=1, col=2
    )
    
    fig2.update_xaxes(title_text="Construction Days", row=1, col=2)
    fig2.update_yaxes(title_text="Completion Days", row=1, col=2)
    
    fig2.update_layout(
        title_text="Well-Level Performance Metrics",
        height=400,
        showlegend=False
    )
    
    # Save the performance chart
    fig2.write_html(str(output_path / "well_performance_visualization.html"))
    
    print(f"Well performance saved to: {output_path / 'well_performance_visualization.html'}")
    
    return fig, fig2

def create_production_visualization_prototype():
    """Create production data visualization prototype"""
    
    # Generate sample production data
    dates = pd.date_range(start='2015-01-01', end='2024-12-31', freq='M')
    
    # Sample production curves for different wells
    wells = ['PS001', 'PS002', 'PS003', 'PS004']
    
    fig = go.Figure()
    
    for i, well in enumerate(wells):
        # Generate declining production curve
        peak_rate = np.random.uniform(5000, 15000)
        decline_rate = np.random.uniform(0.01, 0.03)
        production = peak_rate * np.exp(-decline_rate * np.arange(len(dates)))
        
        # Add some noise
        production += np.random.normal(0, production * 0.05)
        production = np.maximum(production, 0)
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=production,
            mode='lines',
            name=well,
            line=dict(width=2)
        ))
    
    fig.update_layout(
        title="Production Rate Over Time by Well",
        xaxis_title="Date",
        yaxis_title="Production Rate (bopd)",
        height=500,
        hovermode='x unified'
    )
    
    # Save the production chart
    output_path = Path("tests/modules/bsee/analysis/comprehensive-report-system/results")
    fig.write_html(str(output_path / "production_visualization.html"))
    
    print(f"Production visualization saved to: {output_path / 'production_visualization.html'}")
    
    return fig

def create_visualization_config():
    """Create configuration for visualization templates"""
    
    config = {
        "visualization_types": {
            "field_level": [
                {
                    "type": "bar_chart",
                    "title": "Field Comparison",
                    "metrics": ["water_depth", "well_count", "avg_construction_days"]
                },
                {
                    "type": "scatter_plot",
                    "title": "Field Complexity Analysis",
                    "x_axis": "water_depth",
                    "y_axis": "construction_days",
                    "size": "well_count"
                },
                {
                    "type": "pie_chart",
                    "title": "Well Distribution by Field",
                    "values": "well_count",
                    "labels": "field_name"
                }
            ],
            "well_level": [
                {
                    "type": "gantt_chart",
                    "title": "Well Construction Timeline",
                    "phases": ["spud", "construction", "completion", "production"]
                },
                {
                    "type": "box_plot",
                    "title": "Well Performance Distribution",
                    "metrics": ["construction_days", "completion_days", "total_days"]
                },
                {
                    "type": "heatmap",
                    "title": "Well Activity Matrix",
                    "rows": "well_name",
                    "columns": "month",
                    "values": "activity_type"
                }
            ],
            "production": [
                {
                    "type": "line_chart",
                    "title": "Production Trends",
                    "x_axis": "date",
                    "y_axis": "production_rate",
                    "grouping": "well"
                },
                {
                    "type": "area_chart",
                    "title": "Cumulative Production",
                    "x_axis": "date",
                    "y_axis": "cumulative_production",
                    "stacking": "field"
                },
                {
                    "type": "waterfall_chart",
                    "title": "Production Changes",
                    "categories": ["base", "new_wells", "workovers", "decline", "current"]
                }
            ]
        },
        "color_schemes": {
            "default": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
            "field": {"Jack": "#1f77b4", "Julia": "#ff7f0e", 
                     "St. Malo": "#2ca02c", "Stones": "#d62728"},
            "status": {"Active": "green", "Inactive": "red", 
                      "Suspended": "orange", "P&A": "gray"}
        },
        "export_formats": ["html", "png", "svg", "pdf"],
        "interactive_features": [
            "zoom", "pan", "hover", "click_data", "selection", "export"
        ]
    }
    
    # Save configuration
    output_path = Path("tests/modules/bsee/analysis/comprehensive-report-system/results")
    with open(output_path / "visualization_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"Visualization config saved to: {output_path / 'visualization_config.json'}")
    
    return config

def main():
    """Create all visualization prototypes"""
    
    print("Creating Visualization Prototypes")
    print("=" * 50)
    
    # Create field-level visualizations
    print("\n1. Creating field-level visualizations...")
    field_fig = create_field_level_visualizations()
    
    # Create well-level visualizations
    print("\n2. Creating well-level visualizations...")
    well_timeline, well_performance = create_well_level_visualizations()
    
    # Create production visualization
    print("\n3. Creating production visualization...")
    production_fig = create_production_visualization_prototype()
    
    # Create visualization configuration
    print("\n4. Creating visualization configuration...")
    config = create_visualization_config()
    
    print("\n" + "=" * 50)
    print("All visualization prototypes created successfully!")
    print("\nVisualization files created in:")
    print("  tests/modules/bsee/analysis/comprehensive-report-system/results/")
    print("\nFiles:")
    print("  - field_level_visualizations.html")
    print("  - well_timeline_visualization.html")
    print("  - well_performance_visualization.html")
    print("  - production_visualization.html")
    print("  - visualization_config.json")

if __name__ == "__main__":
    main()