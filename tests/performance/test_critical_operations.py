"""
Performance Tests for Critical Operations

This module tests the performance of critical operations in worldenergydata
to establish baselines and detect performance regressions.
"""

import os
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

import numpy as np
import numpy_financial as npf
import pandas as pd
import pytest

pytest.importorskip("pytest_benchmark")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestCriticalOperationsPerformance:
    """Test performance of critical operations."""

    def test_data_loading_performance(
        self, benchmark, sample_production_data, tmp_path
    ):
        """Test data loading performance for different file formats."""
        csv_path = tmp_path / "test_data.csv"
        sample_production_data.to_csv(csv_path, index=False)

        def load_csv():
            return pd.read_csv(csv_path)

        result = benchmark(load_csv)
        assert len(result) == len(sample_production_data)

        # Performance threshold
        assert benchmark.stats["mean"] < 0.5  # Should load in < 500ms

    def test_data_processing_performance(self, benchmark, sample_production_data):
        """Test data processing operations performance."""

        def process_data():
            # Simulate typical data processing operations
            df = sample_production_data.copy()

            # Group by operations
            grouped = df.groupby(["well_id", "field_name"]).agg(
                {
                    "oil_production": ["mean", "sum", "std"],
                    "gas_production": ["mean", "sum", "std"],
                    "water_production": ["mean", "sum", "std"],
                }
            )

            # Rolling calculations
            df["oil_ma_7"] = df.groupby("well_id")["oil_production"].transform(
                lambda x: x.rolling(window=7, min_periods=1).mean()
            )
            df["oil_ma_30"] = df.groupby("well_id")["oil_production"].transform(
                lambda x: x.rolling(window=30, min_periods=1).mean()
            )

            # Cumulative calculations
            df["cumulative_oil"] = df.groupby("well_id")["oil_production"].cumsum()
            df["cumulative_gas"] = df.groupby("well_id")["gas_production"].cumsum()

            return df, grouped

        result = benchmark(process_data)
        assert result is not None

        # Performance threshold for processing ~1800 days of data
        assert benchmark.stats["mean"] < 1.0  # Should process in < 1 second

    def test_financial_calculation_performance(self, benchmark, sample_financial_data):
        """Test NPV and financial calculation performance."""

        def calculate_npv():
            df = sample_financial_data.copy()
            discount_rate = 0.10 / 12  # Monthly discount rate

            # Calculate cash flows
            df["cash_flow"] = df["revenue"] - df["opex"] - df["capex"]

            # Calculate discount factors
            df["discount_factor"] = (1 + discount_rate) ** -df["period"]

            # Calculate present values
            df["pv"] = df["cash_flow"] * df["discount_factor"]

            # Calculate NPV
            npv = df["pv"].sum()

            # Calculate IRR (simplified)
            cash_flows = df["cash_flow"].values
            irr = npf.irr(cash_flows) if len(cash_flows) > 0 else 0

            return {
                "npv": npv,
                "irr": irr,
                "total_revenue": df["revenue"].sum(),
                "total_opex": df["opex"].sum(),
                "total_capex": df["capex"].sum(),
            }

        result = benchmark(calculate_npv)
        assert "npv" in result

        # Performance threshold
        assert benchmark.stats["mean"] < 0.25  # Should calculate in < 250ms on CI

    def test_large_dataset_aggregation_performance(self, benchmark, large_dataset):
        """Test performance with large datasets (1M rows)."""

        def aggregate_large_dataset():
            df = large_dataset.copy()

            # Multiple aggregations
            result = df.groupby("category").agg(
                {
                    "value1": ["mean", "std", "min", "max"],
                    "value2": ["mean", "std", "min", "max"],
                    "value3": ["sum", "count"],
                }
            )

            # Time-based resampling
            df.set_index("timestamp", inplace=True)
            monthly = df.resample("ME").agg(
                {"value1": "mean", "value2": "sum", "value3": "std"}
            )

            return result, monthly

        # For large dataset, we allow more time
        result = benchmark(aggregate_large_dataset)
        assert result is not None

        # Performance threshold for 1M rows
        assert benchmark.stats["mean"] < 10.0  # Should process in < 10 seconds

    def test_directional_survey_calculation_performance(
        self, benchmark, sample_well_data
    ):
        """Test directional survey calculation performance."""

        def calculate_survey_positions():
            df = sample_well_data.copy()

            # Calculate dogleg severity
            df["delta_md"] = df["measured_depth"].diff()
            df["delta_inc"] = df["inclination"].diff()
            df["delta_azi"] = df["azimuth"].diff()

            # Simplified dogleg calculation
            df["dogleg"] = np.sqrt(
                df["delta_inc"] ** 2
                + (df["delta_azi"] * np.sin(np.radians(df["inclination"]))) ** 2
            )
            df["dogleg_severity"] = df["dogleg"] / df["delta_md"] * 100

            # Calculate 3D positions
            df["delta_n"] = df["northing"].diff()
            df["delta_e"] = df["easting"].diff()
            df["delta_v"] = df["tvd"].diff()

            df["horizontal_displacement"] = np.sqrt(
                df["northing"] ** 2 + df["easting"] ** 2
            )

            return df

        result = benchmark(calculate_survey_positions)
        assert "dogleg_severity" in result.columns

        # Performance threshold
        assert benchmark.stats["mean"] < 0.5  # Should calculate in < 500ms


