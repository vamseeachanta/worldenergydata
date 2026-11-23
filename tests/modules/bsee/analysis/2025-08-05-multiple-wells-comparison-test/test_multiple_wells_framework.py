"""
Standalone test for multiple wells comparison framework functionality.

This test module verifies the core functionality without relying on
potentially problematic dependencies.
"""

import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

# Add the test directory to Python path to import our module
sys.path.insert(0, os.path.dirname(__file__))

try:
    from multiple_wells_comparison_test import MultipleWellsDataProcessor

    PROCESSOR_AVAILABLE = True
except ImportError as e:
    PROCESSOR_AVAILABLE = False
    print(f"Warning: Could not import MultipleWellsDataProcessor: {e}")


@pytest.mark.skipif(
    not PROCESSOR_AVAILABLE, reason="MultipleWellsDataProcessor not available"
)
class TestMultipleWellsFrameworkCore:
    """Core tests for multiple wells comparison framework."""

    @pytest.fixture
    def processor(self):
        """Create a MultipleWellsDataProcessor for testing."""
        return MultipleWellsDataProcessor(chunk_size=10)

    @pytest.fixture
    def sample_data_120_wells(self):
        """Create sample data with 120+ wells for testing."""
        api12_wells = [f"60812400{i:04d}" for i in range(1, 123)]

        lease_data = pd.DataFrame(
            {
                "API12": api12_wells,
                "Well Name": [f"Lease Well {i}" for i in range(1, 123)],
                "Drilling Days": [35 + (i % 25) for i in range(122)],
                "Completion Days": [8 + (i % 12) for i in range(122)],
            }
        )

        api12_data = pd.DataFrame(
            {
                "API12": api12_wells,
                "Well Name": [f"API12 Well {i}" for i in range(1, 123)],
                "Drilling Days": [37 + (i % 23) for i in range(122)],
                "Completion Days": [9 + (i % 11) for i in range(122)],
            }
        )

        return lease_data, api12_data

    def test_processor_initialization(self, processor):
        """Test processor initializes correctly for multiple wells."""
        assert processor.chunk_size == 10
        assert processor.processing_stats["total_wells_processed"] == 0
        assert processor.processing_stats["successful_comparisons"] == 0
        assert processor.processing_stats["failed_comparisons"] == 0

    def test_multiple_wells_batch_processing(self, processor, sample_data_120_wells):
        """Test batch processing with 120+ wells."""
        lease_data, api12_data = sample_data_120_wells

        # Verify we have 122 wells
        assert len(lease_data) == 122
        assert len(api12_data) == 122

        # Process in batches
        results = processor.process_in_batches(lease_data, api12_data)

        # Verify results
        assert len(results) == 122
        assert processor.processing_stats["total_wells_processed"] == 122
        assert processor.processing_stats["successful_comparisons"] == 122
        assert processor.processing_stats["failed_comparisons"] == 0

    def test_memory_optimization_chunk_sizes(self, sample_data_120_wells):
        """Test different chunk sizes for memory optimization."""
        lease_data, api12_data = sample_data_120_wells

        # Test with different chunk sizes
        chunk_sizes = [10, 25, 50]

        for chunk_size in chunk_sizes:
            processor = MultipleWellsDataProcessor(chunk_size=chunk_size)
            results = processor.process_in_batches(lease_data, api12_data)

            assert len(results) == 122
            assert processor.processing_stats["total_wells_processed"] == 122
            assert processor.chunk_size == chunk_size

    def test_data_validation_large_dataset(self, processor):
        """Test data validation with large datasets."""
        # Create valid large dataset
        large_valid_data = pd.DataFrame(
            {
                "API12": [f"60812400{i:04d}" for i in range(1, 201)],  # 200 wells
                "Well Name": [f"Well {i}" for i in range(1, 201)],
                "Drilling Days": [40 + (i % 30) for i in range(200)],
                "Completion Days": [10 + (i % 15) for i in range(200)],
            }
        )

        # Should validate successfully
        assert processor.validate_data_format(large_valid_data, "large_test_method")

        # Test with missing columns
        invalid_data = pd.DataFrame(
            {
                "API12": [f"60812400{i:04d}" for i in range(1, 51)],
                "Wrong_Column": [40 for _ in range(50)],
            }
        )

        with pytest.raises(ValueError, match="missing required columns"):
            processor.validate_data_format(invalid_data, "invalid_test_method")

    def test_column_standardization(self, processor):
        """Test that column names are standardized correctly."""
        # Test various column name formats
        test_data = pd.DataFrame(
            {
                "API_WELL_NUMBER": ["608124001000"],
                "DRILLING_DAYS": [45],
                "COMPLETION_DAYS": [15],
                "WELL_NAME": ["Test Well"],
            }
        )

        standardized = processor._standardize_column_names(test_data)

        assert "API12" in standardized.columns
        assert "Drilling Days" in standardized.columns
        assert "Completion Days" in standardized.columns
        assert "Well Name" in standardized.columns

    def test_comparison_accuracy(self, processor):
        """Test that comparison calculations are accurate."""
        # Create test row with known values
        test_row = pd.Series(
            {
                "API12": "608124001000",
                "Well Name_lease": "Test Well",
                "Drilling Days_lease": 40,
                "Drilling Days_api12": 45,
                "Completion Days_lease": 10,
                "Completion Days_api12": 12,
            }
        )

        result = processor._compare_well_data(test_row)

        # Verify calculations
        assert result["API12"] == "608124001000"
        assert result["Drilling_Days_Diff"] == 5  # 45 - 40
        assert result["Completion_Days_Diff"] == 2  # 12 - 10
        assert result["Drilling_Days_Pct_Diff"] == 12.5  # (5/40) * 100
        assert result["Completion_Days_Pct_Diff"] == 20.0  # (2/10) * 100

    def test_status_determination_logic(self, processor):
        """Test status determination for different scenarios."""
        # Test OK status (small differences)
        status_ok = processor._determine_status(2, 1, 4.0, 8.0)
        assert status_ok == "OK"

        # Test REVIEW status (one threshold exceeded)
        status_review = processor._determine_status(
            6, 1, 12.0, 8.0
        )  # drilling abs > 5 AND drilling pct > 10%
        assert (
            status_review == "ERROR"
        )  # This actually triggers ERROR due to both thresholds

        # Test actual REVIEW status (only one condition exceeded)
        status_review_actual = processor._determine_status(
            6, 1, 8.0, 3.0
        )  # only drilling abs > 5
        assert status_review_actual == "REVIEW"

        # Test ERROR status (multiple thresholds exceeded)
        status_error = processor._determine_status(
            8, 7, 20.0, 15.0
        )  # multiple exceeded
        assert status_error == "ERROR"

    def test_error_handling_missing_data(self, processor):
        """Test error handling with missing or corrupted data."""
        # Test with missing file
        with pytest.raises(FileNotFoundError):
            processor.load_method_data("nonexistent_file.csv", "test_method")

        # Test with empty dataframe
        empty_df = pd.DataFrame()
        with pytest.raises(ValueError, match="output is empty"):
            processor.validate_data_format(empty_df, "empty_method")

    def test_results_directory_creation(self):
        """Test that results directory is created correctly."""
        test_results_dir = tempfile.mkdtemp()
        try:
            # Import here to avoid dependency issues in module-level import
            sys.path.insert(0, os.path.dirname(__file__))
            from query_api_multiple_wells_rig_days_test import (
                MultipleWellsComparisonFramework,
            )

            framework = MultipleWellsComparisonFramework(results_dir=test_results_dir)
            assert framework.results_dir.exists()

        except ImportError:
            pytest.skip("MultipleWellsComparisonFramework not available")
        finally:
            # Clean up
            import shutil

            shutil.rmtree(test_results_dir, ignore_errors=True)


def test_framework_integration_without_dependencies():
    """Test that framework works without external dependencies."""
    if not PROCESSOR_AVAILABLE:
        pytest.skip("Processor not available")

    # Test basic processor functionality
    processor = MultipleWellsDataProcessor(chunk_size=20)
    assert processor is not None

    # Test with sample data
    sample_lease = pd.DataFrame(
        {
            "API12": ["608124001000", "608124001001"],
            "Well Name": ["Well A", "Well B"],
            "Drilling Days": [40, 35],
            "Completion Days": [10, 8],
        }
    )

    sample_api12 = pd.DataFrame(
        {
            "API12": ["608124001000", "608124001001"],
            "Well Name": ["Well A", "Well B"],
            "Drilling Days": [42, 33],
            "Completion Days": [11, 9],
        }
    )

    results = processor.process_in_batches(sample_lease, sample_api12)

    assert len(results) == 2
    assert processor.processing_stats["successful_comparisons"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
