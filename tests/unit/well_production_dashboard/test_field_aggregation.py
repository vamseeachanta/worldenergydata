"""
Tests for field aggregation module using BSEE framework.

Tests field-level rollups, comparative analysis, and economic summaries.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Import the module we're testing
from worldenergydata.well_production_dashboard.field_aggregation import (
    FieldAggregationDashboard,
    FieldComparator,
    FieldEconomicSummary,
    FieldProductionChart,
    FieldAggregationConfig
)


class TestFieldAggregationConfig(unittest.TestCase):
    """Test field aggregation configuration."""
    
    def test_config_initialization(self):
        """Test configuration initialization with defaults."""
        config = FieldAggregationConfig(
            field_name="Test Field",
            aggregation_level="field"
        )
        
        self.assertEqual(config.field_name, "Test Field")
        self.assertEqual(config.aggregation_level, "field")
        self.assertTrue(config.include_verification)
        self.assertEqual(config.comparison_metrics, ['production', 'economics', 'efficiency'])
    
    def test_config_custom_values(self):
        """Test configuration with custom values."""
        config = FieldAggregationConfig(
            field_name="Custom Field",
            aggregation_level="lease",
            include_verification=False,
            comparison_metrics=['production']
        )
        
        self.assertEqual(config.field_name, "Custom Field")
        self.assertEqual(config.aggregation_level, "lease")
        self.assertFalse(config.include_verification)
        self.assertEqual(config.comparison_metrics, ['production'])


class TestFieldAggregationDashboard(unittest.TestCase):
    """Test main field aggregation dashboard."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = FieldAggregationConfig(
            field_name="Test Field",
            aggregation_level="field"
        )
        self.dashboard = FieldAggregationDashboard(self.config)
        
        # Create sample well data
        self.sample_wells = self._create_sample_wells()
    
    def _create_sample_wells(self):
        """Create sample well data for testing."""
        wells = []
        for i in range(5):
            well_data = {
                'api_number': f'42-001-{10000+i}',
                'well_name': f'Well-{i+1}',
                'field_name': 'Test Field',
                'lease_name': f'Lease-{i//2+1}',
                'production_data': pd.DataFrame({
                    'date': pd.date_range('2023-01-01', periods=12, freq='M'),
                    'oil_bbls': np.random.uniform(1000, 5000, 12),
                    'gas_mcf': np.random.uniform(500, 2000, 12),
                    'water_bbls': np.random.uniform(100, 500, 12)
                }),
                'economic_data': {
                    'revenue': np.random.uniform(100000, 500000),
                    'opex': np.random.uniform(50000, 150000),
                    'capex': np.random.uniform(200000, 1000000)
                },
                'verification_score': np.random.uniform(0.7, 1.0)
            }
            wells.append(well_data)
        return wells
    
    @patch('worldenergydata.well_production_dashboard.field_aggregation.BSEEAggregator')
    def test_aggregate_field_data(self, mock_aggregator):
        """Test field-level data aggregation."""
        # Setup mock
        mock_aggregator_instance = MagicMock()
        mock_aggregator.return_value = mock_aggregator_instance
        mock_aggregator_instance.aggregate.return_value = {
            'total_oil': 50000,
            'total_gas': 25000,
            'total_water': 5000,
            'well_count': 5,
            'active_wells': 4
        }
        
        # Test aggregation
        result = self.dashboard.aggregate_field_data(self.sample_wells)
        
        # Verify results
        self.assertIsNotNone(result)
        self.assertIn('total_oil', result)
        self.assertIn('well_count', result)
        mock_aggregator_instance.aggregate.assert_called_once()
    
    def test_create_field_rollup(self):
        """Test creation of field-level rollups."""
        rollup = self.dashboard.create_field_rollup(self.sample_wells)
        
        self.assertIsNotNone(rollup)
        self.assertIn('production_summary', rollup)
        self.assertIn('economic_summary', rollup)
        self.assertIn('well_statistics', rollup)
        self.assertIn('quality_metrics', rollup)
    
    def test_calculate_field_metrics(self):
        """Test field-level metric calculations."""
        metrics = self.dashboard.calculate_field_metrics(self.sample_wells)
        
        self.assertIn('average_production_per_well', metrics)
        self.assertIn('field_decline_rate', metrics)
        self.assertIn('water_cut', metrics)
        self.assertIn('gas_oil_ratio', metrics)
        self.assertIn('field_efficiency', metrics)
    
    @patch('worldenergydata.well_production_dashboard.field_aggregation.VerificationSystem')
    def test_apply_verification_overlay(self, mock_verification):
        """Test verification overlay on aggregated data."""
        # Setup mock
        mock_verification_instance = MagicMock()
        mock_verification.return_value = mock_verification_instance
        mock_verification_instance.get_quality_scores.return_value = {
            'data_completeness': 0.95,
            'data_accuracy': 0.88,
            'data_consistency': 0.92
        }
        
        # Test verification overlay
        aggregated_data = {'total_oil': 50000, 'well_count': 5}
        result = self.dashboard.apply_verification_overlay(aggregated_data)
        
        self.assertIn('quality_indicators', result)
        self.assertIn('data_completeness', result['quality_indicators'])


