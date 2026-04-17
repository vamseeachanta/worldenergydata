"""
Execution Time Benchmarks

This module establishes execution time benchmarks for all critical operations
and provides regression detection capabilities.
"""

import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List

import numpy as np
import pandas as pd
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class BenchmarkRecorder:
    """Record and compare benchmark results over time."""

    def __init__(self, results_dir: Path = None):
        self.results_dir = results_dir or Path("tests/performance/benchmark_results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.current_results = {}

    def record(self, operation: str, execution_time: float, metadata: Dict = None):
        """Record a benchmark result."""
        self.current_results[operation] = {
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

    def save_results(self, name: str = None):
        """Save benchmark results to file."""
        if not name:
            name = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        file_path = self.results_dir / f"{name}.json"
        with open(file_path, "w") as f:
            json.dump(self.current_results, f, indent=2)

        return file_path

    def load_baseline(self, baseline_name: str = "baseline"):
        """Load baseline benchmark results."""
        file_path = self.results_dir / f"{baseline_name}.json"
        if file_path.exists():
            with open(file_path, "r") as f:
                return json.load(f)
        return {}

    def compare_with_baseline(self, tolerance: float = 0.2):
        """Compare current results with baseline (20% tolerance by default)."""
        baseline = self.load_baseline()
        regressions = []

        for operation, current in self.current_results.items():
            if operation in baseline:
                baseline_time = baseline[operation]["execution_time"]
                current_time = current["execution_time"]

                if current_time > baseline_time * (1 + tolerance):
                    regressions.append(
                        {
                            "operation": operation,
                            "baseline": baseline_time,
                            "current": current_time,
                            "increase": (current_time - baseline_time)
                            / baseline_time
                            * 100,
                        }
                    )

        return regressions


class TestExecutionBenchmarks:
    """Test execution time benchmarks for all operations."""

    @pytest.fixture
    def recorder(self):
        """Create a benchmark recorder."""
        return BenchmarkRecorder()

    def test_data_import_benchmarks(self, recorder, tmp_path, sample_production_data):
        """Benchmark data import operations."""
        # Prepare test files
        csv_file = tmp_path / "test.csv"
        excel_file = tmp_path / "test.xlsx"
        parquet_file = tmp_path / "test.parquet"

        sample_production_data.to_csv(csv_file, index=False)
        sample_production_data.to_excel(excel_file, index=False)
        sample_production_data.to_parquet(parquet_file, index=False)

        # Benchmark CSV import
        start = time.perf_counter()
        df_csv = pd.read_csv(csv_file)
        csv_time = time.perf_counter() - start
        recorder.record("import_csv", csv_time, {"rows": len(df_csv)})
        assert csv_time < 0.5  # Should import in < 500ms

        # Benchmark Excel import
        start = time.perf_counter()
        df_excel = pd.read_excel(excel_file)
        excel_time = time.perf_counter() - start
        recorder.record("import_excel", excel_time, {"rows": len(df_excel)})
        assert excel_time < 2.0  # Excel is slower, allow 2 seconds

        # Benchmark Parquet import
        start = time.perf_counter()
        df_parquet = pd.read_parquet(parquet_file)
        parquet_time = time.perf_counter() - start
        recorder.record("import_parquet", parquet_time, {"rows": len(df_parquet)})
        assert parquet_time < 0.3  # Parquet should be fastest

    def test_data_transformation_benchmarks(self, recorder, sample_production_data):
        """Benchmark data transformation operations."""

        # Benchmark filtering
        start = time.perf_counter()
        filtered = sample_production_data[
            sample_production_data["oil_production"] > 5000
        ]
        filter_time = time.perf_counter() - start
        recorder.record("filter_data", filter_time, {"rows": len(filtered)})
        assert filter_time < 0.01  # Should be very fast

        # Benchmark grouping
        start = time.perf_counter()
        grouped = sample_production_data.groupby("well_id").agg(
            {
                "oil_production": ["mean", "sum", "std"],
                "gas_production": ["mean", "sum", "std"],
            }
        )
        group_time = time.perf_counter() - start
        recorder.record("group_aggregate", group_time, {"groups": len(grouped)})
        assert group_time < 0.1  # Should complete in < 100ms

        # Benchmark pivoting
        start = time.perf_counter()
        pivoted = sample_production_data.pivot_table(
            index="date", columns="well_id", values="oil_production", aggfunc="mean"
        )
        pivot_time = time.perf_counter() - start
        recorder.record("pivot_table", pivot_time, {"shape": pivoted.shape})
        assert pivot_time < 0.5  # Should complete in < 500ms

        # Benchmark merging
        df2 = sample_production_data.copy()
        df2["new_col"] = df2["oil_production"] * 2

        start = time.perf_counter()
        merged = pd.merge(
            sample_production_data,
            df2[["date", "well_id", "new_col"]],
            on=["date", "well_id"],
        )
        merge_time = time.perf_counter() - start
        recorder.record("merge_data", merge_time, {"rows": len(merged)})
        assert merge_time < 0.1  # Should complete in < 100ms

    def test_calculation_benchmarks(self, recorder, sample_production_data):
        """Benchmark calculation operations."""

        # Benchmark rolling calculations
        start = time.perf_counter()
        sample_production_data["ma_7"] = sample_production_data.groupby("well_id")[
            "oil_production"
        ].transform(lambda x: x.rolling(window=7, min_periods=1).mean())
        rolling_time = time.perf_counter() - start
        recorder.record("rolling_mean", rolling_time, {"window": 7})
        assert rolling_time < 0.5  # Should complete in < 500ms

        # Benchmark cumulative calculations
        start = time.perf_counter()
        sample_production_data["cumulative"] = sample_production_data.groupby(
            "well_id"
        )["oil_production"].cumsum()
        cumsum_time = time.perf_counter() - start
        recorder.record("cumulative_sum", cumsum_time)
        assert cumsum_time < 0.1  # Should be fast

        # Benchmark statistical calculations
        start = time.perf_counter()
        stats = {
            "mean": sample_production_data["oil_production"].mean(),
            "std": sample_production_data["oil_production"].std(),
            "median": sample_production_data["oil_production"].median(),
            "quantiles": sample_production_data["oil_production"].quantile(
                [0.25, 0.5, 0.75]
            ),
        }
        stats_time = time.perf_counter() - start
        recorder.record("statistical_calculations", stats_time)
        assert stats_time < 0.05  # Should be very fast

    def test_export_benchmarks(self, recorder, tmp_path, sample_production_data):
        """Benchmark data export operations."""

        # Benchmark CSV export
        csv_file = tmp_path / "export.csv"
        start = time.perf_counter()
        sample_production_data.to_csv(csv_file, index=False)
        csv_time = time.perf_counter() - start
        recorder.record("export_csv", csv_time, {"rows": len(sample_production_data)})
        assert csv_time < 0.5  # Should export in < 500ms

        # Benchmark Excel export
        excel_file = tmp_path / "export.xlsx"
        start = time.perf_counter()
        sample_production_data.to_excel(excel_file, index=False)
        excel_time = time.perf_counter() - start
        recorder.record(
            "export_excel", excel_time, {"rows": len(sample_production_data)}
        )
        assert excel_time < 2.0  # Excel is slower

        # Benchmark Parquet export
        parquet_file = tmp_path / "export.parquet"
        start = time.perf_counter()
        sample_production_data.to_parquet(parquet_file, index=False)
        parquet_time = time.perf_counter() - start
        recorder.record(
            "export_parquet", parquet_time, {"rows": len(sample_production_data)}
        )
        assert parquet_time < 0.3  # Parquet should be fast

        # Benchmark JSON export
        json_file = tmp_path / "export.json"
        start = time.perf_counter()
        sample_production_data.to_json(json_file, orient="records")
        json_time = time.perf_counter() - start
        recorder.record("export_json", json_time, {"rows": len(sample_production_data)})
        assert json_time < 1.0  # JSON can be slower

    def test_string_operations_benchmarks(self, recorder):
        """Benchmark string operation performance."""
        # Create string data
        size = 10000
        df = pd.DataFrame(
            {
                "text": ["Sample text " + str(i) for i in range(size)],
                "codes": ["CODE-" + str(i).zfill(5) for i in range(size)],
            }
        )

        # Benchmark string contains
        start = time.perf_counter()
        contains = df[df["text"].str.contains("Sample")]
        contains_time = time.perf_counter() - start
        recorder.record("string_contains", contains_time, {"rows": len(contains)})
        assert contains_time < 0.1  # Should be fast

        # Benchmark string replace
        start = time.perf_counter()
        df["text_replaced"] = df["text"].str.replace("Sample", "Example")
        replace_time = time.perf_counter() - start
        recorder.record("string_replace", replace_time, {"rows": size})
        assert replace_time < 0.2  # Should complete quickly

        # Benchmark string split
        start = time.perf_counter()
        df["text_split"] = df["text"].str.split(" ")
        split_time = time.perf_counter() - start
        recorder.record("string_split", split_time, {"rows": size})
        assert split_time < 0.2  # Should complete quickly

    def test_datetime_operations_benchmarks(self, recorder):
        """Benchmark datetime operation performance."""
        # Create datetime data
        dates = pd.date_range(start="2020-01-01", end="2024-12-31", freq="H")
        df = pd.DataFrame({"timestamp": dates, "value": np.random.randn(len(dates))})

        # Benchmark datetime extraction
        start = time.perf_counter()
        df["year"] = df["timestamp"].dt.year
        df["month"] = df["timestamp"].dt.month
        df["day"] = df["timestamp"].dt.day
        df["hour"] = df["timestamp"].dt.hour
        extract_time = time.perf_counter() - start
        recorder.record("datetime_extraction", extract_time, {"rows": len(df)})
        assert extract_time < 0.5  # Should complete in < 500ms

        # Benchmark resampling
        start = time.perf_counter()
        resampled = df.set_index("timestamp").resample("D").agg({"value": "mean"})
        resample_time = time.perf_counter() - start
        recorder.record("datetime_resample", resample_time, {"periods": len(resampled)})
        assert resample_time < 1.0  # Should complete in < 1 second

        # Benchmark time zone conversion
        start = time.perf_counter()
        df["timestamp_utc"] = (
            df["timestamp"].dt.tz_localize("US/Central").dt.tz_convert("UTC")
        )
        tz_time = time.perf_counter() - start
        recorder.record("timezone_conversion", tz_time, {"rows": len(df)})
        assert tz_time < 0.5  # Should complete quickly


class TestRegressionDetection:
    """Test performance regression detection."""

    def test_establish_baseline(self, tmp_path):
        """Establish performance baseline."""
        recorder = BenchmarkRecorder(results_dir=tmp_path / "benchmarks")

        # Simulate baseline measurements
        baseline_operations = {
            "data_load": 0.5,
            "data_process": 1.0,
            "data_export": 0.8,
            "calculation": 0.3,
        }

        for op, time in baseline_operations.items():
            recorder.record(op, time)

        # Save as baseline
        baseline_path = recorder.save_results("baseline")
        assert baseline_path.exists()

        # Load and verify baseline
        baseline = recorder.load_baseline()
        assert len(baseline) == 4
        assert baseline["data_load"]["execution_time"] == 0.5

    def test_detect_regression(self, tmp_path):
        """Test regression detection."""
        recorder = BenchmarkRecorder(results_dir=tmp_path / "benchmarks")

        # Create baseline
        baseline_ops = {"fast_op": 0.1, "medium_op": 0.5, "slow_op": 2.0}

        for op, time in baseline_ops.items():
            recorder.record(op, time)
        recorder.save_results("baseline")

        # Create new measurements with some regressions
        recorder.current_results = {}
        recorder.record("fast_op", 0.11)  # 10% slower - OK
        recorder.record("medium_op", 0.65)  # 30% slower - REGRESSION
        recorder.record("slow_op", 2.5)  # 25% slower - REGRESSION

        # Detect regressions (20% tolerance)
        regressions = recorder.compare_with_baseline(tolerance=0.2)

        assert len(regressions) == 2
        assert any(r["operation"] == "medium_op" for r in regressions)
        assert any(r["operation"] == "slow_op" for r in regressions)

    def test_performance_trends(self, tmp_path):
        """Test performance trend analysis."""
        recorder = BenchmarkRecorder(results_dir=tmp_path / "benchmarks")

        # Simulate multiple benchmark runs over time
        for day in range(5):
            recorder.current_results = {}
            # Gradually degrading performance
            recorder.record("operation_a", 0.5 + day * 0.05)
            recorder.record("operation_b", 1.0 + day * 0.1)
            recorder.save_results(f"day_{day}")

        # Analyze trends
        all_results = []
        for day in range(5):
            file_path = recorder.results_dir / f"day_{day}.json"
            with open(file_path, "r") as f:
                results = json.load(f)
                all_results.append(results)

        # Check trend for operation_a
        times_a = [r["operation_a"]["execution_time"] for r in all_results]
        assert times_a == [0.5, 0.55, 0.6, 0.65, 0.7]

        # Calculate trend
        trend = statistics.linear_regression(range(5), times_a)
        assert trend.slope > 0  # Performance is degrading
