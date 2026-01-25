"""
Tests for the Visualization System in the Comprehensive Report System.
"""
import unittest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta
from decimal import Decimal
import numpy as np
import pandas as pd

from worldenergydata.modules.bsee.reports.comprehensive.visualizations.production_charts import ProductionChart
from worldenergydata.modules.bsee.reports.comprehensive.visualizations.well_performance_charts import WellPerformanceChart
from worldenergydata.modules.bsee.reports.comprehensive.visualizations.economic_charts import EconomicChart
from worldenergydata.modules.bsee.reports.comprehensive.visualizations.geographic_charts import GeographicChart
from worldenergydata.modules.bsee.reports.comprehensive.visualizations.dashboard_builder import DashboardBuilder


class TestProductionCharts(unittest.TestCase):
    """Tests for production chart generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.chart_builder = ProductionChart()
        self.sample_data = self._create_sample_production_data()
    
    def _create_sample_production_data(self):
        """Create sample production data for testing."""
        dates = pd.date_range(start='2023-01-01', periods=12, freq='M')
        return pd.DataFrame({
            'date': dates,
            'oil_bbls': np.random.randint(80000, 120000, 12),
            'gas_mcf': np.random.randint(40000, 60000, 12),
            'water_bbls': np.random.randint(5000, 15000, 12),
            'well_count': np.random.randint(20, 30, 12)
        })
    
    @patch('worldenergydata.modules.bsee.reports.comprehensive.visualizations.production_charts.go')
    def test_production_trend_chart_creation(self, mock_go):
        """Test creation of production trend chart."""
        mock_figure = MagicMock()
        mock_go.Figure.return_value = mock_figure
        
        chart = self.chart_builder.create_production_trend(
            self.sample_data,
            title="Production Trend",
            show_oil=True,
            show_gas=True,
            show_water=True
        )
        
        self.assertEqual(chart, mock_figure)
        mock_go.Figure.assert_called_once()
        
        # Verify traces were added for each product
        self.assertGreaterEqual(mock_figure.add_trace.call_count, 3)
    
    def test_production_data_validation(self):
        """Test validation of production data."""
        # Valid data
        self.assertTrue(self.chart_builder.validate_data(self.sample_data))
        
        # Invalid data - missing required columns
        invalid_data = pd.DataFrame({'date': [1, 2, 3]})
        self.assertFalse(self.chart_builder.validate_data(invalid_data))
        
        # Empty data
        self.assertFalse(self.chart_builder.validate_data(pd.DataFrame()))
    
    @patch('worldenergydata.modules.bsee.reports.comprehensive.visualizations.production_charts.go')
    def test_cumulative_production_chart(self, mock_go):
        """Test cumulative production chart generation."""
        mock_figure = MagicMock()
        mock_go.Figure.return_value = mock_figure
        
        chart = self.chart_builder.create_cumulative_production(
            self.sample_data,
            product_type='oil'
        )
        
        self.assertEqual(chart, mock_figure)
        mock_go.Figure.assert_called_once()
    
    @patch('worldenergydata.modules.bsee.reports.comprehensive.visualizations.production_charts.go')
    def test_production_by_well_chart(self, mock_go):
        """Test production by well chart."""
        mock_figure = MagicMock()
        mock_go.Figure.return_value = mock_figure
        
        well_data = pd.DataFrame({
            'well_name': ['W001', 'W002', 'W003', 'W004', 'W005'],
            'oil_production': [50000, 45000, 60000, 35000, 40000],
            'gas_production': [25000, 22000, 30000, 17000, 20000]
        })
        
        chart = self.chart_builder.create_well_production_bars(well_data)
        
        self.assertEqual(chart, mock_figure)
        mock_go.Figure.assert_called_once()
    
    def test_production_forecast_chart(self):
        """Test production forecast chart with historical and predicted data."""
        forecast_data = self.sample_data.copy()
        forecast_data['forecast'] = False
        
        # Add forecast data
        future_dates = pd.date_range(start='2024-01-01', periods=6, freq='M')
        forecast_rows = pd.DataFrame({
            'date': future_dates,
            'oil_bbls': np.random.randint(70000, 90000, 6),
            'gas_mcf': np.random.randint(35000, 45000, 6),
            'water_bbls': np.random.randint(8000, 12000, 6),
            'well_count': [25] * 6,
            'forecast': [True] * 6
        })
        
        combined_data = pd.concat([forecast_data, forecast_rows], ignore_index=True)
        
        with patch.object(self.chart_builder, 'create_forecast_chart') as mock_forecast:
            mock_forecast.return_value = MagicMock()
            
            chart = self.chart_builder.create_forecast_chart(combined_data)
            
            mock_forecast.assert_called_once_with(combined_data)
            self.assertIsNotNone(chart)


class TestWellPerformanceCharts(unittest.TestCase):
    """Tests for well performance visualizations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.chart_builder = WellPerformanceChart()
        self.well_data = self._create_well_performance_data()
    
    def _create_well_performance_data(self):
        """Create sample well performance data."""
        return pd.DataFrame({
            'well_id': [f'W{i:03d}' for i in range(1, 21)],
            'latitude': np.random.uniform(27.5, 29.5, 20),
            'longitude': np.random.uniform(-94, -91, 20),
            'production_rate': np.random.uniform(100, 1000, 20),
            'efficiency': np.random.uniform(0.7, 0.95, 20),
            'uptime': np.random.uniform(0.85, 0.99, 20),
            'depth': np.random.uniform(5000, 15000, 20)
        })
    
    @patch('worldenergydata.modules.bsee.reports.comprehensive.visualizations.well_performance_charts.go')
    def test_scatter_plot_creation(self, mock_go):
        """Test creation of well performance scatter plot."""
        mock_figure = MagicMock()
        mock_go.Figure.return_value = mock_figure
        
        chart = self.chart_builder.create_performance_scatter(
            self.well_data,
            x_axis='depth',
            y_axis='production_rate',
            color_by='efficiency'
        )
        
        self.assertEqual(chart, mock_figure)
        mock_go.Figure.assert_called_once()
    
    @patch('worldenergydata.modules.bsee.reports.comprehensive.visualizations.well_performance_charts.go')
    def test_heat_map_creation(self, mock_go):
        """Test creation of well performance heat map."""
        mock_figure = MagicMock()
        mock_go.Figure.return_value = mock_figure
        
        # Create matrix data for heat map
        matrix_data = self.well_data.pivot_table(
            values='production_rate',
            index='well_id',
            columns='efficiency'
        )
        
        chart = self.chart_builder.create_heat_map(
            matrix_data,
            title="Well Performance Heat Map"
        )
        
        self.assertEqual(chart, mock_figure)
    
    @patch('worldenergydata.modules.bsee.reports.comprehensive.visualizations.well_performance_charts.go')
    def test_bubble_chart_creation(self, mock_go):
        """Test creation of bubble chart for multi-dimensional data."""
        mock_figure = MagicMock()
        mock_go.Figure.return_value = mock_figure
        
        chart = self.chart_builder.create_bubble_chart(
            self.well_data,
            x='depth',
            y='production_rate',
            size='efficiency',
            color='uptime'
        )
        
        self.assertEqual(chart, mock_figure)
    
    def test_performance_metrics_calculation(self):
        """Test calculation of performance metrics for visualization."""
        metrics = self.chart_builder.calculate_performance_metrics(self.well_data)
        
        self.assertIn('mean_production', metrics)
        self.assertIn('median_efficiency', metrics)
        self.assertIn('total_production', metrics)
        self.assertIn('top_performers', metrics)
        
        # Check top performers
        self.assertIsInstance(metrics['top_performers'], list)
        self.assertLessEqual(len(metrics['top_performers']), 5)


