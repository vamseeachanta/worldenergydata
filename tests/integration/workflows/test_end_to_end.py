"""
End-to-end integration tests for complete workflows.

These tests execute full workflows from configuration to output,
testing the entire system integration.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from tests.test_markers import integration, slow
from worldenergydata.engine import engine


@integration
class TestCompleteWorkflow:
    """Test complete end-to-end workflows."""

    @pytest.fixture
    def complete_config(self, tmp_path):
        """Create complete configuration for workflow testing."""
        config_file = tmp_path / "workflow_config.yml"
        results_dir = tmp_path / "results"
        results_dir.mkdir(exist_ok=True)

        config = {
            "basename": "bsee",
            "meta": {
                "project": "test_workflow",
                "run_id": "integration_001",
                "description": "End-to-end workflow test",
            },
            "Analysis": {
                "analysis_root_folder": str(tmp_path),
                "result_folder": str(results_dir),
            },
            "parameters": {
                "filepath": {
                    "apm": {"bin": str(tmp_path / "test_data" / "bin")},
                    "data": {"root": str(tmp_path / "test_data")},
                },
                "refresh_flag": False,
            },
            "analysis": {
                "flag": True,
                "type": "production",
                "fields": ["JULIA", "JACK"],
                "date_range": {"start": "2020-01-01", "end": "2023-12-31"},
            },
            "data": {"source": "test", "format": "csv", "refresh_flag": False},
            "output": {
                "format": "csv",
                "include_plots": False,
                "directory": str(results_dir),
            },
        }

        # Create test data directories
        (tmp_path / "test_data" / "bin").mkdir(parents=True, exist_ok=True)

        # Write config file
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        return config_file, config

    @pytest.fixture
    def test_data_files(self, tmp_path):
        """Create test data files."""
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)

        # Create well data file
        well_data = pd.DataFrame(
            {
                "API12": ["608124003301", "608124003302", "608124003303"],
                "WELL_NAME": ["JULIA-1", "JULIA-2", "JACK-1"],
                "FIELD": ["JULIA", "JULIA", "JACK"],
                "SPUD_DATE": ["2014-03-15", "2014-06-20", "2015-01-10"],
                "COMPLETION_DATE": ["2014-09-20", "2014-12-15", "2015-07-25"],
            }
        )
        well_file = data_dir / "wells.csv"
        well_data.to_csv(well_file, index=False)

        # Create production data file
        prod_data = pd.DataFrame(
            {
                "API12": ["608124003301"] * 12 + ["608124003302"] * 12,
                "DATE": pd.date_range("2020-01-01", periods=12, freq="M").tolist() * 2,
                "OIL_BBL": np.random.uniform(10000, 20000, 24),
                "GAS_MCF": np.random.uniform(5000, 10000, 24),
            }
        )
        prod_file = data_dir / "production.csv"
        prod_data.to_csv(prod_file, index=False)

        return {"wells": well_file, "production": prod_file}

    @patch("worldenergydata.engine.app_manager.save_cfg")
    @patch("worldenergydata.engine.bsee")
    def test_complete_bsee_workflow(
        self, mock_bsee_class, mock_save_cfg, complete_config, test_data_files
    ):
        """Test complete BSEE analysis workflow."""
        config_file, config = complete_config

        # Setup mock to simulate BSEE processing
        mock_bsee_instance = MagicMock()
        mock_bsee_class.return_value = mock_bsee_instance

        # Simulate router returning processed config
        def router_side_effect(cfg):
            cfg["processed"] = True
            cfg["results"] = {
                "well_count": 3,
                "total_production": 500000,
                "fields_analyzed": ["JULIA", "JACK"],
            }
            return cfg

        mock_bsee_instance.router.side_effect = router_side_effect

        # Execute workflow
        result = engine(cfg=config, config_flag=False)

        # Verify workflow execution
        assert result is not None
        assert result["basename"] == "bsee"
        assert result.get("processed") == True
        assert "results" in result
        assert result["results"]["well_count"] == 3
        mock_bsee_instance.router.assert_called_once()

    @patch("worldenergydata.engine.app_manager")
    @patch("worldenergydata.engine.wwyaml")
    @patch("worldenergydata.engine.bsee")
    def test_yaml_to_output_workflow(
        self, mock_bsee_class, mock_wwyaml, mock_app_mgr, complete_config, tmp_path
    ):
        """Test workflow from YAML input to output generation."""
        config_file, config = complete_config

        # Setup app_manager mock
        mock_app_mgr.validate_arguments_run_methods.return_value = (
            str(config_file),
            {},
        )
        mock_app_mgr.save_cfg.return_value = None

        # Setup YAML mock (patch the instance, not the class)
        mock_wwyaml.ymlInput.return_value = config

        # Setup BSEE mock
        mock_bsee_instance = MagicMock()
        mock_bsee_class.return_value = mock_bsee_instance
        mock_bsee_instance.router.return_value = config

        # Execute workflow from YAML file
        result = engine(inputfile=str(config_file), config_flag=False)

        # Verify complete workflow
        assert result is not None
        assert result["basename"] == "bsee"
        mock_wwyaml.ymlInput.assert_called_once()
        mock_bsee_instance.router.assert_called_once()


@integration
@slow
class TestDataPipelineIntegration:
    """Test data pipeline integration."""

    def test_data_ingestion_pipeline(self, tmp_path):
        """Test data ingestion and processing pipeline."""
        # Create input data
        input_data = pd.DataFrame(
            {
                "api": ["123", "456", "789"],
                "date": pd.date_range("2020-01-01", periods=3, freq="M"),
                "value": [100, 200, 300],
            }
        )

        # Simulate pipeline stages
        # Stage 1: Data validation
        validated_data = input_data[input_data["value"] > 0].copy()
        assert len(validated_data) == 3

        # Stage 2: Data transformation
        transformed_data = validated_data.copy()
        transformed_data["value_normalized"] = (
            transformed_data["value"] / transformed_data["value"].max()
        )
        assert "value_normalized" in transformed_data.columns

        # Stage 3: Data aggregation
        aggregated_data = transformed_data.groupby("api").agg(
            {"value": "sum", "value_normalized": "mean"}
        )
        assert len(aggregated_data) == 3

        # Stage 4: Output generation
        output_file = tmp_path / "pipeline_output.csv"
        aggregated_data.to_csv(output_file)
        assert output_file.exists()

    def test_multi_source_data_integration(self, tmp_path):
        """Test integration of data from multiple sources."""
        # Source 1: Well data
        well_data = pd.DataFrame(
            {
                "api": ["123", "456"],
                "well_name": ["WELL-1", "WELL-2"],
                "field": ["FIELD-A", "FIELD-B"],
            }
        )

        # Source 2: Production data
        prod_data = pd.DataFrame(
            {
                "api": ["123", "123", "456", "456"],
                "month": pd.date_range("2020-01-01", periods=2, freq="M").tolist() * 2,
                "oil": [1000, 1100, 2000, 2100],
            }
        )

        # Source 3: Economic data
        econ_data = pd.DataFrame(
            {
                "month": pd.date_range("2020-01-01", periods=2, freq="M"),
                "oil_price": [75.0, 78.0],
            }
        )

        # Integrate data sources
        # Step 1: Merge well and production
        merged = pd.merge(prod_data, well_data, on="api", how="left")
        assert "well_name" in merged.columns
        assert len(merged) == 4

        # Step 2: Merge with economic data
        final = pd.merge(merged, econ_data, on="month", how="left")
        assert "oil_price" in final.columns

        # Step 3: Calculate revenue
        final["revenue"] = final["oil"] * final["oil_price"]
        assert all(final["revenue"] > 0)

        # Verify integration
        assert len(final.columns) >= 6
        assert final["revenue"].sum() > 0


@integration
class TestErrorHandlingIntegration:
    """Test error handling in integrated system."""

    def test_invalid_config_handling(self):
        """Test handling of invalid configuration."""
        invalid_config = {"basename": "non_existent_module"}

        with pytest.raises(Exception) as exc_info:
            engine(cfg=invalid_config, config_flag=False)

        assert "not found" in str(exc_info.value)

    def test_missing_data_handling(self, tmp_path):
        """Test handling of missing data."""
        # Create test directories
        (tmp_path / "test_data" / "bin").mkdir(parents=True, exist_ok=True)

        config = {
            "basename": "bsee",
            "parameters": {
                "filepath": {"apm": {"bin": str(tmp_path / "test_data" / "bin")}}
            },
            "data": {"refresh_flag": False},  # Minimal data
        }

        with patch("worldenergydata.engine.app_manager.save_cfg"):
            with patch("worldenergydata.engine.bsee") as mock_bsee:
                mock_instance = MagicMock()
                mock_bsee.return_value = mock_instance
                mock_instance.router.return_value = config

                result = engine(cfg=config, config_flag=False)

                # Should handle missing data gracefully
                assert result is not None

    def test_partial_data_processing(self):
        """Test processing with partial data."""
        # Create data with missing values
        data = pd.DataFrame({"api": ["123", "456", None], "value": [100, None, 300]})

        # Process with null handling
        cleaned = data.dropna(subset=["api"])
        assert len(cleaned) == 2

        # Fill missing values
        filled = cleaned.fillna({"value": 0})
        assert (
            filled["value"].iloc[1] == 0
            if pd.isna(cleaned["value"].iloc[1])
            else cleaned["value"].iloc[1]
        )


@integration
class TestPerformanceIntegration:
    """Test system performance with realistic data volumes."""

    def test_large_dataset_processing(self):
        """Test processing of large datasets."""
        # Create large dataset (10,000 rows)
        large_data = pd.DataFrame(
            {
                "api": np.repeat(range(100), 100),
                "date": pd.date_range("2010-01-01", periods=10000, freq="D"),
                "value": np.random.uniform(100, 1000, 10000),
            }
        )

        # Process data
        start_len = len(large_data)

        # Aggregation
        aggregated = large_data.groupby("api")["value"].sum()
        assert len(aggregated) == 100

        # Verify processing completed
        assert aggregated.sum() > 0
        assert start_len == 10000

    @pytest.mark.benchmark
    def test_workflow_performance(self):
        """Benchmark workflow performance (runs without pytest-benchmark)."""

        def process_workflow():
            data = pd.DataFrame(
                {"api": range(1000), "value": np.random.uniform(0, 100, 1000)}
            )
            result = data["value"].sum()
            return result

        result = process_workflow()
        assert result > 0
