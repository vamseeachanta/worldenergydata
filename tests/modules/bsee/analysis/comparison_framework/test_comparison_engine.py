"""
Test cases for ComparisonEngine class.

Tests the core comparison logic for drilling days analysis between different methods.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, Any, List, Optional

# Import the module we're testing
from .comparison_engine import ComparisonEngine, ComparisonResult, WellCoverageAnalysis


class TestComparisonEngine:
    """Test cases for ComparisonEngine."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.engine = ComparisonEngine()
        
        # Sample data for testing
        self.sample_lease_data = pd.DataFrame({
            'API_WELL_NUMBER': ['420030123450000', '420030456780000', '420030789010000', '420030111220000'],
            'WELL_NAME': ['Test Well 1', 'Test Well 2', 'Test Well 3', 'Test Well 4'],
            'WELL_SPUD_DATE': ['2020-01-15', '2020-02-20', '2020-03-10', '2020-04-05'],
            'TOTAL_DEPTH_DATE': ['2020-02-20', '2020-03-25', '2020-04-15', '2020-05-10'],
            'DRILLING_DAYS': [36, 34, 36, 35],
            'COMPLETION_DAYS': [45, 42, 48, 46]
        })
        
        self.sample_api12_data = pd.DataFrame({
            'API12': ['420030123450', '420030456780', '420030789010', '420030333440'],  # Last one is different
            'WELL_SPUD_DATE': ['2020-01-15', '2020-02-20', '2020-03-10', '2020-05-15'],
            'TOTAL_DEPTH_DATE': ['2020-02-20', '2020-03-25', '2020-04-15', '2020-06-20'],
            'Drilling Days': [36, 33, 37, 36],  # Slight differences
            'Completion Days': [44, 43, 47, 45]  # Slight differences
        })

    def test_initialization(self):
        """Test ComparisonEngine initialization."""
        engine = ComparisonEngine()
        assert engine is not None
        assert engine.tolerance_config == {}
        
        # Test initialization with tolerance config
        tolerance = {'drilling_days': 2, 'completion_days': 3, 'dates': 1}
        engine_with_config = ComparisonEngine(tolerance_config=tolerance)
        assert engine_with_config.tolerance_config == tolerance

    def test_normalize_api_numbers(self):
        """Test API number normalization functionality."""
        # Test API10 to API12 conversion
        api10 = "420030123450000"
        api12 = self.engine._normalize_api_number(api10)
        assert api12 == "420030123450"
        
        # Test API12 remains unchanged
        api12_input = "420030123450"
        api12_output = self.engine._normalize_api_number(api12_input)
        assert api12_output == "420030123450"
        
        # Test invalid API number
        invalid_api = "123"
        normalized = self.engine._normalize_api_number(invalid_api)
        assert normalized == "123"  # Returns as-is for invalid format

    def test_prepare_data_for_comparison(self):
        """Test data preparation for comparison."""
        # Test lease method data preparation
        lease_normalized = self.engine._prepare_data_for_comparison(
            self.sample_lease_data, 
            'lease_method',
            {
                'api': 'API_WELL_NUMBER',
                'drilling_days': 'DRILLING_DAYS',
                'completion_days': 'COMPLETION_DAYS',
                'spud_date': 'WELL_SPUD_DATE',
                'td_date': 'TOTAL_DEPTH_DATE'
            }
        )
        
        assert 'api_normalized' in lease_normalized.columns
        assert 'method' in lease_normalized.columns
        assert lease_normalized['method'].iloc[0] == 'lease_method'
        assert lease_normalized['api_normalized'].iloc[0] == '420030123450'
        
        # Test API12 method data preparation
        api12_normalized = self.engine._prepare_data_for_comparison(
            self.sample_api12_data,
            'api12_method',
            {
                'api': 'API12',
                'drilling_days': 'Drilling Days',
                'completion_days': 'Completion Days',
                'spud_date': 'WELL_SPUD_DATE',
                'td_date': 'TOTAL_DEPTH_DATE'
            }
        )
        
        assert 'api_normalized' in api12_normalized.columns
        assert 'method' in api12_normalized.columns
        assert api12_normalized['method'].iloc[0] == 'api12_method'

    def test_identify_common_wells(self):
        """Test identification of common wells between datasets."""
        # Prepare test data
        lease_prepared = self.engine._prepare_data_for_comparison(
            self.sample_lease_data, 
            'lease_method',
            {
                'api': 'API_WELL_NUMBER',
                'drilling_days': 'DRILLING_DAYS',
                'completion_days': 'COMPLETION_DAYS',
                'spud_date': 'WELL_SPUD_DATE',
                'td_date': 'TOTAL_DEPTH_DATE'
            }
        )
        
        api12_prepared = self.engine._prepare_data_for_comparison(
            self.sample_api12_data,
            'api12_method',
            {
                'api': 'API12',
                'drilling_days': 'Drilling Days',
                'completion_days': 'Completion Days',
                'spud_date': 'WELL_SPUD_DATE',
                'td_date': 'TOTAL_DEPTH_DATE'
            }
        )
        
        common_wells, lease_only, api12_only = self.engine._identify_common_wells(
            lease_prepared, api12_prepared
        )
        
        # Should have 3 common wells
        assert len(common_wells) == 3
        assert '420030123450' in common_wells
        assert '420030456780' in common_wells
        assert '420030789010' in common_wells
        
        # Should have 1 lease-only well
        assert len(lease_only) == 1
        assert '420030111220' in lease_only
        
        # Should have 1 api12-only well
        assert len(api12_only) == 1
        assert '420030333440' in api12_only

    def test_calculate_differences(self):
        """Test calculation of differences between methods."""
        # Create matched data for testing
        matched_data = pd.DataFrame({
            'api_normalized': ['420030123450', '420030456780', '420030789010'],
            'drilling_days_lease': [36, 34, 36],
            'completion_days_lease': [45, 42, 48],
            'drilling_days_api12': [36, 33, 37],
            'completion_days_api12': [44, 43, 47]
        })
        
        differences = self.engine._calculate_differences(matched_data)
        
        assert 'drilling_days_diff' in differences.columns
        assert 'completion_days_diff' in differences.columns
        assert 'drilling_days_abs_diff' in differences.columns
        assert 'completion_days_abs_diff' in differences.columns
        
        # Check specific calculations
        assert differences['drilling_days_diff'].iloc[0] == 0  # 36 - 36
        assert differences['drilling_days_diff'].iloc[1] == 1  # 34 - 33  
        assert differences['drilling_days_diff'].iloc[2] == -1  # 36 - 37
        
        assert differences['completion_days_diff'].iloc[0] == 1  # 45 - 44
        assert differences['completion_days_diff'].iloc[1] == -1  # 42 - 43
        assert differences['completion_days_diff'].iloc[2] == 1  # 48 - 47

    def test_calculate_statistics(self):
        """Test statistical calculations."""
        differences = pd.DataFrame({
            'drilling_days_diff': [0, 1, -1, 2, -2],
            'completion_days_diff': [1, -1, 1, -1, 0],
            'drilling_days_abs_diff': [0, 1, 1, 2, 2],
            'completion_days_abs_diff': [1, 1, 1, 1, 0]
        })
        
        stats = self.engine._calculate_statistics(differences)
        
        # Check drilling days statistics
        assert stats['drilling_days']['mean'] == 0.0
        assert stats['drilling_days']['std'] == pytest.approx(1.58, rel=1e-2)
        assert stats['drilling_days']['median'] == 0.0
        assert stats['drilling_days']['mean_abs_diff'] == 1.2
        assert stats['drilling_days']['max_abs_diff'] == 2
        
        # Check completion days statistics
        assert stats['completion_days']['mean'] == 0.0
        assert stats['completion_days']['median'] == 0.0
        assert stats['completion_days']['mean_abs_diff'] == 0.8

    def test_identify_discrepancies(self):
        """Test discrepancy identification based on tolerance."""
        differences = pd.DataFrame({
            'api_normalized': ['well1', 'well2', 'well3', 'well4'],
            'drilling_days_abs_diff': [1, 3, 0, 5],
            'completion_days_abs_diff': [2, 1, 4, 2]
        })
        
        tolerance = {'drilling_days': 2, 'completion_days': 3}
        discrepancies = self.engine._identify_discrepancies(differences, tolerance)
        
        # Well2 should have drilling days discrepancy (3 > 2)
        # Well3 should have completion days discrepancy (4 > 3)  
        # Well4 should have drilling days discrepancy (5 > 2)
        expected_discrepant_wells = {'well2', 'well3', 'well4'}
        actual_discrepant_wells = set(discrepancies['api_normalized'])
        
        assert expected_discrepant_wells == actual_discrepant_wells

    def test_analyze_well_coverage(self):
        """Test well coverage analysis."""
        lease_data = pd.DataFrame({
            'api_normalized': ['well1', 'well2', 'well3', 'well4']
        })
        
        api12_data = pd.DataFrame({
            'api_normalized': ['well2', 'well3', 'well4', 'well5']
        })
        
        coverage = self.engine._analyze_well_coverage(lease_data, api12_data)
        
        assert isinstance(coverage, WellCoverageAnalysis)
        assert coverage.total_lease_wells == 4
        assert coverage.total_api12_wells == 4
        assert coverage.common_wells == 3
        assert coverage.lease_only_wells == 1
        assert coverage.api12_only_wells == 1
        assert coverage.coverage_percentage == 60.0  # 3/5 * 100 (3 common / 5 total unique wells)

    def test_compare_methods_full_workflow(self):
        """Test complete comparison workflow."""
        column_mapping = {
            'lease_method': {
                'api': 'API_WELL_NUMBER',
                'drilling_days': 'DRILLING_DAYS',
                'completion_days': 'COMPLETION_DAYS',
                'spud_date': 'WELL_SPUD_DATE',
                'td_date': 'TOTAL_DEPTH_DATE'
            },
            'api12_method': {
                'api': 'API12',
                'drilling_days': 'Drilling Days',
                'completion_days': 'Completion Days',
                'spud_date': 'WELL_SPUD_DATE',
                'td_date': 'TOTAL_DEPTH_DATE'
            }
        }
        
        tolerance = {'drilling_days': 2, 'completion_days': 3}
        
        result = self.engine.compare_methods(
            self.sample_lease_data,
            self.sample_api12_data,
            column_mapping,
            tolerance
        )
        
        assert isinstance(result, ComparisonResult)
        assert result.total_common_wells > 0
        assert result.statistics is not None
        assert result.well_coverage is not None
        assert result.matched_data is not None
        assert result.discrepancies is not None

    def test_empty_datasets(self):
        """Test handling of empty datasets."""
        empty_df = pd.DataFrame()
        
        column_mapping = {
            'lease_method': {'api': 'API_WELL_NUMBER', 'drilling_days': 'DRILLING_DAYS'},
            'api12_method': {'api': 'API12', 'drilling_days': 'Drilling Days'}
        }
        
        # Test with empty lease data
        result = self.engine.compare_methods(
            empty_df, self.sample_api12_data, column_mapping, {}
        )
        assert result.total_common_wells == 0
        assert result.well_coverage.total_lease_wells == 0
        
        # Test with both empty
        result = self.engine.compare_methods(
            empty_df, empty_df, column_mapping, {}
        )
        assert result.total_common_wells == 0
        assert result.well_coverage.total_lease_wells == 0
        assert result.well_coverage.total_api12_wells == 0

    def test_missing_columns(self):
        """Test handling of missing columns in data."""
        incomplete_data = pd.DataFrame({
            'API_WELL_NUMBER': ['420030123450000'],
            # Missing drilling_days column
            'COMPLETION_DAYS': [45]
        })
        
        column_mapping = {
            'lease_method': {
                'api': 'API_WELL_NUMBER',
                'drilling_days': 'DRILLING_DAYS',  # This column doesn't exist
                'completion_days': 'COMPLETION_DAYS'
            },
            'api12_method': {
                'api': 'API12',
                'drilling_days': 'Drilling Days',
                'completion_days': 'Completion Days'
            }
        }
        
        with pytest.raises(KeyError):
            self.engine.compare_methods(
                incomplete_data, self.sample_api12_data, column_mapping, {}
            )

    def test_invalid_tolerance_config(self):
        """Test handling of invalid tolerance configuration."""
        # Test with negative tolerance
        tolerance = {'drilling_days': -1, 'completion_days': 3}
        
        with pytest.warns(UserWarning):
            engine = ComparisonEngine(tolerance_config=tolerance)
            # Should still work but with warning

    def teardown_method(self):
        """Clean up after each test method."""
        pass


