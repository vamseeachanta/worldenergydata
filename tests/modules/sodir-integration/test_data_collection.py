"""
Tests for SODIR data collection orchestration.

This module tests the SodirData router and collection workflows:
- Data collection orchestration
- Workflow configuration
- Validation integration
- Storage system
- Dataset generation
"""

import json
import os

# Import modules to be tested
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, call, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "sodir_module"))


class TestSodirDataRouter(unittest.TestCase):
    """Tests for SodirData router orchestrating data collection."""

    def setUp(self):
        """Set up test fixtures."""
        from worldenergydata.sodir.data import SodirData

        # Mock configuration
        self.config = {
            "api": {
                "base_url": "https://factmaps.sodir.no/api/rest",
                "timeout": 30,
                "rate_limit": 10,
            },
            "cache": {"ttl_hours": 24, "max_size": 1000},
            "storage": {
                "base_path": "tests/modules/sodir-integration/data",
                "format": "json",
                "compression": False,
            },
            "collection": {
                "datasets": ["blocks", "wellbores", "fields"],
                "batch_size": 100,
                "validate": True,
            },
        }

        self.sodir_data = SodirData(self.config)

        # Mock data samples
        self.sample_block = {
            "blcName": "35/11",
            "blcStatus": "AWARDED",
            "blcOperatorName": "EQUINOR ENERGY AS",
        }

        self.sample_wellbore = {
            "wlbName": "35/11-1",
            "wlbStatus": "P&A",
            "wlbTotalDepth": 3500.0,
        }

        self.sample_field = {
            "fldName": "JOHAN SVERDRUP",
            "fldStatus": "PRODUCING",
            "fldOriginalReservesOil": 2700.0,
        }

    def test_initialization(self):
        """Test SodirData initialization with configuration."""
        self.assertIsNotNone(self.sodir_data)
        self.assertEqual(self.sodir_data.config, self.config)
        self.assertIsNotNone(self.sodir_data.api_client)
        self.assertIsNotNone(self.sodir_data.processors)
        self.assertIsNotNone(self.sodir_data.storage)

    def test_collect_single_dataset(self):
        """Test collecting a single dataset type."""
        with patch.object(self.sodir_data.api_client, "get_blocks") as mock_get:
            mock_get.return_value = [self.sample_block]

            result = self.sodir_data.collect_dataset("blocks")

            self.assertIsNotNone(result)
            self.assertEqual(result["dataset"], "blocks")
            self.assertEqual(result["count"], 1)
            self.assertIn("data", result)
            self.assertIn("metadata", result)
            mock_get.assert_called_once()

    def test_collect_multiple_datasets(self):
        """Test collecting multiple datasets."""
        with patch.object(
            self.sodir_data.api_client, "get_blocks"
        ) as mock_blocks, patch.object(
            self.sodir_data.api_client, "get_wellbores"
        ) as mock_wellbores, patch.object(
            self.sodir_data.api_client, "get_fields"
        ) as mock_fields:

            mock_blocks.return_value = [self.sample_block]
            mock_wellbores.return_value = [self.sample_wellbore]
            mock_fields.return_value = [self.sample_field]

            datasets = ["blocks", "wellbores", "fields"]
            results = self.sodir_data.collect_multiple_datasets(datasets)

            self.assertEqual(len(results), 3)
            self.assertIn("blocks", results)
            self.assertIn("wellbores", results)
            self.assertIn("fields", results)

            for dataset in datasets:
                self.assertIn("count", results[dataset])
                self.assertIn("data", results[dataset])

    def test_data_processing_pipeline(self):
        """Test data flows through processing pipeline."""
        with patch.object(self.sodir_data.api_client, "get_fields") as mock_get:
            mock_get.return_value = [self.sample_field]

            result = self.sodir_data.collect_dataset("fields")

            # Check data was processed
            processed_data = result["data"][0]
            self.assertIn("field_name", processed_data)
            self.assertIn("status", processed_data)
            self.assertIn("original_reserves_oil_mmbbl", processed_data)
            self.assertIn("processed_timestamp", processed_data)

    def test_data_validation(self):
        """Test data validation during collection."""
        # Test with valid data
        with patch.object(self.sodir_data.api_client, "get_blocks") as mock_get:
            mock_get.return_value = [self.sample_block]

            result = self.sodir_data.collect_dataset("blocks", validate=True)

            self.assertIn("validation", result["metadata"])
            self.assertEqual(result["metadata"]["validation"]["valid_count"], 1)
            self.assertEqual(result["metadata"]["validation"]["invalid_count"], 0)

        # Test with invalid data
        invalid_block = {"blcName": ""}  # Missing required fields
        with patch.object(self.sodir_data.api_client, "get_blocks") as mock_get:
            mock_get.return_value = [invalid_block]

            result = self.sodir_data.collect_dataset("blocks", validate=True)

            self.assertEqual(result["metadata"]["validation"]["invalid_count"], 1)
            self.assertIn("errors", result["metadata"]["validation"])

    def test_storage_integration(self):
        """Test data storage functionality."""
        with patch.object(self.sodir_data.storage, "save") as mock_save:
            with patch.object(self.sodir_data.api_client, "get_wellbores") as mock_get:
                mock_get.return_value = [self.sample_wellbore]

                result = self.sodir_data.collect_and_store("wellbores")

                mock_save.assert_called_once()
                call_args = mock_save.call_args[0]
                self.assertEqual(call_args[0], "wellbores")
                self.assertIsInstance(call_args[1], dict)

    def test_incremental_collection(self):
        """Test incremental data collection with date filtering."""
        since_date = datetime.now() - timedelta(days=7)

        with patch.object(self.sodir_data.api_client, "get_fields") as mock_get:
            mock_get.return_value = [self.sample_field]

            result = self.sodir_data.collect_dataset(
                "fields", since=since_date.isoformat()
            )

            self.assertIn("filters", result["metadata"])
            self.assertEqual(
                result["metadata"]["filters"]["since"], since_date.isoformat()
            )

    def test_error_handling_during_collection(self):
        """Test error handling when API fails."""
        with patch.object(self.sodir_data.api_client, "get_blocks") as mock_get:
            mock_get.side_effect = Exception("API Error")

            result = self.sodir_data.collect_dataset("blocks")

            self.assertIn("error", result)
            self.assertEqual(result["status"], "failed")
            self.assertIn("API Error", result["error"])

    def test_collection_statistics(self):
        """Test collection statistics are tracked."""
        with patch.object(self.sodir_data.api_client, "get_blocks") as mock_get:
            mock_get.return_value = [self.sample_block] * 5

            result = self.sodir_data.collect_dataset("blocks")
            stats = self.sodir_data.get_statistics()

            self.assertIn("collections", stats)
            self.assertIn("total_records", stats)
            self.assertIn("errors", stats)
            self.assertEqual(stats["total_records"], 5)


