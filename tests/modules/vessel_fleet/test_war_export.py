"""Tests for WAR fleet to vessel_fleet format export."""

from __future__ import annotations

import pandas as pd
import pytest

from worldenergydata.vessel_fleet.exporters.war_export import (
    export_war_to_vessel_fleet,
)


def _make_war_df(rows: list[dict]) -> pd.DataFrame:
    """Build a WAR-style DataFrame from a list of row dicts."""
    base = {
        "RIG_NAME": None,
        "RIG_TYPE": None,
        "RIG_STATUS": None,
        "OWNER": None,
        "OPERATOR": None,
        "WATER_DEPTH_RATING_FT": None,
        "DRILLING_DEPTH_RATING_FT": None,
        "MAX_WATER_DEPTH_FT": None,
        "DATA_SOURCE": None,
        "IS_OFFSHORE": None,
        "WELLS_DRILLED_COUNT": None,
        "LAST_WAR_DATE": None,
        "FIRST_WAR_DATE": None,
        "LAST_AREA_CODE": None,
        "LAST_BLOCK_NUMBER": None,
        "LOA_M": None,
        "BEAM_M": None,
        "DP_CLASS": None,
        "YEAR_BUILT": None,
        "IMO_NUMBER": None,
        "FLAG_STATE": None,
    }
    full_rows = [{**base, **r} for r in rows]
    return pd.DataFrame(full_rows)


class TestVesselNameMapping:
    """RIG_NAME must be copied to VESSEL_NAME."""

    def test_vessel_name_populated_from_rig_name(self):
        # Arrange
        df = _make_war_df([{"RIG_NAME": "DEEPWATER HORIZON"}])

        # Act
        records = export_war_to_vessel_fleet(df)

        # Assert
        assert len(records) == 1
        assert records[0]["VESSEL_NAME"] == "DEEPWATER HORIZON"

    def test_rig_name_preserved_alongside_vessel_name(self):
        # Arrange
        df = _make_war_df([{"RIG_NAME": "OCEAN STAR"}])

        # Act
        records = export_war_to_vessel_fleet(df)

        # Assert
        assert records[0]["RIG_NAME"] == "OCEAN STAR"
        assert records[0]["VESSEL_NAME"] == "OCEAN STAR"


class TestMandatoryFields:
    """DATA_SOURCE, VESSEL_CATEGORY, IS_OFFSHORE must be set."""

    def test_data_source_set_to_bsee_war(self):
        # Arrange
        df = _make_war_df([{"RIG_NAME": "WEST SIRIUS"}])

        # Act
        records = export_war_to_vessel_fleet(df)

        # Assert
        assert records[0]["DATA_SOURCE"] == "bsee_war"

    def test_vessel_category_set_to_drilling_rig(self):
        # Arrange
        df = _make_war_df([{"RIG_NAME": "WEST SIRIUS"}])

        # Act
        records = export_war_to_vessel_fleet(df)

        # Assert
        assert records[0]["VESSEL_CATEGORY"] == "drilling_rig"

    def test_is_offshore_true_for_all_records(self):
        # Arrange
        df = _make_war_df([
            {"RIG_NAME": "RIG A", "IS_OFFSHORE": False},
            {"RIG_NAME": "RIG B", "IS_OFFSHORE": None},
        ])

        # Act
        records = export_war_to_vessel_fleet(df)

        # Assert
        assert all(r["IS_OFFSHORE"] is True for r in records)


class TestRigTypePreserved:
    """RIG_TYPE values from WAR fleet must be carried over."""

    def test_rig_type_preserved(self):
        # Arrange
        df = _make_war_df([
            {"RIG_NAME": "DEEPWATER TITAN", "RIG_TYPE": "drillship"},
            {"RIG_NAME": "NOBLE CLYDE", "RIG_TYPE": "jackup"},
        ])

        # Act
        records = export_war_to_vessel_fleet(df)

        # Assert
        types = {r["VESSEL_NAME"]: r["RIG_TYPE"] for r in records}
        assert types["DEEPWATER TITAN"] == "drillship"
        assert types["NOBLE CLYDE"] == "jackup"


class TestFiltering:
    """Empty/null RIG_NAME and NON RIG entries must be filtered out."""

    def test_null_rig_name_filtered(self):
        # Arrange
        df = _make_war_df([
            {"RIG_NAME": "VALID RIG"},
            {"RIG_NAME": None},
        ])

        # Act
        records = export_war_to_vessel_fleet(df)

        # Assert
        assert len(records) == 1
        assert records[0]["VESSEL_NAME"] == "VALID RIG"

    def test_empty_string_rig_name_filtered(self):
        # Arrange
        df = _make_war_df([
            {"RIG_NAME": "VALID RIG"},
            {"RIG_NAME": ""},
            {"RIG_NAME": "   "},
        ])

        # Act
        records = export_war_to_vessel_fleet(df)

        # Assert
        assert len(records) == 1

    def test_non_rig_unit_operation_filtered(self):
        # Arrange
        df = _make_war_df([
            {"RIG_NAME": "VALID RIG"},
            {"RIG_NAME": "* NON RIG UNIT OPERATION"},
            {"RIG_NAME": "NON RIG UNIT OPERATION"},
        ])

        # Act
        records = export_war_to_vessel_fleet(df)

        # Assert
        assert len(records) == 1
        assert records[0]["VESSEL_NAME"] == "VALID RIG"


class TestOutputFormat:
    """Output must be a list of dicts ready for ParquetStore.save()."""

    def test_returns_list_of_dicts(self):
        # Arrange
        df = _make_war_df([{"RIG_NAME": "RIG A"}, {"RIG_NAME": "RIG B"}])

        # Act
        records = export_war_to_vessel_fleet(df)

        # Assert
        assert isinstance(records, list)
        assert all(isinstance(r, dict) for r in records)

    def test_empty_dataframe_returns_empty_list(self):
        # Arrange
        df = _make_war_df([])

        # Act
        records = export_war_to_vessel_fleet(df)

        # Assert
        assert records == []


class TestColumnPassthrough:
    """Columns like MAX_WATER_DEPTH_FT, OWNER, OPERATOR pass through."""

    def test_max_water_depth_preserved(self):
        # Arrange
        df = _make_war_df([
            {"RIG_NAME": "RIG X", "MAX_WATER_DEPTH_FT": 8500.0},
        ])

        # Act
        records = export_war_to_vessel_fleet(df)

        # Assert
        assert records[0]["MAX_WATER_DEPTH_FT"] == 8500.0

    def test_owner_and_operator_preserved(self):
        # Arrange
        df = _make_war_df([
            {"RIG_NAME": "RIG Y", "OWNER": "Transocean", "OPERATOR": "Shell"},
        ])

        # Act
        records = export_war_to_vessel_fleet(df)

        # Assert
        assert records[0]["OWNER"] == "Transocean"
        assert records[0]["OPERATOR"] == "Shell"

    def test_dimensional_fields_preserved(self):
        # Arrange
        df = _make_war_df([
            {"RIG_NAME": "RIG Z", "LOA_M": 228.0, "BEAM_M": 42.0},
        ])

        # Act
        records = export_war_to_vessel_fleet(df)

        # Assert
        assert records[0]["LOA_M"] == 228.0
        assert records[0]["BEAM_M"] == 42.0
