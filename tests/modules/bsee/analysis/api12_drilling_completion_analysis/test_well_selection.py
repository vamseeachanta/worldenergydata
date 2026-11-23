"""
Test module for well selection algorithms in API12 drilling completion analysis.

This module tests the functionality for selecting wells with high and low
differences in drilling and completion days between lease-based and API12-based methods.
"""

from typing import Tuple

import numpy as np
import pandas as pd
import pytest


class TestWellSelection:
    """Test class for well selection functionality."""

    @pytest.fixture
    def sample_comparison_data(self):
        """Create sample comparison data for testing."""
        return pd.DataFrame(
            {
                "api12": [
                    608114062100,
                    608114062101,
                    608114063500,
                    608114063501,
                    608124003300,
                ],
                "lease_drilling_days": [64, 19, 110, 20, 78],
                "api12_drilling_days": [51, 46, 105, 21, 80],
                "drilling_diff": [13, -27, 5, -1, -2],
                "lease_completion_days": [12, 48, 54, 19, 35],
                "api12_completion_days": [0, 0, 0, 0, 37],
                "completion_diff": [12, 48, 54, 19, -2],
                "total_diff": [25, 75, 59, 20, 4],
                "well_name": ["001", "001", "002", "002", "JU101"],
                "field_name": ["Anchor", "Anchor", "Anchor", "Anchor", "Julia"],
            }
        )

    @pytest.fixture
    def large_comparison_data(self):
        """Create large comparison dataset for more comprehensive testing."""
        np.random.seed(42)  # For reproducible results
        n_wells = 100

        # Generate realistic API12 numbers
        api12_base = 608114000000
        api12_numbers = [
            api12_base + i * 100 + np.random.randint(1, 99) for i in range(n_wells)
        ]

        # Generate realistic drilling and completion days with variations
        lease_drilling = np.random.normal(60, 20, n_wells).clip(10, 200).astype(int)
        api12_drilling = lease_drilling + np.random.normal(0, 10, n_wells).astype(int)

        lease_completion = np.random.normal(25, 15, n_wells).clip(0, 100).astype(int)
        api12_completion = lease_completion + np.random.normal(0, 8, n_wells).astype(
            int
        )

        drilling_diff = lease_drilling - api12_drilling
        completion_diff = lease_completion - api12_completion
        total_diff = np.abs(drilling_diff) + np.abs(completion_diff)

        return pd.DataFrame(
            {
                "api12": api12_numbers,
                "lease_drilling_days": lease_drilling,
                "api12_drilling_days": api12_drilling,
                "drilling_diff": drilling_diff,
                "lease_completion_days": lease_completion,
                "api12_completion_days": api12_completion,
                "completion_diff": completion_diff,
                "total_diff": total_diff,
                "well_name": [f"Well_{i:03d}" for i in range(n_wells)],
                "field_name": ["TestField"] * n_wells,
            }
        )

    def test_find_high_difference_well(self, sample_comparison_data):
        """Test finding well with highest total difference."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.well_selector import (
            find_high_difference_well,
        )

        high_diff_well = find_high_difference_well(sample_comparison_data)

        # Should return the well with highest total_diff (75)
        assert high_diff_well["api12"] == 608114062101
        assert high_diff_well["total_diff"] == 75
        assert high_diff_well["drilling_diff"] == -27
        assert high_diff_well["completion_diff"] == 48

    def test_find_low_difference_well(self, sample_comparison_data):
        """Test finding well with lowest total difference."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.well_selector import (
            find_low_difference_well,
        )

        low_diff_well = find_low_difference_well(sample_comparison_data)

        # Should return the well with lowest total_diff (4)
        assert low_diff_well["api12"] == 608124003300
        assert low_diff_well["total_diff"] == 4
        assert low_diff_well["drilling_diff"] == -2
        assert low_diff_well["completion_diff"] == -2

    def test_find_wells_with_zero_difference(self):
        """Test handling of wells with zero total difference."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.well_selector import (
            find_low_difference_well,
        )

        # Create data with zero differences
        zero_diff_data = pd.DataFrame(
            {
                "api12": [608114062100, 608114062101, 608114063500],
                "total_diff": [0, 5, 0],
                "drilling_diff": [0, 3, 0],
                "completion_diff": [0, 2, 0],
                "well_name": ["001", "002", "003"],
                "field_name": ["Field1", "Field1", "Field1"],
            }
        )

        low_diff_well = find_low_difference_well(zero_diff_data)

        # Should return one of the zero difference wells
        assert low_diff_well["total_diff"] == 0

    def test_select_representative_wells(self, sample_comparison_data):
        """Test selecting both high and low difference wells."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.well_selector import (
            select_representative_wells,
        )

        high_well, low_well = select_representative_wells(sample_comparison_data)

        # High difference well
        assert high_well["api12"] == 608114062101
        assert high_well["total_diff"] == 75

        # Low difference well
        assert low_well["api12"] == 608124003300
        assert low_well["total_diff"] == 4

        # Ensure they are different wells
        assert high_well["api12"] != low_well["api12"]

    def test_well_selection_with_large_dataset(self, large_comparison_data):
        """Test well selection with larger dataset."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.well_selector import (
            select_representative_wells,
        )

        high_well, low_well = select_representative_wells(large_comparison_data)

        # Should select different wells
        assert high_well["api12"] != low_well["api12"]

        # High difference well should have higher total_diff than low difference well
        assert high_well["total_diff"] > low_well["total_diff"]

        # High difference well should be among the highest differences
        max_diff = large_comparison_data["total_diff"].max()
        assert high_well["total_diff"] == max_diff

        # Low difference well should be among the lowest differences
        min_diff = large_comparison_data["total_diff"].min()
        assert low_well["total_diff"] == min_diff

    def test_empty_dataset_handling(self):
        """Test handling of empty comparison data."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.well_selector import (
            select_representative_wells,
        )

        empty_data = pd.DataFrame(
            columns=[
                "api12",
                "total_diff",
                "drilling_diff",
                "completion_diff",
                "well_name",
                "field_name",
            ]
        )

        with pytest.raises(ValueError, match="Empty dataset"):
            select_representative_wells(empty_data)

    def test_single_well_dataset(self):
        """Test handling of dataset with single well."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.well_selector import (
            select_representative_wells,
        )

        single_well_data = pd.DataFrame(
            {
                "api12": [608114062100],
                "total_diff": [25],
                "drilling_diff": [10],
                "completion_diff": [15],
                "well_name": ["001"],
                "field_name": ["Field1"],
            }
        )

        high_well, low_well = select_representative_wells(single_well_data)

        # Should return the same well for both high and low
        assert high_well["api12"] == low_well["api12"]
        assert high_well["api12"] == 608114062100

    def test_get_well_details(self, sample_comparison_data):
        """Test extracting detailed information for selected wells."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.well_selector import (
            get_well_details,
        )

        api12_num = 608114062101
        details = get_well_details(sample_comparison_data, api12_num)

        assert details["api12"] == api12_num
        assert details["well_name"] == "001"
        assert details["field_name"] == "Anchor"
        assert details["lease_drilling_days"] == 19
        assert details["api12_drilling_days"] == 46
        assert details["drilling_diff"] == -27
        assert details["lease_completion_days"] == 48
        assert details["api12_completion_days"] == 0
        assert details["completion_diff"] == 48
        assert details["total_diff"] == 75

    def test_get_well_details_nonexistent(self, sample_comparison_data):
        """Test getting details for non-existent well."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.well_selector import (
            get_well_details,
        )

        with pytest.raises(ValueError, match="Well with API12"):
            get_well_details(sample_comparison_data, 999999999999)

    def test_calculate_difference_statistics(self, sample_comparison_data):
        """Test calculation of difference statistics."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.well_selector import (
            calculate_difference_statistics,
        )

        stats = calculate_difference_statistics(sample_comparison_data)

        # Test basic statistics structure
        assert "drilling_diff" in stats
        assert "completion_diff" in stats
        assert "total_diff" in stats

        # Test drilling difference statistics
        drilling_stats = stats["drilling_diff"]
        assert "mean" in drilling_stats
        assert "std" in drilling_stats
        assert "min" in drilling_stats
        assert "max" in drilling_stats
        assert "median" in drilling_stats

        # Test values
        expected_drilling_mean = np.mean([-27, 13, 5, -1, -2])
        assert abs(drilling_stats["mean"] - expected_drilling_mean) < 0.001

        # Test total difference statistics
        total_stats = stats["total_diff"]
        expected_total_max = max([25, 75, 59, 20, 4])
        expected_total_min = min([25, 75, 59, 20, 4])
        assert total_stats["max"] == expected_total_max
        assert total_stats["min"] == expected_total_min

    def test_filter_wells_by_criteria(self, large_comparison_data):
        """Test filtering wells by various criteria."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.well_selector import (
            filter_wells_by_criteria,
        )

        # Filter wells with high drilling differences
        high_drilling_diff = filter_wells_by_criteria(
            large_comparison_data, criteria={"drilling_diff": (">", 10)}
        )

        assert all(high_drilling_diff["drilling_diff"] > 10)

        # Filter wells with low total differences
        low_total_diff = filter_wells_by_criteria(
            large_comparison_data, criteria={"total_diff": ("<", 5)}
        )

        assert all(low_total_diff["total_diff"] < 5)

        # Multiple criteria
        complex_filter = filter_wells_by_criteria(
            large_comparison_data,
            criteria={"drilling_diff": (">", 0), "completion_diff": ("<", 0)},
        )

        assert all(complex_filter["drilling_diff"] > 0)
        assert all(complex_filter["completion_diff"] < 0)

    def test_ranking_wells_by_difference(self, sample_comparison_data):
        """Test ranking wells by total difference."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.well_selector import (
            rank_wells_by_difference,
        )

        ranked_wells = rank_wells_by_difference(sample_comparison_data)

        # Should be sorted by total_diff in descending order
        assert ranked_wells.iloc[0]["total_diff"] == 75  # Highest
        assert ranked_wells.iloc[-1]["total_diff"] == 4  # Lowest

        # Verify order is correct
        total_diffs = ranked_wells["total_diff"].tolist()
        assert total_diffs == sorted(total_diffs, reverse=True)

    def test_well_matching_validation(self, sample_comparison_data):
        """Test validation that selected wells exist in comparison data."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.well_selector import (
            validate_well_selection,
        )

        # Test with valid wells
        valid_wells = [608114062100, 608114062101]
        assert validate_well_selection(sample_comparison_data, valid_wells) is True

        # Test with invalid wells
        invalid_wells = [999999999999, 888888888888]
        assert validate_well_selection(sample_comparison_data, invalid_wells) is False

        # Test with mixed valid/invalid wells
        mixed_wells = [608114062100, 999999999999]
        assert validate_well_selection(sample_comparison_data, mixed_wells) is False
