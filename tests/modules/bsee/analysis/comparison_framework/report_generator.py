"""
ReportGenerator for Drilling Days Comparison Analysis

Generates comprehensive reports including HTML, CSV, and visualizations for drilling days comparison.
"""

import logging
import warnings
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import base64
from io import BytesIO

from .comparison_engine import ComparisonResult, WellCoverageAnalysis

logger = logging.getLogger(__name__)


class HTMLReportGenerator:
    """
    Generates comprehensive HTML reports for drilling days comparison analysis.
    
    Creates interactive HTML reports with:
    - Statistical summaries
    - Well coverage analysis
    - Comparison charts and visualizations
    - Detailed discrepancy tables
    - Interactive elements for data exploration
    """

    def __init__(self, template_path: Optional[Path] = None, custom_css: Optional[str] = None):
        """
        Initialize HTMLReportGenerator.
        
        Args:
            template_path: Optional path to custom HTML templates
            custom_css: Optional custom CSS styling
        """
        self.template_path = template_path
        self.custom_css = custom_css or self._get_default_css()
        logger.info("HTMLReportGenerator initialized")

    def _get_default_css(self) -> str:
        """Get default CSS styling for reports."""
        return """
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background-color: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1, h2, h3 {
                color: #2c3e50;
                margin-top: 30px;
            }
            .summary-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }
            .stat-card {
                background-color: #f8f9fa;
                padding: 20px;
                border-radius: 6px;
                border-left: 4px solid #007bff;
            }
            .stat-value {
                font-size: 2em;
                font-weight: bold;
                color: #007bff;
            }
            .stat-label {
                color: #6c757d;
                font-size: 0.9em;
                margin-top: 5px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #dee2e6;
            }
            th {
                background-color: #f8f9fa;
                font-weight: 600;
                color: #495057;
            }
            tr:hover {
                background-color: #f8f9fa;
            }
            .warning {
                background-color: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 10px;
                margin: 10px 0;
                border-radius: 4px;
            }
            .success {
                background-color: #d4edda;
                border-left: 4px solid #28a745;
                padding: 10px;
                margin: 10px 0;
                border-radius: 4px;
            }
            .chart-container {
                margin: 30px 0;
                text-align: center;
            }
            .chart-container img {
                max-width: 100%;
                height: auto;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            .discrepancy-high {
                background-color: #f8d7da;
                color: #721c24;
            }
            .timestamp {
                color: #6c757d;
                font-size: 0.9em;
                text-align: right;
                margin-top: 30px;
            }
        </style>
        """

    def _generate_header(self, title: str) -> str:
        """Generate HTML header with title and metadata."""
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            {self.custom_css}
        </head>
        <body>
            <div class="container">
                <h1>{title}</h1>
                <p class="timestamp">Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        """

    def _generate_summary_section(self, result: ComparisonResult) -> str:
        """Generate summary section with key metrics."""
        html = "<h2>Executive Summary</h2>"
        
        # Well Coverage Summary
        coverage = result.well_coverage
        html += """
        <div class="summary-grid">
            <div class="stat-card">
                <div class="stat-value">{}</div>
                <div class="stat-label">Total Common Wells</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{:.1f}%</div>
                <div class="stat-label">Well Coverage</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{}</div>
                <div class="stat-label">Discrepancies Found</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{:.1f}%</div>
                <div class="stat-label">Discrepancy Rate</div>
            </div>
        </div>
        """.format(
            result.total_common_wells,
            coverage.coverage_percentage,
            len(result.discrepancies),
            len(result.discrepancies) / result.total_common_wells * 100 if result.total_common_wells > 0 else 0
        )
        
        # Well Coverage Details
        html += """
        <h3>Well Coverage Analysis</h3>
        <table>
            <tr>
                <th>Method</th>
                <th>Total Wells</th>
                <th>Common Wells</th>
                <th>Unique Wells</th>
            </tr>
            <tr>
                <td>Lease Method</td>
                <td>{}</td>
                <td rowspan="2" style="text-align: center; vertical-align: middle; font-weight: bold;">{}</td>
                <td>{}</td>
            </tr>
            <tr>
                <td>API12 Method</td>
                <td>{}</td>
                <td>{}</td>
            </tr>
        </table>
        """.format(
            coverage.total_lease_wells,
            coverage.common_wells,
            coverage.lease_only_wells,
            coverage.total_api12_wells,
            coverage.api12_only_wells
        )
        
        return html

    def _generate_statistics_table(self, statistics: Dict[str, Dict[str, float]]) -> str:
        """Generate statistics summary table."""
        if not statistics:
            return "<p>No statistics available.</p>"
        
        html = """
        <h2>Statistical Summary</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Mean Diff</th>
                <th>Std Dev</th>
                <th>Median</th>
                <th>Min</th>
                <th>Max</th>
                <th>Mean Abs Diff</th>
                <th>Max Abs Diff</th>
            </tr>
        """
        
        for metric, stats in statistics.items():
            metric_display = metric.replace('_', ' ').title()
            html += """
            <tr>
                <td><strong>{}</strong></td>
                <td>{:.2f}</td>
                <td>{:.2f}</td>
                <td>{:.2f}</td>
                <td>{:.2f}</td>
                <td>{:.2f}</td>
                <td>{:.2f}</td>
                <td>{:.2f}</td>
            </tr>
            """.format(
                metric_display,
                stats.get('mean', 0),
                stats.get('std', 0),
                stats.get('median', 0),
                stats.get('min', 0),
                stats.get('max', 0),
                stats.get('mean_abs_diff', 0),
                stats.get('max_abs_diff', 0)
            )
        
        html += "</table>"
        return html

    def _generate_discrepancy_table(self, discrepancies: pd.DataFrame) -> str:
        """Generate table of wells with significant discrepancies."""
        if discrepancies.empty:
            return """
            <h2>Discrepancy Analysis</h2>
            <div class="success">No significant discrepancies found! Methods show good agreement.</div>
            """
        
        html = """
        <h2>Discrepancy Analysis</h2>
        <p>Wells with differences exceeding tolerance thresholds:</p>
        <table>
            <tr>
                <th>API Number</th>
                <th>Drilling Days<br>(Lease)</th>
                <th>Drilling Days<br>(API12)</th>
                <th>Drilling Days<br>Difference</th>
                <th>Completion Days<br>(Lease)</th>
                <th>Completion Days<br>(API12)</th>
                <th>Completion Days<br>Difference</th>
            </tr>
        """
        
        for idx, row in discrepancies.iterrows():
            # Highlight rows with large discrepancies
            row_class = ""
            if ('drilling_days_abs_diff' in row and row['drilling_days_abs_diff'] > 5) or \
               ('completion_days_abs_diff' in row and row['completion_days_abs_diff'] > 5):
                row_class = ' class="discrepancy-high"'
            
            html += """
            <tr{}>
                <td>{}</td>
                <td>{:.0f}</td>
                <td>{:.0f}</td>
                <td>{:+.0f}</td>
                <td>{:.0f}</td>
                <td>{:.0f}</td>
                <td>{:+.0f}</td>
            </tr>
            """.format(
                row_class,
                row.get('api_normalized', ''),
                row.get('drilling_days_lease', 0),
                row.get('drilling_days_api12', 0),
                row.get('drilling_days_diff', 0),
                row.get('completion_days_lease', 0),
                row.get('completion_days_api12', 0),
                row.get('completion_days_diff', 0)
            )
        
        html += "</table>"
        
        if len(discrepancies) > 10:
            html += f'<p class="warning">Showing top 10 discrepancies. Total: {len(discrepancies)} wells with discrepancies.</p>'
        
        return html

    def _generate_visualizations(self, result: ComparisonResult, output_dir: Path) -> List[Dict[str, str]]:
        """Generate visualization charts and save them."""
        charts = []
        
        if result.total_common_wells == 0:
            return charts
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Box plot of differences
        if 'drilling_days_diff' in result.matched_data.columns:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
            
            # Drilling days box plot
            data_drilling = result.matched_data['drilling_days_diff'].dropna()
            ax1.boxplot([data_drilling], tick_labels=['Drilling Days'])
            ax1.set_ylabel('Difference (days)')
            ax1.set_title('Distribution of Drilling Days Differences')
            ax1.grid(True, alpha=0.3)
            
            # Completion days box plot
            if 'completion_days_diff' in result.matched_data.columns:
                data_completion = result.matched_data['completion_days_diff'].dropna()
                ax2.boxplot([data_completion], tick_labels=['Completion Days'])
                ax2.set_ylabel('Difference (days)')
                ax2.set_title('Distribution of Completion Days Differences')
                ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            box_plot_path = output_dir / 'box_plot_differences.png'
            plt.savefig(box_plot_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            charts.append({
                'path': str(box_plot_path),
                'title': 'Distribution of Differences',
                'type': 'box_plot'
            })
        
        # 2. Scatter plot of drilling vs completion days
        if all(col in result.matched_data.columns for col in ['drilling_days_lease', 'drilling_days_api12']):
            fig, ax = plt.subplots(figsize=(10, 8))
            
            ax.scatter(result.matched_data['drilling_days_lease'], 
                      result.matched_data['drilling_days_api12'],
                      alpha=0.6, s=50)
            
            # Add perfect agreement line
            min_val = min(result.matched_data['drilling_days_lease'].min(), 
                         result.matched_data['drilling_days_api12'].min())
            max_val = max(result.matched_data['drilling_days_lease'].max(), 
                         result.matched_data['drilling_days_api12'].max())
            ax.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.8, label='Perfect Agreement')
            
            ax.set_xlabel('Drilling Days (Lease Method)')
            ax.set_ylabel('Drilling Days (API12 Method)')
            ax.set_title('Drilling Days Comparison: Lease vs API12 Methods')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            scatter_plot_path = output_dir / 'scatter_plot_drilling_days.png'
            plt.savefig(scatter_plot_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            charts.append({
                'path': str(scatter_plot_path),
                'title': 'Drilling Days Method Comparison',
                'type': 'scatter_plot'
            })
        
        # 3. Histogram of absolute differences
        if 'drilling_days_abs_diff' in result.matched_data.columns:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            data = result.matched_data['drilling_days_abs_diff'].dropna()
            ax.hist(data, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
            ax.set_xlabel('Absolute Difference (days)')
            ax.set_ylabel('Number of Wells')
            ax.set_title('Distribution of Absolute Drilling Days Differences')
            ax.grid(True, alpha=0.3, axis='y')
            
            # Add statistics
            mean_diff = data.mean()
            median_diff = data.median()
            ax.axvline(mean_diff, color='red', linestyle='--', label=f'Mean: {mean_diff:.1f}')
            ax.axvline(median_diff, color='green', linestyle='--', label=f'Median: {median_diff:.1f}')
            ax.legend()
            
            hist_plot_path = output_dir / 'histogram_abs_differences.png'
            plt.savefig(hist_plot_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            charts.append({
                'path': str(hist_plot_path),
                'title': 'Distribution of Absolute Differences',
                'type': 'histogram'
            })
        
        return charts

    def _embed_chart(self, chart_path: str) -> str:
        """Convert chart image to base64 for embedding in HTML."""
        try:
            with open(chart_path, 'rb') as f:
                image_data = f.read()
            encoded = base64.b64encode(image_data).decode()
            return f'<img src="data:image/png;base64,{encoded}" alt="Chart">'
        except Exception as e:
            logger.warning(f"Failed to embed chart {chart_path}: {e}")
            return f'<p>Chart: {Path(chart_path).name}</p>'

    def generate_report(
        self, 
        result: ComparisonResult, 
        output_path: Path,
        title: str = "Drilling Days Comparison Report",
        embed_charts: bool = True
    ) -> None:
        """
        Generate complete HTML report.
        
        Args:
            result: ComparisonResult object from comparison engine
            output_path: Path to save HTML report
            title: Report title
            embed_charts: Whether to embed charts in HTML or link to files
        """
        logger.info(f"Generating HTML report: {output_path}")
        
        # Start HTML document
        html = self._generate_header(title)
        
        # Add summary section
        html += self._generate_summary_section(result)
        
        # Add statistics section
        if result.statistics:
            html += self._generate_statistics_table(result.statistics)
        
        # Generate visualizations
        output_dir = output_path.parent
        charts = self._generate_visualizations(result, output_dir)
        
        # Add visualizations section
        if charts:
            html += "<h2>Visualizations</h2>"
            for chart in charts:
                html += f'<div class="chart-container">'
                html += f'<h3>{chart["title"]}</h3>'
                if embed_charts:
                    html += self._embed_chart(chart['path'])
                else:
                    html += f'<img src="{Path(chart["path"]).name}" alt="{chart["title"]}">'
                html += '</div>'
        
        # Add discrepancy section
        html += self._generate_discrepancy_table(result.discrepancies)
        
        # Add data quality notes
        html += self._generate_data_quality_section(result)
        
        # Close HTML document
        html += """
            </div>
        </body>
        </html>
        """
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"HTML report generated successfully: {output_path}")

    def _generate_data_quality_section(self, result: ComparisonResult) -> str:
        """Generate data quality notes and recommendations."""
        html = "<h2>Data Quality Notes</h2>"
        
        recommendations = []
        
        # Check coverage
        if result.well_coverage.coverage_percentage < 80:
            recommendations.append(
                f"Low well coverage ({result.well_coverage.coverage_percentage:.1f}%). "
                "Consider investigating why many wells are not matched between methods."
            )
        
        # Check for high discrepancy rate
        if result.total_common_wells > 0:
            discrepancy_rate = len(result.discrepancies) / result.total_common_wells * 100
            if discrepancy_rate > 10:
                recommendations.append(
                    f"High discrepancy rate ({discrepancy_rate:.1f}%). "
                    "Review calculation methods for systematic differences."
                )
        
        # Check for systematic bias
        for metric, stats in result.statistics.items():
            if stats.get('count', 0) > 0:
                if abs(stats.get('mean', 0)) > 2:
                    recommendations.append(
                        f"Systematic bias detected in {metric.replace('_', ' ')}: "
                        f"average difference of {stats['mean']:.1f} days."
                    )
        
        if recommendations:
            html += '<div class="warning"><strong>Recommendations:</strong><ul>'
            for rec in recommendations:
                html += f"<li>{rec}</li>"
            html += "</ul></div>"
        else:
            html += '<div class="success">Data quality appears good with no major issues detected.</div>'
        
        return html


class CSVReportGenerator:
    """
    Generates CSV reports for drilling days comparison analysis.
    
    Creates structured CSV files with:
    - Summary comparison data
    - Detailed well-by-well comparisons
    - Statistical summaries
    - Export options for further analysis
    """

    def __init__(self, include_statistics: bool = True):
        """
        Initialize CSVReportGenerator.
        
        Args:
            include_statistics: Whether to include statistics in reports
        """
        self.include_statistics = include_statistics
        logger.info("CSVReportGenerator initialized")

    def generate_summary(
        self, 
        result: ComparisonResult, 
        output_path: Path,
        columns: Optional[List[str]] = None
    ) -> None:
        """
        Generate summary CSV with key comparison data.
        
        Args:
            result: ComparisonResult object
            output_path: Path to save CSV file
            columns: Specific columns to include (None for default selection)
        """
        logger.info(f"Generating CSV summary: {output_path}")
        
        if result.matched_data.empty:
            logger.warning("No matched data to export")
            # Create empty CSV with headers
            pd.DataFrame(columns=['api_normalized', 'message']).to_csv(
                output_path, index=False
            )
            return
        
        # Default columns if not specified
        if columns is None:
            columns = [
                'api_normalized',
                'drilling_days_lease',
                'drilling_days_api12',
                'drilling_days_diff',
                'drilling_days_abs_diff',
                'completion_days_lease',
                'completion_days_api12',
                'completion_days_diff',
                'completion_days_abs_diff'
            ]
        
        # Filter to available columns
        available_columns = [col for col in columns if col in result.matched_data.columns]
        
        # Export data
        summary_df = result.matched_data[available_columns].copy()
        
        # Sort by largest differences
        if 'drilling_days_abs_diff' in summary_df.columns:
            summary_df = summary_df.sort_values('drilling_days_abs_diff', ascending=False)
        
        # Save to CSV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        summary_df.to_csv(output_path, index=False, float_format='%.2f')
        
        logger.info(f"CSV summary saved with {len(summary_df)} rows")

    def generate_detailed_report(
        self, 
        result: ComparisonResult, 
        output_path: Path,
        include_all_columns: bool = False
    ) -> None:
        """
        Generate detailed CSV report with all comparison data.
        
        Args:
            result: ComparisonResult object
            output_path: Path to save CSV file
            include_all_columns: Whether to include all columns from matched data
        """
        logger.info(f"Generating detailed CSV report: {output_path}")
        
        if result.matched_data.empty:
            logger.warning("No matched data to export")
            pd.DataFrame().to_csv(output_path, index=False)
            return
        
        # Prepare detailed data
        detailed_df = result.matched_data.copy()
        
        # Add well coverage information as metadata rows
        metadata_rows = []
        
        # Coverage summary
        metadata_rows.append({
            'api_normalized': '=== WELL COVERAGE SUMMARY ===',
            'drilling_days_lease': result.well_coverage.total_lease_wells,
            'drilling_days_api12': result.well_coverage.total_api12_wells
        })
        
        metadata_rows.append({
            'api_normalized': 'Common Wells',
            'drilling_days_lease': result.well_coverage.common_wells,
            'drilling_days_api12': result.well_coverage.common_wells
        })
        
        metadata_rows.append({
            'api_normalized': 'Coverage Percentage',
            'drilling_days_lease': result.well_coverage.coverage_percentage,
            'drilling_days_api12': result.well_coverage.coverage_percentage
        })
        
        # Add statistics if requested
        if self.include_statistics and result.statistics:
            metadata_rows.append({
                'api_normalized': '=== STATISTICS SUMMARY ==='
            })
            
            for metric, stats in result.statistics.items():
                metadata_rows.append({
                    'api_normalized': f'{metric} - Mean Difference',
                    'drilling_days_lease': stats.get('mean', 0),
                    'drilling_days_api12': stats.get('mean_abs_diff', 0)
                })
        
        # Create metadata dataframe
        metadata_df = pd.DataFrame(metadata_rows)
        
        # Combine metadata and data with separator
        separator_df = pd.DataFrame([{
            'api_normalized': '=== WELL DATA ==='
        }])
        
        final_df = pd.concat([metadata_df, separator_df, detailed_df], ignore_index=True)
        
        # Select columns based on parameter
        if not include_all_columns:
            # Select key columns only
            key_columns = [
                'api_normalized',
                'drilling_days_lease',
                'drilling_days_api12',
                'drilling_days_diff',
                'completion_days_lease',
                'completion_days_api12',
                'completion_days_diff'
            ]
            available_columns = [col for col in key_columns if col in final_df.columns]
            final_df = final_df[available_columns]
        
        # Save to CSV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_df.to_csv(output_path, index=False, float_format='%.2f')
        
        logger.info(f"Detailed CSV report saved with {len(detailed_df)} data rows")

    def export_statistics(
        self, 
        statistics: Dict[str, Dict[str, float]], 
        output_path: Path
    ) -> None:
        """
        Export statistics summary to CSV.
        
        Args:
            statistics: Statistics dictionary from ComparisonResult
            output_path: Path to save CSV file
        """
        logger.info(f"Exporting statistics to CSV: {output_path}")
        
        if not statistics:
            logger.warning("No statistics to export")
            pd.DataFrame().to_csv(output_path, index=False)
            return
        
        # Convert statistics to dataframe
        rows = []
        for metric, stats in statistics.items():
            row = {'metric': metric}
            row.update(stats)
            rows.append(row)
        
        stats_df = pd.DataFrame(rows)
        
        # Reorder columns for better readability
        column_order = [
            'metric', 'count', 'mean', 'std', 'median', 
            'min', 'max', 'mean_abs_diff', 'max_abs_diff',
            'q25', 'q75'
        ]
        available_columns = [col for col in column_order if col in stats_df.columns]
        stats_df = stats_df[available_columns]
        
        # Save to CSV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        stats_df.to_csv(output_path, index=False, float_format='%.2f')
        
        logger.info(f"Statistics exported for {len(statistics)} metrics")

    def export_discrepancies(
        self, 
        discrepancies: pd.DataFrame, 
        output_path: Path,
        tolerance_config: Optional[Dict[str, float]] = None
    ) -> None:
        """
        Export discrepancies to separate CSV file.
        
        Args:
            discrepancies: DataFrame of wells with discrepancies
            output_path: Path to save CSV file
            tolerance_config: Tolerance thresholds used
        """
        logger.info(f"Exporting discrepancies to CSV: {output_path}")
        
        if discrepancies.empty:
            # Create CSV with message
            pd.DataFrame([{
                'message': 'No discrepancies found - methods show good agreement'
            }]).to_csv(output_path, index=False)
            return
        
        # Prepare discrepancy data
        disc_df = discrepancies.copy()
        
        # Add tolerance information as header rows if provided
        if tolerance_config:
            tolerance_rows = []
            tolerance_rows.append({
                'api_normalized': '=== TOLERANCE THRESHOLDS ==='
            })
            
            for metric, threshold in tolerance_config.items():
                tolerance_rows.append({
                    'api_normalized': f'{metric} tolerance',
                    'drilling_days_diff': threshold
                })
            
            tolerance_rows.append({
                'api_normalized': '=== DISCREPANCIES ==='
            })
            
            # Combine with discrepancy data
            tolerance_df = pd.DataFrame(tolerance_rows)
            disc_df = pd.concat([tolerance_df, disc_df], ignore_index=True)
        
        # Save to CSV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        disc_df.to_csv(output_path, index=False, float_format='%.2f')
        
        logger.info(f"Exported {len(discrepancies)} discrepancies")


class ReportManager:
    """
    Orchestrates report generation across different formats.
    
    Manages:
    - HTML report generation
    - CSV report generation
    - Report configuration
    - Output directory management
    - Report metadata
    """

    def __init__(self):
        """Initialize ReportManager with default generators."""
        self.html_generator = HTMLReportGenerator()
        self.csv_generator = CSVReportGenerator()
        logger.info("ReportManager initialized")

    def generate_all_reports(
        self,
        result: ComparisonResult,
        output_dir: Path,
        report_name: str = "drilling_days_comparison",
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Path]:
        """
        Generate all configured report types.
        
        Args:
            result: ComparisonResult object
            output_dir: Directory to save reports
            report_name: Base name for report files
            config: Report configuration options
            
        Returns:
            Dictionary mapping report types to file paths
        """
        logger.info(f"Generating all reports in: {output_dir}")
        
        # Default configuration
        default_config = {
            'html': {'enabled': True, 'filename': f'{report_name}.html'},
            'csv_summary': {'enabled': True, 'filename': f'{report_name}_summary.csv'},
            'csv_detailed': {'enabled': True, 'filename': f'{report_name}_detailed.csv'},
            'csv_statistics': {'enabled': True, 'filename': f'{report_name}_statistics.csv'},
            'csv_discrepancies': {'enabled': True, 'filename': f'{report_name}_discrepancies.csv'}
        }
        
        # Merge with provided config
        if config:
            for report_type, settings in config.items():
                if report_type in default_config:
                    default_config[report_type].update(settings)
        
        config = default_config
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Track generated reports
        report_paths = {}
        
        # Generate HTML report
        if config['html']['enabled']:
            html_path = output_dir / config['html']['filename']
            self.html_generator.generate_report(
                result, 
                html_path,
                title=f"Drilling Days Comparison: {report_name}"
            )
            report_paths['html_report'] = html_path
        
        # Generate CSV summary
        if config['csv_summary']['enabled']:
            csv_summary_path = output_dir / config['csv_summary']['filename']
            self.csv_generator.generate_summary(result, csv_summary_path)
            report_paths['csv_summary'] = csv_summary_path
        
        # Generate detailed CSV
        if config['csv_detailed']['enabled']:
            csv_detailed_path = output_dir / config['csv_detailed']['filename']
            self.csv_generator.generate_detailed_report(
                result, 
                csv_detailed_path,
                include_all_columns=True
            )
            report_paths['csv_detailed'] = csv_detailed_path
        
        # Generate statistics CSV
        if config['csv_statistics']['enabled'] and result.statistics:
            csv_stats_path = output_dir / config['csv_statistics']['filename']
            self.csv_generator.export_statistics(result.statistics, csv_stats_path)
            report_paths['csv_statistics'] = csv_stats_path
        
        # Generate discrepancies CSV
        if config['csv_discrepancies']['enabled']:
            csv_disc_path = output_dir / config['csv_discrepancies']['filename']
            self.csv_generator.export_discrepancies(
                result.discrepancies, 
                csv_disc_path
            )
            report_paths['csv_discrepancies'] = csv_disc_path
        
        logger.info(f"Generated {len(report_paths)} reports")
        return report_paths

    def generate_reports_with_metadata(
        self,
        result: ComparisonResult,
        output_dir: Path,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate reports with metadata tracking.
        
        Args:
            result: ComparisonResult object
            output_dir: Directory to save reports
            metadata: Additional metadata to include
            
        Returns:
            Dictionary containing report paths and metadata
        """
        # Generate reports
        report_paths = self.generate_all_reports(result, output_dir)
        
        # Prepare metadata
        report_metadata = {
            'generation_timestamp': datetime.now().isoformat(),
            'reports': {
                name: str(path) for name, path in report_paths.items()
            },
            'summary': {
                'total_wells': result.total_common_wells,
                'discrepancy_count': len(result.discrepancies),
                'coverage_percentage': result.well_coverage.coverage_percentage
            }
        }
        
        # Add custom metadata if provided
        if metadata:
            report_metadata['custom'] = metadata
        
        # Save metadata as JSON
        metadata_path = output_dir / 'report_metadata.json'
        import json
        with open(metadata_path, 'w') as f:
            json.dump(report_metadata, f, indent=2)
        
        report_metadata['metadata_file'] = str(metadata_path)
        
        return report_metadata