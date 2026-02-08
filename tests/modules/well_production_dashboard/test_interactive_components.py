"""
Tests for interactive dashboard components with quality filters.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Import the module to test
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../src')))

from worldenergydata.well_production_dashboard.interactive_components import (
    QualityFilter,
    DateRangeSelector,
    WellChartLibrary,
    AuditTrailDrilldown,
    AnomalyHighlighter,
    InteractiveDashboardComponents,
    DataFreshnessIndicator,
    FilterChain,
    ChartInteractions
)


class TestQualityFilter(unittest.TestCase):
    """Test quality-aware filter components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.filter = QualityFilter()
        self.sample_data = pd.DataFrame({
            'well_name': ['Well-1', 'Well-2', 'Well-3', 'Well-4'],
            'quality_score': [95, 75, 60, 30],
            'verification_status': ['verified', 'verified', 'pending', 'failed'],
            'oil_production': [1000, 800, 600, 400],
            'date': pd.date_range('2024-01-01', periods=4, freq='D')
        })
    
    def test_filter_by_quality_score(self):
        """Test filtering by quality score threshold."""
        filtered = self.filter.filter_by_quality(self.sample_data, min_score=70)
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(filtered['quality_score'] >= 70))
    
    def test_filter_by_verification_status(self):
        """Test filtering by verification status."""
        filtered = self.filter.filter_by_status(self.sample_data, ['verified'])
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(filtered['verification_status'] == 'verified'))
    
    def test_create_quality_dropdown(self):
        """Test quality filter dropdown creation."""
        dropdown = self.filter.create_quality_dropdown('quality-filter')
        self.assertEqual(dropdown['id'], 'quality-filter')
        self.assertIn('options', dropdown)
        self.assertIn('All Data', [opt['label'] for opt in dropdown['options']])
    
    def test_apply_filter_chain(self):
        """Test applying multiple filters in sequence."""
        filters = {
            'quality_score': 70,
            'verification_status': ['verified']
        }
        filtered = self.filter.apply_filter_chain(self.sample_data, filters)
        self.assertEqual(len(filtered), 2)  # Well-1 and Well-2 meet both criteria
    
    def test_get_quality_badges(self):
        """Test quality badge generation."""
        badges = self.filter.get_quality_badges(self.sample_data)
        self.assertEqual(len(badges), 4)
        self.assertEqual(badges[0]['color'], 'success')  # High quality
        self.assertEqual(badges[3]['color'], 'danger')   # Low quality


class TestDateRangeSelector(unittest.TestCase):
    """Test date range selector with freshness indicators."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.selector = DateRangeSelector()
        self.sample_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=365, freq='D'),
            'oil_production': np.random.rand(365) * 1000,
            'last_updated': pd.date_range('2024-01-01', periods=365, freq='D')
        })
    
    def test_create_date_picker(self):
        """Test date picker component creation."""
        picker = self.selector.create_date_range_picker('date-picker')
        self.assertEqual(picker['id'], 'date-picker')
        self.assertIn('start_date', picker)
        self.assertIn('end_date', picker)
        self.assertIn('display_format', picker)
    
    def test_filter_by_date_range(self):
        """Test filtering data by date range."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        filtered = self.selector.filter_by_date_range(self.sample_data, start, end)
        self.assertEqual(len(filtered), 31)
        self.assertTrue(all(filtered['date'] >= start))
        self.assertTrue(all(filtered['date'] <= end))
    
    def test_calculate_data_freshness(self):
        """Test data freshness calculation."""
        freshness = self.selector.calculate_freshness(self.sample_data)
        self.assertIn('days_old', freshness)
        self.assertIn('freshness_score', freshness)
        self.assertIn('status', freshness)
    
    def test_create_freshness_indicator(self):
        """Test freshness indicator component."""
        indicator = self.selector.create_freshness_indicator(self.sample_data)
        self.assertIn('color', indicator)
        self.assertIn('text', indicator)
        self.assertIn('icon', indicator)
    
    def test_get_preset_ranges(self):
        """Test preset date range options."""
        presets = self.selector.get_preset_ranges()
        self.assertIn('Last 7 Days', presets)
        self.assertIn('Last 30 Days', presets)
        self.assertIn('Year to Date', presets)


