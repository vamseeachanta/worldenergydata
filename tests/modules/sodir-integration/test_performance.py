"""
Performance tests for SODIR integration with realistic data volumes.

Tests system performance under load with large datasets to ensure
the module can handle production-scale data efficiently.
"""

import json
import random
import string
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock, Mock, patch

import numpy as np

# import memory_profiler  # Not installed in current environment
import pandas as pd

from worldenergydata.sodir.analysis import SodirAnalysis

# Import SODIR components
from worldenergydata.sodir.api_client import SodirAPIClient
from worldenergydata.sodir.batch import BatchConfig, SodirBatchProcessor
from worldenergydata.sodir.cache import SodirCache
from worldenergydata.sodir.cache_optimizer import SodirCacheOptimizer
from worldenergydata.sodir.parallel import SodirParallelProcessor
from worldenergydata.sodir.processors.block_processor import BlockProcessor
from worldenergydata.sodir.processors.field_processor import FieldProcessor
from worldenergydata.sodir.processors.wellbore_processor import WellboreProcessor
from worldenergydata.sodir.storage import DataStorage


class TestPerformance(unittest.TestCase):
    """Performance tests with realistic data volumes."""

    @classmethod
    def setUpClass(cls):
        """Set up large test datasets once for all tests."""
        cls.temp_dir = tempfile.mkdtemp()

        # Generate realistic data volumes
        cls.large_blocks = cls._generate_blocks(1000)  # 1000 blocks
        cls.large_wellbores = cls._generate_wellbores(5000)  # 5000 wellbores
        cls.large_fields = cls._generate_fields(500)  # 500 fields
        cls.large_discoveries = cls._generate_discoveries(2000)  # 2000 discoveries
        cls.large_surveys = cls._generate_surveys(3000)  # 3000 surveys

        # Production time series data (5 years monthly)
        cls.production_data = cls._generate_production_data(60)

    @classmethod
    def tearDownClass(cls):
        """Clean up test data."""
        import shutil

        if Path(cls.temp_dir).exists():
            shutil.rmtree(cls.temp_dir)

    @staticmethod
    def _generate_blocks(count: int) -> List[Dict]:
        """Generate realistic block data."""
        blocks = []
        for i in range(count):
            blocks.append(
                {
                    "blockId": f"BLOCK_{i:05d}",
                    "blockName": f"Block {random.randint(1,50)}/{random.randint(1,12)}",
                    "quadrantId": random.randint(1, 50),
                    "status": random.choice(["ACTIVE", "RELINQUISHED", "AVAILABLE"]),
                    "coordinates": {
                        "utmZone": random.randint(31, 35),
                        "northing": 6000000 + random.randint(0, 2000000),
                        "easting": 300000 + random.randint(0, 400000),
                    },
                    "waterDepth": random.randint(50, 2500),
                    "areaKm2": random.uniform(50, 500),
                }
            )
        return blocks

    @staticmethod
    def _generate_wellbores(count: int) -> List[Dict]:
        """Generate realistic wellbore data."""
        wellbores = []
        operators = ["Equinor", "Aker BP", "ConocoPhillips", "Lundin", "Shell", "Total"]

        for i in range(count):
            wellbores.append(
                {
                    "wellboreId": f"WELL_{i:05d}",
                    "wellboreName": f"{random.randint(1,50)}/{random.randint(1,12)}-{random.randint(1,20)}",
                    "blockId": f"BLOCK_{random.randint(0, 999):05d}",
                    "totalDepthMd": random.randint(1500, 6000),
                    "waterDepth": random.randint(50, 2500),
                    "status": random.choice(
                        ["PRODUCING", "PLUGGED", "SUSPENDED", "DRILLING"]
                    ),
                    "drillingOperator": random.choice(operators),
                    "spudDate": f"{random.randint(1970, 2023)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                    "completionDate": f"{random.randint(1971, 2024)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                    "kellyBushingElevation": random.uniform(15, 35),
                    "purpose": random.choice(
                        ["EXPLORATION", "PRODUCTION", "INJECTION"]
                    ),
                }
            )
        return wellbores

    @staticmethod
    def _generate_fields(count: int) -> List[Dict]:
        """Generate realistic field data."""
        fields = []
        statuses = ["PRODUCING", "SHUT_IN", "ABANDONED", "PLANNED"]

        for i in range(count):
            original_oil = random.uniform(10, 1000) * 1000000  # Million Sm³
            original_gas = random.uniform(5, 500) * 1000000
            recovery_factor = random.uniform(0.3, 0.7)

            fields.append(
                {
                    "fieldId": f"FIELD_{i:04d}",
                    "fieldName": f"Field_{i}_{random.choice(string.ascii_uppercase)}",
                    "blockId": f"BLOCK_{random.randint(0, 999):05d}",
                    "originalOilInPlaceSm3": original_oil,
                    "originalGasInPlaceSm3": original_gas,
                    "remainingOilSm3": original_oil * (1 - recovery_factor),
                    "remainingGasSm3": original_gas * (1 - recovery_factor),
                    "status": random.choice(statuses),
                    "discoveryYear": random.randint(1960, 2023),
                    "productionStartYear": random.randint(1965, 2024),
                    "mainOperator": random.choice(
                        ["Equinor", "Aker BP", "ConocoPhillips"]
                    ),
                }
            )
        return fields

    @staticmethod
    def _generate_discoveries(count: int) -> List[Dict]:
        """Generate realistic discovery data."""
        discoveries = []

        for i in range(count):
            discoveries.append(
                {
                    "discoveryId": f"DISC_{i:05d}",
                    "discoveryName": f"Discovery_{i}",
                    "blockId": f"BLOCK_{random.randint(0, 999):05d}",
                    "wellboreId": f"WELL_{random.randint(0, 4999):05d}",
                    "discoveryYear": random.randint(1965, 2024),
                    "recoverableOilSm3": random.uniform(1, 100) * 1000000,
                    "recoverableGasSm3": random.uniform(0.5, 50) * 1000000,
                    "discoveryType": random.choice(
                        ["OIL", "GAS", "OIL_GAS", "GAS_CONDENSATE"]
                    ),
                    "evaluationStatus": random.choice(
                        ["PLANNING", "ONGOING", "DECIDED", "PRODUCTION"]
                    ),
                }
            )
        return discoveries

    @staticmethod
    def _generate_surveys(count: int) -> List[Dict]:
        """Generate realistic survey data."""
        surveys = []
        survey_types = ["2D", "3D", "4D", "SITE_SURVEY", "GEOTECHNICAL"]

        for i in range(count):
            surveys.append(
                {
                    "surveyId": f"SURV_{i:05d}",
                    "surveyName": f"Survey_{random.randint(1000, 9999)}",
                    "surveyType": random.choice(survey_types),
                    "acquisitionYear": random.randint(1980, 2024),
                    "areaKm2": random.uniform(10, 1000),
                    "blocksCovered": [
                        f"BLOCK_{random.randint(0, 999):05d}"
                        for _ in range(random.randint(1, 5))
                    ],
                    "operator": random.choice(["PGS", "CGG", "TGS", "WesternGeco"]),
                    "dataQuality": random.choice(["EXCELLENT", "GOOD", "FAIR", "POOR"]),
                }
            )
        return surveys

    @staticmethod
    def _generate_production_data(months: int) -> pd.DataFrame:
        """Generate realistic production time series data."""
        dates = pd.date_range(start="2019-01-01", periods=months, freq="M")
        num_fields = 50

        data = []
        for date in dates:
            for field_id in range(num_fields):
                data.append(
                    {
                        "date": date,
                        "field_id": f"FIELD_{field_id:04d}",
                        "oil_production_sm3": random.uniform(10000, 500000),
                        "gas_production_sm3": random.uniform(5000, 250000),
                        "water_production_sm3": random.uniform(1000, 100000),
                        "injection_gas_sm3": random.uniform(0, 50000),
                        "injection_water_sm3": random.uniform(0, 75000),
                    }
                )

        return pd.DataFrame(data)

    def test_large_scale_data_processing(self):
        """Test processing of large datasets."""
        # Initialize processors
        block_processor = BlockProcessor()
        wellbore_processor = WellboreProcessor()
        field_processor = FieldProcessor()

        # Measure processing time for blocks
        start_time = time.perf_counter()
        processed_blocks = block_processor.process_batch(self.large_blocks)
        block_time = time.perf_counter() - start_time

        # Verify processing
        self.assertEqual(len(processed_blocks), 1000)
        self.assertLess(block_time, 5.0)  # Should process 1000 blocks in < 5 seconds
        print(f"Processed 1000 blocks in {block_time:.3f} seconds")

        # Measure processing time for wellbores
        start_time = time.perf_counter()
        processed_wellbores = wellbore_processor.process_batch(self.large_wellbores)
        wellbore_time = time.perf_counter() - start_time

        self.assertEqual(len(processed_wellbores), 5000)
        self.assertLess(
            wellbore_time, 10.0
        )  # Should process 5000 wellbores in < 10 seconds
        print(f"Processed 5000 wellbores in {wellbore_time:.3f} seconds")

        # Measure processing time for fields
        start_time = time.perf_counter()
        processed_fields = field_processor.process_batch(self.large_fields)
        field_time = time.perf_counter() - start_time

        self.assertEqual(len(processed_fields), 500)
        self.assertLess(field_time, 3.0)  # Should process 500 fields in < 3 seconds
        print(f"Processed 500 fields in {field_time:.3f} seconds")

    def test_parallel_processing_performance(self):
        """Test performance improvements with parallel processing."""
        parallel = SodirParallelProcessor(max_workers=4, use_threads=True)

        # Create processing tasks
        data_batches = [
            ("blocks", self.large_blocks[:250]),
            ("blocks", self.large_blocks[250:500]),
            ("blocks", self.large_blocks[500:750]),
            ("blocks", self.large_blocks[750:]),
        ]

        # Sequential processing baseline
        start_time = time.perf_counter()
        processor = BlockProcessor()
        for _, batch in data_batches:
            processor.process_batch(batch)
        sequential_time = time.perf_counter() - start_time

        # Parallel processing
        processor_map = {"blocks": BlockProcessor().process_batch}

        start_time = time.perf_counter()
        results = parallel.parallel_process_data(data_batches, processor_map)
        parallel_time = time.perf_counter() - start_time

        # Calculate speedup
        speedup = sequential_time / parallel_time if parallel_time > 0 else 0

        print(
            f"Sequential: {sequential_time:.3f}s, Parallel: {parallel_time:.3f}s, Speedup: {speedup:.2f}x"
        )

        # Should achieve at least 2x speedup with 4 workers
        self.assertGreater(speedup, 1.5)
        self.assertEqual(len(results), 4)

    def test_cache_performance_under_load(self):
        """Test cache performance with high volume of requests."""
        cache = SodirCacheOptimizer(max_size_mb=50, default_ttl=3600)

        # Generate cache keys
        num_unique_keys = 500
        num_requests = 10000
        keys = [f"key_{i}" for i in range(num_unique_keys)]

        # Populate cache with initial data
        for key in keys[:200]:  # Pre-populate 200 items
            cache.set(key, {"data": f"value_{key}"}, priority=random.randint(1, 10))

        # Simulate high-volume requests
        hits = 0
        misses = 0

        start_time = time.perf_counter()

        for _ in range(num_requests):
            key = random.choice(keys)
            result = cache.get(key)

            if result:
                hits += 1
            else:
                misses += 1
                # Simulate fetching and caching
                cache.set(key, {"data": f"value_{key}"})

        elapsed = time.perf_counter() - start_time

        # Calculate metrics
        hit_rate = hits / num_requests
        requests_per_second = num_requests / elapsed

        print(
            f"Cache performance: {requests_per_second:.0f} req/s, Hit rate: {hit_rate:.2%}"
        )

        # Should handle at least 5000 requests per second
        self.assertGreater(requests_per_second, 5000)

        # Should maintain reasonable hit rate
        self.assertGreater(hit_rate, 0.3)

        # Check cache statistics
        stats = cache.get_statistics()
        self.assertGreater(stats.cache_efficiency_score, 0.4)

    def test_batch_processing_performance(self):
        """Test batch processing performance with large datasets."""
        config = BatchConfig(
            batch_size=100, max_workers=4, use_parallel=True, save_intermediate=True
        )
        batch_processor = SodirBatchProcessor(config)

        # Mock API client
        mock_client = Mock()
        mock_client.get_blocks.return_value = self.large_blocks[:100]
        mock_client.get_wellbores.return_value = self.large_wellbores[:100]
        mock_client.get_fields.return_value = self.large_fields[:100]

        # Define collection specs for batch processing
        collection_specs = [
            {"data_type": "blocks", "params": {"limit": 100}},
            {"data_type": "wellbores", "params": {"limit": 100}},
            {"data_type": "fields", "params": {"limit": 100}},
        ] * 10  # 30 total collections

        # Execute batch processing
        start_time = time.perf_counter()
        result = batch_processor.process_data_collection(
            mock_client, collection_specs, Path(self.temp_dir)
        )
        batch_time = time.perf_counter() - start_time

        print(
            f"Batch processed {len(collection_specs)} collections in {batch_time:.3f} seconds"
        )

        # Should complete within reasonable time
        self.assertLess(batch_time, 10.0)
        self.assertEqual(result.total_items, 30)
        self.assertGreaterEqual(result.processed_items, 0)

    def test_storage_performance(self):
        """Test storage performance with large datasets."""
        storage = DataStorage(self.temp_dir)

        # Test write performance
        start_time = time.perf_counter()

        # Save large datasets
        storage.save_raw_data(self.large_blocks, "blocks")
        storage.save_raw_data(self.large_wellbores, "wellbores")
        storage.save_raw_data(self.large_fields, "fields")

        write_time = time.perf_counter() - start_time

        print(f"Wrote 6500 records in {write_time:.3f} seconds")

        # Should write quickly
        self.assertLess(write_time, 5.0)

        # Test read performance
        start_time = time.perf_counter()

        # Read back data
        blocks_file = (
            Path(self.temp_dir)
            / "raw"
            / f'blocks_{datetime.now().strftime("%Y%m%d")}.json'
        )
        if blocks_file.exists():
            loaded_blocks = json.loads(blocks_file.read_text())
            self.assertEqual(len(loaded_blocks), 1000)

        read_time = time.perf_counter() - start_time

        print(f"Read 1000 records in {read_time:.3f} seconds")

        # Should read quickly
        self.assertLess(read_time, 1.0)

    def test_analysis_performance(self):
        """Test analysis performance with large datasets."""
        analysis = SodirAnalysis(config={"output_dir": self.temp_dir})

        # Process fields first
        field_processor = FieldProcessor()
        processed_fields = field_processor.process_batch(self.large_fields)

        # Test field analysis performance
        start_time = time.perf_counter()
        field_metrics = analysis.analyze_fields(processed_fields)
        analysis_time = time.perf_counter() - start_time

        print(f"Analyzed 500 fields in {analysis_time:.3f} seconds")

        # Should complete analysis quickly
        self.assertLess(analysis_time, 2.0)
        self.assertIn("total_fields", field_metrics)
        self.assertIn("total_original_oil_sm3", field_metrics)

        # Test portfolio analysis performance
        start_time = time.perf_counter()
        portfolio_metrics = analysis.analyze_portfolio(processed_fields)
        portfolio_time = time.perf_counter() - start_time

        print(f"Portfolio analysis in {portfolio_time:.3f} seconds")

        # Should complete portfolio analysis quickly
        self.assertLess(portfolio_time, 3.0)

    def test_concurrent_api_simulation(self):
        """Test system performance under concurrent API load."""
        # Simulate multiple concurrent users/processes
        num_concurrent = 10
        requests_per_user = 50

        def simulate_user_requests(user_id: int) -> Tuple[int, float]:
            """Simulate a user making multiple API requests."""
            cache = SodirCache(ttl_seconds=3600)
            processor = BlockProcessor()

            start_time = time.perf_counter()

            for i in range(requests_per_user):
                # Check cache
                cache_key = f"user_{user_id}_req_{i}"
                cached = cache.get(cache_key)

                if not cached:
                    # Process some data
                    sample_blocks = random.sample(self.large_blocks, 10)
                    processed = processor.process_batch(sample_blocks)

                    # Cache result
                    cache.set(cache_key, processed)

            elapsed = time.perf_counter() - start_time
            return user_id, elapsed

        # Execute concurrent user simulations
        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [
                executor.submit(simulate_user_requests, i)
                for i in range(num_concurrent)
            ]

            results = []
            for future in as_completed(futures):
                user_id, user_time = future.result()
                results.append((user_id, user_time))
                print(f"User {user_id} completed in {user_time:.3f} seconds")

        total_time = time.perf_counter() - start_time

        print(f"All {num_concurrent} users completed in {total_time:.3f} seconds")

        # System should handle concurrent load efficiently
        self.assertLess(total_time, 30.0)  # Should complete in < 30 seconds

        # Average time per user should be reasonable
        avg_user_time = sum(t for _, t in results) / len(results)
        self.assertLess(avg_user_time, 10.0)

    def test_memory_efficiency(self):
        """Test memory efficiency with large datasets."""
        import tracemalloc

        # Start memory tracking
        tracemalloc.start()

        # Get initial memory
        initial = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB

        # Process large datasets
        processor = BlockProcessor()
        processed = processor.process_batch(self.large_blocks)

        # Get memory after processing
        after_processing = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB

        # Clear processed data
        processed = None

        # Get memory after cleanup
        after_cleanup = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB

        tracemalloc.stop()

        # Calculate memory usage
        processing_memory = after_processing - initial
        leaked_memory = after_cleanup - initial

        print(
            f"Memory usage - Processing: {processing_memory:.2f} MB, Leaked: {leaked_memory:.2f} MB"
        )

        # Should use reasonable memory for processing
        self.assertLess(processing_memory, 100)  # Less than 100 MB for 1000 blocks

        # Should not leak significant memory
        self.assertLess(leaked_memory, 10)  # Less than 10 MB leaked

    def test_scalability_limits(self):
        """Test system scalability limits."""
        # Test with increasingly large datasets
        sizes = [100, 500, 1000, 5000, 10000]
        times = []

        processor = BlockProcessor()

        for size in sizes:
            # Generate data
            blocks = self._generate_blocks(size)

            # Measure processing time
            start_time = time.perf_counter()
            processed = processor.process_batch(blocks)
            elapsed = time.perf_counter() - start_time

            times.append(elapsed)
            print(f"Size {size}: {elapsed:.3f} seconds ({size/elapsed:.0f} items/sec)")

            # Verify processing completed
            self.assertEqual(len(processed), size)

        # Check that processing scales reasonably (not exponentially)
        # Time complexity should be roughly O(n)
        for i in range(1, len(sizes)):
            size_ratio = sizes[i] / sizes[i - 1]
            time_ratio = times[i] / times[i - 1]

            # Time should scale roughly linearly (allow 50% deviation)
            self.assertLess(time_ratio, size_ratio * 1.5)

    def test_production_data_processing(self):
        """Test processing of production time series data."""
        # Process production data
        start_time = time.perf_counter()

        # Group by field and calculate metrics
        field_production = self.production_data.groupby("field_id").agg(
            {
                "oil_production_sm3": "sum",
                "gas_production_sm3": "sum",
                "water_production_sm3": "sum",
            }
        )

        # Calculate monthly averages
        monthly_avg = self.production_data.groupby(
            self.production_data["date"].dt.to_period("M")
        ).agg({"oil_production_sm3": "mean", "gas_production_sm3": "mean"})

        processing_time = time.perf_counter() - start_time

        print(
            f"Processed {len(self.production_data)} production records in {processing_time:.3f} seconds"
        )

        # Should process time series data quickly
        self.assertLess(processing_time, 2.0)
        self.assertEqual(len(field_production), 50)  # 50 fields
        self.assertEqual(len(monthly_avg), 60)  # 60 months


class TestStressConditions(unittest.TestCase):
    """Test system behavior under stress conditions."""

    def test_api_timeout_handling(self):
        """Test handling of API timeouts under load."""
        client = SodirAPIClient(
            base_url="https://factmaps.sodir.no/api/rest",
            timeout=1,  # Very short timeout
            max_retries=2,
            retry_delay=0.1,
        )

        # Mock slow API response
        with patch("requests.Session.get") as mock_get:
            mock_get.side_effect = lambda *args, **kwargs: time.sleep(
                2
            )  # Simulate slow response

            start_time = time.perf_counter()
            result = client.get_blocks(limit=10)
            elapsed = time.perf_counter() - start_time

            # Should timeout and retry
            self.assertIsNone(result)
            self.assertLess(elapsed, 5.0)  # Should fail fast with retries

    def test_cache_eviction_under_pressure(self):
        """Test cache eviction when memory limit is reached."""
        # Small cache to force evictions
        cache = SodirCacheOptimizer(max_size_mb=1, default_ttl=3600)

        # Add items until cache is full
        evictions = 0
        for i in range(1000):
            key = f"key_{i}"
            # Large value to fill cache quickly
            value = {"data": "x" * 1000}

            cache.set(key, value, priority=random.randint(1, 5))

            # Check if early items were evicted
            if i > 100 and cache.get("key_0") is None:
                evictions += 1

        # Should have evicted items
        stats = cache.get_statistics()
        self.assertGreater(stats.evictions, 0)
        print(f"Cache evicted {stats.evictions} items under memory pressure")

    def test_error_recovery(self):
        """Test system recovery from errors."""
        processor = BlockProcessor()

        # Mix valid and invalid data
        mixed_data = [
            {"blockId": "VALID_001", "blockName": "Valid Block"},
            {"invalid": "data"},  # Invalid format
            {"blockId": "VALID_002", "blockName": "Another Valid"},
            None,  # Null entry
            {"blockId": "VALID_003", "blockName": "Third Valid"},
        ]

        # Should handle errors gracefully
        processed = processor.process_batch(mixed_data)

        # Should process valid items
        self.assertGreaterEqual(len(processed), 3)

        # Check that valid items were processed
        valid_ids = [item.get("block_id") for item in processed if item.get("block_id")]
        self.assertIn("VALID_001", valid_ids)
        self.assertIn("VALID_002", valid_ids)


if __name__ == "__main__":
    # Run with verbosity for performance metrics
    unittest.main(verbosity=2)