class TestEconomicCharts(unittest.TestCase):
    """Tests for economic visualization charts."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.chart_builder = EconomicChart()
        self.economic_data = self._create_economic_data()
    
    def _create_economic_data(self):
        """Create sample economic data."""
        return {
            'revenue_breakdown': {
                'oil_revenue': 85000000,
                'gas_revenue': 35000000,
                'ngl_revenue': 5000000
            },
            'cost_breakdown': {
                'operating_cost': 30000000,
                'capital_cost': 15000000,
                'royalties': 10000000,
                'taxes': 8000000
            },
            'monthly_cashflow': pd.DataFrame({
                'month': pd.date_range('2023-01-01', periods=12, freq='M'),
                'revenue': np.random.uniform(8e6, 12e6, 12),
                'costs': np.random.uniform(4e6, 6e6, 12),
                'net_cashflow': np.random.uniform(2e6, 6e6, 12)
            })
        }
    
    @patch('worldenergydata.modules.bsee.reports.comprehensive.visualizations.go')
    def test_waterfall_chart_creation(self, mock_go):
        """Test creation of waterfall chart for revenue/cost breakdown."""
        mock_figure = MagicMock()
        mock_go.Figure.return_value = mock_figure
        
        chart = self.chart_builder.create_waterfall_chart(
            revenue=self.economic_data['revenue_breakdown'],
            costs=self.economic_data['cost_breakdown'],
            title="Economic Waterfall"
        )
        
        self.assertEqual(chart, mock_figure)
        mock_go.Figure.assert_called_once()
    
    @patch('worldenergydata.modules.bsee.reports.comprehensive.visualizations.go')
    def test_roi_chart_creation(self, mock_go):
        """Test creation of ROI visualization."""
        mock_figure = MagicMock()
        mock_go.Figure.return_value = mock_figure
        
        roi_data = pd.DataFrame({
            'year': [2020, 2021, 2022, 2023, 2024],
            'investment': [100e6, 20e6, 15e6, 10e6, 5e6],
            'return': [0, 30e6, 60e6, 90e6, 120e6],
            'roi_percentage': [-100, -70, -20, 40, 110]
        })
        
        chart = self.chart_builder.create_roi_chart(roi_data)
        
        self.assertEqual(chart, mock_figure)
    
    @patch('worldenergydata.modules.bsee.reports.comprehensive.visualizations.economic_charts.go')
    def test_cashflow_chart(self, mock_go):
        """Test cashflow visualization."""
        mock_figure = MagicMock()
        mock_go.Figure.return_value = mock_figure
        
        chart = self.chart_builder.create_cashflow_chart(
            self.economic_data['monthly_cashflow']
        )
        
        self.assertEqual(chart, mock_figure)
    
    def test_npv_sensitivity_chart(self):
        """Test NPV sensitivity analysis chart."""
        sensitivity_data = {
            'oil_price': {
                'values': [40, 50, 60, 70, 80],
                'npv': [50e6, 100e6, 150e6, 200e6, 250e6]
            },
            'discount_rate': {
                'values': [0.08, 0.10, 0.12, 0.14, 0.16],
                'npv': [200e6, 150e6, 110e6, 80e6, 50e6]
            }
        }
        
        with patch.object(self.chart_builder, 'create_sensitivity_chart') as mock_sens:
            mock_sens.return_value = MagicMock()
            
            chart = self.chart_builder.create_sensitivity_chart(sensitivity_data)
            
            mock_sens.assert_called_once_with(sensitivity_data)
            self.assertIsNotNone(chart)


class TestGeographicCharts(unittest.TestCase):
    """Tests for geographic mapping visualizations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.chart_builder = GeographicChart()
        self.location_data = self._create_location_data()
    
    def _create_location_data(self):
        """Create sample location data."""
        return pd.DataFrame({
            'well_name': [f'W{i:03d}' for i in range(1, 31)],
            'latitude': np.random.uniform(27.0, 30.0, 30),
            'longitude': np.random.uniform(-95.0, -90.0, 30),
            'production': np.random.uniform(100, 1000, 30),
            'status': np.random.choice(['Active', 'Shut-in', 'P&A'], 30),
            'field': np.random.choice(['Field A', 'Field B', 'Field C'], 30)
        })
    
    @patch('worldenergydata.modules.bsee.reports.comprehensive.visualizations.go')
    def test_well_location_map(self, mock_go):
        """Test creation of well location map."""
        mock_figure = MagicMock()
        mock_go.Figure.return_value = mock_figure
        
        chart = self.chart_builder.create_well_map(
            self.location_data,
            color_by='status',
            size_by='production'
        )
        
        self.assertEqual(chart, mock_figure)
        mock_go.Figure.assert_called_once()
    
    @patch('worldenergydata.modules.bsee.reports.comprehensive.visualizations.go')
    def test_field_boundary_map(self, mock_go):
        """Test creation of field boundary map."""
        mock_figure = MagicMock()
        mock_go.Figure.return_value = mock_figure
        
        # Group by field and get boundaries
        field_boundaries = self.location_data.groupby('field').agg({
            'latitude': ['min', 'max'],
            'longitude': ['min', 'max']
        })
        
        chart = self.chart_builder.create_field_boundary_map(
            self.location_data,
            field_boundaries
        )
        
        self.assertEqual(chart, mock_figure)
    
    def test_coordinate_validation(self):
        """Test validation of geographic coordinates."""
        # Valid coordinates
        valid_data = self.location_data.copy()
        self.assertTrue(self.chart_builder.validate_coordinates(valid_data))
        
        # Invalid latitude
        invalid_data = valid_data.copy()
        invalid_data.loc[0, 'latitude'] = 200  # Invalid latitude
        self.assertFalse(self.chart_builder.validate_coordinates(invalid_data))
        
        # Invalid longitude
        invalid_data = valid_data.copy()
        invalid_data.loc[0, 'longitude'] = 300  # Invalid longitude
        self.assertFalse(self.chart_builder.validate_coordinates(invalid_data))
    
    @patch('worldenergydata.modules.bsee.reports.comprehensive.visualizations.go')
    def test_production_density_map(self, mock_go):
        """Test production density heat map."""
        mock_figure = MagicMock()
        mock_go.Figure.return_value = mock_figure
        
        chart = self.chart_builder.create_production_density_map(
            self.location_data,
            resolution=10
        )
        
        self.assertEqual(chart, mock_figure)