class TestDataCollectionWorkflow(unittest.TestCase):
    """Tests for data collection workflows."""

    def setUp(self):
        """Set up test fixtures."""
        from worldenergydata.sodir.workflows.collection import CollectionWorkflow

        self.workflow_config = {
            "name": "daily_collection",
            "datasets": ["blocks", "wellbores", "fields"],
            "schedule": "daily",
            "filters": {"status": "ACTIVE", "updated_since": "yesterday"},
            "validation": {"enabled": True, "strict": False},
            "storage": {"format": "json", "compression": True},
        }

        self.workflow = CollectionWorkflow(self.workflow_config)

    def test_workflow_initialization(self):
        """Test workflow initialization with configuration."""
        self.assertEqual(self.workflow.name, "daily_collection")
        self.assertEqual(len(self.workflow.datasets), 3)
        self.assertTrue(self.workflow.validation_enabled)

    def test_workflow_execution(self):
        """Test complete workflow execution."""
        with patch.object(self.workflow, "collect_data") as mock_collect, patch.object(
            self.workflow, "validate_data"
        ) as mock_validate, patch.object(self.workflow, "store_data") as mock_store:

            mock_collect.return_value = {"data": [], "count": 10}
            mock_validate.return_value = {"valid": True, "errors": []}
            mock_store.return_value = {"success": True, "path": "/data/output.json"}

            result = self.workflow.execute()

            self.assertTrue(result["success"])
            self.assertIn("execution_time", result)
            self.assertIn("datasets_collected", result)
            mock_collect.assert_called()
            mock_validate.assert_called()
            mock_store.assert_called()

    def test_workflow_filters(self):
        """Test workflow applies configured filters."""
        with patch.object(self.workflow, "api_client") as mock_client:
            mock_client.get_fields.return_value = []

            self.workflow.collect_dataset("fields")

            # Verify filters were applied
            call_args = mock_client.get_fields.call_args
            self.assertIn("filters", call_args[1] if len(call_args) > 1 else {})

    def test_workflow_error_recovery(self):
        """Test workflow handles errors gracefully."""
        with patch.object(self.workflow, "collect_data") as mock_collect:
            mock_collect.side_effect = Exception("Collection failed")

            result = self.workflow.execute()

            self.assertFalse(result["success"])
            self.assertIn("error", result)
            self.assertIn("Collection failed", result["error"])

    def test_parallel_dataset_collection(self):
        """Test parallel collection of multiple datasets."""
        with patch("concurrent.futures.ThreadPoolExecutor") as mock_executor:
            mock_future = Mock()
            mock_future.result.return_value = {"data": [], "count": 5}
            mock_executor.return_value.__enter__.return_value.submit.return_value = (
                mock_future
            )

            result = self.workflow.collect_parallel(["blocks", "wellbores"])

            self.assertEqual(len(result), 2)
            self.assertIn("blocks", result)
            self.assertIn("wellbores", result)


