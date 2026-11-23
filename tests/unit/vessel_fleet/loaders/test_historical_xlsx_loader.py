# ABOUTME: Tests for the historical Drive-corpus fleet spreadsheet loader.
# ABOUTME: CI-safe synthetic fixtures + one skip-if-missing real-file probe.

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.vessel_fleet.constants import DataSource
from worldenergydata.vessel_fleet.loaders.historical_xlsx_loader import (
    COLLECTION_DATE,
    DATA_SOURCE,
    DRIVE_FLEET_FILES,
    load_drive_fleet_spreadsheets,
    normalize_to_records,
)

_REAL_BASE = Path("/mnt/ace/gdrive/shared-with-me")


@pytest.fixture
def row_oriented_df() -> pd.DataFrame:
    """Synthetic row-oriented sheet mimicking 'Semi sub Basic info'."""
    return pd.DataFrame(
        {
            "VESSEL NAME": ["TEST RIG A", "TEST RIG B", None],
            "CURRENT STATUS": ["Operating", "Cold Stacked", "Operating"],
            "VESSEL TYPE": ["SS", "DS Gusto", "SS- PQ"],
            "VESSEL OPERATOR": ["Acme Drilling", "Beta Energy", "Gamma"],
            "VESSEL OWNER": ["Acme", "Beta", "Gamma"],
            "OPERATING WATER DEPTH": ["7,072'", "5000", "1000"],
            "CLASSIFICATION": ["ABS", "DNV", "LR"],
            # An unmapped column that must survive in RAW.
            "RANDOM SPEC": ["foo", "bar", "baz"],
        }
    )


def test_constants_tag_historical_baseline():
    assert DATA_SOURCE == DataSource.XLS_HISTORICAL.value
    assert COLLECTION_DATE == "2010-2014"


def test_normalize_maps_known_columns(row_oriented_df):
    records = normalize_to_records(row_oriented_df, "Synthetic.xlsx", "Sheet1")

    # Third row has no vessel name -> skipped.
    assert len(records) == 2

    first = records[0]
    assert first["VESSEL_NAME"] == "TEST RIG A"
    assert first["STATUS"] == "Operating"
    assert first["RIG_TYPE"] == "semi_submersible"
    assert first["OPERATOR"] == "Acme Drilling"
    assert first["OWNER"] == "Acme"
    assert first["CLASSIFICATION_SOCIETY"] == "ABS"
    # "7,072'" -> 7072.0 (comma + trailing foot-mark stripped).
    assert first["WATER_DEPTH_RATING_FT"] == 7072.0


def test_normalize_sets_provenance_tags(row_oriented_df):
    records = normalize_to_records(row_oriented_df, "Synthetic.xlsx", "Sheet1")
    for rec in records:
        assert rec["DATA_SOURCE"] == DATA_SOURCE
        assert rec["COLLECTION_DATE"] == COLLECTION_DATE
        assert rec["SOURCE_FILE"] == "Synthetic.xlsx"
        assert rec["SOURCE_SHEET"] == "Sheet1"


def test_normalize_preserves_unmapped_columns_in_raw(row_oriented_df):
    records = normalize_to_records(row_oriented_df, "Synthetic.xlsx")
    raw = records[0]["RAW"]
    # Unmapped original column header preserved verbatim.
    assert raw["RANDOM SPEC"] == "foo"
    # Mapped originals are still kept in RAW too (nothing dropped).
    assert raw["VESSEL NAME"] == "TEST RIG A"
    assert raw["CLASSIFICATION"] == "ABS"


def test_normalize_rig_type_code_variants(row_oriented_df):
    records = normalize_to_records(row_oriented_df, "Synthetic.xlsx")
    # "DS Gusto" -> drillship; "SS- PQ" excluded (no name on that row).
    assert records[1]["RIG_TYPE"] == "drillship"


def test_normalize_meters_water_depth_converted():
    df = pd.DataFrame(
        {
            "VESSEL NAME": ["METRIC RIG"],
            "OPERATING WATER DEPTH (M)": ["100"],
        }
    )
    records = normalize_to_records(df, "Metric.xlsx")
    # 100 m -> ~328.1 ft (unit-aware conversion for the *_FT schema field).
    assert records[0]["WATER_DEPTH_RATING_FT"] == pytest.approx(328.1, abs=0.2)


def test_normalize_no_name_column_returns_empty():
    df = pd.DataFrame({"FOO": [1, 2], "BAR": [3, 4]})
    assert normalize_to_records(df, "Nameless.xlsx") == []


def test_normalize_empty_dataframe_returns_empty():
    assert normalize_to_records(pd.DataFrame(), "Empty.xlsx") == []


def test_load_drive_fleet_missing_dir_returns_empty(tmp_path):
    df = load_drive_fleet_spreadsheets(tmp_path)
    assert isinstance(df, pd.DataFrame)
    assert df.empty


@pytest.mark.skipif(
    not (_REAL_BASE / DRIVE_FLEET_FILES[0]).exists(),
    reason="Drive corpus xlsx not present on /mnt/ace",
)
def test_load_real_drive_fleet_spreadsheets():
    df = load_drive_fleet_spreadsheets(_REAL_BASE)
    assert not df.empty
    assert len(df) > 0
    # Every real record carries the historical provenance tags.
    assert set(df["DATA_SOURCE"].unique()) == {DATA_SOURCE}
    assert set(df["COLLECTION_DATE"].unique()) == {COLLECTION_DATE}
    assert df["VESSEL_NAME"].notna().all()
