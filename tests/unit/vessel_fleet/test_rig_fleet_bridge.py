"""Tests for rig fleet bridge convert_curated_to_rig_fleet."""

import pandas as pd
import pytest

from worldenergydata.vessel_fleet.bridge.rig_fleet_bridge import (
    LEGACY_COLUMNS,
    convert_curated_to_rig_fleet,
)


class TestLegacyColumns:
    def test_contains_rig_name(self):
        assert "RIG_NAME" in LEGACY_COLUMNS

    def test_contains_data_source(self):
        assert "DATA_SOURCE" in LEGACY_COLUMNS

    def test_count(self):
        assert len(LEGACY_COLUMNS) == 23


class TestConvertCuratedToRigFleet:
    def test_basic_conversion(self):
        df = pd.DataFrame({
            "RIG_NAME": ["Rig A", "Rig B"],
            "RIG_TYPE": ["Drillship", "Semi"],
        })
        result = convert_curated_to_rig_fleet(df)
        assert len(result) == 2
        assert "RIG_NAME" in result.columns
        assert set(result.columns) == set(LEGACY_COLUMNS)

    def test_missing_columns_filled_none(self):
        df = pd.DataFrame({"RIG_NAME": ["Rig A"]})
        result = convert_curated_to_rig_fleet(df)
        assert result["OWNER"].iloc[0] is None

    def test_vessel_name_fallback(self):
        df = pd.DataFrame({
            "RIG_NAME": [None, "Rig B"],
            "VESSEL_NAME": ["Vessel A", "Vessel B"],
        })
        result = convert_curated_to_rig_fleet(df)
        assert len(result) == 2
        assert result.iloc[0]["RIG_NAME"] == "Vessel A"

    def test_drops_null_rig_name(self):
        df = pd.DataFrame({
            "RIG_NAME": [None, "Rig B"],
        })
        result = convert_curated_to_rig_fleet(df)
        assert len(result) == 1

    def test_drops_empty_rig_name(self):
        df = pd.DataFrame({
            "RIG_NAME": ["", "  ", "Rig C"],
        })
        result = convert_curated_to_rig_fleet(df)
        assert len(result) == 1

    def test_only_legacy_columns_returned(self):
        df = pd.DataFrame({
            "RIG_NAME": ["Rig A"],
            "EXTRA_COL": ["extra"],
        })
        result = convert_curated_to_rig_fleet(df)
        assert "EXTRA_COL" not in result.columns

    def test_reset_index(self):
        df = pd.DataFrame(
            {"RIG_NAME": ["A", None, "C"]},
            index=[10, 20, 30],
        )
        result = convert_curated_to_rig_fleet(df)
        assert list(result.index) == [0, 1]

    def test_does_not_mutate_input(self):
        df = pd.DataFrame({"RIG_NAME": ["Rig A"]})
        orig_cols = list(df.columns)
        convert_curated_to_rig_fleet(df)
        assert list(df.columns) == orig_cols
