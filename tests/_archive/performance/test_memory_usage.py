"""
Memory Usage Performance Tests

This module tests memory consumption patterns and identifies memory leaks
in worldenergydata operations.
"""

import gc
import os
import sys
import tempfile
import tracemalloc
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import psutil
import pytest
from memory_profiler import profile

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class MemoryMonitor:
    """Context manager for monitoring memory usage."""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.process = psutil.Process(os.getpid())
        self.start_memory = 0
        self.peak_memory = 0

    def __enter__(self):
        gc.collect()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        tracemalloc.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        self.peak_memory = peak / 1024 / 1024  # MB
        end_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        print(f"\nMemory Report for {self.operation_name}:")
        print(f"  Start Memory: {self.start_memory:.2f} MB")
        print(f"  End Memory: {end_memory:.2f} MB")
        print(f"  Peak Memory: {self.peak_memory:.2f} MB")
        print(f"  Memory Increase: {end_memory - self.start_memory:.2f} MB")

        gc.collect()


class TestMemoryUsagePatterns:
    """Test memory usage patterns for different operations."""

    def test_dataframe_operations_memory(self, sample_production_data):
        """Test memory usage of DataFrame operations."""
        with MemoryMonitor("DataFrame Operations") as monitor:
            # Create copies
            df1 = sample_production_data.copy()
            df2 = sample_production_data.copy()
            df3 = sample_production_data.copy()

            # Merge operations
            merged = pd.merge(df1, df2, on="well_id", suffixes=("_1", "_2"))

            # Concatenation
            concatenated = pd.concat([df1, df2, df3], ignore_index=True)

            # Pivot operations
            pivoted = df1.pivot_table(
                index="date", columns="well_id", values="oil_production", aggfunc="mean"
            )

        # Memory should not exceed reasonable limits
        assert monitor.peak_memory < 500  # Less than 500MB for sample data

    def test_array_operations_memory(self):
        """Test memory usage of NumPy array operations."""
        size = 1_000_000

        with MemoryMonitor("NumPy Array Operations") as monitor:
            # Create large arrays
            arr1 = np.random.randn(size)
            arr2 = np.random.randn(size)

            # Mathematical operations
            result = np.sqrt(arr1**2 + arr2**2)

            # Statistical operations
            mean = np.mean(result)
            std = np.std(result)
            percentiles = np.percentile(result, [25, 50, 75])

            # Matrix operations
            matrix = arr1.reshape(1000, 1000)
            transposed = matrix.T
            dot_product = np.dot(matrix[:100], transposed[:, :100])

        # Memory usage should be predictable
        expected_memory = (size * 8 * 4) / 1024 / 1024  # 4 arrays * 8 bytes
        assert monitor.peak_memory < expected_memory * 2  # Allow 2x overhead

    def test_file_io_memory(self, tmp_path, large_dataset):
        """Test memory usage during file I/O operations."""
        csv_path = tmp_path / "large_data.csv"
        parquet_path = tmp_path / "large_data.parquet"

        # Write operations
        with MemoryMonitor("CSV Write") as monitor:
            large_dataset.to_csv(csv_path, index=False)
        assert monitor.peak_memory < 2000  # Less than 2GB for 1M rows

        with MemoryMonitor("Parquet Write") as monitor:
            large_dataset.to_parquet(parquet_path, index=False)
        assert monitor.peak_memory < 1500  # Parquet should be more efficient

        # Read operations
        with MemoryMonitor("CSV Read") as monitor:
            df_csv = pd.read_csv(csv_path)
        assert monitor.peak_memory < 2000

        with MemoryMonitor("Parquet Read") as monitor:
            df_parquet = pd.read_parquet(parquet_path)
        assert monitor.peak_memory < 1500

    def test_iterative_processing_memory(self, sample_production_data):
        """Test memory usage in iterative processing scenarios."""

        def process_chunk(chunk):
            """Process a single chunk of data."""
            chunk["processed"] = chunk["oil_production"] * 1.1
            chunk["category"] = pd.cut(
                chunk["oil_production"],
                bins=[0, 3000, 7000, 10000],
                labels=["Low", "Medium", "High"],
            )
            return chunk

        with MemoryMonitor("Iterative Processing") as monitor:
            # Process in chunks
            chunk_size = 100
            results = []

            for i in range(0, len(sample_production_data), chunk_size):
                chunk = sample_production_data.iloc[i : i + chunk_size].copy()
                processed = process_chunk(chunk)
                results.append(processed)

            final_result = pd.concat(results, ignore_index=True)

        # Memory should stay constant during iteration
        assert monitor.peak_memory < 100  # Should use minimal memory

    def test_memory_leak_detection(self, sample_production_data):
        """Test for memory leaks in repeated operations."""
        initial_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        # Perform operations repeatedly
        for i in range(100):
            df = sample_production_data.copy()
            df["new_col"] = df["oil_production"] * i
            grouped = df.groupby("well_id").agg({"oil_production": "mean"})
            del df, grouped

            if i % 10 == 0:
                gc.collect()

        gc.collect()
        final_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        # Memory increase should be minimal (allowing for some overhead)
        memory_increase = final_memory - initial_memory
        assert memory_increase < 50  # Less than 50MB increase after 100 iterations


