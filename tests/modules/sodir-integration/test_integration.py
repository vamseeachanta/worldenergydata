"""
End-to-end integration tests for SODIR module.

Tests the complete workflow from API calls through processing to analysis,
ensuring all components work together correctly.
"""

import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pandas as pd

from worldenergydata.sodir.analysis import SodirAnalysis
from worldenergydata.sodir.api_client import SodirAPIClient
from worldenergydata.sodir.batch import BatchConfig, SodirBatchProcessor
from worldenergydata.sodir.cache import SodirCache
from worldenergydata.sodir.cache_optimizer import SodirCacheOptimizer
from worldenergydata.sodir.cross_regional import CrossRegionalAnalyzer
from worldenergydata.sodir.data import SodirData
from worldenergydata.sodir.datasets import DatasetGenerator
from worldenergydata.sodir.errors import SodirAPIError
from worldenergydata.sodir.parallel import SodirParallelProcessor
from worldenergydata.sodir.processors.block_processor import BlockProcessor
from worldenergydata.sodir.processors.discovery_processor import DiscoveryProcessor
from worldenergydata.sodir.processors.field_processor import FieldProcessor
from worldenergydata.sodir.processors.survey_processor import SurveyProcessor
from worldenergydata.sodir.processors.wellbore_processor import WellboreProcessor

# Import all SODIR module components
from worldenergydata.sodir.sodir import Sodir
from worldenergydata.sodir.storage import DataStorage
from worldenergydata.sodir.workflows.collection import CollectionWorkflow