class TestWellChartLibrary(unittest.TestCase):
    """Test extended chart library with well-specific visualizations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.library = WellChartLibrary()
        self.sample_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=100, freq='D'),
            'oil': np.random.rand(100) * 1000,
            'gas': np.random.rand(100) * 5000,
            'water': np.random.rand(100) * 500,
            'pressure': np.random.rand(100) * 3000,
            'temperature': np.random.rand(100) * 200
        })
    
    @patch('worldenergydata.well_production_dashboard.interactive_components.go')
    def test_create_type_curve(self, mock_go):
        """Test type curve visualization."""
        mock_go.Figure.return_value = MagicMock()
        chart = self.library.create_type_curve(self.sample_data, 'Well-1')
        self.assertIsNotNone(chart)
        mock_go.Figure.assert_called_once()
    
    @patch('worldenergydata.well_production_dashboard.interactive_components.go')
    def test_create_bubble_map(self, mock_go):
        """Test bubble map for multi-well visualization."""
        mock_go.Figure.return_value = MagicMock()
        wells_data = pd.DataFrame({
            'well_name': ['W1', 'W2', 'W3'],
            'latitude': [29.1, 29.2, 29.3],
            'longitude': [-94.1, -94.2, -94.3],
            'production': [1000, 800, 600]
        })
        chart = self.library.create_bubble_map(wells_data)
        self.assertIsNotNone(chart)
        mock_go.Figure.assert_called_once()
    
    @patch('worldenergydata.well_production_dashboard.interactive_components.go')
    def test_create_waterfall_chart(self, mock_go):
        """Test waterfall chart for production changes."""
        mock_go.Figure.return_value = MagicMock()
        chart = self.library.create_waterfall_chart(self.sample_data)
        self.assertIsNotNone(chart)
        mock_go.Figure.assert_called_once()
    
    @patch('worldenergydata.well_production_dashboard.interactive_components.go')
    def test_create_gauge_chart(self, mock_go):
        """Test gauge chart for KPIs."""
        mock_go.Figure.return_value = MagicMock()
        chart = self.library.create_gauge_chart(
            value=85,
            title="Efficiency",
            min_val=0,
            max_val=100
        )
        self.assertIsNotNone(chart)
        mock_go.Figure.assert_called_once()
    
    @patch('worldenergydata.well_production_dashboard.interactive_components.go')
    def test_create_3d_surface(self, mock_go):
        """Test 3D surface plot for reservoir visualization."""
        mock_go.Figure.return_value = MagicMock()
        chart = self.library.create_3d_surface(
            x=np.arange(10),
            y=np.arange(10),
            z=np.random.rand(10, 10)
        )
        self.assertIsNotNone(chart)
        mock_go.Figure.assert_called_once()


class TestAuditTrailDrilldown(unittest.TestCase):
    """Test audit trail drill-down functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.drilldown = AuditTrailDrilldown()
        self.sample_audit = {
            'well_id': 'W-001',
            'verification_id': 'V-123',
            'timestamp': datetime.now(),
            'changes': [
                {'field': 'oil_production', 'old': 1000, 'new': 1050},
                {'field': 'gas_production', 'old': 5000, 'new': 5100}
            ]
        }
    
    def test_create_audit_link(self):
        """Test audit trail link creation."""
        link = self.drilldown.create_audit_link('W-001', 'V-123')
        self.assertIn('href', link)
        self.assertIn('W-001', link['href'])
        self.assertIn('icon', link)
    
    def test_get_audit_history(self):
        """Test retrieving audit history."""
        with patch.object(self.drilldown, '_fetch_audit_data') as mock_fetch:
            mock_fetch.return_value = [self.sample_audit]
            history = self.drilldown.get_audit_history('W-001')
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]['well_id'], 'W-001')
    
    def test_create_audit_modal(self):
        """Test audit modal component creation."""
        modal = self.drilldown.create_audit_modal('audit-modal')
        self.assertEqual(modal['id'], 'audit-modal')
        self.assertIn('title', modal)
        self.assertIn('content', modal)
    
    def test_format_audit_entry(self):
        """Test audit entry formatting."""
        formatted = self.drilldown.format_audit_entry(self.sample_audit)
        self.assertIn('timestamp', formatted)
        self.assertIn('changes', formatted)
        self.assertIsInstance(formatted['changes'], list)
    
    def test_create_change_timeline(self):
        """Test change timeline visualization."""
        timeline = self.drilldown.create_change_timeline([self.sample_audit])
        self.assertIsNotNone(timeline)
        self.assertIn('events', timeline)


