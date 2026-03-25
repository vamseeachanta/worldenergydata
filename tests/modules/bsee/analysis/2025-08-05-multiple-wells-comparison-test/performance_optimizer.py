"""
Performance Optimization and Memory Management Module

This module provides memory usage optimization and performance benchmarking
capabilities for handling 120+ wells comparison analysis efficiently.
"""

import gc
import os
import sys
import threading
import time
import warnings
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

import numpy as np
import pandas as pd
import psutil


@dataclass
class MemoryProfile:
    """Memory usage profile for analysis operations."""

    peak_memory_mb: float = 0.0
    start_memory_mb: float = 0.0
    end_memory_mb: float = 0.0
    memory_delta_mb: float = 0.0
    max_memory_percent: float = 0.0
    gc_collections: Dict[str, int] = None

    def __post_init__(self):
        if self.gc_collections is None:
            self.gc_collections = {"gen0": 0, "gen1": 0, "gen2": 0}


@dataclass
class PerformanceMetrics:
    """Performance metrics for analysis operations."""

    execution_time_seconds: float = 0.0
    rows_processed: int = 0
    rows_per_second: float = 0.0
    memory_efficiency_score: float = 0.0
    processing_chunks: int = 0
    average_chunk_time: float = 0.0


@dataclass
class ResourceConstraints:
    """Resource constraints and limits for processing."""

    max_memory_mb: Optional[float] = None
    max_processing_time_seconds: Optional[float] = None
    max_chunk_size: int = 100
    min_chunk_size: int = 10
    memory_warning_threshold: float = 0.8  # 80% of available memory
    enable_gc_optimization: bool = True


class MemoryMonitor:
    """Real-time memory usage monitoring."""

    def __init__(self, sampling_interval: float = 0.1):
        self.sampling_interval = sampling_interval
        self._monitoring = False
        self._memory_samples = []
        self._monitor_thread = None
        self._start_time = None

    def start_monitoring(self):
        """Start memory monitoring in background thread."""
        if self._monitoring:
            return

        self._monitoring = True
        self._memory_samples = []
        self._start_time = time.time()
        self._monitor_thread = threading.Thread(target=self._monitor_memory)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()

    def stop_monitoring(self) -> List[Tuple[float, float]]:
        """Stop monitoring and return memory samples."""
        if not self._monitoring:
            return []

        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)

        return self._memory_samples.copy()

    def _monitor_memory(self):
        """Internal memory monitoring loop."""
        process = psutil.Process()

        while self._monitoring:
            try:
                memory_mb = process.memory_info().rss / 1024 / 1024
                elapsed_time = time.time() - self._start_time
                self._memory_samples.append((elapsed_time, memory_mb))
                time.sleep(self.sampling_interval)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break

    def get_peak_memory(self) -> float:
        """Get peak memory usage from samples."""
        if not self._memory_samples:
            return 0.0
        return max(sample[1] for sample in self._memory_samples)


class DataTypeOptimizer:
    """Optimize pandas DataFrame data types for memory efficiency."""

    @staticmethod
    def optimize_dataframe(df: pd.DataFrame, aggressive: bool = False) -> pd.DataFrame:
        """
        Optimize DataFrame data types for memory efficiency.

        Args:
            df: DataFrame to optimize
            aggressive: Enable aggressive optimization (may affect precision)

        Returns:
            Optimized DataFrame
        """
        df_optimized = df.copy()

        # Optimize numeric columns (handle all integer types)
        for col in df_optimized.select_dtypes(
            include=["int64", "int32", "int16"]
        ).columns:
            col_min = df_optimized[col].min()
            col_max = df_optimized[col].max()

            # Try different integer types (optimize to smallest possible)
            if col_min >= -128 and col_max <= 127:
                df_optimized[col] = df_optimized[col].astype("int8")
            elif col_min >= -32768 and col_max <= 32767:
                df_optimized[col] = df_optimized[col].astype("int16")
            elif col_min >= -2147483648 and col_max <= 2147483647:
                if (
                    df_optimized[col].dtype != "int32"
                ):  # Only convert if not already int32
                    df_optimized[col] = df_optimized[col].astype("int32")

        # Optimize float columns
        for col in df_optimized.select_dtypes(include=["float64"]).columns:
            if aggressive:
                # Check if we can use float32 without significant precision loss
                original_values = df_optimized[col].dropna()
                if len(original_values) > 0:
                    float32_values = original_values.astype("float32")
                    relative_error = np.abs(
                        (original_values - float32_values) / original_values
                    ).max()
                    if relative_error < 1e-6:  # Less than 0.0001% error
                        df_optimized[col] = df_optimized[col].astype("float32")

        # Optimize string columns to category if beneficial
        for col in df_optimized.select_dtypes(include=["object"]).columns:
            if df_optimized[col].dtype == "object":
                try:
                    unique_count = df_optimized[col].nunique()
                    total_count = len(df_optimized)

                    # Convert to category if less than 50% unique values
                    if unique_count / total_count < 0.5 and unique_count > 1:
                        df_optimized[col] = df_optimized[col].astype("category")
                except Exception:
                    continue  # Skip if conversion fails

        return df_optimized

    @staticmethod
    def get_memory_usage(df: pd.DataFrame) -> Dict[str, float]:
        """Get detailed memory usage information for DataFrame."""
        memory_info = {
            "total_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
            "index_mb": df.index.memory_usage(deep=True) / 1024 / 1024,
            "columns": {},
        }

        for col in df.columns:
            memory_info["columns"][col] = {
                "mb": df[col].memory_usage(deep=True) / 1024 / 1024,
                "dtype": str(df[col].dtype),
            }

        return memory_info


