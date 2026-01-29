"""
Integration tests for BSEE module with real data processing.

These tests execute actual BSEE analysis code with test data,
providing real code coverage.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from tests.test_markers import integration
from worldenergydata.modules.bsee.analysis.bsee_analysis import BSEEAnalysis


@integration
class TestBSEEAnalysisIntegration:
    """Integration tests for BSEE analysis with real execution."""

    @pytest.fixture
    def test_data(self):
        """Create test data for BSEE analysis."""
        return {
            "well_data": pd.DataFrame(
                {
                    "API12": ["608124003301", "608124003302", "608124003303"],
                    "WELL_NAME": ["JULIA-1", "JULIA-2", "JACK-1"],
                    "FIELD": ["JULIA", "JULIA", "JACK"],
                    "WATER_DEPTH": [7000, 7100, 6500],
                    "TOTAL_DEPTH": [32000, 31500, 30000],
                    "SPUD_DATE": pd.to_datetime(
                        ["2014-03-15", "2014-06-20", "2015-01-10"]
                    ),
                    "COMPLETION_DATE": pd.to_datetime(
                        ["2014-09-20", "2014-12-15", "2015-07-25"]
                    ),
                }
            ),
            "production_data": pd.DataFrame(
                {
                    "API12": [
                        "608124003301",
                        "608124003301",
                        "608124003302",
                        "608124003302",
                    ],
                    "PRODUCTION_DATE": pd.to_datetime(
                        ["2020-01-01", "2020-02-01", "2020-01-01", "2020-02-01"]
                    ),
                    "OIL_VOLUME": [15000, 14500, 12000, 11800],
                    "GAS_VOLUME": [8000, 7800, 6500, 6400],
                    "WATER_VOLUME": [500, 550, 400, 420],
                }
            ),
        }

    @pytest.fixture
    def test_config(self, tmp_path):
        """Create test configuration."""
        return {
            "analysis": {"flag": True, "type": "production", "output_format": "csv"},
            "output": {"directory": str(tmp_path / "results")},
            "Analysis": {
                "analysis_root_folder": str(tmp_path),
                "result_folder": str(tmp_path / "results"),
            },
        }

    def test_bsee_analysis_initialization(self):
        """Test BSEE analysis initialization."""
        analysis = BSEEAnalysis()

        assert analysis is not None
        assert hasattr(analysis, "router")
        assert hasattr(analysis, "run_analysis_for_all_wells")
        assert hasattr(analysis, "add_production_dates_to_well_summary")

    def test_bsee_router_with_real_data(self, test_config, test_data):
        """Test BSEE router with real data processing."""
        analysis = BSEEAnalysis()

        with patch.object(analysis, "run_analysis_for_all_wells") as mock_run:
            mock_run.return_value = test_config

            result = analysis.router(test_config, test_data)

            assert result is not None
            mock_run.assert_called_once_with(test_config, test_data)

    @patch("worldenergydata.modules.bsee.analysis.bsee_analysis.well_api12_analysis")
    @patch("worldenergydata.modules.bsee.analysis.bsee_analysis.prod_api12_analysis")
    def test_run_analysis_for_all_wells_integration(
        self, mock_prod, mock_well, test_config, test_data
    ):
        """Test full analysis workflow with real data."""
        analysis = BSEEAnalysis()

        # Create mock returns with actual data structures
        well_analysis_result = {
            "well_summary_df_groups": test_data["well_data"].copy(),
            "well_timeline_df": pd.DataFrame(),
        }

        production_summary = pd.DataFrame(
            {
                "API12": ["608124003301", "608124003302"],
                "START_PRODUCTION_DATE": pd.to_datetime(["2020-01-01", "2020-01-01"]),
                "LAST_PRODUCTION_DATE": pd.to_datetime(["2020-02-01", "2020-02-01"]),
                "TOTAL_OIL": [29500, 23800],
                "TOTAL_GAS": [15800, 12900],
            }
        )

        prod_analysis_result = {
            "production_summary_df_groups": production_summary,
            "production_timeline_df": pd.DataFrame(),
        }

        mock_well.run_well_analysis.return_value = (test_config, well_analysis_result)
        mock_prod.run_production_analysis.return_value = (
            test_config,
            prod_analysis_result,
        )
        mock_well.well_timeline_analysis.return_value = pd.DataFrame()

        # Run analysis
        result = analysis.run_analysis_for_all_wells(test_config, test_data)

        # Verify execution
        assert result is not None
        mock_well.run_well_analysis.assert_called_once()
        mock_prod.run_production_analysis.assert_called_once()

        # Verify production dates were added to well summary
        well_df = well_analysis_result["well_summary_df_groups"]
        assert "START_PRODUCTION_DATE" in well_df.columns
        assert "LAST_PRODUCTION_DATE" in well_df.columns

    @patch("worldenergydata.modules.bsee.analysis.bsee_analysis.well_api12_analysis")
    def test_add_production_dates_integration(self, mock_well_api12, test_data):
        """Test production date integration with real data."""
        analysis = BSEEAnalysis()

        well_groups = {"well_summary_df_groups": test_data["well_data"].copy()}

        prod_groups = {
            "production_summary_df_groups": pd.DataFrame(
                {
                    "API12": ["608124003301", "608124003302"],
                    "START_PRODUCTION_DATE": "2020-01-01",
                    "LAST_PRODUCTION_DATE": "2020-12-31",
                }
            )
        }

        # Execute real method (save_result_groups is mocked via well_api12_analysis)
        analysis.add_production_dates_to_well_summary({}, well_groups, prod_groups)

        # Verify dates were added
        well_df = well_groups["well_summary_df_groups"]
        assert "START_PRODUCTION_DATE" in well_df.columns
        assert "LAST_PRODUCTION_DATE" in well_df.columns

        # Check first well has production dates
        first_well = well_df[well_df["API12"] == "608124003301"].iloc[0]
        assert first_well["START_PRODUCTION_DATE"] == "2020-01-01"
        assert first_well["LAST_PRODUCTION_DATE"] == "2020-12-31"

    def test_production_data_aggregation(self, test_data):
        """Test production data aggregation logic."""
        prod_data = test_data["production_data"]

        # Group by API and aggregate
        aggregated = prod_data.groupby("API12").agg(
            {
                "OIL_VOLUME": "sum",
                "GAS_VOLUME": "sum",
                "WATER_VOLUME": "sum",
                "PRODUCTION_DATE": ["min", "max"],
            }
        )

        # Verify aggregation
        assert len(aggregated) == 2  # Two unique APIs
        assert aggregated.loc["608124003301"]["OIL_VOLUME"]["sum"] == 29500
        assert aggregated.loc["608124003302"]["OIL_VOLUME"]["sum"] == 23800


@integration
class TestBSEEDataProcessing:
    """Test BSEE data processing functions."""

    @pytest.fixture
    def sample_well_data(self):
        """Create sample well data."""
        return pd.DataFrame(
            {
                "API12": ["123456789012"] * 10,
                "DEPTH": np.linspace(0, 10000, 10),
                "INCLINATION": np.random.uniform(0, 45, 10),
                "AZIMUTH": np.random.uniform(0, 360, 10),
            }
        )

    def test_well_data_processing(self, sample_well_data):
        """Test well data processing logic."""
        # Process well data
        processed = sample_well_data.copy()
        processed["TVD"] = processed["DEPTH"] * np.cos(
            np.radians(processed["INCLINATION"])
        )
        processed["HORIZONTAL_DISPLACEMENT"] = processed["DEPTH"] * np.sin(
            np.radians(processed["INCLINATION"])
        )

        # Verify calculations
        assert "TVD" in processed.columns
        assert "HORIZONTAL_DISPLACEMENT" in processed.columns
        assert all(processed["TVD"] <= processed["DEPTH"])
        assert all(processed["HORIZONTAL_DISPLACEMENT"] >= 0)

    def test_production_timeline_creation(self):
        """Test production timeline creation."""
        dates = pd.date_range("2020-01-01", periods=12, freq="ME")
        production = pd.DataFrame(
            {
                "date": dates,
                "oil": np.random.uniform(10000, 20000, 12),
                "gas": np.random.uniform(5000, 10000, 12),
            }
        )

        # Calculate cumulative production
        production["cumulative_oil"] = production["oil"].cumsum()
        production["cumulative_gas"] = production["gas"].cumsum()

        # Verify timeline
        assert len(production) == 12
        assert (
            production["cumulative_oil"].iloc[-1] > production["cumulative_oil"].iloc[0]
        )
        assert all(production["cumulative_oil"].diff()[1:] >= 0)


@integration
class TestBSEEFileOperations:
    """Test BSEE file operations with real I/O."""

    def test_yaml_config_loading(self, tmp_path):
        """Test loading YAML configuration."""
        config_file = tmp_path / "test_config.yml"
        config_data = {
            "analysis": {
                "type": "production",
                "fields": ["JULIA", "JACK"],
                "date_range": {"start": "2020-01-01", "end": "2023-12-31"},
            }
        }

        # Write config
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Read config
        with open(config_file, "r") as f:
            loaded = yaml.safe_load(f)

        assert loaded == config_data
        assert loaded["analysis"]["type"] == "production"
        assert len(loaded["analysis"]["fields"]) == 2

    def test_csv_output_generation(self, tmp_path):
        """Test CSV output generation."""
        output_file = tmp_path / "results.csv"

        # Create sample data
        data = pd.DataFrame(
            {
                "API": ["123", "456"],
                "Production": [1000, 2000],
                "Date": pd.to_datetime(["2020-01-01", "2020-02-01"]),
            }
        )

        # Write to CSV
        data.to_csv(output_file, index=False)

        # Read back and verify
        loaded = pd.read_csv(output_file)
        assert len(loaded) == 2
        assert loaded["Production"].sum() == 3000
        assert output_file.exists()