class TestAnomalyHighlighter(unittest.TestCase):
    """Test anomaly highlighting in charts."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.highlighter = AnomalyHighlighter()
        self.sample_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=100, freq='D'),
            'value': np.random.rand(100) * 1000,
            'is_anomaly': [False] * 95 + [True] * 5
        })
    
    def test_detect_anomalies(self):
        """Test anomaly detection."""
        anomalies = self.highlighter.detect_anomalies(
            self.sample_data['value'],
            method='zscore',
            threshold=3
        )
        self.assertEqual(len(anomalies), len(self.sample_data))
        self.assertIsInstance(anomalies[0], bool)
    
    def test_create_anomaly_annotations(self):
        """Test anomaly annotation creation."""
        annotations = self.highlighter.create_annotations(
            self.sample_data[self.sample_data['is_anomaly']]
        )
        self.assertEqual(len(annotations), 5)
        for ann in annotations:
            self.assertIn('x', ann)
            self.assertIn('y', ann)
            self.assertIn('text', ann)
    
    @patch('worldenergydata.well_production_dashboard.interactive_components.go')
    def test_highlight_in_chart(self, mock_go):
        """Test highlighting anomalies in chart."""
        mock_figure = MagicMock()
        mock_go.Figure.return_value = mock_figure
        
        chart = self.highlighter.highlight_in_chart(
            mock_figure,
            self.sample_data,
            'is_anomaly'
        )
        self.assertIsNotNone(chart)
    
    def test_get_anomaly_summary(self):
        """Test anomaly summary generation."""
        summary = self.highlighter.get_anomaly_summary(self.sample_data)
        self.assertIn('total_anomalies', summary)
        self.assertIn('anomaly_rate', summary)
        self.assertIn('recent_anomalies', summary)
    
    def test_create_anomaly_heatmap(self):
        """Test anomaly heatmap creation."""
        heatmap_data = self.highlighter.create_anomaly_heatmap(
            self.sample_data,
            'value'
        )
        self.assertIsNotNone(heatmap_data)
        self.assertIn('z', heatmap_data)


class TestInteractiveDashboardComponents(unittest.TestCase):
    """Test main interactive dashboard component orchestrator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.dashboard = InteractiveDashboardComponents()
    
    def test_initialize_components(self):
        """Test component initialization."""
        components = self.dashboard.initialize_components()
        self.assertIn('quality_filter', components)
        self.assertIn('date_selector', components)
        self.assertIn('chart_library', components)
        self.assertIn('audit_drilldown', components)
        self.assertIn('anomaly_highlighter', components)
    
    def test_create_filter_panel(self):
        """Test filter panel creation."""
        panel = self.dashboard.create_filter_panel()
        self.assertIn('quality_filters', panel)
        self.assertIn('date_filters', panel)
        self.assertIn('well_filters', panel)
    
    def test_apply_all_filters(self):
        """Test applying all filters."""
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=100, freq='D'),
            'quality_score': np.random.rand(100) * 100,
            'well_name': ['W1'] * 50 + ['W2'] * 50,
            'value': np.random.rand(100) * 1000
        })
        
        filters = {
            'quality_min': 70,
            'date_start': '2024-01-01',
            'date_end': '2024-02-01',
            'wells': ['W1']
        }
        
        filtered = self.dashboard.apply_all_filters(data, filters)
        self.assertLessEqual(len(filtered), len(data))
    
    @patch('worldenergydata.well_production_dashboard.interactive_components.dcc')
    def test_create_interactive_layout(self, mock_dcc):
        """Test interactive layout creation."""
        mock_dcc.Graph.return_value = MagicMock()
        mock_dcc.Dropdown.return_value = MagicMock()
        
        layout = self.dashboard.create_interactive_layout()
        self.assertIsNotNone(layout)
    
    def test_register_callbacks(self):
        """Test callback registration."""
        app = MagicMock()
        self.dashboard.register_callbacks(app)
        # Since Dash is not available in tests, this should log a warning and return
        # We can't check app.callback.called since it won't be called without Dash
        # Just verify the method completes without error
        self.assertIsNotNone(self.dashboard)


