"""
Test suite for Performance Optimization and Memory Management Module

This module tests the memory usage optimization and performance benchmarking
capabilities for handling 120+ wells comparison analysis efficiently.
"""

import gc
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import psutil
import pytest

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

try:
    from performance_optimizer import (
        BatchProcessor,
        DataTypeOptimizer,
        MemoryMonitor,
        MemoryProfile,
        PerformanceMetrics,
        PerformanceOptimizer,
        ResourceConstraints,
        benchmark_comparison_performance,
        memory_profiler,
    )

    OPTIMIZER_AVAILABLE = True
except ImportError as e:
    OPTIMIZER_AVAILABLE = False
    print(f"Warning: Could not import performance optimizer: {e}")


@pytest.mark.skipif(
    not OPTIMIZER_AVAILABLE, reason="Performance optimizer not available"
)
class TestMemoryProfile:
    """Test memory profile data structure."""

    def test_memory_profile_creation(self):
        """Test memory profile initialization."""
        profile = MemoryProfile(
            peak_memory_mb=100.5,
            start_memory_mb=80.0,
            end_memory_mb=90.0,
            memory_delta_mb=10.0,
            max_memory_percent=15.5,
        )

        assert profile.peak_memory_mb == 100.5
        assert profile.start_memory_mb == 80.0
        assert profile.end_memory_mb == 90.0
        assert profile.memory_delta_mb == 10.0
        assert profile.max_memory_percent == 15.5
        assert profile.gc_collections is not None

    def test_memory_profile_defaults(self):
        """Test memory profile default values."""
        profile = MemoryProfile()

        assert profile.peak_memory_mb == 0.0
        assert profile.start_memory_mb == 0.0
        assert profile.end_memory_mb == 0.0
        assert profile.memory_delta_mb == 0.0
        assert profile.max_memory_percent == 0.0
        assert profile.gc_collections == {"gen0": 0, "gen1": 0, "gen2": 0}


@pytest.mark.skipif(
    not OPTIMIZER_AVAILABLE, reason="Performance optimizer not available"
)
class TestPerformanceMetrics:
    """Test performance metrics data structure."""

    def test_performance_metrics_creation(self):
        """Test performance metrics initialization."""
        metrics = PerformanceMetrics(
            execution_time_seconds=2.5,
            rows_processed=1000,
            rows_per_second=400.0,
            memory_efficiency_score=85.5,
            processing_chunks=5,
            average_chunk_time=0.5,
        )

        assert metrics.execution_time_seconds == 2.5
        assert metrics.rows_processed == 1000
        assert metrics.rows_per_second == 400.0
        assert metrics.memory_efficiency_score == 85.5
        assert metrics.processing_chunks == 5
        assert metrics.average_chunk_time == 0.5


@pytest.mark.skipif(
    not OPTIMIZER_AVAILABLE, reason="Performance optimizer not available"
)
class TestResourceConstraints:
    """Test resource constraints configuration."""

    def test_resource_constraints_defaults(self):
        """Test default resource constraints."""
        constraints = ResourceConstraints()

        assert constraints.max_memory_mb is None
        assert constraints.max_processing_time_seconds is None
        assert constraints.max_chunk_size == 100
        assert constraints.min_chunk_size == 10
        assert constraints.memory_warning_threshold == 0.8
        assert constraints.enable_gc_optimization == True

    def test_resource_constraints_custom(self):
        """Test custom resource constraints."""
        constraints = ResourceConstraints(
            max_memory_mb=512.0,
            max_processing_time_seconds=60.0,
            max_chunk_size=50,
            min_chunk_size=5,
            memory_warning_threshold=0.7,
            enable_gc_optimization=False,
        )

        assert constraints.max_memory_mb == 512.0
        assert constraints.max_processing_time_seconds == 60.0
        assert constraints.max_chunk_size == 50
        assert constraints.min_chunk_size == 5
        assert constraints.memory_warning_threshold == 0.7
        assert constraints.enable_gc_optimization == False


