import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import os

# Import the comparison logic classes from local module
try:
    from comparison_logic import (
        ComparisonDataLoader,
        ComparisonAnalyzer
    )
except ImportError:
    # Classes will be implemented after tests are written
    ComparisonDataLoader = None
    ComparisonAnalyzer = None


class TestComparisonDataLoader:
    """Test cases for ComparisonDataLoader class"""

    @pytest.fixture
    def sample_excel_data(self):
        """Sample data mimicking lease method Excel output"""
        return pd.DataFrame({
            'API_WELL_NUMBER': [608084001500, 608124009400, 608124011101],
            'WELL_NAME': ['TIBER-001', 'JACK-001', 'JULIA-001'],
            'DRILLING_DAYS': [151, 45, 78],
            'COMPLETION_DAYS': [13, 25, 32],
            'LEASE_NAME': ['Tiber', 'Jack', 'Julia'],
            'WATER_DEPTH': [4130, 7000, 7200]
        })

    @pytest.fixture
    def sample_csv_data(self):
        """Sample data mimicking API12 method CSV output"""
        return pd.DataFrame({
            'API12': [608084001500, 608124009400],
            'WELL_NAME': ['TIBER ST00BP00 001', 'JACK ST00BP00 001'],
            'Drilling Days': [157, 43],
            'Completion Days': [13, 27],
            'Water Depth (feet)': [4130, 7000],
            'rigdays_by_milestone': [
                '{"drilling_days": 157, "completion_days": 13, "rig_days": 170}',
                '{"drilling_days": 43, "completion_days": 27, "rig_days": 70}'
            ]
        })

    @pytest.fixture
    def temp_excel_file(self, sample_excel_data):
        """Create temporary Excel file for testing"""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            sample_excel_data.to_excel(tmp.name, index=False)
            yield tmp.name
        os.unlink(tmp.name)

    @pytest.fixture
    def temp_csv_file(self, sample_csv_data):
        """Create temporary CSV file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
            sample_csv_data.to_csv(tmp.name, index=False)
            yield tmp.name
        os.unlink(tmp.name)

    def test_load_excel_file(self, temp_excel_file):
        """Test loading Excel file from lease method"""
        if ComparisonDataLoader is None:
            pytest.skip("ComparisonDataLoader not implemented yet")
        
        loader = ComparisonDataLoader()
        data = loader.load_lease_method_data(temp_excel_file)
        
        assert isinstance(data, pd.DataFrame)
        assert len(data) == 3
        assert 'api_number' in data.columns
        assert 'drilling_days_lease' in data.columns
        assert 'completion_days_lease' in data.columns

    def test_load_csv_file(self, temp_csv_file):
        """Test loading CSV file from API12 method"""
        if ComparisonDataLoader is None:
            pytest.skip("ComparisonDataLoader not implemented yet")
            
        loader = ComparisonDataLoader()
        data = loader.load_api12_method_data(temp_csv_file)
        
        assert isinstance(data, pd.DataFrame)
        assert len(data) == 2
        assert 'api_number' in data.columns
        assert 'drilling_days_api12' in data.columns
        assert 'completion_days_api12' in data.columns

    def test_handle_missing_file(self):
        """Test error handling for missing files"""
        if ComparisonDataLoader is None:
            pytest.skip("ComparisonDataLoader not implemented yet")
            
        loader = ComparisonDataLoader()
        
        with pytest.raises(FileNotFoundError):
            loader.load_lease_method_data("nonexistent_file.xlsx")
        
        with pytest.raises(FileNotFoundError):
            loader.load_api12_method_data("nonexistent_file.csv")

    def test_column_name_standardization(self, temp_excel_file, temp_csv_file):
        """Test that column names are standardized across methods"""
        if ComparisonDataLoader is None:
            pytest.skip("ComparisonDataLoader not implemented yet")
            
        loader = ComparisonDataLoader()
        lease_data = loader.load_lease_method_data(temp_excel_file)
        api12_data = loader.load_api12_method_data(temp_csv_file)
        
        # Both should have standardized API column
        assert 'api_number' in lease_data.columns
        assert 'api_number' in api12_data.columns


class TestComparisonAnalyzer:
    """Test cases for ComparisonAnalyzer class"""

    @pytest.fixture
    def sample_lease_data(self):
        """Sample lease method data for comparison"""
        return pd.DataFrame({
            'api_number': [608084001500, 608124009400, 608124011101],
            'well_name': ['TIBER-001', 'JACK-001', 'JULIA-001'],
            'drilling_days_lease': [151, 45, 78],
            'completion_days_lease': [13, 25, 32]
        })

    @pytest.fixture
    def sample_api12_data(self):
        """Sample API12 method data for comparison"""
        return pd.DataFrame({
            'api_number': [608084001500, 608124009400],
            'well_name': ['TIBER ST00BP00 001', 'JACK ST00BP00 001'],
            'drilling_days_api12': [157, 43],
            'completion_days_api12': [13, 27]
        })

    def test_api12_matching_logic(self, sample_lease_data, sample_api12_data):
        """Test API12 matching between datasets"""
        if ComparisonAnalyzer is None:
            pytest.skip("ComparisonAnalyzer not implemented yet")
            
        analyzer = ComparisonAnalyzer()
        matched_data = analyzer.match_wells_by_api(sample_lease_data, sample_api12_data)
        
        assert isinstance(matched_data, pd.DataFrame)
        assert len(matched_data) == 2  # Two wells should match
        assert 608084001500 in matched_data['api_number'].values
        assert 608124009400 in matched_data['api_number'].values

    def test_drilling_days_difference_calculation(self, sample_lease_data, sample_api12_data):
        """Test drilling days difference calculations"""
        if ComparisonAnalyzer is None:
            pytest.skip("ComparisonAnalyzer not implemented yet")
            
        analyzer = ComparisonAnalyzer()
        matched_data = analyzer.match_wells_by_api(sample_lease_data, sample_api12_data)
        comparison_result = analyzer.calculate_drilling_days_differences(matched_data)
        
        assert 'drilling_days_difference' in comparison_result.columns
        assert 'drilling_days_percent_diff' in comparison_result.columns
        
        # Check specific calculations for TIBER well (151 vs 157)
        tiber_row = comparison_result[comparison_result['api_number'] == 608084001500]
        assert len(tiber_row) == 1
        assert tiber_row['drilling_days_difference'].iloc[0] == -6  # 151 - 157 = -6

    def test_completion_days_difference_calculation(self, sample_lease_data, sample_api12_data):
        """Test completion days difference calculations"""
        if ComparisonAnalyzer is None:
            pytest.skip("ComparisonAnalyzer not implemented yet")
            
        analyzer = ComparisonAnalyzer()
        matched_data = analyzer.match_wells_by_api(sample_lease_data, sample_api12_data)
        comparison_result = analyzer.calculate_completion_days_differences(matched_data)
        
        assert 'completion_days_difference' in comparison_result.columns
        assert 'completion_days_percent_diff' in comparison_result.columns
        
        # Check specific calculations for TIBER well (13 vs 13)
        tiber_row = comparison_result[comparison_result['api_number'] == 608084001500]
        assert len(tiber_row) == 1
        assert tiber_row['completion_days_difference'].iloc[0] == 0  # 13 - 13 = 0

    def test_percentage_difference_calculations(self):
        """Test percentage difference calculation logic"""
        if ComparisonAnalyzer is None:
            pytest.skip("ComparisonAnalyzer not implemented yet")
            
        analyzer = ComparisonAnalyzer()
        
        # Test normal percentage calculation
        percent_diff = analyzer._calculate_percentage_difference(100, 110)
        expected = ((100 - 110) / 110) * 100  # Should be -9.09%
        assert abs(percent_diff - expected) < 0.01
        
        # Test division by zero handling (second parameter is zero)
        percent_diff = analyzer._calculate_percentage_difference(10, 0)
        assert percent_diff == float('inf') or pd.isna(percent_diff)
        
        # Test normal case where first value is 0
        percent_diff = analyzer._calculate_percentage_difference(0, 10)
        assert percent_diff == -100.0  # 0 compared to 10 is -100%

    def test_discrepancy_flagging_logic(self, sample_lease_data, sample_api12_data):
        """Test discrepancy flagging based on thresholds"""
        if ComparisonAnalyzer is None:
            pytest.skip("ComparisonAnalyzer not implemented yet")
            
        analyzer = ComparisonAnalyzer()
        matched_data = analyzer.match_wells_by_api(sample_lease_data, sample_api12_data)
        
        # First calculate differences, then apply flags
        comparison_result = analyzer.calculate_drilling_days_differences(matched_data)
        comparison_result = analyzer.calculate_completion_days_differences(comparison_result)
        comparison_result = analyzer.apply_discrepancy_flags(comparison_result)
        
        assert 'status_flag' in comparison_result.columns
        
        # Check that flags are assigned correctly
        flags = comparison_result['status_flag'].unique()
        assert any(flag in ['OK', 'REVIEW', 'ERROR'] for flag in flags)

    def test_comparison_with_missing_data(self):
        """Test handling of datasets with different well counts"""
        if ComparisonAnalyzer is None:
            pytest.skip("ComparisonAnalyzer not implemented yet")
            
        lease_data = pd.DataFrame({
            'api_number': [608084001500, 608124009400, 608124011101],
            'drilling_days_lease': [151, 45, 78],
            'completion_days_lease': [13, 25, 32]
        })
        
        api12_data = pd.DataFrame({
            'api_number': [608084001500],  # Only one well
            'drilling_days_api12': [157],
            'completion_days_api12': [13]
        })
        
        analyzer = ComparisonAnalyzer()
        matched_data = analyzer.match_wells_by_api(lease_data, api12_data)
        
        assert len(matched_data) == 1  # Only one well should match
        assert matched_data['api_number'].iloc[0] == 608084001500


class TestIntegrationWithActualData:
    """Integration tests using actual output files from Task 1"""

    def test_load_actual_lease_method_output(self):
        """Test loading actual Excel output from lease method"""
        if ComparisonDataLoader is None:
            pytest.skip("ComparisonDataLoader not implemented yet")
        
        # Use the actual file generated in Task 1
        results_dir = Path(__file__).parent / "results"
        excel_files = list(results_dir.glob("drilling_and_completion_days_by_api_validation_*.xlsx"))
        
        if not excel_files:
            pytest.skip("No actual Excel output file found")
        
        loader = ComparisonDataLoader()
        data = loader.load_lease_method_data(str(excel_files[0]))
        
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        assert 'api_number' in data.columns

    def test_load_actual_api12_method_output(self):
        """Test loading actual CSV output from API12 method"""
        if ComparisonDataLoader is None:
            pytest.skip("ComparisonDataLoader not implemented yet")
        
        # Use the actual file from Task 1
        results_dir = Path(__file__).parent / "results"
        csv_file = results_dir / "well_summ_goa_tiber.csv"
        
        if not csv_file.exists():
            pytest.skip("No actual CSV output file found")
        
        loader = ComparisonDataLoader()
        data = loader.load_api12_method_data(str(csv_file))
        
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        assert 'api_number' in data.columns

    def test_end_to_end_comparison_with_actual_data(self):
        """Test complete comparison workflow with actual data"""
        if ComparisonDataLoader is None or ComparisonAnalyzer is None:
            pytest.skip("Comparison classes not implemented yet")
        
        results_dir = Path(__file__).parent / "results"
        excel_files = list(results_dir.glob("drilling_and_completion_days_by_api_validation_*.xlsx"))
        csv_file = results_dir / "well_summ_goa_tiber.csv"
        
        if not excel_files or not csv_file.exists():
            pytest.skip("Required actual output files not found")
        
        # Load data
        loader = ComparisonDataLoader()
        lease_data = loader.load_lease_method_data(str(excel_files[0]))
        api12_data = loader.load_api12_method_data(str(csv_file))
        
        # Perform comparison
        analyzer = ComparisonAnalyzer()
        matched_data = analyzer.match_wells_by_api(lease_data, api12_data)
        comparison_result = analyzer.perform_complete_comparison(matched_data)
        
        assert isinstance(comparison_result, pd.DataFrame)
        assert len(comparison_result) >= 1  # At least one well should match (Tiber)
        
        # Verify required columns exist
        expected_columns = [
            'api_number', 'drilling_days_difference', 'completion_days_difference',
            'drilling_days_percent_diff', 'completion_days_percent_diff', 'status_flag'
        ]
        for col in expected_columns:
            assert col in comparison_result.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])