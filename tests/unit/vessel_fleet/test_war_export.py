"""Tests for vessel fleet WAR export function."""

import pandas as pd
import pytest

from worldenergydata.vessel_fleet.exporters.war_export import (
    export_war_to_vessel_fleet,
)


class TestExportWarToVesselFleet:
    def test_basic_export(self):
        df = pd.DataFrame({"RIG_NAME": ["Deepwater Horizon", "Ocean Star"]})
        records = export_war_to_vessel_fleet(df)
        assert len(records) == 2
        assert records[0]["VESSEL_NAME"] == "Deepwater Horizon"
        assert records[0]["DATA_SOURCE"] == "bsee_war"
        assert records[0]["VESSEL_CATEGORY"] == "drilling_rig"
        assert records[0]["IS_OFFSHORE"] is True

    def test_empty_dataframe(self):
        df = pd.DataFrame(columns=["RIG_NAME"])
        records = export_war_to_vessel_fleet(df)
        assert records == []

    def test_missing_rig_name_column(self):
        df = pd.DataFrame({"OTHER_COL": ["value"]})
        records = export_war_to_vessel_fleet(df)
        assert records == []

    def test_filters_null_rig_names(self):
        df = pd.DataFrame({"RIG_NAME": ["Rig A", None, "Rig C"]})
        records = export_war_to_vessel_fleet(df)
        assert len(records) == 2

    def test_filters_empty_rig_names(self):
        df = pd.DataFrame({"RIG_NAME": ["Rig A", "", "  "]})
        records = export_war_to_vessel_fleet(df)
        assert len(records) == 1

    def test_filters_non_rig_entries(self):
        df = pd.DataFrame({
            "RIG_NAME": ["Rig A", "* NON RIG UNIT OPERATION", "Rig B"]
        })
        records = export_war_to_vessel_fleet(df)
        assert len(records) == 2
        names = [r["RIG_NAME"] for r in records]
        assert "* NON RIG UNIT OPERATION" not in names

    def test_strips_whitespace(self):
        df = pd.DataFrame({"RIG_NAME": ["  Rig A  "]})
        records = export_war_to_vessel_fleet(df)
        assert records[0]["RIG_NAME"] == "Rig A"

    def test_preserves_extra_columns(self):
        df = pd.DataFrame({
            "RIG_NAME": ["Rig A"],
            "WATER_DEPTH": [5000],
        })
        records = export_war_to_vessel_fleet(df)
        assert records[0]["WATER_DEPTH"] == 5000

    def test_all_non_rig_returns_empty(self):
        df = pd.DataFrame({
            "RIG_NAME": ["* NON RIG UNIT", "NON RIG STUFF"]
        })
        records = export_war_to_vessel_fleet(df)
        assert records == []
