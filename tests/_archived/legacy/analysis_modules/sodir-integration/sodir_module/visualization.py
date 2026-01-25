"""
Visualization module for SODIR data.

This module provides visualization capabilities for Norwegian Continental Shelf data,
including maps, charts, and comparative dashboards.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set style for better looking plots
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)

logger = logging.getLogger(__name__)


class ChartType(Enum):
    """Available chart types"""
    LINE = "line"
    BAR = "bar"
    SCATTER = "scatter"
    SCATTER_MAP = "scatter_map"
    HEATMAP = "heatmap"
    STACKED_AREA = "stacked_area"
    PIE = "pie"
    BOX = "box"
    HISTOGRAM = "histogram"


@dataclass
class ChartConfig:
    """Configuration for chart creation"""
    title: str
    chart_type: Union[ChartType, str]
    x_label: str = ""
    y_label: str = ""
    color_by: Optional[str] = None
    size_by: Optional[str] = None
    figsize: Tuple[int, int] = (12, 6)
    style: str = "seaborn"
    show_legend: bool = True
    show_grid: bool = True
    
    def __post_init__(self):
        """Convert string to ChartType if needed"""
        if isinstance(self.chart_type, str):
            self.chart_type = ChartType(self.chart_type)


@dataclass
class MapVisualization:
    """Map visualization container"""
    figure: Any  # matplotlib figure
    layers: Dict[str, Any]  # Map layers
    bounds: str  # Geographic bounds
    projection: str = "mercator"
    
    def add_layer(self, name: str, data: Any) -> None:
        """Add layer to map"""
        self.layers[name] = data
    
    def save(self, filepath: str) -> None:
        """Save map to file"""
        if self.figure:
            self.figure.savefig(filepath, dpi=300, bbox_inches='tight')


@dataclass
class DashboardGenerator:
    """Dashboard generator for multiple visualizations"""
    charts: List[Any]
    layout: Tuple[int, int]  # Grid layout (rows, cols)
    title: str = "SODIR Analysis Dashboard"
    figure: Optional[Any] = None
    
    def generate(self) -> Any:
        """Generate the dashboard"""
        # Create subplot grid
        fig, axes = plt.subplots(self.layout[0], self.layout[1], figsize=(20, 12))
        fig.suptitle(self.title, fontsize=16, fontweight='bold')
        
        # Flatten axes if needed
        if self.layout[0] * self.layout[1] == 1:
            axes = [axes]
        else:
            axes = axes.flatten()
        
        # Add charts to grid
        for i, (ax, chart) in enumerate(zip(axes, self.charts)):
            if chart is not None:
                # Chart would be rendered here
                pass
        
        # Hide extra subplots
        for i in range(len(self.charts), len(axes)):
            axes[i].axis('off')
        
        plt.tight_layout()
        self.figure = fig
        return fig
    
    def save(self, filepath: str) -> None:
        """Save dashboard to file"""
        if self.figure:
            self.figure.savefig(filepath, dpi=300, bbox_inches='tight')


class SodirVisualizer:
    """Main visualizer for SODIR data"""
    
    def __init__(self):
        """Initialize visualizer"""
        self.figures = []
        self.color_palette = sns.color_palette("husl", 10)
        
    def create_field_map(self, fields_df: pd.DataFrame, 
                        config: ChartConfig = None) -> MapVisualization:
        """
        Create map visualization of Norwegian fields.
        
        Args:
            fields_df: DataFrame with field data including coordinates
            config: Chart configuration
        
        Returns:
            MapVisualization object
        """
        if config is None:
            config = ChartConfig(
                title="Norwegian Continental Shelf Fields",
                chart_type=ChartType.SCATTER_MAP
            )
        
        # Create figure
        fig, ax = plt.subplots(figsize=config.figsize)
        
        # Norwegian Continental Shelf approximate bounds
        # Longitude: 0-15 E, Latitude: 56-72 N
        ax.set_xlim([0, 15])
        ax.set_ylim([56, 72])
        
        # Plot fields
        if 'longitude' in fields_df.columns and 'latitude' in fields_df.columns:
            # Determine color and size
            color_data = fields_df.get(config.color_by, 'blue')
            size_data = fields_df.get(config.size_by, 100)
            
            scatter = ax.scatter(
                fields_df['longitude'],
                fields_df['latitude'],
                c=color_data,
                s=size_data,
                alpha=0.6,
                cmap='viridis'
            )
            
            # Add colorbar if coloring by numeric data
            if config.color_by and pd.api.types.is_numeric_dtype(fields_df[config.color_by]):
                cbar = plt.colorbar(scatter, ax=ax)
                cbar.set_label(config.color_by)
            
            # Add field names for major fields
            if 'field_name' in fields_df.columns and 'recoverable_oil_mmbbl' in fields_df.columns:
                major_fields = fields_df.nlargest(10, 'recoverable_oil_mmbbl')
                for _, field in major_fields.iterrows():
                    ax.annotate(
                        field['field_name'],
                        (field['longitude'], field['latitude']),
                        fontsize=8,
                        alpha=0.7
                    )
        
        # Formatting
        ax.set_xlabel('Longitude (°E)')
        ax.set_ylabel('Latitude (°N)')
        ax.set_title(config.title)
        ax.grid(True, alpha=0.3)
        
        # Add coastline reference (simplified)
        ax.axvline(x=2, color='gray', linestyle='--', alpha=0.3, label='2°E')
        ax.axvline(x=5, color='gray', linestyle='--', alpha=0.3, label='5°E')
        ax.axhline(y=60, color='gray', linestyle='--', alpha=0.3, label='60°N')
        ax.axhline(y=65, color='gray', linestyle='--', alpha=0.3, label='65°N')
        
        map_viz = MapVisualization(
            figure=fig,
            layers={'fields': fields_df},
            bounds='norwegian_continental_shelf'
        )
        
        self.figures.append(fig)
        
        return map_viz
    
    def create_production_chart(self, production_data: pd.DataFrame,
                               chart_type: str = 'line') -> Any:
        """
        Create production chart.
        
        Args:
            production_data: Production data with time series
            chart_type: Type of chart ('line', 'stacked_area', 'bar')
        
        Returns:
            Chart object
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Prepare data
        if 'year' in production_data.columns:
            x_data = production_data['year']
        else:
            x_data = production_data.index
        
        # Create chart based on type
        if chart_type == 'line':
            if 'oil' in production_data.columns:
                ax.plot(x_data, production_data['oil'], label='Oil (MMbbl)', 
                       color='darkgreen', linewidth=2)
            if 'gas' in production_data.columns:
                ax.plot(x_data, production_data['gas'], label='Gas (BCF)', 
                       color='darkblue', linewidth=2)
            
        elif chart_type == 'stacked_area':
            oil_data = production_data.get('oil', pd.Series(0, index=x_data))
            gas_data = production_data.get('gas', pd.Series(0, index=x_data))
            
            ax.fill_between(x_data, 0, oil_data, label='Oil', color='darkgreen', alpha=0.7)
            ax.fill_between(x_data, oil_data, oil_data + gas_data, label='Gas', 
                          color='darkblue', alpha=0.7)
            
        elif chart_type == 'bar':
            width = 0.35
            x_pos = np.arange(len(x_data))
            
            if 'oil' in production_data.columns:
                ax.bar(x_pos - width/2, production_data['oil'], width, 
                      label='Oil', color='darkgreen')
            if 'gas' in production_data.columns:
                ax.bar(x_pos + width/2, production_data['gas'], width, 
                      label='Gas', color='darkblue')
            
            ax.set_xticks(x_pos)
            ax.set_xticklabels(x_data)
        
        # Formatting
        ax.set_xlabel('Year')
        ax.set_ylabel('Production')
        ax.set_title('Production Profile')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Store chart info
        chart = {
            'figure': fig,
            'data': production_data,
            'series': list(production_data.columns)
        }
        
        self.figures.append(fig)
        
        return chart
    
    def create_comparison_dashboard(self, sodir_data: Dict[str, pd.DataFrame],
                                  bsee_data: Dict[str, pd.DataFrame],
                                  metrics: List[str] = None) -> DashboardGenerator:
        """
        Create cross-regional comparison dashboard.
        
        Args:
            sodir_data: Norwegian data
            bsee_data: US Gulf data
            metrics: Metrics to compare
        
        Returns:
            DashboardGenerator object
        """
        if metrics is None:
            metrics = ['recovery_factor', 'water_depth', 'field_size', 'production_rate']
        
        charts = []
        
        # Create comparison charts for each metric
        for metric in metrics:
            chart = self._create_comparison_chart(sodir_data, bsee_data, metric)
            charts.append(chart)
        
        # Determine layout
        num_charts = len(charts)
        if num_charts <= 2:
            layout = (1, 2)
        elif num_charts <= 4:
            layout = (2, 2)
        elif num_charts <= 6:
            layout = (2, 3)
        else:
            layout = (3, 3)
        
        dashboard = DashboardGenerator(
            charts=charts,
            layout=layout,
            title="SODIR vs BSEE Comparison Dashboard"
        )
        
        return dashboard
    
    def _create_comparison_chart(self, sodir_data: Dict[str, pd.DataFrame],
                                bsee_data: Dict[str, pd.DataFrame],
                                metric: str) -> Any:
        """Create individual comparison chart"""
        fig, ax = plt.subplots(figsize=(8, 6))
        
        # Extract relevant data based on metric
        if metric == 'recovery_factor' and 'fields' in sodir_data and 'fields' in bsee_data:
            sodir_values = sodir_data['fields'].get('recovery_factor', pd.Series())
            bsee_values = bsee_data['fields'].get('recovery_factor', pd.Series())
            
            # Create box plot
            data = [sodir_values.dropna(), bsee_values.dropna()]
            ax.boxplot(data, labels=['Norway (SODIR)', 'US Gulf (BSEE)'])
            ax.set_ylabel('Recovery Factor')
            ax.set_title('Recovery Factor Comparison')
            
        elif metric == 'water_depth' and 'fields' in sodir_data and 'fields' in bsee_data:
            sodir_values = sodir_data['fields'].get('water_depth_m', pd.Series())
            bsee_values = bsee_data['fields'].get('water_depth_m', pd.Series())
            
            # Create histogram
            ax.hist(sodir_values.dropna(), bins=20, alpha=0.5, label='Norway', color='blue')
            ax.hist(bsee_values.dropna(), bins=20, alpha=0.5, label='US Gulf', color='orange')
            ax.set_xlabel('Water Depth (m)')
            ax.set_ylabel('Number of Fields')
            ax.set_title('Water Depth Distribution')
            ax.legend()
            
        elif metric == 'field_size' and 'fields' in sodir_data and 'fields' in bsee_data:
            # Calculate BOE for field size
            sodir_boe = (sodir_data['fields'].get('recoverable_oil_mmbbl', 0) + 
                        sodir_data['fields'].get('recoverable_gas_bcf', 0) / 6)
            bsee_boe = (bsee_data['fields'].get('recoverable_oil_mmbbl', 0) + 
                       bsee_data['fields'].get('recoverable_gas_bcf', 0) / 6)
            
            # Create scatter plot
            ax.scatter(range(len(sodir_boe)), sodir_boe, alpha=0.5, label='Norway', color='blue')
            ax.scatter(range(len(bsee_boe)), bsee_boe, alpha=0.5, label='US Gulf', color='orange')
            ax.set_xlabel('Field Index')
            ax.set_ylabel('Recoverable Resources (MMBOE)')
            ax.set_title('Field Size Comparison')
            ax.set_yscale('log')
            ax.legend()
            
        elif metric == 'production_rate':
            # Bar chart comparing average production rates
            categories = ['Oil (MMbbl/yr)', 'Gas (BCF/yr)']
            sodir_rates = [100, 500]  # Placeholder values
            bsee_rates = [80, 300]    # Placeholder values
            
            x = np.arange(len(categories))
            width = 0.35
            
            ax.bar(x - width/2, sodir_rates, width, label='Norway', color='blue')
            ax.bar(x + width/2, bsee_rates, width, label='US Gulf', color='orange')
            ax.set_xlabel('Production Type')
            ax.set_ylabel('Average Annual Production')
            ax.set_title('Production Rate Comparison')
            ax.set_xticks(x)
            ax.set_xticklabels(categories)
            ax.legend()
        
        plt.tight_layout()
        
        return {'figure': fig, 'metric': metric}
    
    def export_chart(self, chart: Any, filepath: str, 
                    format: str = 'png', dpi: int = 300) -> None:
        """
        Export chart to file.
        
        Args:
            chart: Chart object to export
            filepath: Output file path
            format: File format (png, pdf, svg)
            dpi: Resolution for raster formats
        """
        if isinstance(chart, dict) and 'figure' in chart:
            fig = chart['figure']
        elif hasattr(chart, 'figure'):
            fig = chart.figure
        else:
            fig = chart
        
        # Ensure directory exists
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save figure
        if fig:
            fig.savefig(filepath, format=format, dpi=dpi, bbox_inches='tight')
            logger.info(f"Chart exported to {filepath}")
    
    def create_field_ranking_chart(self, fields_df: pd.DataFrame,
                                 rank_by: str = 'recoverable_oil_mmbbl',
                                 top_n: int = 20) -> Any:
        """
        Create field ranking chart.
        
        Args:
            fields_df: Fields data
            rank_by: Column to rank by
            top_n: Number of top fields to show
        
        Returns:
            Chart object
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Get top fields
        top_fields = fields_df.nlargest(top_n, rank_by)
        
        # Create horizontal bar chart
        y_pos = np.arange(len(top_fields))
        ax.barh(y_pos, top_fields[rank_by], color='steelblue')
        
        # Formatting
        ax.set_yticks(y_pos)
        ax.set_yticklabels(top_fields['field_name'])
        ax.invert_yaxis()
        ax.set_xlabel(rank_by.replace('_', ' ').title())
        ax.set_title(f'Top {top_n} Fields by {rank_by.replace("_", " ").title()}')
        ax.grid(axis='x', alpha=0.3)
        
        # Add value labels
        for i, v in enumerate(top_fields[rank_by]):
            ax.text(v, i, f' {v:.0f}', va='center')
        
        plt.tight_layout()
        
        chart = {
            'figure': fig,
            'data': top_fields,
            'ranking_metric': rank_by
        }
        
        self.figures.append(fig)
        
        return chart
    
    def create_discovery_timeline(self, fields_df: pd.DataFrame) -> Any:
        """
        Create discovery timeline visualization.
        
        Args:
            fields_df: Fields data with discovery years
        
        Returns:
            Chart object
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        if 'discovery_year' in fields_df.columns:
            # Timeline of discoveries
            discovery_counts = fields_df.groupby('discovery_year').size()
            ax1.bar(discovery_counts.index, discovery_counts.values, color='navy', alpha=0.7)
            ax1.set_xlabel('Discovery Year')
            ax1.set_ylabel('Number of Discoveries')
            ax1.set_title('Field Discovery Timeline')
            ax1.grid(axis='y', alpha=0.3)
            
            # Cumulative discoveries
            cumulative = discovery_counts.cumsum()
            ax2.plot(cumulative.index, cumulative.values, color='darkred', linewidth=2)
            ax2.fill_between(cumulative.index, 0, cumulative.values, alpha=0.3, color='darkred')
            ax2.set_xlabel('Year')
            ax2.set_ylabel('Cumulative Discoveries')
            ax2.set_title('Cumulative Field Discoveries')
            ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        chart = {
            'figure': fig,
            'discovery_counts': discovery_counts if 'discovery_year' in fields_df.columns else None,
            'cumulative': cumulative if 'discovery_year' in fields_df.columns else None
        }
        
        self.figures.append(fig)
        
        return chart
    
    def create_correlation_heatmap(self, data_df: pd.DataFrame,
                                 columns: List[str] = None) -> Any:
        """
        Create correlation heatmap.
        
        Args:
            data_df: Data for correlation analysis
            columns: Specific columns to include
        
        Returns:
            Chart object
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Select columns
        if columns:
            numeric_data = data_df[columns].select_dtypes(include=[np.number])
        else:
            numeric_data = data_df.select_dtypes(include=[np.number])
        
        # Calculate correlation
        correlation = numeric_data.corr()
        
        # Create heatmap
        sns.heatmap(correlation, annot=True, cmap='coolwarm', center=0,
                   square=True, linewidths=1, cbar_kws={"shrink": 0.8},
                   ax=ax)
        
        ax.set_title('Correlation Matrix')
        
        plt.tight_layout()
        
        chart = {
            'figure': fig,
            'correlation_matrix': correlation
        }
        
        self.figures.append(fig)
        
        return chart
    
    def close_all(self) -> None:
        """Close all open figures"""
        for fig in self.figures:
            plt.close(fig)
        self.figures = []