class TestDataStorage(unittest.TestCase):
    """Tests for data storage system."""

    def setUp(self):
        """Set up test fixtures."""
        from worldenergydata.sodir.storage import DataStorage

        self.storage_config = {
            "base_path": "tests/modules/sodir-integration/data",
            "format": "json",
            "compression": False,
            "structure": "hierarchical",
        }

        self.storage = DataStorage(self.storage_config)

        self.test_data = {
            "dataset": "blocks",
            "timestamp": datetime.now().isoformat(),
            "count": 10,
            "data": [
                {"block_name": "35/11", "status": "AWARDED"},
                {"block_name": "35/12", "status": "OPEN"},
            ],
        }

    def test_storage_initialization(self):
        """Test storage system initialization."""
        self.assertEqual(self.storage.base_path, Path(self.storage_config["base_path"]))
        self.assertEqual(self.storage.format, "json")
        self.assertFalse(self.storage.compression)

    def test_save_data(self):
        """Test saving data to filesystem."""
        with patch("builtins.open", create=True) as mock_open:
            with patch("json.dump") as mock_json_dump:
                with patch("os.makedirs") as mock_makedirs:

                    path = self.storage.save("blocks", self.test_data)

                    self.assertIsNotNone(path)
                    mock_makedirs.assert_called()
                    mock_open.assert_called()
                    mock_json_dump.assert_called()

    def test_load_data(self):
        """Test loading data from filesystem."""
        with patch("builtins.open", create=True) as mock_open:
            with patch("json.load") as mock_json_load:
                mock_json_load.return_value = self.test_data

                data = self.storage.load("blocks", "2024-01-01")

                self.assertEqual(data, self.test_data)
                mock_open.assert_called()
                mock_json_load.assert_called()

    def test_hierarchical_structure(self):
        """Test hierarchical directory structure creation."""
        expected_path = self.storage.get_path("blocks", datetime.now())

        # Should create structure like: data/blocks/2024/01/blocks_2024-01-01.json
        self.assertIn("blocks", str(expected_path))
        self.assertTrue(str(expected_path).endswith(".json"))

    def test_compression_support(self):
        """Test data compression when enabled."""
        self.storage.compression = True

        with patch("gzip.open") as mock_gzip:
            with patch("json.dump") as mock_json_dump:
                with patch("os.makedirs") as mock_makedirs:

                    path = self.storage.save("fields", self.test_data)

                    self.assertTrue(str(path).endswith(".json.gz"))
                    mock_gzip.assert_called()

    def test_list_available_datasets(self):
        """Test listing available datasets."""
        with patch("os.walk") as mock_walk:
            mock_walk.return_value = [
                ("data/blocks", ["2024"], []),
                ("data/blocks/2024", ["01"], ["blocks_2024-01-01.json"]),
            ]

            datasets = self.storage.list_datasets()

            self.assertIn("blocks", datasets)
            self.assertIn("2024-01-01", datasets["blocks"])

    def test_cleanup_old_data(self):
        """Test cleanup of old data files."""
        with patch("os.remove") as mock_remove:
            with patch("os.walk") as mock_walk:
                mock_walk.return_value = [
                    ("data/blocks", [], ["blocks_2023-01-01.json"]),
                ]

                deleted = self.storage.cleanup(older_than_days=365)

                self.assertGreater(deleted, 0)
                mock_remove.assert_called()


