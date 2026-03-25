"""
Performance profiling for SODIR API client.

This module profiles the SODIR API client to identify bottlenecks
and measure performance metrics for optimization.
"""

import concurrent.futures
import cProfile
import io
import json
import os
import pstats
import statistics
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sodir_module.api_client import SodirAPIClient
from sodir_module.cache import SodirCache
from sodir_module.processors.block_processor import BlockProcessor
from sodir_module.processors.field_processor import FieldProcessor
from sodir_module.processors.wellbore_processor import WellboreProcessor


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    operation: str
    avg_time: float
    min_time: float
    max_time: float
    std_dev: float
    total_calls: int
    cache_hits: int = 0
    cache_misses: int = 0
    memory_used_mb: float = 0.0
    error_count: int = 0


class SodirPerformanceProfiler:
    """
    Performance profiler for SODIR API client and data processing.

    Identifies bottlenecks and measures:
    - API response times
    - Cache effectiveness
    - Processing times
    - Memory usage
    - Concurrent request handling
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize profiler with API client."""
        # Initialize with SODIR API base URL
        base_url = "https://factmaps.sodir.no/api/rest"
        self.client = SodirAPIClient(
            base_url=base_url, rate_limit=10, cache_ttl=86400, max_retries=3
        )
        self.cache = SodirCache(ttl_seconds=86400)  # 24 hour TTL
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.config_path = config_path

        # Initialize processors for testing
        self.processors = {
            "blocks": BlockProcessor(),
            "wellbores": WellboreProcessor(),
            "fields": FieldProcessor(),
        }

    def profile_api_calls(self, iterations: int = 10) -> Dict[str, PerformanceMetrics]:
        """
        Profile API call performance.

        Args:
            iterations: Number of test iterations per endpoint

        Returns:
            Performance metrics for each endpoint
        """
        endpoints = [
            ("blocks", {"limit": 10}),
            ("wellbores", {"limit": 10}),
            ("fields", {"limit": 10}),
            ("discoveries", {"limit": 10}),
            ("surveys", {"limit": 10}),
        ]

        results = {}

        for endpoint, params in endpoints:
            print(f"Profiling {endpoint} endpoint...")
            times = []
            cache_hits = 0
            cache_misses = 0
            errors = 0

            # Clear cache for clean measurement
            self.cache.clear()

            for i in range(iterations):
                try:
                    # Measure with cache key
                    cache_key = f"{endpoint}_{json.dumps(params)}"

                    # Check cache first
                    cached = self.cache.get(cache_key)
                    if cached:
                        cache_hits += 1
                        continue

                    cache_misses += 1

                    # Measure API call time
                    start = time.perf_counter()

                    if endpoint == "blocks":
                        data = self.client.get_blocks(**params)
                    elif endpoint == "wellbores":
                        data = self.client.get_wellbores(**params)
                    elif endpoint == "fields":
                        data = self.client.get_fields(**params)
                    elif endpoint == "discoveries":
                        data = self.client.get_discoveries(**params)
                    else:  # surveys
                        data = self.client.get_surveys(**params)

                    elapsed = time.perf_counter() - start
                    times.append(elapsed)

                    # Cache the result
                    if data:
                        self.cache.set(cache_key, data)

                except Exception as e:
                    print(f"Error calling {endpoint}: {e}")
                    errors += 1
                    times.append(0)

            # Calculate metrics
            valid_times = [t for t in times if t > 0]
            if valid_times:
                results[endpoint] = PerformanceMetrics(
                    operation=f"API_{endpoint}",
                    avg_time=statistics.mean(valid_times),
                    min_time=min(valid_times),
                    max_time=max(valid_times),
                    std_dev=(
                        statistics.stdev(valid_times) if len(valid_times) > 1 else 0
                    ),
                    total_calls=iterations,
                    cache_hits=cache_hits,
                    cache_misses=cache_misses,
                    error_count=errors,
                )

        return results

    def profile_concurrent_requests(self, num_workers: int = 5) -> Dict[str, Any]:
        """
        Profile concurrent API request handling.

        Args:
            num_workers: Number of concurrent workers

        Returns:
            Metrics for concurrent processing
        """
        print(f"Profiling concurrent requests with {num_workers} workers...")

        # Test concurrent fetching of different data types
        endpoints = ["blocks", "wellbores", "fields", "discoveries", "surveys"]

        def fetch_data(endpoint: str) -> Tuple[str, float, bool]:
            """Fetch data from endpoint."""
            start = time.perf_counter()
            success = True

            try:
                if endpoint == "blocks":
                    data = self.client.get_blocks(limit=20)
                elif endpoint == "wellbores":
                    data = self.client.get_wellbores(limit=20)
                elif endpoint == "fields":
                    data = self.client.get_fields(limit=20)
                elif endpoint == "discoveries":
                    data = self.client.get_discoveries(limit=20)
                else:
                    data = self.client.get_surveys(limit=20)

                success = data is not None
            except Exception as e:
                print(f"Error in concurrent fetch {endpoint}: {e}")
                success = False

            elapsed = time.perf_counter() - start
            return endpoint, elapsed, success

        # Sequential baseline
        sequential_start = time.perf_counter()
        sequential_results = []
        for endpoint in endpoints:
            result = fetch_data(endpoint)
            sequential_results.append(result)
        sequential_time = time.perf_counter() - sequential_start

        # Clear cache for parallel test
        self.cache.clear()

        # Parallel execution
        parallel_start = time.perf_counter()
        parallel_results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(fetch_data, endpoint) for endpoint in endpoints]

            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                parallel_results.append(result)

        parallel_time = time.perf_counter() - parallel_start

        return {
            "sequential_time": sequential_time,
            "parallel_time": parallel_time,
            "speedup": sequential_time / parallel_time if parallel_time > 0 else 0,
            "efficiency": (
                (sequential_time / parallel_time) / num_workers
                if parallel_time > 0
                else 0
            ),
            "sequential_results": sequential_results,
            "parallel_results": parallel_results,
        }

    def profile_data_processing(
        self, sample_size: int = 100
    ) -> Dict[str, PerformanceMetrics]:
        """
        Profile data processing performance.

        Args:
            sample_size: Number of records to process

        Returns:
            Processing metrics for each data type
        """
        print(f"Profiling data processing with {sample_size} records...")

        results = {}

        # Test data processing for each type
        test_cases = [
            ("blocks", self._generate_block_data(sample_size)),
            ("wellbores", self._generate_wellbore_data(sample_size)),
            ("fields", self._generate_field_data(sample_size)),
        ]

        for data_type, test_data in test_cases:
            processor = self.processors[data_type]
            times = []

            # Process in batches
            batch_size = 10
            for i in range(0, len(test_data), batch_size):
                batch = test_data[i : i + batch_size]

                start = time.perf_counter()
                processed = processor.process_batch(batch)
                elapsed = time.perf_counter() - start

                times.append(elapsed)

            if times:
                results[f"process_{data_type}"] = PerformanceMetrics(
                    operation=f"Process_{data_type}",
                    avg_time=statistics.mean(times),
                    min_time=min(times),
                    max_time=max(times),
                    std_dev=statistics.stdev(times) if len(times) > 1 else 0,
                    total_calls=len(times),
                )

        return results

    def profile_cache_effectiveness(self) -> Dict[str, Any]:
        """
        Profile cache effectiveness and memory usage.

        Returns:
            Cache performance metrics
        """
        print("Profiling cache effectiveness...")

        # Start memory tracking
        tracemalloc.start()

        # Simulate realistic cache usage
        cache_test = SodirCache(ttl_seconds=3600)

        # Measure cache operations
        set_times = []
        get_times = []
        hits = 0
        misses = 0

        # Add items to cache
        for i in range(100):
            key = f"test_key_{i % 20}"  # Reuse some keys
            value = {"data": f"value_{i}" * 100}  # Some data

            # Set operation
            start = time.perf_counter()
            cache_test.set(key, value)
            set_times.append(time.perf_counter() - start)

            # Get operation
            start = time.perf_counter()
            result = cache_test.get(key)
            get_times.append(time.perf_counter() - start)

            if result:
                hits += 1
            else:
                misses += 1

        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        return {
            "set_avg_time": statistics.mean(set_times),
            "get_avg_time": statistics.mean(get_times),
            "hit_rate": hits / (hits + misses) if (hits + misses) > 0 else 0,
            "cache_size": len(cache_test.cache),
            "memory_used_mb": peak / 1024 / 1024,
            "items_cached": len(cache_test.cache),
        }

    def profile_memory_usage(self) -> Dict[str, Any]:
        """
        Profile memory usage during operations.

        Returns:
            Memory usage metrics
        """
        print("Profiling memory usage...")

        tracemalloc.start()
        memory_snapshots = []

        # Track memory during different operations
        operations = [
            ("initial", lambda: None),
            ("load_client", lambda: SodirAPIClient()),
            (
                "load_processors",
                lambda: {
                    "block": BlockProcessor(),
                    "wellbore": WellboreProcessor(),
                    "field": FieldProcessor(),
                },
            ),
            (
                "process_data",
                lambda: self.processors["blocks"].process_batch(
                    self._generate_block_data(100)
                ),
            ),
        ]

        results = {}
        for op_name, operation in operations:
            operation()
            current, peak = tracemalloc.get_traced_memory()
            results[op_name] = {
                "current_mb": current / 1024 / 1024,
                "peak_mb": peak / 1024 / 1024,
            }

        tracemalloc.stop()
        return results

    def generate_bottleneck_report(self) -> str:
        """
        Generate a comprehensive bottleneck analysis report.

        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 80)
        report.append("SODIR API CLIENT PERFORMANCE PROFILE REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")

        # Profile different aspects
        api_metrics = self.profile_api_calls(iterations=5)
        concurrent_metrics = self.profile_concurrent_requests(num_workers=5)
        processing_metrics = self.profile_data_processing(sample_size=50)
        cache_metrics = self.profile_cache_effectiveness()
        memory_metrics = self.profile_memory_usage()

        # API Performance Section
        report.append("\n1. API CALL PERFORMANCE")
        report.append("-" * 40)
        for endpoint, metrics in api_metrics.items():
            report.append(f"\n{endpoint.upper()}:")
            report.append(f"  Average Time: {metrics.avg_time:.3f}s")
            report.append(
                f"  Min/Max: {metrics.min_time:.3f}s / {metrics.max_time:.3f}s"
            )
            report.append(
                f"  Cache Hit Rate: {metrics.cache_hits}/{metrics.total_calls}"
            )
            if metrics.error_count > 0:
                report.append(f"  Errors: {metrics.error_count}")

        # Concurrent Processing Section
        report.append("\n2. CONCURRENT REQUEST HANDLING")
        report.append("-" * 40)
        report.append(f"Sequential Time: {concurrent_metrics['sequential_time']:.3f}s")
        report.append(f"Parallel Time: {concurrent_metrics['parallel_time']:.3f}s")
        report.append(f"Speedup: {concurrent_metrics['speedup']:.2f}x")
        report.append(f"Efficiency: {concurrent_metrics['efficiency']:.2%}")

        # Data Processing Section
        report.append("\n3. DATA PROCESSING PERFORMANCE")
        report.append("-" * 40)
        for processor, metrics in processing_metrics.items():
            report.append(f"\n{processor.upper()}:")
            report.append(f"  Average Time: {metrics.avg_time:.4f}s per batch")
            report.append(f"  Total Batches: {metrics.total_calls}")

        # Cache Performance Section
        report.append("\n4. CACHE EFFECTIVENESS")
        report.append("-" * 40)
        report.append(f"Set Operation Avg: {cache_metrics['set_avg_time']:.6f}s")
        report.append(f"Get Operation Avg: {cache_metrics['get_avg_time']:.6f}s")
        report.append(f"Hit Rate: {cache_metrics['hit_rate']:.2%}")
        report.append(f"Items Cached: {cache_metrics['items_cached']}")
        report.append(f"Memory Used: {cache_metrics['memory_used_mb']:.2f} MB")

        # Memory Usage Section
        report.append("\n5. MEMORY USAGE PROFILE")
        report.append("-" * 40)
        for operation, mem_data in memory_metrics.items():
            report.append(f"{operation}: {mem_data['peak_mb']:.2f} MB (peak)")

        # Bottleneck Analysis
        report.append("\n6. IDENTIFIED BOTTLENECKS")
        report.append("-" * 40)

        # Identify slowest API endpoint
        slowest_api = max(api_metrics.items(), key=lambda x: x[1].avg_time)
        report.append(
            f"• Slowest API Endpoint: {slowest_api[0]} ({slowest_api[1].avg_time:.3f}s avg)"
        )

        # Check if parallel processing helps
        if concurrent_metrics["speedup"] > 1.5:
            report.append(
                f"• Parallel Processing Beneficial: {concurrent_metrics['speedup']:.2f}x speedup achieved"
            )
        else:
            report.append(
                "• Limited Parallel Processing Benefit: Consider optimizing sequential flow"
            )

        # Cache effectiveness
        if cache_metrics["hit_rate"] < 0.5:
            report.append(
                f"• Low Cache Hit Rate: {cache_metrics['hit_rate']:.2%} - Consider cache optimization"
            )

        # Recommendations
        report.append("\n7. OPTIMIZATION RECOMMENDATIONS")
        report.append("-" * 40)

        if slowest_api[1].avg_time > 1.0:
            report.append("• Implement request batching for slow endpoints")

        if concurrent_metrics["speedup"] > 2.0:
            report.append("• Increase parallel processing usage for bulk operations")

        if cache_metrics["hit_rate"] < 0.7:
            report.append(
                "• Implement intelligent cache pre-loading for common queries"
            )
            report.append("• Consider longer TTL for stable data")

        report.append("\n" + "=" * 80)
        return "\n".join(report)

    def _generate_block_data(self, count: int) -> List[Dict]:
        """Generate sample block data for testing."""
        return [
            {
                "blockId": f"BLOCK_{i:04d}",
                "blockName": f"Block {i}",
                "quadrantId": i % 4 + 1,
                "coordinates": {
                    "utmZone": 32,
                    "northing": 6500000 + i * 1000,
                    "easting": 500000 + i * 500,
                },
            }
            for i in range(count)
        ]

    def _generate_wellbore_data(self, count: int) -> List[Dict]:
        """Generate sample wellbore data for testing."""
        return [
            {
                "wellboreId": f"WELL_{i:04d}",
                "wellboreName": f"Wellbore {i}",
                "totalDepthMd": 3000 + i * 100,
                "waterDepth": 200 + i * 10,
                "status": "ACTIVE" if i % 2 == 0 else "PLUGGED",
            }
            for i in range(count)
        ]

    def _generate_field_data(self, count: int) -> List[Dict]:
        """Generate sample field data for testing."""
        return [
            {
                "fieldId": f"FIELD_{i:04d}",
                "fieldName": f"Field {i}",
                "originalOilInPlaceSm3": 1000000 * (i + 1),
                "originalGasInPlaceSm3": 500000 * (i + 1),
                "remainingOilSm3": 500000 * (i + 1),
                "remainingGasSm3": 250000 * (i + 1),
            }
            for i in range(count)
        ]


def main():
    """Run performance profiling and generate report."""
    print("Starting SODIR API Performance Profiling...")
    print("-" * 40)

    profiler = SodirPerformanceProfiler()

    # Generate comprehensive report
    report = profiler.generate_bottleneck_report()

    # Save report to file
    report_path = Path("performance_report.txt")
    report_path.write_text(report)

    print(report)
    print(f"\nReport saved to: {report_path}")

    # Also generate a Python profile for detailed analysis
    print("\nGenerating detailed Python profile...")

    pr = cProfile.Profile()
    pr.enable()

    # Profile main operations
    profiler.profile_api_calls(iterations=3)
    profiler.profile_data_processing(sample_size=20)

    pr.disable()

    # Save detailed profile
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(20)  # Top 20 time-consuming functions

    profile_path = Path("performance_profile_detailed.txt")
    profile_path.write_text(s.getvalue())
    print(f"Detailed profile saved to: {profile_path}")

    print("\nPerformance profiling complete!")


if __name__ == "__main__":
    main()
