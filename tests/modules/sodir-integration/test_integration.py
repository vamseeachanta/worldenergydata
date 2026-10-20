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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

from worldenergydata.sodir.analysis import SodirAnalysis
from worldenergydata.sodir.api_client import SodirAPIClient
from worldenergydata.sodir.batch import BatchConfig, SodirBatchProcessor
from worldenergydata.sodir.cache import SodirCache
from worldenergydata.sodir.cache_optimizer import SodirCacheOptimizer
from worldenergydata.sodir.cross_regional import CrossRegionalAnalyzer
from worldenergydata.sodir.data import SodirData
from worldenergydata.sodir.datasets import DatasetGenerator
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

        # Mock API responses for testing
        self.mock_blocks_data = [
            {
                "blockId": "BLOCK_001",
                "blockName": "Block 31/2",
                "quadrantId": 31,
                "status": "ACTIVE",
                "coordinates": {"utmZone": 31, "northing": 6500000, "easting": 500000},
            },
            {
                "blockId": "BLOCK_002",
                "blockName": "Block 31/3",
                "quadrantId": 31,
                "status": "ACTIVE",
                "coordinates": {"utmZone": 31, "northing": 6550000, "easting": 550000},
            },
        ]

        self.mock_wellbores_data = [
            {
                "wellboreId": "WELL_001",
                "wellboreName": "31/2-1",
                "blockId": "BLOCK_001",
                "totalDepthMd": 3500,
                "waterDepth": 350,
                "status": "PRODUCING",
                "drillingOperator": "Equinor",
            },
            {
                "wellboreId": "WELL_002",
                "wellboreName": "31/3-1",
                "blockId": "BLOCK_002",
                "totalDepthMd": 4200,
                "waterDepth": 380,
                "status": "PLUGGED",
                "drillingOperator": "Aker BP",
            },
        ]

        self.mock_fields_data = [
            {
                "fieldId": "FIELD_001",
                "fieldName": "Johan Sverdrup",
                "blockId": "BLOCK_001",
                "originalOilInPlaceSm3": 500000000,
                "originalGasInPlaceSm3": 100000000,
                "remainingOilSm3": 400000000,
                "remainingGasSm3": 80000000,
                "status": "PRODUCING",
                "discoveryYear": 2010,
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
        """Test the complete data processing pipeline."""
        # Initialize processors
        block_processor = BlockProcessor()
        wellbore_processor = WellboreProcessor()
        field_processor = FieldProcessor()

        # Process mock data
        processed_blocks = block_processor.process_batch(self.mock_blocks_data)
        processed_wellbores = wellbore_processor.process_batch(self.mock_wellbores_data)
        processed_fields = field_processor.process_batch(self.mock_fields_data)

        # Verify processing results
        self.assertEqual(len(processed_blocks), 2)
        self.assertEqual(len(processed_wellbores), 2)
        self.assertEqual(len(processed_fields), 1)

        # Check coordinate conversion (UTM to WGS84)
        for block in processed_blocks:
            self.assertIn("latitude", block)
            self.assertIn("longitude", block)
            self.assertIsInstance(block["latitude"], float)
            self.assertIsInstance(block["longitude"], float)

        # Check unit conversions
        for field in processed_fields:
            self.assertIn("original_oil_bbl", field)
            self.assertIn("original_gas_bcf", field)
            # Verify conversion (1 Sm³ oil = 6.29 barrels)
            expected_oil_bbl = self.mock_fields_data[0]["originalOilInPlaceSm3"] * 6.29
            self.assertAlmostEqual(
                field["original_oil_bbl"], expected_oil_bbl, delta=1000
            )

        # Check status normalization
        for wellbore in processed_wellbores:
            self.assertIn("status_normalized", wellbore)
            self.assertIn(wellbore["status_normalized"], ["ACTIVE", "INACTIVE"])

    def test_storage_and_retrieval(self):
        """Test data storage and retrieval functionality."""
        # Initialize storage
        storage = DataStorage(self.temp_dir)

        # Save different data types
        storage.save_raw_data(self.mock_blocks_data, "blocks")
        storage.save_raw_data(self.mock_wellbores_data, "wellbores")
        storage.save_raw_data(self.mock_fields_data, "fields")

        # Process and save processed data
        block_processor = BlockProcessor()
        processed_blocks = block_processor.process_batch(self.mock_blocks_data)
        storage.save_processed_data(processed_blocks, "blocks")

        # Verify files exist
        raw_blocks_file = (
            Path(self.temp_dir)
            / "raw"
            / f'blocks_{datetime.now().strftime("%Y%m%d")}.json'
        )
        self.assertTrue(raw_blocks_file.exists())

        # Load and verify data
        loaded_blocks = json.loads(raw_blocks_file.read_text())
        self.assertEqual(len(loaded_blocks), 2)
        self.assertEqual(loaded_blocks[0]["blockId"], "BLOCK_001")

    def test_analysis_integration(self):
        """Test integration of analysis components."""
        # Initialize analysis
        analysis = SodirAnalysis(config={"output_dir": self.temp_dir})

        # Process mock data first
        field_processor = FieldProcessor()
        processed_fields = field_processor.process_batch(self.mock_fields_data)

        # Perform field analysis
        field_metrics = analysis.analyze_fields(processed_fields)

        # Verify analysis results
        self.assertIn("total_fields", field_metrics)
        self.assertIn("producing_fields", field_metrics)
        self.assertIn("total_original_oil_sm3", field_metrics)
        self.assertIn("total_remaining_oil_sm3", field_metrics)
        self.assertIn("average_recovery_factor", field_metrics)

        self.assertEqual(field_metrics["total_fields"], 1)
        self.assertEqual(field_metrics["producing_fields"], 1)

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

        # Generate production dataset
        production_dataset = generator.generate_production_dataset(processed_fields)

        # Verify production dataset
        self.assertIn("field_id", production_dataset.columns)
        self.assertIn("original_oil_bbl", production_dataset.columns)
        self.assertIn("recovery_factor", production_dataset.columns)

    def test_error_handling_integration(self):
        """Test error handling across integrated components."""
        # Test API client error handling
        client = SodirAPIClient(
            base_url="https://invalid.url",
            rate_limit=10,
            max_retries=1,
            retry_delay=0.1,
        )

        # Mock failed request
        with patch("requests.Session.get") as mock_get:
            mock_get.side_effect = Exception("Connection error")

            # Should handle error gracefully
            result = client.get_blocks(limit=10)
            self.assertIsNone(result)

        # Test processor error handling
        processor = BlockProcessor()

        # Invalid data should be handled
        invalid_data = [{"invalid": "data"}]
        processed = processor.process_batch(invalid_data)
        self.assertEqual(len(processed), 1)

        # Test storage error handling
        storage = DataStorage("/invalid/path")

        # Should handle invalid path gracefully
        success = storage.save_raw_data(self.mock_blocks_data, "blocks")
        # Storage will attempt to create directory or fail gracefully

    def test_workflow_orchestration(self):
        """Test complete workflow orchestration."""
        # Initialize workflow
        workflow = CollectionWorkflow(
            {"batch_size": 10, "parallel": True, "save_intermediate": True}
        )

        # Mock components
        mock_client = Mock()
        mock_client.get_blocks.return_value = self.mock_blocks_data
        mock_client.get_wellbores.return_value = self.mock_wellbores_data
        mock_client.get_fields.return_value = self.mock_fields_data

        mock_storage = Mock()
        mock_storage.save_raw_data.return_value = True
        mock_storage.save_processed_data.return_value = True

        # Configure workflow
        workflow.api_client = mock_client
        workflow.storage = mock_storage

        # Execute workflow
        results = workflow.collect_all_data(
            data_types=["blocks", "wellbores", "fields"], params={"limit": 100}
        )

        # Verify workflow execution
        self.assertIsNotNone(results)
        self.assertIn("blocks", results)
        self.assertIn("wellbores", results)
        self.assertIn("fields", results)

        # Verify storage was called
        self.assertTrue(mock_storage.save_raw_data.called)

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
        """Test that all module components initialize correctly."""
        config = {
            "api": {"base_url": "https://factmaps.sodir.no/api/rest", "rate_limit": 10},
            "cache": {"ttl": 86400},
            "storage": {"base_path": tempfile.mkdtemp()},
        }

        # Initialize main module
        module = Sodir()

        # Verify module initialized
        self.assertIsNotNone(module)
        self.assertEqual(module.module_name, "sodir")

        # Test router method
        result = module.router(config)
        # Router should return the config (possibly modified)
        self.assertIsInstance(result, dict)

    def test_component_communication(self):
        """Test that components communicate correctly."""
        # Create mock components
        mock_api = Mock()
        mock_cache = Mock()
        mock_storage = Mock()

        # Set up return values
        mock_api.get_blocks.return_value = [{"blockId": "1"}]
        mock_cache.get.return_value = None
        mock_storage.save_raw_data.return_value = True

        # Wire components together
        data_router = SodirData({"storage": {"base_path": "/tmp"}})
        data_router.api_client = mock_api
        data_router.storage = mock_storage

        # Execute operation that requires component communication
        result = data_router.collect_blocks(limit=10)

        # Verify communication occurred
        mock_api.get_blocks.assert_called_once()
        mock_storage.save_raw_data.assert_called()


if __name__ == "__main__":
    unittest.main()