class TestMemoryOptimization:
    """Test memory optimization techniques."""

    def test_dtype_optimization(self, sample_production_data):
        """Test memory savings from dtype optimization."""
        original_memory = (
            sample_production_data.memory_usage(deep=True).sum() / 1024 / 1024
        )

        # Optimize dtypes
        optimized = sample_production_data.copy()

        # Convert float64 to float32
        float_cols = optimized.select_dtypes(include=["float64"]).columns
        optimized[float_cols] = optimized[float_cols].astype("float32")

        # Convert object to category for repeated strings
        for col in ["well_id", "field_name"]:
            if col in optimized.columns:
                optimized[col] = optimized[col].astype("category")

        optimized_memory = optimized.memory_usage(deep=True).sum() / 1024 / 1024

        # Should achieve significant memory reduction
        reduction_percentage = (1 - optimized_memory / original_memory) * 100
        assert reduction_percentage > 20  # At least 20% reduction

    def test_chunked_processing(self, tmp_path):
        """Test memory-efficient chunked processing."""
        # Create a large CSV file
        csv_path = tmp_path / "large_file.csv"

        # Generate and write large dataset in chunks
        chunk_size = 10000
        num_chunks = 10

        for i in range(num_chunks):
            chunk_data = pd.DataFrame(
                {
                    "id": range(i * chunk_size, (i + 1) * chunk_size),
                    "value": np.random.randn(chunk_size),
                }
            )

            if i == 0:
                chunk_data.to_csv(csv_path, index=False)
            else:
                chunk_data.to_csv(csv_path, index=False, mode="a", header=False)

        # Process file in chunks
        with MemoryMonitor("Chunked Processing") as monitor:
            chunk_results = []

            for chunk in pd.read_csv(csv_path, chunksize=5000):
                # Process each chunk
                result = chunk["value"].mean()
                chunk_results.append(result)

            final_result = np.mean(chunk_results)

        # Memory usage should stay low despite large file
        assert monitor.peak_memory < 50  # Less than 50MB despite 100k rows

    def test_sparse_data_memory(self):
        """Test memory optimization for sparse data."""
        # Create sparse data
        size = 100000
        data = {"dense_col": np.random.randn(size), "sparse_col": np.zeros(size)}

        # Add sparse values (only 1% non-zero)
        sparse_indices = np.random.choice(size, size=int(size * 0.01), replace=False)
        data["sparse_col"][sparse_indices] = np.random.randn(len(sparse_indices))

        df_dense = pd.DataFrame(data)

        # Convert to sparse
        df_sparse = df_dense.copy()
        df_sparse["sparse_col"] = pd.arrays.SparseArray(df_sparse["sparse_col"])

        # Compare memory usage
        dense_memory = df_dense.memory_usage(deep=True).sum() / 1024 / 1024
        sparse_memory = df_sparse.memory_usage(deep=True).sum() / 1024 / 1024

        # Sparse should use significantly less memory
        assert sparse_memory < dense_memory * 0.7  # At least 30% reduction


class TestMemoryProfiling:
    """Profile memory usage for specific functions."""

    @profile
    def memory_intensive_operation(self, size: int = 100000):
        """Profile a memory-intensive operation."""
        # Create large datasets
        df1 = pd.DataFrame(
            {
                "id": range(size),
                "value1": np.random.randn(size),
                "value2": np.random.randn(size),
            }
        )

        df2 = pd.DataFrame(
            {
                "id": range(size),
                "value3": np.random.randn(size),
                "value4": np.random.randn(size),
            }
        )

        # Merge operations
        merged = pd.merge(df1, df2, on="id")

        # Aggregations
        grouped = merged.groupby(merged.index // 1000).agg(
            {"value1": "mean", "value2": "std", "value3": "sum", "value4": "count"}
        )

        return grouped

    def test_profiled_operation(self):
        """Test the profiled operation."""
        # This will print detailed memory usage line by line
        result = self.memory_intensive_operation(50000)
        assert result is not None
        assert len(result) > 0