@pytest.mark.skipif(
    not OPTIMIZER_AVAILABLE, reason="Performance optimizer not available"
)
class TestMemoryMonitor:
    """Test memory monitoring functionality."""

    def test_memory_monitor_initialization(self):
        """Test memory monitor initialization."""
        monitor = MemoryMonitor(sampling_interval=0.05)

        assert monitor.sampling_interval == 0.05
        assert monitor._monitoring == False
        assert monitor._memory_samples == []

    def test_memory_monitor_start_stop(self):
        """Test memory monitor start and stop."""
        monitor = MemoryMonitor(sampling_interval=0.01)

        # Start monitoring
        monitor.start_monitoring()
        assert monitor._monitoring == True

        # Let it run briefly
        time.sleep(0.05)

        # Stop monitoring
        samples = monitor.stop_monitoring()
        assert monitor._monitoring == False
        assert isinstance(samples, list)
        assert len(samples) > 0

        # Each sample should be (time, memory_mb) tuple
        for sample in samples:
            assert len(sample) == 2
            assert isinstance(sample[0], float)  # time
            assert isinstance(sample[1], float)  # memory_mb
            assert sample[1] > 0  # Memory should be positive

    def test_memory_monitor_peak_memory(self):
        """Test peak memory calculation."""
        monitor = MemoryMonitor(sampling_interval=0.01)

        monitor.start_monitoring()
        time.sleep(0.03)  # Brief monitoring
        monitor.stop_monitoring()

        peak_memory = monitor.get_peak_memory()
        assert isinstance(peak_memory, float)
        assert peak_memory > 0

    def test_memory_monitor_no_samples(self):
        """Test memory monitor with no samples."""
        monitor = MemoryMonitor()
        peak_memory = monitor.get_peak_memory()
        assert peak_memory == 0.0


@pytest.mark.skipif(
    not OPTIMIZER_AVAILABLE, reason="Performance optimizer not available"
)
class TestDataTypeOptimizer:
    """Test data type optimization functionality."""

    @pytest.fixture
    def sample_dataframe(self):
        """Create sample DataFrame for testing."""
        np.random.seed(42)
        return pd.DataFrame(
            {
                "large_int": np.random.randint(0, 100, 1000),  # Can be int8
                "medium_int": np.random.randint(0, 10000, 1000),  # Can be int16
                "small_float": np.random.rand(1000) * 10,  # Can be float32
                "categories": np.random.choice(
                    ["A", "B", "C", "D"], 1000
                ),  # Can be category
                "high_cardinality": [
                    f"item_{i}" for i in range(1000)
                ],  # Should stay object
                "api12": np.random.choice(
                    [f"60812400{i:04d}" for i in range(100)], 1000
                ),  # Repeated API12s - can be category
            }
        )

    def test_datatype_optimizer_basic(self, sample_dataframe):
        """Test basic data type optimization."""
        original_memory = sample_dataframe.memory_usage(deep=True).sum()

        optimized_df = DataTypeOptimizer.optimize_dataframe(sample_dataframe)
        optimized_memory = optimized_df.memory_usage(deep=True).sum()

        # Optimized should use less memory
        assert optimized_memory < original_memory

        # Check specific optimizations
        assert optimized_df["large_int"].dtype == "int8"  # 0-100 range
        assert optimized_df["medium_int"].dtype == "int16"  # 0-10000 range
        assert optimized_df["categories"].dtype.name == "category"  # Low cardinality
        assert optimized_df["api12"].dtype.name == "category"  # Repetitive pattern

    def test_datatype_optimizer_aggressive(self, sample_dataframe):
        """Test aggressive data type optimization."""
        optimized_df = DataTypeOptimizer.optimize_dataframe(
            sample_dataframe, aggressive=True
        )

        # With aggressive optimization, floats might be converted to float32
        assert optimized_df["small_float"].dtype in ["float32", "float64"]

        # Other optimizations should still apply
        assert optimized_df["large_int"].dtype == "int8"
        assert optimized_df["categories"].dtype.name == "category"

    def test_memory_usage_calculation(self, sample_dataframe):
        """Test memory usage calculation."""
        memory_info = DataTypeOptimizer.get_memory_usage(sample_dataframe)

        assert "total_mb" in memory_info
        assert "index_mb" in memory_info
        assert "columns" in memory_info

        assert memory_info["total_mb"] > 0
        assert memory_info["index_mb"] >= 0
        assert len(memory_info["columns"]) == len(sample_dataframe.columns)

        # Check column-specific info
        for col in sample_dataframe.columns:
            assert col in memory_info["columns"]
            assert "mb" in memory_info["columns"][col]
            assert "dtype" in memory_info["columns"][col]
            assert memory_info["columns"][col]["mb"] > 0

    def test_optimization_edge_cases(self):
        """Test optimization with edge cases."""
        # Empty DataFrame
        empty_df = pd.DataFrame()
        optimized_empty = DataTypeOptimizer.optimize_dataframe(empty_df)
        assert len(optimized_empty.columns) == 0

        # DataFrame with NaN values
        nan_df = pd.DataFrame(
            {"with_nan": [1, 2, np.nan, 4, 5], "all_nan": [np.nan] * 5}
        )
        optimized_nan = DataTypeOptimizer.optimize_dataframe(nan_df)
        assert len(optimized_nan) == 5

        # DataFrame with single column
        single_col_df = pd.DataFrame({"single": [1, 2, 3, 4, 5]})
        optimized_single = DataTypeOptimizer.optimize_dataframe(single_col_df)
        assert optimized_single["single"].dtype == "int8"