class TestFieldComparator(unittest.TestCase):
    """Test field comparison functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.comparator = FieldComparator()
        self.field_data = self._create_field_data()
    
    def _create_field_data(self):
        """Create sample field data for comparison."""
        fields = {}
        for i in range(3):
            fields[f'Field-{i+1}'] = {
                'production': {
                    'oil_total': np.random.uniform(100000, 500000),
                    'gas_total': np.random.uniform(50000, 250000),
                    'water_total': np.random.uniform(10000, 50000)
                },
                'economics': {
                    'revenue': np.random.uniform(1000000, 5000000),
                    'costs': np.random.uniform(500000, 2000000),
                    'npv': np.random.uniform(500000, 3000000)
                },
                'efficiency': {
                    'wells_per_lease': np.random.uniform(2, 10),
                    'production_per_well': np.random.uniform(1000, 5000),
                    'uptime': np.random.uniform(0.8, 0.99)
                }
            }
        return fields
    
    def test_compare_production(self):
        """Test production comparison across fields."""
        comparison = self.comparator.compare_production(self.field_data)
        
        self.assertIsNotNone(comparison)
        self.assertIn('rankings', comparison)
        self.assertIn('best_performer', comparison)
        self.assertIn('comparison_chart', comparison)
    
    def test_compare_economics(self):
        """Test economic comparison across fields."""
        comparison = self.comparator.compare_economics(self.field_data)
        
        self.assertIn('npv_ranking', comparison)
        self.assertIn('profit_margins', comparison)
        self.assertIn('roi_comparison', comparison)
    
    def test_compare_efficiency(self):
        """Test efficiency comparison across fields."""
        comparison = self.comparator.compare_efficiency(self.field_data)
        
        self.assertIn('production_efficiency', comparison)
        self.assertIn('operational_uptime', comparison)
        self.assertIn('resource_utilization', comparison)
    
    def test_generate_comparison_matrix(self):
        """Test generation of comprehensive comparison matrix."""
        matrix = self.comparator.generate_comparison_matrix(self.field_data)
        
        self.assertIsInstance(matrix, pd.DataFrame)
        self.assertEqual(len(matrix), len(self.field_data))
        self.assertIn('production_rank', matrix.columns)
        self.assertIn('economic_rank', matrix.columns)


class TestFieldEconomicSummary(unittest.TestCase):
    """Test field economic summary generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.summary_generator = FieldEconomicSummary()
        self.economic_data = self._create_economic_data()
    
    def _create_economic_data(self):
        """Create sample economic data."""
        return {
            'revenue': pd.Series(np.random.uniform(100000, 200000, 12)),
            'opex': pd.Series(np.random.uniform(30000, 60000, 12)),
            'capex': 1500000,
            'production': pd.Series(np.random.uniform(1000, 5000, 12)),
            'prices': pd.Series(np.random.uniform(50, 80, 12))
        }
    
    def test_calculate_field_npv(self):
        """Test field-level NPV calculation."""
        npv = self.summary_generator.calculate_field_npv(
            self.economic_data['revenue'],
            self.economic_data['opex'],
            self.economic_data['capex']
        )
        
        self.assertIsInstance(npv, float)
        self.assertGreater(npv, -self.economic_data['capex'])
    
    def test_calculate_irr(self):
        """Test Internal Rate of Return calculation."""
        cash_flows = self.economic_data['revenue'] - self.economic_data['opex']
        cash_flows.iloc[0] -= self.economic_data['capex']
        
        irr = self.summary_generator.calculate_irr(cash_flows)
        
        self.assertIsInstance(irr, float)
        self.assertGreaterEqual(irr, -1)
        self.assertLessEqual(irr, 10)
    
    def test_calculate_payback_period(self):
        """Test payback period calculation."""
        payback = self.summary_generator.calculate_payback_period(
            self.economic_data['revenue'],
            self.economic_data['opex'],
            self.economic_data['capex']
        )
        
        self.assertIsInstance(payback, float)
        self.assertGreater(payback, 0)
    
    def test_generate_economic_summary(self):
        """Test comprehensive economic summary generation."""
        summary = self.summary_generator.generate_summary(self.economic_data)
        
        self.assertIn('npv', summary)
        self.assertIn('irr', summary)
        self.assertIn('payback_period', summary)
        self.assertIn('profit_margin', summary)
        self.assertIn('break_even_price', summary)
    
    @patch('worldenergydata.well_production_dashboard.field_aggregation.DataQualityFramework')
    def test_apply_quality_scores(self, mock_quality):
        """Test application of quality scores to economic summary."""
        # Setup mock
        mock_quality_instance = MagicMock()
        mock_quality.return_value = mock_quality_instance
        mock_quality_instance.calculate_scores.return_value = {
            'revenue_quality': 0.92,
            'cost_quality': 0.88,
            'overall_quality': 0.90
        }
        
        # Test quality score application
        summary = {'npv': 1000000, 'irr': 0.15}
        result = self.summary_generator.apply_quality_scores(summary)
        
        self.assertIn('quality_adjusted_npv', result)
        self.assertIn('confidence_level', result)