class BatchProcessor:
    """Generator-based batch processing for memory efficiency."""

    def __init__(
        self, chunk_size: int = 50, memory_monitor: Optional[MemoryMonitor] = None
    ):
        self.chunk_size = chunk_size
        self.memory_monitor = memory_monitor or MemoryMonitor()

    def process_dataframe_batches(
        self,
        df: pd.DataFrame,
        processor_func: Callable[[pd.DataFrame], Any],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Generator[Any, None, None]:
        """
        Process DataFrame in batches using generator for memory efficiency.

        Args:
            df: DataFrame to process
            processor_func: Function to apply to each batch
            progress_callback: Optional callback for progress reporting

        Yields:
            Results from processor function for each batch
        """
        total_rows = len(df)
        processed_rows = 0

        for start_idx in range(0, total_rows, self.chunk_size):
            end_idx = min(start_idx + self.chunk_size, total_rows)
            batch_df = df.iloc[start_idx:end_idx].copy()

            # Optimize batch data types
            batch_df = DataTypeOptimizer.optimize_dataframe(batch_df)

            try:
                result = processor_func(batch_df)
                yield result

                processed_rows += len(batch_df)

                if progress_callback:
                    progress_callback(processed_rows, total_rows)

            finally:
                # Clean up batch data
                del batch_df
                if processed_rows % (self.chunk_size * 5) == 0:  # Every 5 batches
                    gc.collect()

    def merge_dataframes_batched(
        self,
        left_df: pd.DataFrame,
        right_df: pd.DataFrame,
        on: str,
        how: str = "inner",
        memory_limit_mb: Optional[float] = None,
    ) -> pd.DataFrame:
        """
        Memory-efficient DataFrame merging for large datasets.

        Args:
            left_df: Left DataFrame
            right_df: Right DataFrame
            on: Column to merge on
            how: Type of merge
            memory_limit_mb: Memory limit for processing

        Returns:
            Merged DataFrame
        """
        # Estimate memory usage for full merge
        estimated_memory_mb = (
            (
                left_df.memory_usage(deep=True).sum()
                + right_df.memory_usage(deep=True).sum()
            )
            / 1024
            / 1024
        )

        if memory_limit_mb and estimated_memory_mb > memory_limit_mb:
            # Use batched merge
            return self._merge_in_batches(left_df, right_df, on, how)
        else:
            # Direct merge if within memory limits
            return pd.merge(left_df, right_df, on=on, how=how)

    def _merge_in_batches(
        self, left_df: pd.DataFrame, right_df: pd.DataFrame, on: str, how: str
    ) -> pd.DataFrame:
        """Internal batched merge implementation."""
        merged_chunks = []

        for batch in self.process_dataframe_batches(left_df, lambda x: x):
            merged_batch = pd.merge(batch, right_df, on=on, how=how)
            if not merged_batch.empty:
                merged_chunks.append(merged_batch)

        if merged_chunks:
            result = pd.concat(merged_chunks, ignore_index=True)
            # Clean up intermediate results
            del merged_chunks
            gc.collect()
            return result
        else:
            return pd.DataFrame()


def memory_profiler(func: Callable) -> Callable:
    """Decorator to profile memory usage of functions."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get initial memory state
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024
        gc_start = {f"gen{i}": gc.get_count()[i] for i in range(3)}

        # Start memory monitoring
        monitor = MemoryMonitor(sampling_interval=0.05)
        monitor.start_monitoring()

        start_time = time.time()
        try:
            result = func(*args, **kwargs)
        finally:
            end_time = time.time()
            memory_samples = monitor.stop_monitoring()

            # Get final memory state
            end_memory = process.memory_info().rss / 1024 / 1024
            gc_end = {f"gen{i}": gc.get_count()[i] for i in range(3)}

            # Calculate metrics
            peak_memory = monitor.get_peak_memory()
            memory_delta = end_memory - start_memory
            execution_time = end_time - start_time

            # Create memory profile
            profile = MemoryProfile(
                peak_memory_mb=peak_memory,
                start_memory_mb=start_memory,
                end_memory_mb=end_memory,
                memory_delta_mb=memory_delta,
                max_memory_percent=(
                    peak_memory / (psutil.virtual_memory().total / 1024 / 1024)
                )
                * 100,
                gc_collections={k: gc_end[k] - gc_start[k] for k in gc_start},
            )

            # Attach profile to result if possible
            if hasattr(result, "__dict__"):
                result.memory_profile = profile
            elif isinstance(result, dict):
                result["memory_profile"] = profile

        return result

    return wrapper


class PerformanceOptimizer:
    """Main performance optimization and memory management class."""

    def __init__(self, constraints: Optional[ResourceConstraints] = None):
        self.constraints = constraints or ResourceConstraints()
        self.batch_processor = BatchProcessor(
            chunk_size=self.constraints.max_chunk_size
        )
        self.data_optimizer = DataTypeOptimizer()
        self._performance_history = []

    def optimize_for_large_dataset(
        self,
        df: pd.DataFrame,
        processing_func: Callable[[pd.DataFrame], Any],
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[Any, PerformanceMetrics]:
        """
        Optimize processing for large datasets with memory management.

        Args:
            df: DataFrame to process
            processing_func: Function to apply to data
            progress_callback: Optional progress callback

        Returns:
            Tuple of (result, performance_metrics)
        """
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024

        if progress_callback:
            progress_callback("Optimizing data types...")

        # Optimize data types first
        optimized_df = self.data_optimizer.optimize_dataframe(df, aggressive=True)

        if progress_callback:
            progress_callback("Determining processing strategy...")

        # Determine processing strategy based on data size and constraints
        df_memory_mb = optimized_df.memory_usage(deep=True).sum() / 1024 / 1024
        available_memory_mb = psutil.virtual_memory().available / 1024 / 1024

        if (
            self.constraints.max_memory_mb
            and df_memory_mb > self.constraints.max_memory_mb
        ) or (
            df_memory_mb
            > available_memory_mb * self.constraints.memory_warning_threshold
        ):
            # Use batch processing
            if progress_callback:
                progress_callback("Using batch processing for memory efficiency...")
            result = self._process_in_batches(
                optimized_df, processing_func, progress_callback
            )
        else:
            # Direct processing
            if progress_callback:
                progress_callback("Processing data directly...")
            result = processing_func(optimized_df)

        # Calculate performance metrics
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024

        execution_time = end_time - start_time
        rows_processed = len(df)

        metrics = PerformanceMetrics(
            execution_time_seconds=execution_time,
            rows_processed=rows_processed,
            rows_per_second=(
                rows_processed / execution_time if execution_time > 0 else 0
            ),
            memory_efficiency_score=self._calculate_memory_efficiency(
                start_memory, end_memory, df_memory_mb
            ),
            processing_chunks=(
                1
                if df_memory_mb <= available_memory_mb * 0.8
                else max(1, len(df) // self.constraints.max_chunk_size)
            ),
            average_chunk_time=execution_time
            / max(1, len(df) // self.constraints.max_chunk_size),
        )

        self._performance_history.append(metrics)

        if progress_callback:
            progress_callback(
                f"Processing complete: {rows_processed} rows in {execution_time:.2f}s"
            )

        return result, metrics

    def _process_in_batches(
        self,
        df: pd.DataFrame,
        processing_func: Callable,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Any:
        """Process DataFrame in batches for memory efficiency."""
        batch_results = []
        total_batches = max(1, len(df) // self.batch_processor.chunk_size)

        def batch_progress(processed_rows: int, total_rows: int):
            if progress_callback:
                progress = (processed_rows / total_rows) * 100
                progress_callback(
                    f"Processing: {progress:.1f}% complete ({processed_rows}/{total_rows} rows)"
                )

        for batch_result in self.batch_processor.process_dataframe_batches(
            df, processing_func, batch_progress
        ):
            batch_results.append(batch_result)

            # Memory cleanup after each batch
            if self.constraints.enable_gc_optimization and len(batch_results) % 5 == 0:
                gc.collect()

        # Combine batch results if they are DataFrames
        if batch_results and isinstance(batch_results[0], pd.DataFrame):
            result = pd.concat(batch_results, ignore_index=True)
            del batch_results
            gc.collect()
            return result
        elif batch_results and isinstance(batch_results[0], list):
            # Flatten list of lists
            result = []
            for batch_list in batch_results:
                result.extend(batch_list)
            return result
        else:
            return batch_results

    def _calculate_memory_efficiency(
        self, start_memory: float, end_memory: float, data_memory: float
    ) -> float:
        """Calculate memory efficiency score (0-100)."""
        memory_delta = end_memory - start_memory
        if data_memory == 0:
            return 100.0

        # Lower memory increase relative to data size = higher efficiency
        efficiency_ratio = max(0, (data_memory - memory_delta) / data_memory)
        return min(100.0, efficiency_ratio * 100)

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of performance optimization history."""
        if not self._performance_history:
            return {"message": "No performance data available"}

        metrics = self._performance_history

        return {
            "total_operations": len(metrics),
            "average_execution_time": np.mean(
                [m.execution_time_seconds for m in metrics]
            ),
            "average_rows_per_second": np.mean([m.rows_per_second for m in metrics]),
            "average_memory_efficiency": np.mean(
                [m.memory_efficiency_score for m in metrics]
            ),
            "total_rows_processed": sum(m.rows_processed for m in metrics),
            "performance_trend": (
                "improving"
                if len(metrics) > 1
                and metrics[-1].memory_efficiency_score
                > metrics[0].memory_efficiency_score
                else "stable"
            ),
        }

    def check_system_resources(self) -> Dict[str, Any]:
        """Check current system resource availability."""
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)

        return {
            "memory": {
                "total_gb": memory.total / 1024 / 1024 / 1024,
                "available_gb": memory.available / 1024 / 1024 / 1024,
                "used_percent": memory.percent,
                "available_for_processing_gb": (
                    memory.available * self.constraints.memory_warning_threshold
                )
                / 1024
                / 1024
                / 1024,
            },
            "cpu": {"usage_percent": cpu_percent, "core_count": psutil.cpu_count()},
            "recommendations": self._get_resource_recommendations(memory, cpu_percent),
        }

    def _get_resource_recommendations(
        self, memory: Any, cpu_percent: float
    ) -> List[str]:
        """Get resource optimization recommendations."""
        recommendations = []

        if memory.percent > 80:
            recommendations.append(
                "High memory usage detected. Consider using batch processing."
            )

        if cpu_percent > 80:
            recommendations.append(
                "High CPU usage detected. Consider reducing chunk size or processing concurrency."
            )

        if memory.available < 2 * 1024 * 1024 * 1024:  # Less than 2GB available
            recommendations.append(
                "Low available memory. Enable aggressive optimization and reduce chunk sizes."
            )

        if not recommendations:
            recommendations.append("System resources are optimal for processing.")

        return recommendations