@pytest.mark.skipif(
    not OPTIMIZER_AVAILABLE, reason="Performance optimizer not available"
)
class TestBatchProcessor:
    """Test batch processing functionality."""

    @pytest.fixture
    def large_dataframe(self):
        """Create large DataFrame for batch testing."""
        np.random.seed(42)
        return pd.DataFrame(
            {
                "api12": [f"60812400{i:04d}" for i in range(250)],  # 250 rows
                "drilling_days": np.random.normal(45, 10, 250).astype(int),
                "completion_days": np.random.normal(15, 4, 250).astype(int),
                "well_name": [f"Well {i+1}" for i in range(250)],
            }
        )

    def test_batch_processor_initialization(self):
        """Test batch processor initialization."""
        processor = BatchProcessor(chunk_size=25)

        assert processor.chunk_size == 25
        assert processor.memory_monitor is not None

    def test_dataframe_batch_processing(self, large_dataframe):
        """Test DataFrame batch processing."""
        processor = BatchProcessor(chunk_size=50)

        # Simple processing function that returns batch size
        def count_rows(batch_df):
            return len(batch_df)

        batch_sizes = []
        progress_calls = []

        def progress_callback(processed, total):
            progress_calls.append((processed, total))

        # Process in batches
        for batch_size in processor.process_dataframe_batches(
            large_dataframe, count_rows, progress_callback
        ):
            batch_sizes.append(batch_size)

        # Verify batching worked correctly
        expected_batches = len(large_dataframe) // 50 + (
            1 if len(large_dataframe) % 50 > 0 else 0
        )
        assert len(batch_sizes) == expected_batches
        assert sum(batch_sizes) == len(large_dataframe)

        # Most batches should be size 50, last might be smaller
        for i, size in enumerate(batch_sizes[:-1]):
            assert size == 50

        # Progress callbacks should have been made
        assert len(progress_calls) > 0
        assert progress_calls[-1][0] == len(
            large_dataframe
        )  # Final progress should be total
        assert progress_calls[-1][1] == len(large_dataframe)

    def test_batch_merge_operations(self, large_dataframe):
        """Test batch merging operations."""
        processor = BatchProcessor(chunk_size=100)

        # Create second DataFrame for merging
        right_df = pd.DataFrame(
            {
                "api12": [
                    f"60812400{i:04d}" for i in range(0, 250, 2)
                ],  # Every other well
                "field_name": [f"Field {i//2}" for i in range(0, 250, 2)],
            }
        )

        # Test direct merge (should fit in memory)
        merged_direct = processor.merge_dataframes_batched(
            large_dataframe, right_df, on="api12", how="inner"
        )

        assert not merged_direct.empty
        assert "field_name" in merged_direct.columns
        assert len(merged_direct) == len(right_df)  # Inner join result

    def test_batch_merge_with_memory_limit(self, large_dataframe):
        """Test batch merging with memory constraints."""
        processor = BatchProcessor(chunk_size=50)

        right_df = pd.DataFrame(
            {
                "api12": large_dataframe["api12"].tolist(),
                "extra_data": ["data"] * len(large_dataframe),
            }
        )

        # Force batched merge with very low memory limit
        merged = processor.merge_dataframes_batched(
            large_dataframe,
            right_df,
            on="api12",
            memory_limit_mb=0.001,  # Tiny limit to force batching
        )

        assert not merged.empty
        assert len(merged) == len(large_dataframe)
        assert "extra_data" in merged.columns

    def test_empty_batch_processing(self):
        """Test batch processing with empty DataFrame."""
        processor = BatchProcessor(chunk_size=10)
        empty_df = pd.DataFrame()

        results = list(processor.process_dataframe_batches(empty_df, lambda x: len(x)))

        assert len(results) == 0