class TestMemoryPerformance:
    """Test memory usage for critical operations."""

    def test_memory_usage_data_loading(self, sample_production_data, tmp_path):
        """Test memory usage during data loading."""
        csv_path = tmp_path / "test_data.csv"
        sample_production_data.to_csv(csv_path, index=False)

        tracemalloc.start()

        # Load data
        df = pd.read_csv(csv_path)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Convert to MB
        peak_mb = peak / 1024 / 1024

        # Memory threshold
        assert peak_mb < 100  # Should use less than 100MB for sample data

    def test_memory_usage_large_operations(self, large_dataset):
        """Test memory usage with large dataset operations."""
        tracemalloc.start()

        # Perform memory-intensive operations
        df_copy = large_dataset.copy()
        grouped = df_copy.groupby("category").agg(
            {
                "value1": ["mean", "std"],
                "value2": ["mean", "std"],
                "value3": ["sum", "count"],
            }
        )

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Convert to MB
        peak_mb = peak / 1024 / 1024

        # Memory threshold for 1M rows
        assert peak_mb < 1000  # Should use less than 1GB for 1M rows

    def test_memory_cleanup(self, sample_production_data):
        """Test that memory is properly released after operations."""
        import gc

        tracemalloc.start()

        # Create and destroy large objects
        for _ in range(10):
            df = sample_production_data.copy()
            df["new_col"] = df["oil_production"] * 2
            del df

        gc.collect()

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Current memory should be much less than peak after cleanup
        assert current < peak * 0.5  # Current should be less than 50% of peak


class TestParallelPerformance:
    """Test performance of parallel operations."""

    def test_parallel_data_processing(self, benchmark, sample_production_data):
        """Test parallel processing performance."""
        import concurrent.futures

        def process_well_data(well_id):
            """Process data for a single well."""
            well_data = sample_production_data[
                sample_production_data["well_id"] == well_id
            ].copy()

            # Perform calculations
            well_data["ma_7"] = (
                well_data["oil_production"].rolling(window=7, min_periods=1).mean()
            )
            well_data["cumulative"] = well_data["oil_production"].cumsum()

            return well_data

        def parallel_processing():
            well_ids = sample_production_data["well_id"].unique()

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                results = list(executor.map(process_well_data, well_ids))

            return pd.concat(results, ignore_index=True)

        result = benchmark(parallel_processing)
        assert len(result) == len(sample_production_data)

        # Parallel should be reasonably fast
        assert benchmark.stats["mean"] < 2.0  # Should complete in < 2 seconds