# Example usage and utility functions
def benchmark_comparison_performance(
    lease_df: pd.DataFrame,
    api12_df: pd.DataFrame,
    comparison_func: Callable,
    iterations: int = 3,
) -> Dict[str, Any]:
    """
    Benchmark comparison performance with multiple iterations.

    Args:
        lease_df: Lease method DataFrame
        api12_df: API12 method DataFrame
        comparison_func: Comparison function to benchmark
        iterations: Number of iterations to run

    Returns:
        Performance benchmark results
    """
    optimizer = PerformanceOptimizer()
    results = []

    for i in range(iterations):

        def combined_processing(df_tuple):
            return comparison_func(df_tuple[0], df_tuple[1])

        # Combine dataframes for processing
        combined_data = (lease_df.copy(), api12_df.copy())

        result, metrics = optimizer.optimize_for_large_dataset(
            pd.DataFrame({"iteration": [i]}),  # Dummy df for metrics
            lambda _: combined_processing(combined_data),
        )

        results.append(
            {
                "iteration": i + 1,
                "execution_time": metrics.execution_time_seconds,
                "memory_efficiency": metrics.memory_efficiency_score,
                "data_size_mb": (
                    lease_df.memory_usage(deep=True).sum()
                    + api12_df.memory_usage(deep=True).sum()
                )
                / 1024
                / 1024,
            }
        )

    # Calculate summary statistics
    execution_times = [r["execution_time"] for r in results]
    memory_scores = [r["memory_efficiency"] for r in results]

    return {
        "benchmark_results": results,
        "summary": {
            "average_execution_time": np.mean(execution_times),
            "min_execution_time": np.min(execution_times),
            "max_execution_time": np.max(execution_times),
            "std_execution_time": np.std(execution_times),
            "average_memory_efficiency": np.mean(memory_scores),
            "total_data_size_mb": results[0]["data_size_mb"] if results else 0,
        },
        "system_info": optimizer.check_system_resources(),
    }