@pytest.mark.skipif(
    not OPTIMIZER_AVAILABLE, reason="Performance optimizer not available"
)
class TestMemoryProfiler:
    """Test memory profiler decorator."""

    def test_memory_profiler_basic(self):
        """Test basic memory profiler functionality."""

        @memory_profiler
        def create_large_array():
            # Create a moderately sized array to trigger memory usage
            arr = np.random.rand(10000, 10)
            return arr.sum()

        result = create_large_array()

        # Result should be a number (sum of array)
        assert isinstance(result, (int, float))
        assert result > 0

    def test_memory_profiler_with_dict_result(self):
        """Test memory profiler with dictionary result."""

        @memory_profiler
        def process_data():
            data = {"processed_items": 1000, "status": "complete"}
            return data

        result = process_data()

        assert "processed_items" in result
        assert "status" in result
        assert "memory_profile" in result

        profile = result["memory_profile"]
        assert isinstance(profile, MemoryProfile)
        assert profile.start_memory_mb > 0
        assert profile.end_memory_mb > 0

    def test_memory_profiler_with_exception(self):
        """Test memory profiler when function raises exception."""

        @memory_profiler
        def failing_function():
            raise ValueError("Test exception")

        with pytest.raises(ValueError, match="Test exception"):
            failing_function()