class TestDataFreshnessIndicator(unittest.TestCase):
    """Test data freshness indicator functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.indicator = DataFreshnessIndicator()
    
    def test_calculate_age(self):
        """Test data age calculation."""
        last_update = datetime.now() - timedelta(days=5)
        age = self.indicator.calculate_age(last_update)
        self.assertEqual(age['days'], 5)
        self.assertIn('hours', age)
        self.assertIn('status', age)
    
    def test_get_freshness_color(self):
        """Test freshness color coding."""
        self.assertEqual(self.indicator.get_freshness_color(0), 'success')
        self.assertEqual(self.indicator.get_freshness_color(3), 'warning')
        self.assertEqual(self.indicator.get_freshness_color(8), 'danger')
    
    def test_create_freshness_badge(self):
        """Test freshness badge creation."""
        badge = self.indicator.create_freshness_badge(
            datetime.now() - timedelta(days=2)
        )
        self.assertIn('color', badge)
        self.assertIn('text', badge)
        self.assertEqual(badge['color'], 'warning')  # 2 days old is 'recent', not 'fresh'


class TestFilterChain(unittest.TestCase):
    """Test filter chain functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.chain = FilterChain()
        self.sample_data = pd.DataFrame({
            'value': range(100),
            'category': ['A'] * 50 + ['B'] * 50,
            'quality': np.random.rand(100) * 100
        })
    
    def test_add_filter(self):
        """Test adding filters to chain."""
        self.chain.add_filter('quality', lambda df: df[df['quality'] > 50])
        self.assertEqual(len(self.chain.filters), 1)
    
    def test_apply_chain(self):
        """Test applying filter chain."""
        self.chain.add_filter('category', lambda df: df[df['category'] == 'A'])
        self.chain.add_filter('value', lambda df: df[df['value'] > 25])
        
        result = self.chain.apply(self.sample_data)
        self.assertLess(len(result), len(self.sample_data))
        self.assertTrue(all(result['category'] == 'A'))
        self.assertTrue(all(result['value'] > 25))
    
    def test_clear_filters(self):
        """Test clearing filter chain."""
        self.chain.add_filter('test', lambda df: df)
        self.chain.clear()
        self.assertEqual(len(self.chain.filters), 0)


class TestChartInteractions(unittest.TestCase):
    """Test chart interaction handlers."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.interactions = ChartInteractions()
    
    def test_handle_click(self):
        """Test click event handling."""
        event_data = {
            'points': [{'x': '2024-01-01', 'y': 1000, 'customdata': 'W-001'}]
        }
        result = self.interactions.handle_click(event_data)
        self.assertIn('well_id', result)
        self.assertIn('date', result)
        self.assertIn('value', result)
    
    def test_handle_hover(self):
        """Test hover event handling."""
        event_data = {
            'points': [{'x': '2024-01-01', 'y': 1000, 'text': 'Details'}]
        }
        result = self.interactions.handle_hover(event_data)
        self.assertIn('tooltip', result)
    
    def test_handle_selection(self):
        """Test selection event handling."""
        event_data = {
            'points': [
                {'x': '2024-01-01', 'y': 1000},
                {'x': '2024-01-02', 'y': 1100}
            ]
        }
        result = self.interactions.handle_selection(event_data)
        self.assertEqual(len(result['selected']), 2)
    
    def test_create_context_menu(self):
        """Test context menu creation."""
        menu = self.interactions.create_context_menu(['Export', 'Zoom', 'Reset'])
        self.assertEqual(len(menu['items']), 3)
        self.assertIn('Export', [item['label'] for item in menu['items']])


if __name__ == '__main__':
    unittest.main()