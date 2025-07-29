"""
Visualization module for Drilling Days Comparison Analysis

Creates advanced visualizations using matplotlib and plotly for comprehensive data analysis.
"""

import logging
import warnings
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio

from .comparison_engine import ComparisonResult, WellCoverageAnalysis

logger = logging.getLogger(__name__)

# Set default plot style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


class ComparisonVisualizer:
    """
    Creates comprehensive visualizations for drilling days comparison analysis.
    
    Generates:
    - Distribution plots (box plots, violin plots, histograms)
    - Correlation plots (scatter plots with regression lines)
    - Difference analysis plots
    - Well coverage visualizations
    - Interactive plotly charts
    """

    def __init__(self, style: str = 'default'):
        """
        Initialize ComparisonVisualizer.
        
        Args:
            style: Matplotlib style to use ('default', 'seaborn', 'ggplot', etc.)
        """
        if style != 'default':
            plt.style.use(style)
        
        self.colors = {
            'primary': '#007bff',
            'secondary': '#6c757d',
            'success': '#28a745',
            'danger': '#dc3545',
            'warning': '#ffc107',
            'info': '#17a2b8'
        }
        
        logger.info("ComparisonVisualizer initialized")

    def create_distribution_plots(
        self, 
        result: ComparisonResult, 
        output_dir: Path,
        format: str = 'png'
    ) -> List[Dict[str, str]]:
        """
        Create distribution plots for drilling and completion days differences.
        
        Args:
            result: ComparisonResult object
            output_dir: Directory to save plots
            format: Output format ('png', 'pdf', 'svg')
            
        Returns:
            List of dictionaries with plot information
        """
        plots = []
        
        if result.matched_data.empty:
            logger.warning("No matched data for distribution plots")
            return plots
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Combined box and violin plot
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # Drilling days distributions
        if 'drilling_days_diff' in result.matched_data.columns:
            data_drilling = result.matched_data['drilling_days_diff'].dropna()
            
            # Box plot
            axes[0, 0].boxplot([data_drilling], tick_labels=['Drilling Days'])
            axes[0, 0].set_ylabel('Difference (days)')
            axes[0, 0].set_title('Box Plot: Drilling Days Differences')
            axes[0, 0].grid(True, alpha=0.3)
            
            # Violin plot
            axes[0, 1].violinplot([data_drilling], positions=[1], showmeans=True, showmedians=True)
            axes[0, 1].set_xticks([1])
            axes[0, 1].set_xticklabels(['Drilling Days'])
            axes[0, 1].set_ylabel('Difference (days)')
            axes[0, 1].set_title('Violin Plot: Drilling Days Differences')
            axes[0, 1].grid(True, alpha=0.3)
        
        # Completion days distributions
        if 'completion_days_diff' in result.matched_data.columns:
            data_completion = result.matched_data['completion_days_diff'].dropna()
            
            # Box plot
            axes[1, 0].boxplot([data_completion], tick_labels=['Completion Days'])
            axes[1, 0].set_ylabel('Difference (days)')
            axes[1, 0].set_title('Box Plot: Completion Days Differences')
            axes[1, 0].grid(True, alpha=0.3)
            
            # Violin plot
            axes[1, 1].violinplot([data_completion], positions=[1], showmeans=True, showmedians=True)
            axes[1, 1].set_xticks([1])
            axes[1, 1].set_xticklabels(['Completion Days'])
            axes[1, 1].set_ylabel('Difference (days)')
            axes[1, 1].set_title('Violin Plot: Completion Days Differences')
            axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        distribution_path = output_dir / f'distribution_plots.{format}'
        plt.savefig(distribution_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        plots.append({
            'path': str(distribution_path),
            'title': 'Distribution Analysis',
            'type': 'distribution'
        })
        
        # 2. Histogram with KDE overlay
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        if 'drilling_days_abs_diff' in result.matched_data.columns:
            data = result.matched_data['drilling_days_abs_diff'].dropna()
            
            # Histogram with KDE
            ax1.hist(data, bins=20, density=True, alpha=0.7, color=self.colors['primary'], edgecolor='black')
            data.plot(kind='density', ax=ax1, color=self.colors['danger'], linewidth=2)
            ax1.set_xlabel('Absolute Difference (days)')
            ax1.set_ylabel('Density')
            ax1.set_title('Distribution of Absolute Drilling Days Differences')
            ax1.grid(True, alpha=0.3)
            
            # Add statistics
            mean_val = data.mean()
            median_val = data.median()
            ax1.axvline(mean_val, color='red', linestyle='--', alpha=0.8, label=f'Mean: {mean_val:.1f}')
            ax1.axvline(median_val, color='green', linestyle='--', alpha=0.8, label=f'Median: {median_val:.1f}')
            ax1.legend()
        
        if 'completion_days_abs_diff' in result.matched_data.columns:
            data = result.matched_data['completion_days_abs_diff'].dropna()
            
            # Histogram with KDE
            ax2.hist(data, bins=20, density=True, alpha=0.7, color=self.colors['info'], edgecolor='black')
            data.plot(kind='density', ax=ax2, color=self.colors['danger'], linewidth=2)
            ax2.set_xlabel('Absolute Difference (days)')
            ax2.set_ylabel('Density')
            ax2.set_title('Distribution of Absolute Completion Days Differences')
            ax2.grid(True, alpha=0.3)
            
            # Add statistics
            mean_val = data.mean()
            median_val = data.median()
            ax2.axvline(mean_val, color='red', linestyle='--', alpha=0.8, label=f'Mean: {mean_val:.1f}')
            ax2.axvline(median_val, color='green', linestyle='--', alpha=0.8, label=f'Median: {median_val:.1f}')
            ax2.legend()
        
        plt.tight_layout()
        histogram_path = output_dir / f'histogram_kde_plots.{format}'
        plt.savefig(histogram_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        plots.append({
            'path': str(histogram_path),
            'title': 'Histogram with Density Overlay',
            'type': 'histogram_kde'
        })
        
        return plots

    def create_correlation_plots(
        self, 
        result: ComparisonResult, 
        output_dir: Path,
        format: str = 'png'
    ) -> List[Dict[str, str]]:
        """
        Create correlation plots comparing methods.
        
        Args:
            result: ComparisonResult object
            output_dir: Directory to save plots
            format: Output format
            
        Returns:
            List of plot information dictionaries
        """
        plots = []
        
        if result.matched_data.empty:
            logger.warning("No matched data for correlation plots")
            return plots
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Scatter plot with regression line
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
        
        # Drilling days correlation
        if all(col in result.matched_data.columns for col in ['drilling_days_lease', 'drilling_days_api12']):
            x = result.matched_data['drilling_days_lease']
            y = result.matched_data['drilling_days_api12']
            
            # Scatter plot
            ax1.scatter(x, y, alpha=0.6, s=50, color=self.colors['primary'])
            
            # Perfect agreement line
            min_val = min(x.min(), y.min())
            max_val = max(x.max(), y.max())
            ax1.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.8, label='Perfect Agreement')
            
            # Regression line
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            ax1.plot(x, p(x), color=self.colors['success'], linewidth=2, alpha=0.8, label=f'Fit: y={z[0]:.2f}x+{z[1]:.2f}')
            
            # Calculate R-squared
            corr = np.corrcoef(x, y)[0, 1]
            ax1.text(0.05, 0.95, f'R² = {corr**2:.3f}', transform=ax1.transAxes, 
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            ax1.set_xlabel('Drilling Days (Lease Method)')
            ax1.set_ylabel('Drilling Days (API12 Method)')
            ax1.set_title('Drilling Days: Method Correlation')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
        
        # Completion days correlation
        if all(col in result.matched_data.columns for col in ['completion_days_lease', 'completion_days_api12']):
            x = result.matched_data['completion_days_lease']
            y = result.matched_data['completion_days_api12']
            
            # Scatter plot
            ax2.scatter(x, y, alpha=0.6, s=50, color=self.colors['info'])
            
            # Perfect agreement line
            min_val = min(x.min(), y.min())
            max_val = max(x.max(), y.max())
            ax2.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.8, label='Perfect Agreement')
            
            # Regression line
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            ax2.plot(x, p(x), color=self.colors['success'], linewidth=2, alpha=0.8, label=f'Fit: y={z[0]:.2f}x+{z[1]:.2f}')
            
            # Calculate R-squared
            corr = np.corrcoef(x, y)[0, 1]
            ax2.text(0.05, 0.95, f'R² = {corr**2:.3f}', transform=ax2.transAxes,
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            ax2.set_xlabel('Completion Days (Lease Method)')
            ax2.set_ylabel('Completion Days (API12 Method)')
            ax2.set_title('Completion Days: Method Correlation')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        correlation_path = output_dir / f'correlation_plots.{format}'
        plt.savefig(correlation_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        plots.append({
            'path': str(correlation_path),
            'title': 'Method Correlation Analysis',
            'type': 'correlation'
        })
        
        return plots

    def create_well_coverage_visualization(
        self, 
        result: ComparisonResult, 
        output_dir: Path,
        format: str = 'png'
    ) -> List[Dict[str, str]]:
        """
        Create well coverage visualization.
        
        Args:
            result: ComparisonResult object
            output_dir: Directory to save plots
            format: Output format
            
        Returns:
            List of plot information dictionaries
        """
        plots = []
        output_dir.mkdir(parents=True, exist_ok=True)
        
        coverage = result.well_coverage
        
        # Venn diagram style visualization
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
        
        # Bar chart of well counts
        categories = ['Lease\nMethod', 'API12\nMethod', 'Common\nWells', 'Lease\nOnly', 'API12\nOnly']
        counts = [
            coverage.total_lease_wells,
            coverage.total_api12_wells,
            coverage.common_wells,
            coverage.lease_only_wells,
            coverage.api12_only_wells
        ]
        colors = [self.colors['primary'], self.colors['info'], self.colors['success'], 
                 self.colors['warning'], self.colors['danger']]
        
        bars = ax1.bar(categories, counts, color=colors, alpha=0.8, edgecolor='black')
        ax1.set_ylabel('Number of Wells')
        ax1.set_title('Well Coverage Summary')
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(count)}', ha='center', va='bottom')
        
        # Pie chart of coverage distribution
        sizes = [coverage.common_wells, coverage.lease_only_wells, coverage.api12_only_wells]
        labels = ['Common Wells', 'Lease Only', 'API12 Only']
        colors_pie = [self.colors['success'], self.colors['warning'], self.colors['danger']]
        
        wedges, texts, autotexts = ax2.pie(sizes, labels=labels, colors=colors_pie, 
                                           autopct='%1.1f%%', startangle=90)
        ax2.set_title(f'Well Distribution\n(Total Coverage: {coverage.coverage_percentage:.1f}%)')
        
        plt.tight_layout()
        coverage_path = output_dir / f'well_coverage_analysis.{format}'
        plt.savefig(coverage_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        plots.append({
            'path': str(coverage_path),
            'title': 'Well Coverage Analysis',
            'type': 'coverage'
        })
        
        return plots

    def create_difference_heatmap(
        self, 
        result: ComparisonResult, 
        output_dir: Path,
        format: str = 'png',
        max_wells: int = 50
    ) -> List[Dict[str, str]]:
        """
        Create heatmap of differences for top wells.
        
        Args:
            result: ComparisonResult object
            output_dir: Directory to save plots
            format: Output format
            max_wells: Maximum number of wells to display
            
        Returns:
            List of plot information dictionaries
        """
        plots = []
        
        if result.matched_data.empty:
            logger.warning("No matched data for heatmap")
            return plots
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare data for heatmap
        diff_columns = [col for col in result.matched_data.columns if col.endswith('_diff') and not col.endswith('_abs_diff')]
        
        if not diff_columns:
            logger.warning("No difference columns found for heatmap")
            return plots
        
        # Get top wells by total absolute difference
        if 'drilling_days_abs_diff' in result.matched_data.columns:
            sorted_data = result.matched_data.nlargest(min(max_wells, len(result.matched_data)), 'drilling_days_abs_diff')
        else:
            sorted_data = result.matched_data.head(min(max_wells, len(result.matched_data)))
        
        # Create heatmap data
        heatmap_data = sorted_data[diff_columns].T
        heatmap_data.columns = sorted_data['api_normalized'].values
        
        # Create figure
        fig, ax = plt.subplots(figsize=(max(12, len(heatmap_data.columns) * 0.3), 6))
        
        # Create heatmap
        sns.heatmap(heatmap_data, annot=True, fmt='.0f', cmap='RdBu_r', center=0,
                   cbar_kws={'label': 'Difference (days)'}, ax=ax)
        
        ax.set_title(f'Difference Heatmap (Top {len(heatmap_data.columns)} Wells by Absolute Difference)')
        ax.set_xlabel('Well API Number')
        ax.set_ylabel('Metric')
        
        # Rotate x-axis labels
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        heatmap_path = output_dir / f'difference_heatmap.{format}'
        plt.savefig(heatmap_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        plots.append({
            'path': str(heatmap_path),
            'title': 'Difference Heatmap',
            'type': 'heatmap'
        })
        
        return plots

    def create_interactive_plots(
        self, 
        result: ComparisonResult, 
        output_dir: Path
    ) -> List[Dict[str, str]]:
        """
        Create interactive Plotly visualizations.
        
        Args:
            result: ComparisonResult object
            output_dir: Directory to save plots
            
        Returns:
            List of plot information dictionaries
        """
        plots = []
        
        if result.matched_data.empty:
            logger.warning("No matched data for interactive plots")
            return plots
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Interactive scatter plot
        if all(col in result.matched_data.columns for col in ['drilling_days_lease', 'drilling_days_api12']):
            fig = go.Figure()
            
            # Add scatter trace
            fig.add_trace(go.Scatter(
                x=result.matched_data['drilling_days_lease'],
                y=result.matched_data['drilling_days_api12'],
                mode='markers',
                marker=dict(
                    size=8,
                    color=result.matched_data.get('drilling_days_abs_diff', 1),
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="Abs Diff<br>(days)")
                ),
                text=result.matched_data['api_normalized'],
                hovertemplate='<b>API:</b> %{text}<br>' +
                             '<b>Lease:</b> %{x}<br>' +
                             '<b>API12:</b> %{y}<br>' +
                             '<extra></extra>'
            ))
            
            # Add perfect agreement line
            min_val = min(result.matched_data['drilling_days_lease'].min(), 
                         result.matched_data['drilling_days_api12'].min())
            max_val = max(result.matched_data['drilling_days_lease'].max(), 
                         result.matched_data['drilling_days_api12'].max())
            
            fig.add_trace(go.Scatter(
                x=[min_val, max_val],
                y=[min_val, max_val],
                mode='lines',
                line=dict(color='red', dash='dash'),
                name='Perfect Agreement',
                hoverinfo='skip'
            ))
            
            fig.update_layout(
                title='Interactive Drilling Days Comparison',
                xaxis_title='Drilling Days (Lease Method)',
                yaxis_title='Drilling Days (API12 Method)',
                hovermode='closest',
                showlegend=True
            )
            
            interactive_scatter_path = output_dir / 'interactive_scatter.html'
            fig.write_html(str(interactive_scatter_path))
            
            plots.append({
                'path': str(interactive_scatter_path),
                'title': 'Interactive Scatter Plot',
                'type': 'interactive_scatter'
            })
        
        # 2. Interactive box plots
        if 'drilling_days_diff' in result.matched_data.columns:
            fig = make_subplots(
                rows=1, cols=2,
                subplot_titles=('Drilling Days Differences', 'Completion Days Differences')
            )
            
            # Drilling days box plot
            fig.add_trace(
                go.Box(
                    y=result.matched_data['drilling_days_diff'],
                    name='Drilling Days',
                    boxpoints='all',
                    jitter=0.3,
                    pointpos=-1.8,
                    marker=dict(color=self.colors['primary'])
                ),
                row=1, col=1
            )
            
            # Completion days box plot if available
            if 'completion_days_diff' in result.matched_data.columns:
                fig.add_trace(
                    go.Box(
                        y=result.matched_data['completion_days_diff'],
                        name='Completion Days',
                        boxpoints='all',
                        jitter=0.3,
                        pointpos=-1.8,
                        marker=dict(color=self.colors['info'])
                    ),
                    row=1, col=2
                )
            
            fig.update_yaxes(title_text="Difference (days)", row=1, col=1)
            fig.update_yaxes(title_text="Difference (days)", row=1, col=2)
            
            fig.update_layout(
                title_text="Interactive Distribution Analysis",
                showlegend=False,
                height=500
            )
            
            interactive_box_path = output_dir / 'interactive_box_plots.html'
            fig.write_html(str(interactive_box_path))
            
            plots.append({
                'path': str(interactive_box_path),
                'title': 'Interactive Box Plots',
                'type': 'interactive_box'
            })
        
        return plots

    def create_all_visualizations(
        self, 
        result: ComparisonResult, 
        output_dir: Path,
        format: str = 'png',
        interactive: bool = True
    ) -> List[Dict[str, str]]:
        """
        Create all available visualizations.
        
        Args:
            result: ComparisonResult object
            output_dir: Directory to save plots
            format: Output format for static plots
            interactive: Whether to create interactive plots
            
        Returns:
            List of all generated plot information
        """
        all_plots = []
        
        # Create static visualizations
        all_plots.extend(self.create_distribution_plots(result, output_dir, format))
        all_plots.extend(self.create_correlation_plots(result, output_dir, format))
        all_plots.extend(self.create_well_coverage_visualization(result, output_dir, format))
        all_plots.extend(self.create_difference_heatmap(result, output_dir, format))
        
        # Create interactive visualizations
        if interactive:
            all_plots.extend(self.create_interactive_plots(result, output_dir))
        
        logger.info(f"Created {len(all_plots)} visualizations")
        return all_plots