@pytest.mark.skipif(
    not OPTIMIZER_AVAILABLE, reason="Performance optimizer not available"
)
class TestPerformanceOptimizer:
    """Test main performance optimizer functionality."""

    @pytest.fixture
    def large_dataset(self):
        """Create large dataset for testing."""
        np.random.seed(42)
        return pd.DataFrame(
            {
                "api12": [f"60812400{i:04d}" for i in range(150)],
                "well_name": [f"Well {i+1}" for i in range(150)],
                "drilling_days": np.random.normal(50, 12, 150).astype(int),
                "completion_days": np.random.normal(18, 5, 150).astype(int),
                "operator": np.random.choice(["OpA", "OpB", "OpC"], 150),
                "field": np.random.choice(
                    ["Field1", "Field2", "Field3", "Field4"], 150
                ),
            }
        )

    def test_optimizer_initialization(self):
        """Test optimizer initialization."""
        constraints = ResourceConstraints(max_chunk_size=75)
        optimizer = PerformanceOptimizer(constraints)

        assert optimizer.constraints.max_chunk_size == 75
        assert optimizer.batch_processor is not None
        assert optimizer.data_optimizer is not None
        assert len(optimizer._performance_history) == 0

    def test_optimize_for_large_dataset(self, large_dataset):
        """Test optimization for large dataset."""
        optimizer = PerformanceOptimizer()

        progress_messages = []

        def progress_callback(message):
            progress_messages.append(message)

        # Simple processing function
        def process_data(df):
            return {
                "total_wells": len(df),
                "avg_drilling_days": df["drilling_days"].mean(),
                "avg_completion_days": df["completion_days"].mean(),
            }

        result, metrics = optimizer.optimize_for_large_dataset(
            large_dataset, process_data, progress_callback
        )

        # Check result
        assert "total_wells" in result
        assert result["total_wells"] == 150
        assert "avg_drilling_days" in result
        assert "avg_completion_days" in result

        # Check metrics
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.execution_time_seconds > 0
        assert metrics.rows_processed == 150
        assert metrics.rows_per_second > 0
        assert 0 <= metrics.memory_efficiency_score <= 100

        # Check progress messages
        assert len(progress_messages) > 0
        assert any("Optimizing data types" in msg for msg in progress_messages)
        assert any("complete" in msg.lower() for msg in progress_messages)

    def test_system_resource_check(self):
        """Test system resource checking."""
        optimizer = PerformanceOptimizer()
        resources = optimizer.check_system_resources()

        assert "memory" in resources
        assert "cpu" in resources
        assert "recommendations" in resources

        # Memory info
        memory_info = resources["memory"]
        assert "total_gb" in memory_info
        assert "available_gb" in memory_info
        assert "used_percent" in memory_info
        assert "available_for_processing_gb" in memory_info

        assert memory_info["total_gb"] > 0
        assert memory_info["available_gb"] > 0
        assert 0 <= memory_info["used_percent"] <= 100

        # CPU info
        cpu_info = resources["cpu"]
        assert "usage_percent" in cpu_info
        assert "core_count" in cpu_info
        assert cpu_info["core_count"] > 0

        # Recommendations
        assert isinstance(resources["recommendations"], list)
        assert len(resources["recommendations"]) > 0

    def test_performance_summary(self, large_dataset):
        """Test performance summary generation."""
        optimizer = PerformanceOptimizer()

        # Initially no performance data
        summary = optimizer.get_performance_summary()
        assert "message" in summary
        assert "No performance data available" in summary["message"]

        # Run some operations to generate performance data
        def simple_process(df):
            return df.groupby("operator").size().to_dict()

        for i in range(3):
            optimizer.optimize_for_large_dataset(large_dataset, simple_process)

        # Now should have performance summary
        summary = optimizer.get_performance_summary()

        assert "total_operations" in summary
        assert summary["total_operations"] == 3
        assert "average_execution_time" in summary
        assert "average_rows_per_second" in summary
        assert "average_memory_efficiency" in summary
        assert "total_rows_processed" in summary
        assert "performance_trend" in summary

        assert summary["average_execution_time"] > 0
        assert summary["total_rows_processed"] == 150 * 3  # 3 operations * 150 rows

    def test_memory_constrained_processing(self, large_dataset):
        """Test processing with memory constraints."""
        # Set very low memory limit to force batch processing
        constraints = ResourceConstraints(
            max_memory_mb=1.0,  # Very low limit
            max_chunk_size=25,
            enable_gc_optimization=True,
        )

        optimizer = PerformanceOptimizer(constraints)

        def memory_intensive_process(df):
            # Create some additional data to use memory
            df_copy = df.copy()
            df_copy["extra_col"] = df_copy["drilling_days"] * df_copy["completion_days"]
            return df_copy.groupby("field")["extra_col"].sum().to_dict()

        result, metrics = optimizer.optimize_for_large_dataset(
            large_dataset, memory_intensive_process
        )

        # Should still get valid results
        assert isinstance(result, dict)
        assert len(result) > 0

        # Should have used multiple chunks due to memory constraints
        assert metrics.processing_chunks > 1
        assert metrics.average_chunk_time > 0