class TestDatasetGeneration(unittest.TestCase):
    """Tests for analysis-ready dataset generation."""

    def setUp(self):
        """Set up test fixtures."""
        from worldenergydata.sodir.datasets import DatasetGenerator

        self.generator = DatasetGenerator()

        self.sample_blocks = [
            {"block_name": "35/11", "status": "AWARDED", "operator": "EQUINOR"},
            {"block_name": "35/12", "status": "OPEN", "operator": None},
        ]

        self.sample_fields = [
            {
                "field_name": "JOHAN SVERDRUP",
                "status": "PRODUCING",
                "oil_reserves": 2700,
            },
            {"field_name": "MARTIN LINGE", "status": "PRODUCING", "oil_reserves": 200},
        ]

    def test_create_analysis_dataset(self):
        """Test creating analysis-ready dataset."""
        dataset = self.generator.create_dataset(
            blocks=self.sample_blocks, fields=self.sample_fields
        )

        self.assertIn("blocks", dataset)
        self.assertIn("fields", dataset)
        self.assertIn("metadata", dataset)
        self.assertIn("summary", dataset)

    def test_cross_reference_data(self):
        """Test cross-referencing between datasets."""
        # Add wellbores that reference blocks
        wellbores = [
            {"wellbore_name": "35/11-1", "block": "35/11"},
            {"wellbore_name": "35/12-1", "block": "35/12"},
        ]

        dataset = self.generator.create_cross_referenced_dataset(
            blocks=self.sample_blocks, wellbores=wellbores
        )

        # Check cross-references were created
        self.assertIn("block_wellbores", dataset)
        self.assertEqual(len(dataset["block_wellbores"]["35/11"]), 1)

    def test_summary_statistics(self):
        """Test generation of summary statistics."""
        stats = self.generator.generate_statistics(fields=self.sample_fields)

        self.assertIn("total_fields", stats)
        self.assertIn("producing_fields", stats)
        self.assertIn("total_reserves", stats)
        self.assertEqual(stats["total_fields"], 2)
        self.assertEqual(stats["producing_fields"], 2)

    def test_export_formats(self):
        """Test exporting datasets in different formats."""
        dataset = self.generator.create_dataset(blocks=self.sample_blocks)

        # Test JSON export
        json_output = self.generator.export_json(dataset)
        self.assertIsInstance(json_output, str)

        # Test CSV export
        csv_output = self.generator.export_csv(dataset["blocks"])
        self.assertIn("block_name", csv_output)
        self.assertIn("35/11", csv_output)

    def test_filtering_and_sorting(self):
        """Test dataset filtering and sorting capabilities."""
        # Filter for awarded blocks only
        filtered = self.generator.filter_dataset(
            self.sample_blocks, criteria={"status": "AWARDED"}
        )

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["block_name"], "35/11")

        # Sort by field reserves
        sorted_fields = self.generator.sort_dataset(
            self.sample_fields, by="oil_reserves", descending=True
        )

        self.assertEqual(sorted_fields[0]["field_name"], "JOHAN SVERDRUP")


class TestDataValidationIntegration(unittest.TestCase):
    """Tests for validation integration in data collection."""

    def setUp(self):
        """Set up test fixtures."""
        from worldenergydata.sodir.data import SodirData
        from worldenergydata.sodir.validators import DataValidator

        self.validator = DataValidator()
        config = {
            "collection": {"validate": True},
            "storage": {"base_path": "test_data"},
        }
        self.sodir_data = SodirData(config)

    def test_validate_collected_data(self):
        """Test validation of collected data."""
        test_field = {
            "fldName": "TEST FIELD",
            "fldDiscoveryYear": 2020,
            "fldProductionStartYear": 2019,  # Invalid: production before discovery
        }

        is_valid, errors = self.sodir_data.validate_field(test_field)

        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        self.assertIn("Production start", errors[0])

    def test_validation_report_generation(self):
        """Test generation of validation reports."""
        test_data = [
            {"fldName": "VALID FIELD", "fldDiscoveryYear": 2010},
            {"fldName": "", "fldDiscoveryYear": 2020},  # Invalid: missing name
        ]

        report = self.sodir_data.generate_validation_report(test_data, "fields")

        self.assertIn("total_records", report)
        self.assertIn("valid_records", report)
        self.assertIn("invalid_records", report)
        self.assertIn("errors", report)
        self.assertEqual(report["total_records"], 2)
        self.assertEqual(report["valid_records"], 1)
        self.assertEqual(report["invalid_records"], 1)


if __name__ == "__main__":
    unittest.main()