class TestComparisonResult:
    """Test cases for ComparisonResult data structure."""

    def test_comparison_result_initialization(self):
        """Test ComparisonResult initialization."""
        coverage = WellCoverageAnalysis(
            total_lease_wells=10,
            total_api12_wells=8,
            common_wells=6,
            lease_only_wells=4,
            api12_only_wells=2,
            coverage_percentage=60.0
        )
        
        statistics = {
            'drilling_days': {'mean': 0.5, 'std': 1.2, 'median': 0.0},
            'completion_days': {'mean': -0.3, 'std': 2.1, 'median': 0.0}
        }
        
        matched_data = pd.DataFrame({'api': ['test']})
        discrepancies = pd.DataFrame({'api': ['test2']})
        
        result = ComparisonResult(
            total_common_wells=6,
            statistics=statistics,
            well_coverage=coverage,
            matched_data=matched_data,
            discrepancies=discrepancies
        )
        
        assert result.total_common_wells == 6
        assert result.statistics == statistics
        assert result.well_coverage == coverage
        assert len(result.matched_data) == 1
        assert len(result.discrepancies) == 1

    def test_well_coverage_analysis_initialization(self):
        """Test WellCoverageAnalysis initialization."""
        coverage = WellCoverageAnalysis(
            total_lease_wells=10,
            total_api12_wells=8,
            common_wells=6,
            lease_only_wells=4,
            api12_only_wells=2,
            coverage_percentage=60.0
        )
        
        assert coverage.total_lease_wells == 10
        assert coverage.total_api12_wells == 8
        assert coverage.common_wells == 6
        assert coverage.lease_only_wells == 4
        assert coverage.api12_only_wells == 2
        assert coverage.coverage_percentage == 60.0