@pytest.mark.skipif(
    not OPTIMIZER_AVAILABLE, reason="Performance optimizer not available"
)
class TestPerformanceBenchmarking:
    """Test performance benchmarking functionality."""

    @pytest.fixture
    def benchmark_datasets(self):
        """Create datasets for benchmarking."""
        np.random.seed(42)

        lease_df = pd.DataFrame(
            {
                "API12": [f"60812400{i:04d}" for i in range(100)],
                "Well_Name": [f"Lease Well {i}" for i in range(100)],
                "Drilling_Days": np.random.normal(45, 8, 100).astype(int),
                "Completion_Days": np.random.normal(15, 3, 100).astype(int),
            }
        )

        api12_df = pd.DataFrame(
            {
                "API12": [f"60812400{i:04d}" for i in range(100)],
                "Well_Name": [f"API12 Well {i}" for i in range(100)],
                "Drilling_Days": np.random.normal(47, 9, 100).astype(int),
                "Completion_Days": np.random.normal(16, 4, 100).astype(int),
            }
        )

        return lease_df, api12_df

    def test_benchmark_comparison_performance(self, benchmark_datasets):
        """Test comparison performance benchmarking."""
        lease_df, api12_df = benchmark_datasets

        def simple_comparison(df1, df2):
            """Simple comparison function for benchmarking."""
            merged = pd.merge(df1, df2, on="API12", suffixes=("_lease", "_api12"))
            merged["drilling_diff"] = (
                merged["Drilling_Days_api12"] - merged["Drilling_Days_lease"]
            )
            merged["completion_diff"] = (
                merged["Completion_Days_api12"] - merged["Completion_Days_lease"]
            )
            return merged[["API12", "drilling_diff", "completion_diff"]]

        # Run benchmark with 2 iterations for speed
        benchmark_results = benchmark_comparison_performance(
            lease_df, api12_df, simple_comparison, iterations=2
        )

        # Check benchmark structure
        assert "benchmark_results" in benchmark_results
        assert "summary" in benchmark_results
        assert "system_info" in benchmark_results

        # Check individual results
        results = benchmark_results["benchmark_results"]
        assert len(results) == 2

        for result in results:
            assert "iteration" in result
            assert "execution_time" in result
            assert "memory_efficiency" in result
            assert "data_size_mb" in result

            assert result["execution_time"] > 0
            assert 0 <= result["memory_efficiency"] <= 100
            assert result["data_size_mb"] > 0

        # Check summary statistics
        summary = benchmark_results["summary"]
        assert "average_execution_time" in summary
        assert "min_execution_time" in summary
        assert "max_execution_time" in summary
        assert "std_execution_time" in summary
        assert "average_memory_efficiency" in summary
        assert "total_data_size_mb" in summary

        assert summary["average_execution_time"] > 0
        assert summary["min_execution_time"] <= summary["average_execution_time"]
        assert summary["max_execution_time"] >= summary["average_execution_time"]

        # Check system info
        system_info = benchmark_results["system_info"]
        assert "memory" in system_info
        assert "cpu" in system_info
        assert "recommendations" in system_info


