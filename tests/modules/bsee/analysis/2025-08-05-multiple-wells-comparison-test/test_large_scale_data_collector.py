"""
Test suite for Large-Scale Data Collection and Processing Module

This module tests the scalable data loading and processing capabilities
for handling 120+ wells from both analysis methods.
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

try:
    from large_scale_data_collector import (
        DataCollectionConfig,
        LargeScaleDataCollector,
        MemoryMonitor,
        ProgressTracker,
        create_mock_data_sources,
    )

    COLLECTOR_AVAILABLE = True
except ImportError as e:
    COLLECTOR_AVAILABLE = False
    print(f"Warning: Could not import data collector: {e}")


@pytest.mark.skipif(not COLLECTOR_AVAILABLE, reason="Data collector not available")
class TestDataCollectionConfig:
    """Test configuration class for data collection."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DataCollectionConfig()

        assert config.chunk_size == 50
        assert config.memory_limit_mb == 1024
        assert config.enable_progress_tracking == True
        assert config.enable_logging == True
        assert config.log_level == "INFO"
        assert config.validation_enabled == True
        assert config.type_optimization == True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = DataCollectionConfig(
            chunk_size=25,
            memory_limit_mb=512,
            enable_progress_tracking=False,
            log_level="DEBUG",
        )

        assert config.chunk_size == 25
        assert config.memory_limit_mb == 512
        assert config.enable_progress_tracking == False
        assert config.log_level == "DEBUG"


@pytest.mark.skipif(not COLLECTOR_AVAILABLE, reason="Data collector not available")
class TestProgressTracker:
    """Test progress tracking functionality."""

    def test_progress_tracker_initialization(self):
        """Test progress tracker initialization."""
        tracker = ProgressTracker(100, "Test Operation", enable_logging=False)

        assert tracker.total_items == 100
        assert tracker.operation_name == "Test Operation"
        assert tracker.processed_items == 0
        assert tracker.enable_logging == False

    def test_progress_update(self):
        """Test progress update functionality."""
        tracker = ProgressTracker(100, "Test Operation", enable_logging=False)

        tracker.update(10)
        assert tracker.processed_items == 10

        tracker.update(5)
        assert tracker.processed_items == 15

    def test_progress_completion(self):
        """Test progress completion."""
        tracker = ProgressTracker(10, "Test Operation", enable_logging=False)

        for i in range(10):
            tracker.update(1)

        assert tracker.processed_items == 10
        tracker.finish(success=True)


@pytest.mark.skipif(not COLLECTOR_AVAILABLE, reason="Data collector not available")
class TestMemoryMonitor:
    """Test memory monitoring functionality."""

    def test_memory_monitor_initialization(self):
        """Test memory monitor initialization."""
        monitor = MemoryMonitor(512)

        assert monitor.memory_limit_bytes == 512 * 1024 * 1024
        assert monitor.peak_memory_usage == 0

    def test_memory_usage_check(self):
        """Test memory usage checking."""
        monitor = MemoryMonitor(512)

        usage_stats = monitor.check_memory_usage()

        assert "current_usage_mb" in usage_stats
        assert "peak_usage_mb" in usage_stats
        assert "memory_limit_mb" in usage_stats
        assert "usage_percentage" in usage_stats
        assert "approaching_limit" in usage_stats
        assert "exceeded_limit" in usage_stats

        assert usage_stats["memory_limit_mb"] == 512

    def test_memory_optimization(self):
        """Test memory optimization (garbage collection)."""
        monitor = MemoryMonitor(512)

        # Should not raise any exceptions
        monitor.optimize_memory()