class TestInteractiveDashboard(unittest.TestCase):
    """Tests for interactive dashboard features."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.dashboard_builder = DashboardBuilder()
        self.dashboard_data = self._create_dashboard_data()
    
    def _create_dashboard_data(self):
        """Create sample dashboard data."""
        return {
            'kpis': [
                {'name': 'Total Production', 'value': 1500000, 'unit': 'BBL'},
                {'name': 'Revenue', 'value': 125000000, 'unit': '$'},
                {'name': 'Active Wells', 'value': 25, 'unit': 'wells'},
                {'name': 'Efficiency', 'value': 0.92, 'unit': '%'}
            ],
            'production_trend': pd.DataFrame({
                'date': pd.date_range('2023-01-01', periods=12, freq='M'),
                'oil': np.random.uniform(80000, 120000, 12),
                'gas': np.random.uniform(40000, 60000, 12)
            }),
            'well_status': pd.DataFrame({
                'status': ['Active', 'Shut-in', 'P&A'],
                'count': [20, 3, 2]
            })
        }
    
    @patch('plotly.subplots.make_subplots')
    def test_dashboard_layout_creation(self, mock_subplots):
        """Test creation of dashboard layout with multiple charts."""
        mock_fig = MagicMock()
        mock_subplots.return_value = mock_fig
        
        dashboard = self.dashboard_builder.create_dashboard(
            self.dashboard_data,
            layout='grid',
            rows=2,
            cols=2
        )
        
        mock_subplots.assert_called_once()
        self.assertEqual(dashboard, mock_fig)
        
        # Verify configuration
        call_args = mock_subplots.call_args
        self.assertEqual(call_args[1]['rows'], 2)
        self.assertEqual(call_args[1]['cols'], 2)
    
    def test_filter_configuration(self):
        """Test configuration of dashboard filters."""
        filters = self.dashboard_builder.configure_filters({
            'date_range': {'start': '2023-01-01', 'end': '2023-12-31'},
            'well_status': ['Active', 'Shut-in'],
            'field': ['Field A', 'Field B']
        })
        
        self.assertIn('date_range', filters)
        self.assertIn('well_status', filters)
        self.assertIn('field', filters)
        
        # Verify filter types
        self.assertEqual(filters['date_range']['type'], 'daterange')
        self.assertEqual(filters['well_status']['type'], 'multiselect')
        self.assertEqual(filters['field']['type'], 'multiselect')
    
    @patch('worldenergydata.modules.bsee.reports.comprehensive.visualizations.dashboard_builder.go')
    def test_drill_down_capability(self, mock_go):
        """Test drill-down functionality in charts."""
        mock_figure = MagicMock()
        mock_go.Figure.return_value = mock_figure
        
        # Create hierarchical data
        hierarchical_data = {
            'block': 'Block 525',
            'fields': {
                'Field A': {'wells': 10, 'production': 500000},
                'Field B': {'wells': 15, 'production': 1000000}
            }
        }
        
        chart = self.dashboard_builder.create_drilldown_chart(
            hierarchical_data,
            initial_level='block'
        )
        
        self.assertEqual(chart, mock_figure)
        
        # Verify click events are configured
        mock_figure.update_layout.assert_called()
    
    def test_dashboard_export_config(self):
        """Test dashboard export configuration."""
        config = self.dashboard_builder.get_export_config()
        
        self.assertIn('formats', config)
        self.assertIn('html', config['formats'])
        self.assertIn('png', config['formats'])
        self.assertIn('pdf', config['formats'])
        
        # Verify export dimensions
        self.assertIn('width', config)
        self.assertIn('height', config)
        self.assertGreater(config['width'], 0)
        self.assertGreater(config['height'], 0)
    
    def test_real_time_update_capability(self):
        """Test real-time update configuration for dashboard."""
        update_config = self.dashboard_builder.configure_realtime_updates(
            update_interval=5000,  # 5 seconds
            data_source='api',
            max_points=100
        )
        
        self.assertEqual(update_config['interval'], 5000)
        self.assertEqual(update_config['source'], 'api')
        self.assertEqual(update_config['max_points'], 100)
        self.assertTrue(update_config['enabled'])


class TestChartExport(unittest.TestCase):
    """Tests for chart export functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.chart_builder = ChartBuilder()
    
    @patch('plotly.graph_objects.Figure')
    def test_export_to_png(self, mock_figure_class):
        """Test export of chart to PNG format."""
        mock_figure = MagicMock()
        mock_figure_class.return_value = mock_figure
        
        # Create a simple chart
        chart = mock_figure
        
        # Mock the write_image method
        chart.write_image = MagicMock()
        
        # Export to PNG
        export_path = 'test_chart.png'
        self.chart_builder.export_chart(chart, export_path, format='png')
        
        chart.write_image.assert_called_once_with(export_path)
    
    @patch('plotly.graph_objects.Figure')
    def test_export_to_svg(self, mock_figure_class):
        """Test export of chart to SVG format."""
        mock_figure = MagicMock()
        mock_figure_class.return_value = mock_figure
        
        chart = mock_figure
        chart.write_image = MagicMock()
        
        export_path = 'test_chart.svg'
        self.chart_builder.export_chart(chart, export_path, format='svg')
        
        chart.write_image.assert_called_once_with(export_path)
    
    def test_export_to_html(self):
        """Test export of interactive chart to HTML."""
        with patch.object(self.chart_builder, 'export_to_html') as mock_export:
            mock_export.return_value = True
            
            chart = MagicMock()
            result = self.chart_builder.export_to_html(
                chart,
                'test_dashboard.html',
                include_plotlyjs='cdn'
            )
            
            self.assertTrue(result)
            mock_export.assert_called_once()
    
    def test_batch_export(self):
        """Test batch export of multiple charts."""
        charts = {
            'production': MagicMock(),
            'economics': MagicMock(),
            'performance': MagicMock()
        }
        
        with patch.object(self.chart_builder, 'export_batch') as mock_batch:
            mock_batch.return_value = {'success': 3, 'failed': 0}
            
            result = self.chart_builder.export_batch(
                charts,
                output_dir='exports/',
                format='png'
            )
            
            self.assertEqual(result['success'], 3)
            self.assertEqual(result['failed'], 0)


if __name__ == '__main__':
    unittest.main()