@pytest.mark.skipif(
    not OPTIMIZER_AVAILABLE, reason="Performance optimizer not available"
)
class TestPerformanceOptimizerIntegration:
    """Integration tests for performance optimizer with large datasets."""

    def test_120_plus_wells_optimization(self):
        """Test performance optimization with 120+ wells."""
        # Create 125 wells dataset
        np.random.seed(123)

        large_dataset = pd.DataFrame(
            {
                "api12": [f"60812400{i:05d}" for i in range(122)],
                "well_name": [f"Well {i+1}" for i in range(122)],
                "drilling_days": np.random.normal(50, 15, 122).astype(int),
                "completion_days": np.random.normal(18, 6, 122).astype(int),
                "operator": np.random.choice(["Shell", "BP", "Exxon", "Chevron"], 122),
                "field": np.random.choice(["Field_A", "Field_B", "Field_C"], 122),
                "water_depth": np.random.normal(1500, 500, 125).astype(int),
            }
        )

        # Performance-constrained optimizer
        constraints = ResourceConstraints(
            max_chunk_size=40,  # Smaller chunks
            memory_warning_threshold=0.6,
            enable_gc_optimization=True,
        )

        optimizer = PerformanceOptimizer(constraints)

        def complex_analysis(df):
            """Complex analysis function to test performance."""
            # Multiple operations to stress test
            grouped = (
                df.groupby(["operator", "field"])
                .agg(
                    {
                        "drilling_days": ["mean", "std", "count"],
                        "completion_days": ["mean", "std", "count"],
                        "water_depth": ["mean", "min", "max"],
                    }
                )
                .round(2)
            )

            # Flatten multi-level columns
            grouped.columns = ["_".join(col).strip() for col in grouped.columns]

            return grouped.reset_index()

        progress_updates = []

        def track_progress(message):
            progress_updates.append(message)

        # Execute optimization
        result, metrics = optimizer.optimize_for_large_dataset(
            large_dataset, complex_analysis, track_progress
        )

        # Verify results
        assert not result.empty
        assert len(result) > 0  # Should have grouped results
        assert "operator" in result.columns
        assert "field" in result.columns

        # Verify performance metrics
        assert metrics.rows_processed == 125
        assert metrics.execution_time_seconds > 0
        assert metrics.rows_per_second > 0
        assert 0 <= metrics.memory_efficiency_score <= 100

        # Should have processed efficiently
        assert metrics.execution_time_seconds < 30  # Should complete within 30 seconds
        assert metrics.rows_per_second > 5  # At least 5 rows per second

        # Verify progress tracking
        assert len(progress_updates) > 0
        assert any("Optimizing data types" in msg for msg in progress_updates)
        assert any("complete" in msg.lower() for msg in progress_updates)

    def test_memory_efficiency_large_dataset(self):
        """Test memory efficiency with large dataset processing."""
        # Create dataset with memory-intensive data types
        np.random.seed(456)

        inefficient_dataset = pd.DataFrame(
            {
                "api12": [f"60812400{i:05d}" for i in range(200)],  # Could be category
                "well_name": [f"Well {i+1}" for i in range(200)],  # High cardinality
                "large_ints": np.random.randint(0, 100, 200),  # Could be int8
                "medium_ints": np.random.randint(0, 5000, 200),  # Could be int16
                "float_data": np.random.rand(200) * 100,  # Could be float32
                "status": np.random.choice(
                    ["Active", "Inactive", "Pending"], 200
                ),  # Could be category
                "notes": [f"Note for well {i}" for i in range(200)],  # Variable strings
            }
        )

        optimizer = PerformanceOptimizer()

        # Get initial memory usage
        initial_memory = inefficient_dataset.memory_usage(deep=True).sum() / 1024 / 1024

        def memory_analysis(df):
            """Analysis that should benefit from memory optimization."""
            # Analyze memory usage
            memory_info = DataTypeOptimizer.get_memory_usage(df)

            # Perform some calculations
            status_counts = df["status"].value_counts()
            int_stats = df["large_ints"].describe()

            return {
                "memory_info": memory_info,
                "status_distribution": status_counts.to_dict(),
                "int_statistics": int_stats.to_dict(),
                "optimized_dtypes": {col: str(df[col].dtype) for col in df.columns},
            }

        result, metrics = optimizer.optimize_for_large_dataset(
            inefficient_dataset, memory_analysis
        )

        # Verify memory optimization occurred
        optimized_memory = result["memory_info"]["total_mb"]
        assert optimized_memory < initial_memory  # Should use less memory

        # Check data type optimizations
        dtypes = result["optimized_dtypes"]
        assert dtypes["large_ints"] == "int8"  # Should be optimized
        assert dtypes["medium_ints"] in ["int16", "int32"]  # Should be optimized
        assert dtypes["status"] == "category"  # Should be categorical
        assert dtypes["api12"] == "category"  # Should be categorical

        # Verify good memory efficiency score
        assert metrics.memory_efficiency_score > 60  # Should have good efficiency

        # Verify performance
        assert metrics.execution_time_seconds < 20  # Should be reasonably fast
        assert metrics.rows_processed == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