@pytest.mark.skipif(not COLLECTOR_AVAILABLE, reason="Data collector not available")
class TestLargeScaleDataCollector:
    """Test large-scale data collection functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def config(self, temp_dir):
        """Create test configuration."""
        return DataCollectionConfig(
            chunk_size=10,
            memory_limit_mb=256,
            enable_progress_tracking=False,  # Disable for cleaner test output
            enable_logging=False,
            output_directory=temp_dir,
            validation_enabled=True,
            type_optimization=True,
        )

    @pytest.fixture
    def collector(self, config):
        """Create data collector instance."""
        return LargeScaleDataCollector(config)

    @pytest.fixture
    def mock_data_sources(self, temp_dir):
        """Create mock data sources for testing."""
        # Create lease method data files
        lease_sources = []
        api12_sources = []

        for i in range(3):  # 3 files with 10 wells each = 30 wells total
            # Lease method data
            lease_data = pd.DataFrame(
                {
                    "API_WELL_NUMBER": [
                        f"60812400{j:04d}" for j in range(i * 10, (i + 1) * 10)
                    ],
                    "WELL_NAME": [
                        f"Lease Well {j}" for j in range(i * 10, (i + 1) * 10)
                    ],
                    "DRILLING_DAYS": np.random.randint(20, 80, 10),
                    "COMPLETION_DAYS": np.random.randint(5, 25, 10),
                }
            )

            lease_file = Path(temp_dir) / f"lease_data_{i}.xlsx"
            lease_data.to_excel(lease_file, index=False)
            lease_sources.append(str(lease_file))

            # API12 method data
            api12_data = pd.DataFrame(
                {
                    "API12": [f"60812400{j:04d}" for j in range(i * 10, (i + 1) * 10)],
                    "Well_Name": [
                        f"API12 Well {j}" for j in range(i * 10, (i + 1) * 10)
                    ],
                    "Drilling Days": np.random.randint(18, 85, 10),
                    "Completion Days": np.random.randint(4, 28, 10),
                }
            )

            api12_file = Path(temp_dir) / f"api12_data_{i}.csv"
            api12_data.to_csv(api12_file, index=False)
            api12_sources.append(str(api12_file))

        return lease_sources, api12_sources

    def test_collector_initialization(self, collector):
        """Test collector initialization."""
        assert collector.config is not None
        assert collector.memory_monitor is not None
        assert collector.collection_stats["total_wells_collected"] == 0
        assert collector.collection_stats["successful_loads"] == 0
        assert collector.collection_stats["failed_loads"] == 0

    def test_lease_method_data_collection(self, collector, mock_data_sources):
        """Test lease method data collection."""
        lease_sources, _ = mock_data_sources

        collected_data = list(collector.collect_lease_method_data(lease_sources))

        assert len(collected_data) == 3  # 3 source files
        assert collector.collection_stats["successful_loads"] == 3
        assert collector.collection_stats["failed_loads"] == 0
        assert collector.collection_stats["total_wells_collected"] == 30

        # Check data structure
        for df in collected_data:
            assert "API12" in df.columns
            assert "Drilling Days" in df.columns
            assert "Completion Days" in df.columns
            assert len(df) == 10  # 10 wells per file

    def test_api12_method_data_collection(self, collector, mock_data_sources):
        """Test API12 method data collection."""
        _, api12_sources = mock_data_sources

        collected_data = list(collector.collect_api12_method_data(api12_sources))

        assert len(collected_data) == 3  # 3 source files
        assert collector.collection_stats["successful_loads"] == 3
        assert collector.collection_stats["failed_loads"] == 0
        assert collector.collection_stats["total_wells_collected"] == 30

        # Check data structure
        for df in collected_data:
            assert "API12" in df.columns
            assert "Drilling Days" in df.columns
            assert "Completion Days" in df.columns
            assert len(df) == 10  # 10 wells per file

    def test_data_aggregation(self, collector, mock_data_sources):
        """Test data aggregation functionality."""
        lease_sources, _ = mock_data_sources

        # Generate data and aggregate
        data_generator = collector.collect_lease_method_data(lease_sources)
        aggregated_df = collector.aggregate_collected_data(data_generator, max_wells=30)

        assert len(aggregated_df) == 30
        assert "API12" in aggregated_df.columns
        assert "Drilling Days" in aggregated_df.columns
        assert "Completion Days" in aggregated_df.columns

    def test_data_aggregation_with_limit(self, collector, mock_data_sources):
        """Test data aggregation with well limit."""
        lease_sources, _ = mock_data_sources

        # Generate data and aggregate with limit
        data_generator = collector.collect_lease_method_data(lease_sources)
        aggregated_df = collector.aggregate_collected_data(data_generator, max_wells=15)

        assert len(aggregated_df) == 15  # Should be limited to 15 wells

    def test_column_standardization_lease(self, collector):
        """Test lease method column standardization."""
        test_df = pd.DataFrame(
            {
                "API_WELL_NUMBER": ["608124001000"],
                "DRILLING_DAYS": [45],
                "COMPLETION_DAYS": [15],
                "WELL_NAME": ["Test Well"],
            }
        )

        standardized = collector._standardize_lease_columns(test_df)

        assert "API12" in standardized.columns
        assert "Drilling Days" in standardized.columns
        assert "Completion Days" in standardized.columns
        assert "Well Name" in standardized.columns

    def test_column_standardization_api12(self, collector):
        """Test API12 method column standardization."""
        test_df = pd.DataFrame(
            {
                "api12": ["608124001000"],
                "drilling_days": [45],
                "completion_days": [15],
                "well_name": ["Test Well"],
            }
        )

        standardized = collector._standardize_api12_columns(test_df)

        assert "API12" in standardized.columns
        assert "Drilling Days" in standardized.columns
        assert "Completion Days" in standardized.columns
        assert "Well Name" in standardized.columns

    def test_data_validation_lease(self, collector):
        """Test lease method data validation."""
        # Valid data
        valid_df = pd.DataFrame(
            {
                "API12": ["608124001000", "608124001001"],
                "Drilling Days": [45, 35],
                "Completion Days": [15, 12],
                "Well Name": ["Well A", "Well B"],
            }
        )

        validation_result = collector._validate_lease_data(valid_df, "test_source")
        assert validation_result["is_valid"] == True
        assert len(validation_result["errors"]) == 0

        # Invalid data - missing columns
        invalid_df = pd.DataFrame({"API12": ["608124001000"], "Wrong_Column": [45]})

        validation_result = collector._validate_lease_data(invalid_df, "test_source")
        assert validation_result["is_valid"] == False
        assert len(validation_result["errors"]) > 0

    def test_data_validation_api12(self, collector):
        """Test API12 method data validation."""
        # Valid data
        valid_df = pd.DataFrame(
            {
                "API12": ["608124001000", "608124001001"],
                "Drilling Days": [45, 35],
                "Completion Days": [15, 12],
            }
        )

        validation_result = collector._validate_api12_data(valid_df, "test_source")
        assert validation_result["is_valid"] == True

        # Invalid data - duplicate APIs
        invalid_df = pd.DataFrame(
            {
                "API12": ["608124001000", "608124001000"],  # Duplicate
                "Drilling Days": [45, 35],
                "Completion Days": [15, 12],
            }
        )

        validation_result = collector._validate_api12_data(invalid_df, "test_source")
        assert validation_result["is_valid"] == False
        assert any("Duplicate API12" in error for error in validation_result["errors"])

    def test_data_type_optimization(self, collector):
        """Test data type optimization."""
        test_df = pd.DataFrame(
            {
                "API12": ["608124001000", "608124001001"],
                "Drilling Days": [45, 35],
                "Completion Days": [15, 12],
                "Well Name": ["Well A", "Well B"],
            }
        )

        optimized_df = collector._optimize_data_types(test_df)

        # Check that numeric columns are optimized
        assert optimized_df["Drilling Days"].dtype in [
            "uint8",
            "uint16",
            "int16",
            "int32",
        ]
        assert optimized_df["Completion Days"].dtype in [
            "uint8",
            "uint16",
            "int16",
            "int32",
        ]

        # String columns should be optimized
        assert optimized_df["API12"].dtype == "string"

    def test_error_handling_missing_files(self, collector):
        """Test error handling for missing files."""
        non_existent_sources = ["non_existent_file1.csv", "non_existent_file2.xlsx"]

        collected_data = list(collector.collect_lease_method_data(non_existent_sources))

        assert len(collected_data) == 0
        assert collector.collection_stats["failed_loads"] == 2
        assert collector.collection_stats["successful_loads"] == 0

    def test_statistics_export(self, collector, temp_dir):
        """Test statistics export functionality."""
        # Set some test statistics
        collector.collection_stats["total_wells_collected"] = 125
        collector.collection_stats["successful_loads"] = 5
        collector.collection_stats["failed_loads"] = 1

        stats_file = collector.export_collection_stats()

        assert os.path.exists(stats_file)

        # Load and verify statistics
        with open(stats_file, "r") as f:
            stats_data = json.load(f)

        assert "timestamp" in stats_data
        assert "config" in stats_data
        assert "statistics" in stats_data
        assert stats_data["statistics"]["total_wells_collected"] == 125
        assert stats_data["statistics"]["successful_loads"] == 5
        assert stats_data["statistics"]["failed_loads"] == 1


@pytest.mark.skipif(not COLLECTOR_AVAILABLE, reason="Data collector not available")
class TestLargeScaleDataCollectionIntegration:
    """Integration tests for large-scale data collection."""

    def test_120_plus_wells_collection(self):
        """Test collection of 120+ wells."""
        config = DataCollectionConfig(
            chunk_size=30,
            memory_limit_mb=512,
            enable_progress_tracking=False,
            enable_logging=False,
            validation_enabled=True,
            type_optimization=True,
        )

        collector = LargeScaleDataCollector(config)

        # Create mock data sources with 125 wells total
        lease_sources, api12_sources = create_mock_data_sources(5, 25)

        try:
            # Collect lease method data
            lease_data_gen = collector.collect_lease_method_data(lease_sources)
            lease_df = collector.aggregate_collected_data(lease_data_gen, max_wells=125)

            # Reset collector stats for API12 collection
            collector.collection_stats = {
                "total_wells_collected": 0,
                "successful_loads": 0,
                "failed_loads": 0,
                "processing_time_seconds": 0,
                "peak_memory_usage_mb": 0,
                "data_validation_errors": 0,
            }

            # Collect API12 method data
            api12_data_gen = collector.collect_api12_method_data(api12_sources)
            api12_df = collector.aggregate_collected_data(api12_data_gen, max_wells=125)

            # Verify results
            assert len(lease_df) == 125
            assert len(api12_df) == 125

            # Verify required columns are present
            for df in [lease_df, api12_df]:
                assert "API12" in df.columns
                assert "Drilling Days" in df.columns
                assert "Completion Days" in df.columns

            # Verify data types are optimized
            assert lease_df["Drilling Days"].dtype in [
                "uint8",
                "uint16",
                "int16",
                "int32",
            ]
            assert api12_df["Completion Days"].dtype in [
                "uint8",
                "uint16",
                "int16",
                "int32",
            ]

        finally:
            # Cleanup mock files
            for source_list in [lease_sources, api12_sources]:
                for source in source_list:
                    try:
                        os.remove(source)
                    except:
                        pass

    def test_memory_optimization_large_dataset(self):
        """Test memory optimization with large datasets."""
        config = DataCollectionConfig(
            chunk_size=20,
            memory_limit_mb=256,  # Lower limit to test optimization
            enable_progress_tracking=False,
            enable_logging=False,
        )

        collector = LargeScaleDataCollector(config)

        # Create larger mock data sources
        lease_sources, api12_sources = create_mock_data_sources(6, 30)  # 180 wells

        try:
            # Test that collection completes without memory errors
            lease_data_gen = collector.collect_lease_method_data(lease_sources)
            lease_df = collector.aggregate_collected_data(lease_data_gen, max_wells=150)

            assert len(lease_df) <= 150
            assert len(lease_df) > 0

            # Verify memory monitoring worked
            memory_status = collector.memory_monitor.check_memory_usage()
            assert memory_status["peak_usage_mb"] > 0

        finally:
            # Cleanup
            for source_list in [lease_sources, api12_sources]:
                for source in source_list:
                    try:
                        os.remove(source)
                    except:
                        pass

    def test_error_recovery_mixed_sources(self):
        """Test error recovery with mix of valid and invalid sources."""
        config = DataCollectionConfig(enable_logging=False, validation_enabled=True)

        collector = LargeScaleDataCollector(config)

        # Create mix of valid and invalid sources
        valid_sources, _ = create_mock_data_sources(2, 20)  # 40 valid wells
        invalid_sources = ["non_existent1.csv", "non_existent2.xlsx"]

        mixed_sources = valid_sources + invalid_sources

        try:
            collected_data = list(collector.collect_lease_method_data(mixed_sources))

            # Should have collected from valid sources only
            assert len(collected_data) == 2  # Only 2 valid sources
            assert collector.collection_stats["successful_loads"] == 2
            assert collector.collection_stats["failed_loads"] == 2
            assert collector.collection_stats["total_wells_collected"] == 40

        finally:
            # Cleanup
            for source in valid_sources:
                try:
                    os.remove(source)
                except:
                    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
