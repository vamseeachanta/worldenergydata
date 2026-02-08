"""
Tests for Executive Template visualization components.
"""
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
from decimal import Decimal
import json

from worldenergydata.bsee.reports.comprehensive.templates.executive_template import (
    ExecutiveTemplate,
    ExecutiveDashboard,
    TrafficLightIndicator,
    ExecutiveChart
)


class TestExecutiveVisualization(unittest.TestCase):
    """Tests for executive dashboard visualizations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.template = ExecutiveTemplate()
        self.dashboard_data = self._create_dashboard_data()
    
    def _create_dashboard_data(self):
        """Create sample dashboard data."""
        return {
            'kpis': [
                {'name': 'Revenue', 'value': 125000000, 'target': 130000000, 'status': 'yellow'},
                {'name': 'Production', 'value': 1641667, 'target': 1500000, 'status': 'green'},
                {'name': 'Safety Score', 'value': 95.5, 'target': 90.0, 'status': 'green'},
                {'name': 'Uptime', 'value': 94.5, 'target': 95.0, 'status': 'yellow'},
                {'name': 'Emissions', 'value': 12500, 'target': 15000, 'status': 'green'}
            ],
            'trends': {
                'revenue': [120, 122, 125, 123, 125],
                'production': [1600, 1620, 1640, 1635, 1642],
                'periods': ['Q1', 'Q2', 'Q3', 'Q4', 'Q1']
            }
        }
    
    def test_traffic_light_indicator_creation(self):
        """Test creation of traffic light indicators."""
        indicator = TrafficLightIndicator(
            metric_name="Production Efficiency",
            value=92.5,
            status="green",
            threshold_green=90,
            threshold_yellow=85
        )
        
        self.assertEqual(indicator.metric_name, "Production Efficiency")
        self.assertEqual(indicator.value, 92.5)
        self.assertEqual(indicator.status, "green")
        self.assertEqual(indicator.get_color_code(), "#28a745")  # Green hex color
    
    def test_traffic_light_status_determination(self):
        """Test traffic light status determination."""
        test_cases = [
            (95, 90, 85, "green"),
            (87, 90, 85, "yellow"),
            (82, 90, 85, "red")
        ]
        
        for value, green_threshold, yellow_threshold, expected in test_cases:
            status = self.template.determine_traffic_light_status(
                value, green_threshold, yellow_threshold
            )
            self.assertEqual(status, expected)
    
    @patch('worldenergydata.bsee.reports.comprehensive.templates.executive_template.go')
    def test_executive_dashboard_generation(self, mock_go):
        """Test generation of executive dashboard."""
        mock_go.Figure.return_value = MagicMock()
        
        dashboard = self.template.generate_executive_dashboard(self.dashboard_data)
        
        self.assertIsInstance(dashboard, ExecutiveDashboard)
        self.assertIsNotNone(dashboard.layout)
        self.assertTrue(len(dashboard.charts) > 0)
        
        # Verify dashboard contains expected components
        self.assertIn('kpi_grid', dashboard.components)
        self.assertIn('traffic_lights', dashboard.components)
        self.assertIn('trend_charts', dashboard.components)
    
    @patch('worldenergydata.bsee.reports.comprehensive.templates.executive_template.go')
    def test_kpi_gauge_chart_creation(self, mock_go):
        """Test creation of KPI gauge charts."""
        mock_figure = MagicMock()
        mock_go.Figure.return_value = mock_figure
        
        kpi_data = {
            'name': 'Operational Efficiency',
            'value': 88.5,
            'target': 90.0,
            'min': 0,
            'max': 100
        }
        
        chart = self.template.create_kpi_gauge_chart(kpi_data)
        
        mock_go.Figure.assert_called_once()
        self.assertEqual(chart, mock_figure)
        
        # Verify gauge configuration
        call_args = mock_go.Figure.call_args
        self.assertIn('data', call_args[1])
    
    @patch('worldenergydata.bsee.reports.comprehensive.templates.executive_template.go')
    def test_trend_sparkline_creation(self, mock_go):
        """Test creation of trend sparklines."""
        mock_figure = MagicMock()
        mock_go.Figure.return_value = mock_figure
        
        trend_data = {
            'values': [100, 105, 103, 108, 110],
            'periods': ['Jan', 'Feb', 'Mar', 'Apr', 'May']
        }
        
        sparkline = self.template.create_trend_sparkline(trend_data)
        
        mock_go.Figure.assert_called_once()
        self.assertEqual(sparkline, mock_figure)
    
    @patch('worldenergydata.bsee.reports.comprehensive.templates.executive_template.go')
    def test_executive_summary_chart(self, mock_go):
        """Test creation of executive summary chart."""
        mock_figure = MagicMock()
        mock_go.Figure.return_value = mock_figure
        
        summary_data = {
            'categories': ['Financial', 'Operational', 'Safety', 'Environmental'],
            'scores': [85, 92, 98, 90],
            'targets': [90, 90, 95, 85]
        }
        
        chart = self.template.create_executive_summary_chart(summary_data)
        
        mock_go.Figure.assert_called_once()
        self.assertEqual(chart, mock_figure)
    
    @patch('worldenergydata.bsee.reports.comprehensive.templates.executive_template.go')
    def test_traffic_light_grid_visualization(self, mock_go):
        """Test creation of traffic light grid visualization."""
        mock_figure = MagicMock()
        mock_go.Figure.return_value = mock_figure
        
        metrics = [
            {'name': 'Revenue', 'status': 'green'},
            {'name': 'Production', 'status': 'yellow'},
            {'name': 'Safety', 'status': 'green'},
            {'name': 'Costs', 'status': 'red'},
            {'name': 'Efficiency', 'status': 'green'}
        ]
        
        grid = self.template.create_traffic_light_grid(metrics)
        
        mock_go.Figure.assert_called_once()
        self.assertEqual(grid, mock_figure)
    
    def test_dashboard_layout_configuration(self):
        """Test dashboard layout configuration."""
        layout_config = self.template.get_dashboard_layout_config()
        
        self.assertIn('grid_rows', layout_config)
        self.assertIn('grid_cols', layout_config)
        self.assertIn('component_positions', layout_config)
        
        # Verify layout has proper structure
        self.assertIsInstance(layout_config['grid_rows'], int)
        self.assertIsInstance(layout_config['grid_cols'], int)
        self.assertGreater(layout_config['grid_rows'], 0)
        self.assertGreater(layout_config['grid_cols'], 0)
    
    @patch('worldenergydata.bsee.reports.comprehensive.templates.executive_template.make_subplots')
    def test_multi_panel_dashboard_creation(self, mock_subplots):
        """Test creation of multi-panel executive dashboard."""
        mock_fig = MagicMock()
        mock_subplots.return_value = mock_fig
        
        panels = [
            {'type': 'kpi_grid', 'position': (1, 1)},
            {'type': 'trend_chart', 'position': (1, 2)},
            {'type': 'traffic_lights', 'position': (2, 1)},
            {'type': 'summary_chart', 'position': (2, 2)}
        ]
        
        dashboard = self.template.create_multi_panel_dashboard(panels, self.dashboard_data)
        
        mock_subplots.assert_called_once()
        self.assertEqual(dashboard, mock_fig)
        
        # Verify traces were added for each panel
        self.assertGreater(mock_fig.add_trace.call_count, 0)
    
    def test_dashboard_export_config(self):
        """Test dashboard export configuration."""
        export_config = self.template.get_dashboard_export_config()
        
        self.assertIn('width', export_config)
        self.assertIn('height', export_config)
        self.assertIn('scale', export_config)
        self.assertIn('format', export_config)
        
        # Verify export dimensions
        self.assertGreater(export_config['width'], 0)
        self.assertGreater(export_config['height'], 0)
        self.assertIn(export_config['format'], ['png', 'pdf', 'svg'])


class TestCompetitiveBenchmarking(unittest.TestCase):
    """Tests for competitive benchmarking functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.template = ExecutiveTemplate()
        self.benchmark_data = {
            'company_metrics': {
                'production_efficiency': 88.5,
                'operating_cost_per_boe': 25.50,
                'safety_score': 95.5,
                'environmental_score': 92.0
            },
            'industry_benchmarks': {
                'production_efficiency': {
                    'p25': 82.0,
                    'p50': 87.0,
                    'p75': 92.0,
                    'p90': 95.0
                },
                'operating_cost_per_boe': {
                    'p25': 30.0,
                    'p50': 26.0,
                    'p75': 22.0,
                    'p90': 18.0
                },
                'safety_score': {
                    'p25': 85.0,
                    'p50': 90.0,
                    'p75': 94.0,
                    'p90': 97.0
                },
                'environmental_score': {
                    'p25': 80.0,
                    'p50': 87.0,
                    'p75': 92.0,
                    'p90': 95.0
                }
            },
            'peer_companies': [
                {'name': 'Company A', 'production_efficiency': 90.2, 'safety_score': 93.5},
                {'name': 'Company B', 'production_efficiency': 86.5, 'safety_score': 96.0},
                {'name': 'Company C', 'production_efficiency': 91.8, 'safety_score': 92.0}
            ]
        }
    
    def test_competitive_positioning(self):
        """Test competitive positioning analysis."""
        positioning = self.template.analyze_competitive_position(self.benchmark_data)
        
        self.assertIn('percentile_rankings', positioning)
        self.assertIn('peer_comparison', positioning)
        self.assertIn('strengths', positioning)
        self.assertIn('improvement_areas', positioning)
        
        # Verify percentile calculations
        percentiles = positioning['percentile_rankings']
        self.assertIn('production_efficiency', percentiles)
        self.assertGreaterEqual(percentiles['production_efficiency'], 0)
        self.assertLessEqual(percentiles['production_efficiency'], 100)
    
    @patch('worldenergydata.bsee.reports.comprehensive.templates.executive_template.go')
    def test_benchmark_radar_chart(self, mock_go):
        """Test creation of competitive benchmark radar chart."""
        mock_figure = MagicMock()
        mock_go.Figure.return_value = mock_figure
        
        chart = self.template.create_benchmark_radar_chart(self.benchmark_data)
        
        mock_go.Figure.assert_called_once()
        self.assertEqual(chart, mock_figure)
    
    def test_peer_ranking_table(self):
        """Test generation of peer ranking table."""
        ranking_table = self.template.generate_peer_ranking_table(
            self.benchmark_data['peer_companies']
        )
        
        self.assertIsInstance(ranking_table, list)
        self.assertEqual(len(ranking_table), len(self.benchmark_data['peer_companies']) + 1)  # +1 for our company
        
        # Verify ranking order
        efficiency_values = [row['production_efficiency'] for row in ranking_table]
        self.assertEqual(efficiency_values, sorted(efficiency_values, reverse=True))


if __name__ == '__main__':
    unittest.main()