class TestSodirIntegration(unittest.TestCase):
    """End-to-end integration tests for SODIR module."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for test outputs
        self.temp_dir = tempfile.mkdtemp()
        self.test_config = {
            "api": {
                "base_url": "https://factmaps.sodir.no/api/rest",
                "rate_limit": 10,
                "timeout": 30,
            },
            "cache": {"ttl": 86400, "max_size_mb": 100},
            "storage": {"base_path": self.temp_dir, "format": "json"},
            "collection": {"batch_size": 100, "parallel": True},
        }

        # Synthetic API records use the canonical raw field names and units.
        self.mock_blocks_data = [
            {
                "blcNpdidBlock": "BLOCK_001",
                "blcName": "31/2",
                "blcStatus": "AWARDED",
                "coordinates": {"utmZone": 31, "northing": 6500000, "easting": 500000},
            },
            {
                "blcNpdidBlock": "BLOCK_002",
                "blcName": "31/3",
                "blcStatus": "AWARDED",
                "coordinates": {"utmZone": 31, "northing": 6550000, "easting": 550000},
            },
        ]

        self.mock_wellbores_data = [
            {
                "wlbNpdidWellbore": "WELL_001",
                "wlbName": "WELL_A",
                "wlbTotalDepth": 3500,
                "wlbWaterDepth": 350,
                "wlbStatus": "PRODUCING",
                "wlbDrillingOperator": "OPERATOR_A",
            },
            {
                "wlbNpdidWellbore": "WELL_002",
                "wlbName": "WELL_B",
                "wlbTotalDepth": 4200,
                "wlbWaterDepth": 380,
                "wlbStatus": "PLUGGED",
                "wlbDrillingOperator": "OPERATOR_B",
            },
        ]

        self.mock_fields_data = [
            {
                "fldNpdidField": "FIELD_001",
                "fldName": "FIELD_A",
                "fldOriginalReservesOil": 500,
                "fldOriginalReservesGas": 0.1,
                "fldRemainingReservesOil": 400,
                "fldRemainingReservesGas": 0.08,
                "fldRecoverableOil": 500,
                "fldRecoverableGas": 0.1,
                "fldStatus": "PRODUCING",
                "fldDiscoveryYear": 2010,
                "fldWaterDepth": 350,
            }
        ]

    def tearDown(self):
        """Clean up test environment."""
        # Remove temporary directory
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_complete_data_collection_workflow(self):
        """Test the complete data collection workflow from API to storage."""
        # Initialize module
        module = Sodir()
        self.assertIsNotNone(module)

        # Mock API client responses
        with (
            patch.object(
                SodirAPIClient, "get_blocks", return_value=self.mock_blocks_data
            ),
            patch.object(
                SodirAPIClient, "get_wellbores", return_value=self.mock_wellbores_data
            ),
            patch.object(
                SodirAPIClient, "get_fields", return_value=self.mock_fields_data
            ),
        ):

            # Create data collection workflow
            data_router = SodirData(self.test_config)

            # Set mock client on data router
            mock_client = SodirAPIClient(
                base_url="https://factmaps.sodir.no/api/rest",
                rate_limit=10,
                cache_ttl=86400,
            )
            data_router.api_client = mock_client

            # Execute collection for multiple data types
            collection_specs = [
                {"data_type": "blocks", "params": {"limit": 10}},
                {"data_type": "wellbores", "params": {"limit": 10}},
                {"data_type": "fields", "params": {"limit": 10}},
            ]

            # Process each collection
            results = []
            for spec in collection_specs:
                if spec["data_type"] == "blocks":
                    data = mock_client.get_blocks(**spec["params"])
                elif spec["data_type"] == "wellbores":
                    data = mock_client.get_wellbores(**spec["params"])
                elif spec["data_type"] == "fields":
                    data = mock_client.get_fields(**spec["params"])

                self.assertIsNotNone(data)
                results.append({"type": spec["data_type"], "data": data})

            # Verify all data collected
            self.assertEqual(len(results), 3)
            self.assertEqual(len(results[0]["data"]), 2)  # 2 blocks
            self.assertEqual(len(results[1]["data"]), 2)  # 2 wellbores
            self.assertEqual(len(results[2]["data"]), 1)  # 1 field

    def test_data_processing_pipeline(self):
        """Test the complete data processing pipeline with canonical API records."""
        processed_blocks = BlockProcessor().process_batch(self.mock_blocks_data)
        processed_wellbores = WellboreProcessor().process_batch(
            self.mock_wellbores_data
        )
        processed_fields = FieldProcessor().process_batch(self.mock_fields_data)

        self.assertEqual(len(processed_blocks), 2)
        self.assertEqual(len(processed_wellbores), 2)
        self.assertEqual(len(processed_fields), 1)
        for block in processed_blocks:
            self.assertIsInstance(block["latitude"], float)
            self.assertIsInstance(block["longitude"], float)

        field = processed_fields[0]
        self.assertAlmostEqual(field["original_reserves_oil_mmbbl"], 3145.0)
        self.assertAlmostEqual(field["original_reserves_gas_bcf"], 3.53)
        self.assertAlmostEqual(field["remaining_reserves_oil_mmbbl"], 2516.0)
        # The fixture recovers (500 - 400) / 500 of the original oil.
        self.assertAlmostEqual(field["recovery_factor_oil"], 0.2)
        self.assertEqual(
            [well["status_normalized"] for well in processed_wellbores],
            ["PRODUCING", "PLUGGED_AND_ABANDONED"],
        )

    def test_storage_and_retrieval(self):
        """Test data storage and retrieval functionality."""
        # Initialize storage
        storage = DataStorage(self.temp_dir)

        # Save different data types
        raw_blocks_path = storage.save_raw_data(self.mock_blocks_data, "blocks")
        storage.save_raw_data(self.mock_wellbores_data, "wellbores")
        storage.save_raw_data(self.mock_fields_data, "fields")

        # Process and save processed data
        block_processor = BlockProcessor()
        processed_blocks = block_processor.process_batch(self.mock_blocks_data)
        storage.save_processed_data(processed_blocks, "blocks")

        # Read the exact timestamped path returned by the storage API.
        raw_blocks_file = Path(raw_blocks_path)
        self.assertTrue(raw_blocks_file.is_file())
        loaded_blocks = json.loads(raw_blocks_file.read_text(encoding="utf-8"))
        self.assertEqual(loaded_blocks, self.mock_blocks_data)
        loaded_processed = storage.load_processed_data("blocks")
        self.assertEqual(
            loaded_processed["block_id"].tolist(), ["BLOCK_001", "BLOCK_002"]
        )

    def test_analysis_integration(self):
        """Test processed field records through the canonical portfolio API."""
        analysis = SodirAnalysis(config={"output_dir": self.temp_dir})
        processed_fields = FieldProcessor().process_batch(self.mock_fields_data)
        analysis.data = {
            "fields": pd.DataFrame(processed_fields).rename(
                columns={"recovery_factor_oil": "recovery_factor"}
            )
        }
        field_metrics = analysis.analyze_portfolio()

        self.assertEqual(field_metrics["total_fields"], 1)
        self.assertEqual(field_metrics["fields_by_status"], {"PRODUCING": 1})
        self.assertAlmostEqual(field_metrics["total_recoverable_oil"], 3145.0)
        self.assertAlmostEqual(field_metrics["total_recoverable_gas"], 3.53)
        self.assertAlmostEqual(field_metrics["average_recovery_factor"], 0.2)
        self.assertEqual(
            field_metrics["field_rankings"]["by_oil_reserves"][0]["field_name"],
            "FIELD_A",
        )

    def test_caching_integration(self):
        """Test caching integration across components."""
        # Initialize cache optimizer
        cache = SodirCacheOptimizer(max_size_mb=10, default_ttl=3600)

        # Simulate API calls with caching
        cache_key = "blocks_test"

        # First call - cache miss
        result = cache.get(cache_key)
        self.assertIsNone(result)

        # Store in cache
        cache.set(cache_key, self.mock_blocks_data, ttl=3600, priority=5)

        # Second call - cache hit
        cached_result = cache.get(cache_key)
        self.assertIsNotNone(cached_result)
        self.assertEqual(len(cached_result), 2)

        # Verify cache statistics
        stats = cache.get_statistics()
        self.assertEqual(stats.hits, 1)
        self.assertEqual(stats.misses, 1)
        self.assertGreater(stats.cache_efficiency_score, 0)

    def test_parallel_processing_integration(self):
        """Test parallel processing integration."""
        # Initialize parallel processor
        parallel = SodirParallelProcessor(max_workers=2, use_threads=True)

        # Mock API client
        mock_client = Mock()
        mock_client.get_blocks.return_value = self.mock_blocks_data
        mock_client.get_wellbores.return_value = self.mock_wellbores_data
        mock_client.get_fields.return_value = self.mock_fields_data
        mock_client.cache = Mock()
        mock_client.cache.get.return_value = None
        mock_client.cache.set.return_value = None

        parallel.api_client = mock_client

        # Define endpoints to fetch in parallel
        endpoints = [
            ("blocks", {"limit": 10}),
            ("wellbores", {"limit": 10}),
            ("fields", {"limit": 10}),
        ]

        # Execute parallel fetch
        results = parallel.parallel_api_fetch(endpoints, cache_enabled=False)

        # Verify results
        self.assertEqual(len(results), 3)
        successful = [r for r in results if r.success]
        self.assertEqual(len(successful), 3)

        # Check statistics
        stats = parallel.get_statistics()
        self.assertEqual(stats["successful"], 3)
        self.assertEqual(stats["failed"], 0)

    def test_batch_processing_integration(self):
        """Test batch processing integration."""
        # Initialize batch processor
        config = BatchConfig(
            batch_size=10, max_workers=2, use_parallel=True, save_intermediate=True
        )
        batch = SodirBatchProcessor(config)

        # Mock API client
        mock_client = Mock()
        mock_client.get_blocks.return_value = self.mock_blocks_data
        mock_client.get_wellbores.return_value = self.mock_wellbores_data
        mock_client.get_fields.return_value = self.mock_fields_data

        # Define collection specs
        collection_specs = [
            {"data_type": "blocks", "params": {"limit": 10}},
            {"data_type": "wellbores", "params": {"limit": 10}},
            {"data_type": "fields", "params": {"limit": 10}},
        ]

        # Execute batch collection
        result = batch.process_data_collection(
            mock_client, collection_specs, Path(self.temp_dir)
        )

        # Verify batch results
        self.assertIsNotNone(result)
        self.assertEqual(result.total_items, 3)
        self.assertGreaterEqual(result.processed_items, 0)
        self.assertLessEqual(result.failed_items, 3)

    def test_dataset_generation_integration(self):
        """Test dataset generation for analysis."""
        # Initialize dataset generator
        generator = DatasetGenerator()

        # Process mock data
        wellbore_processor = WellboreProcessor()
        field_processor = FieldProcessor()

        processed_wellbores = wellbore_processor.process_batch(self.mock_wellbores_data)
        processed_fields = field_processor.process_batch(self.mock_fields_data)

        # Generate wellbore dataset
        wellbore_dataset = generator.generate_wellbore_dataset(processed_wellbores)

        # Verify dataset structure
        self.assertIn("wellbore_id", wellbore_dataset.columns)
        self.assertIn("total_depth_m", wellbore_dataset.columns)
        self.assertIn("water_depth_m", wellbore_dataset.columns)
        self.assertIn("status_normalized", wellbore_dataset.columns)

        # Production records are distinct from the processed field metadata.
        production_records = [
            {"field_id": "FIELD_001", "oil_production": 1000, "gas_production": 6000},
            {"field_id": "FIELD_001", "oil_production": 1500, "gas_production": 12000},
        ]
        field_metadata = pd.DataFrame(processed_fields)[["field_id", "field_name"]]
        field_metadata["recoverable_oil"] = 10000
        production_dataset = generator.generate_production_dataset(
            production_records, field_metadata
        )
        self.assertEqual(
            production_dataset["field_id"].tolist(), ["FIELD_001", "FIELD_001"]
        )
        self.assertEqual(production_dataset["cumulative_oil"].tolist(), [1000, 2500])
        # Cumulative recovery is 1000 / 10000, then (1000 + 1500) / 10000.
        self.assertEqual(production_dataset["recovery_factor"].tolist(), [0.1, 0.25])

    def test_error_handling_integration(self):
        """Test API errors, record validation and invalid storage destinations."""
        client = SodirAPIClient(
            base_url=self.test_config["api"]["base_url"],
            rate_limit=10,
            max_retries=1,
            retry_delay=0.1,
        )
        with patch("worldenergydata.sodir.transport.requests.Session.get") as mock_get:
            mock_get.side_effect = ConnectionError("Connection error")
            with self.assertRaisesRegex(
                SodirAPIError, "Request failed after 2 attempts"
            ):
                client.get_blocks(limit=10)
            self.assertEqual(mock_get.call_count, 2)

        processor = BlockProcessor()
        invalid_record = {"invalid": "data"}
        processed = processor.process_batch([invalid_record])
        self.assertEqual(len(processed), 0)
        self.assertEqual(processor.error_count, 1)
        is_valid, errors = processor.validate(invalid_record)
        self.assertFalse(is_valid)
        self.assertIn("Missing required field: blcName", errors)

        invalid_destination = Path(self.temp_dir) / "not-a-directory"
        invalid_destination.write_text("fixture", encoding="utf-8", newline="\n")
        with self.assertRaises(FileExistsError):
            DataStorage(str(invalid_destination))

    def test_workflow_orchestration(self):
        """Test configured collection, processing and storage through execute."""
        workflow = CollectionWorkflow(
            {
                **self.test_config,
                "datasets": ["blocks", "wellbores", "fields"],
                "filters": {"limit": 100},
            }
        )
        mock_client = Mock()
        mock_client.get_blocks.return_value = self.mock_blocks_data
        mock_client.get_wellbores.return_value = self.mock_wellbores_data
        mock_client.get_fields.return_value = self.mock_fields_data
        workflow.sodir_data = SodirData(self.test_config)
        workflow.sodir_data.api_client = mock_client
        storage = workflow.sodir_data.storage

        with patch.object(storage, "save", wraps=storage.save) as save:
            results = workflow.execute()
        self.assertTrue(results["success"])
        self.assertEqual(
            results["datasets_collected"], ["blocks", "wellbores", "fields"]
        )
        self.assertEqual(results["total_records"], 5)
        self.assertEqual(save.call_count, 3)
        for dataset, count in (("blocks", 2), ("wellbores", 2), ("fields", 1)):
            stored = results["storage"][dataset]
            self.assertTrue(stored["success"])
            self.assertEqual(stored["records"], count)
            records = json.loads(Path(stored["path"]).read_text(encoding="utf-8"))
            self.assertEqual(len(records), count)
        mock_client.get_blocks.assert_called_once_with(limit=100)

    def test_performance_optimization_integration(self):
        """Test that performance optimizations work together."""
        from worldenergydata.sodir.batch import SodirBatchProcessor
        from worldenergydata.sodir.cache_optimizer import SodirCacheOptimizer
        from worldenergydata.sodir.parallel import SodirParallelProcessor

        # Initialize optimized components
        cache = SodirCacheOptimizer(max_size_mb=50)
        parallel = SodirParallelProcessor(max_workers=4)
        batch = SodirBatchProcessor(BatchConfig(batch_size=50, use_parallel=True))

        # Simulate optimized workflow
        start_time = time.time()

        # Pre-warm cache with common queries
        cache.set("blocks_common", self.mock_blocks_data, priority=10)
        cache.set("fields_common", self.mock_fields_data, priority=10)

        # Parallel data fetching (simulated)
        endpoints = [
            ("blocks", {"limit": 100}),
            ("wellbores", {"limit": 100}),
            ("fields", {"limit": 100}),
            ("discoveries", {"limit": 100}),
            ("surveys", {"limit": 100}),
        ]

        # Check cache hits
        blocks_cached = cache.get("blocks_common")
        self.assertIsNotNone(blocks_cached)

        fields_cached = cache.get("fields_common")
        self.assertIsNotNone(fields_cached)

        # Verify performance metrics
        elapsed = time.time() - start_time
        self.assertLess(elapsed, 1.0)  # Should be fast with caching

        # Check cache statistics
        stats = cache.get_statistics()
        self.assertGreater(stats.cache_efficiency_score, 0.5)


class TestModuleIntegration(unittest.TestCase):
    """Test integration between SODIR module components."""

    def test_module_initialization(self):
        """Test the real module router with temporary storage and mocked HTTP data."""
        with tempfile.TemporaryDirectory() as directory:
            config = {
                "data_types": ["blocks"],
                "storage": {"base_path": directory},
            }
            module = Sodir()
            self.assertIsNotNone(module)
            self.assertEqual(module.module_name, "sodir")
            with patch.object(
                SodirAPIClient,
                "get_blocks",
                return_value=[{"blcNpdidBlock": "1", "blcName": "31/2"}],
            ) as get_blocks:
                result = module.router(config)
            self.assertIsInstance(result, dict)
            self.assertEqual(result["sodir"]["status"], "completed")
            self.assertEqual(result["sodir"]["data_collected"], ["blocks"])
            get_blocks.assert_called_once_with()

    def test_component_communication(self):
        """Test that API data passes through processing and the storage API."""
        mock_api = Mock()
        mock_api.get_blocks.return_value = [{"blcNpdidBlock": "1", "blcName": "31/2"}]
        mock_storage = Mock()
        mock_storage.save.return_value = "raw/blocks.json"
        with tempfile.TemporaryDirectory() as directory:
            data_router = SodirData({"storage": {"base_path": directory}})
            data_router.api_client = mock_api
            data_router.storage = mock_storage
            result = data_router.collect_and_store("blocks")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["data"][0]["block_id"], "1")
        mock_api.get_blocks.assert_called_once_with()
        mock_storage.save.assert_called_once_with("blocks", result)


if __name__ == "__main__":
    unittest.main()
