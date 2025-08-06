"""
Test actual data loading with real files for API12 drilling completion analysis.

This module tests loading the actual Excel and CSV files referenced in the spec.
"""

import pytest
import pandas as pd
from pathlib import Path
from tests.modules.bsee.analysis.api12_drilling_completion_analysis.data_loader import (
    load_and_prepare_data,
    get_matching_wells,
    calculate_differences
)


class TestActualDataLoading:
    """Test class for loading actual data files."""
    
    def test_load_actual_files(self):
        """Test loading the actual lease and API12 data files."""
        lease_file = "tests/modules/bsee/analysis/results/drilling_and_completion_days_by_api_validation_20250805_191100.xlsx"
        api12_file = "tests/modules/bsee/analysis/results/well_summ_multiple_wells.csv"
        
        # Verify files exist
        assert Path(lease_file).exists(), f"Lease file not found: {lease_file}"
        assert Path(api12_file).exists(), f"API12 file not found: {api12_file}"
        
        # Load and prepare data
        lease_df, api12_df = load_and_prepare_data(lease_file, api12_file)
        
        # Test successful loading
        assert not lease_df.empty
        assert not api12_df.empty
        
        # Test expected columns are present
        assert 'api12' in lease_df.columns
        assert 'drilling_days' in lease_df.columns
        assert 'completion_days' in lease_df.columns
        
        assert 'api12' in api12_df.columns
        assert 'drilling_days' in api12_df.columns
        assert 'completion_days' in api12_df.columns
        
        print(f"Lease data shape: {lease_df.shape}")
        print(f"API12 data shape: {api12_df.shape}")
        
        # Check for matching wells
        matching_wells = get_matching_wells(lease_df, api12_df)
        print(f"Number of matching wells: {len(matching_wells)}")
        assert len(matching_wells) > 0, "No matching wells found between datasets"
        
        # Test difference calculation
        diff_df = calculate_differences(lease_df, api12_df)
        assert not diff_df.empty
        print(f"Comparison data shape: {diff_df.shape}")
        
        # Print first few comparisons for verification
        print("\nFirst 5 well comparisons:")
        print(diff_df[['api12', 'lease_drilling_days', 'api12_drilling_days', 
                       'drilling_diff', 'lease_completion_days', 'api12_completion_days', 
                       'completion_diff', 'total_diff']].head())


if __name__ == "__main__":
    test = TestActualDataLoading()
    test.test_load_actual_files()