"""Tests for SODIR dataset generation module."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.sodir.datasets import DatasetGenerator


def _make_wellbore_df(**overrides):
    defaults = {
        "wellbore_id": ["W1", "W2", "W3"],
        "field_id": ["F1", "F1", "F2"],
        "status": ["PRODUCING", "COMPLETED", "ABANDONED"],
        "water_depth": [100.0, 600.0, 1200.0],
        "spud_date": ["2020-01-15", "2021-03-20", "2022-06-10"],
        "completion_date": ["2020-04-15", "2021-06-20", "2022-10-10"],
        "depth_meters": [3000, 4500, 6000],
    }
    defaults.update(overrides)
    return pd.DataFrame(defaults)


def _make_production_df(**overrides):
    defaults = {
        "field_id": ["F1", "F1", "F2"],
        "production_date": ["2020-01-01", "2020-02-01", "2021-01-01"],
        "oil_production": [100.0, 110.0, 200.0],
        "gas_production": [6000.0, 6600.0, 12000.0],
    }
    defaults.update(overrides)
    return pd.DataFrame(defaults)


def _make_field_df():
    return pd.DataFrame({
        "field_id": ["F1", "F2"],
        "field_name": ["Troll", "Ekofisk"],
        "operator": ["Equinor", "ConocoPhillips"],
        "discovery_year": [1979, 1969],
        "recoverable_oil": [1000.0, 500.0],
    })


# ---------------------------------------------------------------------------
# DatasetGenerator init
# ---------------------------------------------------------------------------

class TestDatasetGeneratorInit:
    def test_init(self):
        gen = DatasetGenerator()
        assert gen.storage is None
        assert "wellbore_analysis" in gen._dataset_configs

    def test_dataset_configs(self):
        gen = DatasetGenerator()
        configs = gen._dataset_configs
        assert "field_production" in configs
        assert "required_fields" in configs["wellbore_analysis"]


# ---------------------------------------------------------------------------
# create_wellbore_dataset
# ---------------------------------------------------------------------------

class TestCreateWellboreDataset:
    def test_basic(self):
        gen = DatasetGenerator()
        df = _make_wellbore_df()
        result = gen.create_wellbore_dataset(df)
        assert "year" in result.columns
        assert "quarter" in result.columns

    def test_drilling_days(self):
        gen = DatasetGenerator()
        df = _make_wellbore_df()
        result = gen.create_wellbore_dataset(df)
        assert "drilling_days" in result.columns
        # W1: Jan 15 to Apr 15 = 91 days
        assert result.loc[0, "drilling_days"] == 91

    def test_success_indicator(self):
        gen = DatasetGenerator()
        df = _make_wellbore_df()
        result = gen.create_wellbore_dataset(df)
        assert "is_successful" in result.columns
        assert result.loc[0, "is_successful"] == True   # PRODUCING
        assert result.loc[2, "is_successful"] == False   # ABANDONED

    def test_water_depth_category(self):
        gen = DatasetGenerator()
        df = _make_wellbore_df()
        result = gen.create_wellbore_dataset(df)
        assert "water_depth_category" in result.columns

    def test_data_completeness(self):
        gen = DatasetGenerator()
        df = _make_wellbore_df()
        result = gen.create_wellbore_dataset(df)
        assert "data_completeness" in result.columns
        assert all(result["data_completeness"] > 0)

    def test_with_field_data(self):
        gen = DatasetGenerator()
        df = _make_wellbore_df()
        fields = _make_field_df()
        result = gen.create_wellbore_dataset(df, fields)
        assert "field_name" in result.columns

    def test_does_not_modify_original(self):
        gen = DatasetGenerator()
        df = _make_wellbore_df()
        original_cols = set(df.columns)
        gen.create_wellbore_dataset(df)
        assert set(df.columns) == original_cols


# ---------------------------------------------------------------------------
# generate_wellbore_dataset
# ---------------------------------------------------------------------------

class TestGenerateWellboreDataset:
    def test_from_dataframe(self):
        gen = DatasetGenerator()
        result = gen.generate_wellbore_dataset(_make_wellbore_df())
        assert "year" in result.columns

    def test_from_list_of_dicts(self):
        gen = DatasetGenerator()
        data = [
            {"wellbore_id": "W1", "status": "PRODUCING", "water_depth": 100},
            {"wellbore_id": "W2", "status": "COMPLETED", "water_depth": 600},
        ]
        result = gen.generate_wellbore_dataset(data)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# create_production_dataset
# ---------------------------------------------------------------------------

class TestCreateProductionDataset:
    def test_basic(self):
        gen = DatasetGenerator()
        prod = _make_production_df()
        fields = _make_field_df()
        result = gen.create_production_dataset(prod, fields)
        assert "year" in result.columns
        assert "boe_production" in result.columns

    def test_cumulative_production(self):
        gen = DatasetGenerator()
        prod = _make_production_df()
        fields = _make_field_df()
        result = gen.create_production_dataset(prod, fields)
        assert "cumulative_oil" in result.columns

    def test_recovery_factor(self):
        gen = DatasetGenerator()
        prod = _make_production_df()
        fields = _make_field_df()
        result = gen.create_production_dataset(prod, fields)
        if "recovery_factor" in result.columns:
            assert all(result["recovery_factor"].dropna() >= 0)


class TestGenerateProductionDataset:
    def test_from_list(self):
        gen = DatasetGenerator()
        data = [{"field_id": "F1", "production_date": "2020-01-01", "oil_production": 100, "gas_production": 6000}]
        fields = _make_field_df()
        result = gen.generate_production_dataset(data, fields)
        assert len(result) >= 1

    def test_no_field_data(self):
        gen = DatasetGenerator()
        prod = _make_production_df()
        result = gen.generate_production_dataset(prod)
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# create_cross_regional_dataset
# ---------------------------------------------------------------------------

class TestCreateCrossRegionalDataset:
    def test_sodir_only(self):
        gen = DatasetGenerator()
        sodir = pd.DataFrame({
            "field_id": ["F1"],
            "water_depth_m": [300.0],
        })
        result = gen.create_cross_regional_dataset(sodir)
        assert result["region"].iloc[0] == "Norway_NCS"
        assert result["regulatory_body"].iloc[0] == "SODIR"

    def test_with_bsee(self):
        gen = DatasetGenerator()
        sodir = pd.DataFrame({
            "field_id": ["F1"],
            "water_depth_m": [300.0],
        })
        bsee = pd.DataFrame({
            "field_id": ["F2"],
            "water_depth_m": [1500.0],
        })
        result = gen.create_cross_regional_dataset(sodir, bsee)
        assert set(result["region"].unique()) == {"Norway_NCS", "US_GOM"}


# ---------------------------------------------------------------------------
# create_summary_statistics
# ---------------------------------------------------------------------------

class TestCreateSummaryStatistics:
    def test_basic(self):
        gen = DatasetGenerator()
        df = pd.DataFrame({
            "region": ["A", "A", "B"],
            "oil": [100.0, 200.0, 300.0],
        })
        result = gen.create_summary_statistics(df, ["region"], ["oil"])
        assert "oil_mean" in result.columns
        assert len(result) == 2

    def test_non_numeric(self):
        gen = DatasetGenerator()
        df = pd.DataFrame({
            "region": ["A", "A", "B"],
            "status": ["active", "active", "idle"],
        })
        result = gen.create_summary_statistics(df, ["region"], ["status"])
        assert "status_count" in result.columns


# ---------------------------------------------------------------------------
# validate_dataset
# ---------------------------------------------------------------------------

class TestValidateDataset:
    def test_valid(self):
        gen = DatasetGenerator()
        df = pd.DataFrame({
            "wellbore_id": ["W1"],
            "field_id": ["F1"],
            "status": ["PRODUCING"],
            "depth_meters": [3000],
            "coordinates": ["(60,5)"],
            "spud_date": ["2020-01-01"],
        })
        result = gen.validate_dataset(df, "wellbore_analysis")
        assert result["valid"] is True
        assert result["record_count"] == 1

    def test_missing_field(self):
        gen = DatasetGenerator()
        df = pd.DataFrame({"wellbore_id": ["W1"]})
        result = gen.validate_dataset(df, "wellbore_analysis")
        assert result["valid"] is False
        assert any("Missing required field" in issue for issue in result["issues"])

    def test_low_completeness_warning(self):
        gen = DatasetGenerator()
        df = pd.DataFrame({
            "wellbore_id": ["W1", "W2", "W3", "W4"],
            "field_id": [None, None, None, "F1"],
            "status": ["A", "B", "C", "D"],
            "depth_meters": [1, 2, 3, 4],
            "coordinates": ["a", "b", "c", "d"],
            "spud_date": ["2020", "2021", "2022", "2023"],
        })
        result = gen.validate_dataset(df, "wellbore_analysis")
        assert any("Low completeness" in w for w in result["warnings"])

    def test_unknown_dataset_type(self):
        gen = DatasetGenerator()
        df = pd.DataFrame({"a": [1]})
        result = gen.validate_dataset(df, "unknown_type")
        assert result["valid"] is True

    def test_duplicate_warning(self):
        gen = DatasetGenerator()
        df = pd.DataFrame({
            "wellbore_id": ["W1", "W1"],
            "field_id": ["F1", "F1"],
        })
        result = gen.validate_dataset(df, "wellbore_analysis")
        assert any("duplicate" in w.lower() for w in result["warnings"])