class TestFieldProductionChart(unittest.TestCase):
    """Test field production chart generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.chart_builder = FieldProductionChart()
        self.production_data = self._create_production_data()
    
    def _create_production_data(self):
        """Create sample production data."""
        dates = pd.date_range('2023-01-01', periods=24, freq='M')
        return pd.DataFrame({
            'date': dates,
            'field_oil': np.random.uniform(10000, 50000, 24),
            'field_gas': np.random.uniform(5000, 25000, 24),
            'field_water': np.random.uniform(1000, 5000, 24),
            'well_count': np.random.randint(5, 15, 24),
            'verification_score': np.random.uniform(0.8, 1.0, 24)
        })
    
    def test_create_production_chart(self):
        """Test creation of field production chart."""
        chart = self.chart_builder.create_production_chart(self.production_data)
        
        self.assertIsNotNone(chart)
        self.assertIn('data', chart)
        self.assertIn('layout', chart)
        self.assertEqual(chart['type'], 'production_time_series')
    
    def test_create_stacked_production(self):
        """Test creation of stacked production chart."""
        chart = self.chart_builder.create_stacked_production(self.production_data)
        
        self.assertIsNotNone(chart)
        self.assertEqual(chart['type'], 'stacked_area')
        self.assertIn('oil', chart['data'])
        self.assertIn('gas', chart['data'])
    
    def test_add_verification_overlay(self):
        """Test adding verification overlay to production chart."""
        base_chart = self.chart_builder.create_production_chart(self.production_data)
        chart_with_overlay = self.chart_builder.add_verification_overlay(
            base_chart,
            self.production_data['verification_score']
        )
        
        self.assertIn('verification_layer', chart_with_overlay)
        self.assertIn('quality_indicators', chart_with_overlay)
    
    def test_create_decline_curve(self):
        """Test creation of field decline curve."""
        chart = self.chart_builder.create_decline_curve(
            self.production_data['field_oil']
        )
        
        self.assertIsNotNone(chart)
        self.assertEqual(chart['type'], 'decline_curve')
        self.assertIn('actual', chart['data'])
        self.assertIn('fitted', chart['data'])
        self.assertIn('forecast', chart['data'])
    
    def test_create_comparison_chart(self):
        """Test creation of multi-field comparison chart."""
        fields_data = {
            'Field-A': self.production_data['field_oil'],
            'Field-B': self.production_data['field_gas'],
            'Field-C': self.production_data['field_water']
        }
        
        chart = self.chart_builder.create_comparison_chart(fields_data)
        
        self.assertIsNotNone(chart)
        self.assertEqual(chart['type'], 'multi_field_comparison')
        self.assertEqual(len(chart['data']), 3)


class TestIntegration(unittest.TestCase):
    """Integration tests for field aggregation module."""
    
    @patch('worldenergydata.well_production_dashboard.field_aggregation.BSEEAggregator')
    @patch('worldenergydata.well_production_dashboard.field_aggregation.VerificationSystem')
    def test_end_to_end_field_aggregation(self, mock_verification, mock_aggregator):
        """Test end-to-end field aggregation workflow."""
        # Setup mocks
        mock_aggregator.return_value.aggregate.return_value = {
            'total_oil': 100000,
            'total_gas': 50000,
            'well_count': 10
        }
        mock_verification.return_value.get_quality_scores.return_value = {
            'overall': 0.9
        }
        
        # Create dashboard
        config = FieldAggregationConfig(field_name="Integration Field")
        dashboard = FieldAggregationDashboard(config)
        
        # Create sample data
        wells = []
        for i in range(10):
            wells.append({
                'api_number': f'42-001-{20000+i}',
                'production_data': pd.DataFrame({
                    'oil_bbls': [1000] * 12
                })
            })
        
        # Run aggregation
        result = dashboard.create_field_dashboard(wells)
        
        # Verify complete dashboard
        self.assertIn('aggregated_data', result)
        self.assertIn('charts', result)
        self.assertIn('economic_summary', result)
        self.assertIn('quality_metrics', result)
        self.assertIn('export_ready', result)


if __name__ == '__main__':
    unittest.main()