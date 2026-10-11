"""Delimiter integrity and semantic anchors for the canonical component CSV."""

import csv
import hashlib
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from worldenergydata.vessel_fleet.loaders.drilling_riser_loader import (
    DrillingRiserLoader,
    _DATA_DIR,
)

CSV_NAME = "drilling_riser_components.csv"
TEXT_DIGEST = "22be7d02a4fc4698684551c21943f9fc2e79d02e58729bd24aeced59759aaa94"
EXPECTED_IDS = """
RJ-21-75-BARE RJ-21-75-BUOY RJ-21-50-PUP RJ-21-40-PUP RJ-21-75-HW
RJ-18.75-75-BARE RJ-18.75-75-BUOY RJ-18.75-50-PUP
BOP-SUB-18.75-15K BOP-SUB-18.75-20K BOP-SUB-18.75-15K-NOV
BOP-SURF-13.625-5K BOP-SURF-18.75-10K
LMRP-18.75-15K LMRP-18.75-20K LMRP-18.75-15K-NOV
FJ-UPPER-21 FJ-LOWER-21 FJ-UPPER-18.75 FJ-LOWER-18.75
TJ-21-50 TJ-21-75 TJ-18.75-50
RJ-21-75-NOV-MERLIN RJ-21-75-NOV-MERLIN-BUOY RJ-21-75-CAM
RJ-21-75-CAM-BUOY RJ-21-75-HYD RJ-21-75-S135 RJ-21-50-PUP-NOV
RJ-21-30-PUP RJ-18.75-75-NOV RJ-18.75-75-CAM RJ-21.5-75-BARE
RJ-24-75-BARE RJ-24-75-BUOY
""".split()


def test_canonical_width_and_text_preservation():
    raw = (_DATA_DIR / CSV_NAME).read_bytes()
    rows = list(csv.reader(raw.decode().splitlines()))
    assert len(rows) == 37
    assert all(len(row) == 31 for row in rows)
    assert [row[0] for row in rows[1:]] == EXPECTED_IDS
    assert len(set(EXPECTED_IDS)) == 36
    assert hashlib.sha256(raw.replace(b",", b"")).hexdigest() == TEXT_DIGEST


@pytest.mark.parametrize("width", [29, 30, 32])
def test_bad_width_rejected_before_pandas(tmp_path: Path, width: int):
    header = (_DATA_DIR / CSV_NAME).read_text().splitlines()[0]
    (tmp_path / CSV_NAME).write_text(header + "\n" + ",".join(["x"] * width))
    loader = DrillingRiserLoader(tmp_path)
    with patch("pandas.read_csv") as read_csv:
        with pytest.raises(ValueError, match=rf"line 2.*expected 31.*actual {width}"):
            loader.load()
        read_csv.assert_not_called()
    assert loader._df is None


def test_physical_line_number_after_quoted_newline(tmp_path: Path):
    (tmp_path / CSV_NAME).write_text(
        'COMPONENT_ID,DATA_SOURCE,NOTES\nA,public,"first\nsecond"\nB,public\n'
    )
    with pytest.raises(ValueError, match="line 4.*expected 3.*actual 2"):
        DrillingRiserLoader(tmp_path).load()


def test_valid_quoted_fields_and_cache(tmp_path: Path):
    (tmp_path / CSV_NAME).write_text(
        'COMPONENT_ID,DATA_SOURCE,NOTES\nA,"public, source","first\nsecond"\n'
    )
    loader = DrillingRiserLoader(tmp_path)
    df = loader.load()
    assert df.iloc[0]["DATA_SOURCE"] == "public, source"
    assert df.iloc[0]["NOTES"] == "first\nsecond"
    assert loader.load() is df


@pytest.mark.parametrize("field", ["DATA_SOURCE", "NOTES"])
@pytest.mark.parametrize("value", ["", "   "])
def test_empty_provenance_rejected(tmp_path: Path, field: str, value: str):
    row = {"COMPONENT_ID": "A", "DATA_SOURCE": "public", "NOTES": "test"}
    row[field] = value
    pd.DataFrame([row]).to_csv(tmp_path / CSV_NAME, index=False)
    loader = DrillingRiserLoader(tmp_path)
    with pytest.raises(ValueError, match=field):
        loader.load()
    assert loader._df is None


@pytest.mark.parametrize("field", ["DATA_SOURCE", "NOTES"])
def test_missing_provenance_column_rejected(tmp_path: Path, field: str):
    row = {"COMPONENT_ID": "A", "DATA_SOURCE": "public", "NOTES": "test"}
    del row[field]
    pd.DataFrame([row]).to_csv(tmp_path / CSV_NAME, index=False)
    with pytest.raises(ValueError, match=field):
        DrillingRiserLoader(tmp_path).load()


def test_canonical_provenance_populated():
    df = DrillingRiserLoader().load()
    for field in ("DATA_SOURCE", "NOTES"):
        assert df[field].notna().all()
        assert df[field].str.strip().ne("").all()
    assert df["DATA_SOURCE"].str.startswith("API ").all()


@pytest.mark.parametrize(
    "component_id,anchors",
    [
        (
            "RJ-21-75-BUOY",
            {
                "OD_IN": 21.0,
                "LENGTH_FT": 75.0,
                "BUOYANCY_OD_IN": 49.0,
                "PRESSURE_RATING_PSI": 5000.0,
                "DATA_SOURCE": "API 16R",
            },
        ),
        (
            "BOP-SUB-18.75-20K",
            {
                "BOP_TYPE": "subsea",
                "BORE_SIZE_IN": 18.75,
                "HEIGHT_FT": 38.0,
                "ANNULAR_COUNT": 1,
                "SHEAR_RAM_COUNT": 2,
                "PIPE_RAM_COUNT": 3,
                "CASING_SHEAR_RAM": True,
                "DATA_SOURCE": "API 16A / API 53",
            },
        ),
        (
            "LMRP-18.75-15K",
            {
                "BORE_SIZE_IN": 18.75,
                "HEIGHT_FT": 18.0,
                "ANNULAR_COUNT": 1,
                "CONNECTOR_TYPE": "H-4 collet",
                "DATA_SOURCE": "API 16R / API 53",
            },
        ),
        (
            "TJ-21-50",
            {
                "STROKE_FT": 50.0,
                "OUTER_BARREL_LENGTH_FT": 65.0,
                "INNER_BARREL_LENGTH_FT": 45.0,
                "DATA_SOURCE": "API 16R",
            },
        ),
        (
            "FJ-UPPER-21",
            {
                "MAX_ANGLE_DEG": 10.0,
                "STIFFNESS_FT_KIP_PER_DEG": 15.0,
                "POSITION": "upper",
                "DATA_SOURCE": "API 16R",
            },
        ),
        (
            "FJ-LOWER-21",
            {
                "MAX_ANGLE_DEG": 10.0,
                "STIFFNESS_FT_KIP_PER_DEG": 20.0,
                "POSITION": "lower",
                "DATA_SOURCE": "API 16R",
            },
        ),
        (
            "FJ-UPPER-18.75",
            {
                "MAX_ANGLE_DEG": 10.0,
                "STIFFNESS_FT_KIP_PER_DEG": 12.0,
                "POSITION": "upper",
                "DATA_SOURCE": "API 16R",
            },
        ),
        (
            "FJ-LOWER-18.75",
            {
                "MAX_ANGLE_DEG": 10.0,
                "STIFFNESS_FT_KIP_PER_DEG": 18.0,
                "POSITION": "lower",
                "DATA_SOURCE": "API 16R",
            },
        ),
    ],
)
def test_type_specific_anchors(component_id: str, anchors: dict):
    row = DrillingRiserLoader().get_by_id(component_id)
    assert row is not None
    for field, expected in anchors.items():
        assert row[field] == expected, (component_id, field)
    if component_id.startswith("FJ-"):
        assert pd.isna(row["CASING_SHEAR_RAM"])
    if component_id.startswith("TJ-"):
        assert pd.isna(row["POSITION"])


@pytest.mark.parametrize(
    "kind,empty_columns,numeric_columns",
    [
        ("riser_joint", slice(15, 29), ["OD_IN", "LENGTH_FT"]),
        ("bop", slice(22, 29), ["BORE_SIZE_IN", "HEIGHT_FT", "PIPE_RAM_COUNT"]),
        ("lmrp", slice(19, 28), ["BORE_SIZE_IN", "HEIGHT_FT", "ANNULAR_COUNT"]),
        (
            "telescopic_joint",
            slice(15, 25),
            ["STROKE_FT", "OUTER_BARREL_LENGTH_FT", "INNER_BARREL_LENGTH_FT"],
        ),
        ("flex_joint", slice(15, 22), ["MAX_ANGLE_DEG", "STIFFNESS_FT_KIP_PER_DEG"]),
    ],
)
def test_every_row_follows_type_layout(kind, empty_columns, numeric_columns):
    df = DrillingRiserLoader().get_by_type(kind)
    assert not df.empty
    assert df.iloc[:, empty_columns].isna().all().all()
    for field in numeric_columns:
        assert pd.to_numeric(df[field], errors="raise").gt(0).all()
    if kind == "lmrp":
        assert df["CONNECTOR_TYPE"].isin(["H-4 collet", "mandrel"]).all()
    if kind == "flex_joint":
        assert df["POSITION"].isin(["upper", "lower"]).all()
        assert df.iloc[:, 25:29].isna().all().all()


@pytest.mark.parametrize(
    "content,line_number",
    [
        ('"unterminated\n', 1),
        ('COMPONENT_ID,DATA_SOURCE,NOTES\nA,public,"unterminated\n', 2),
    ],
)
def test_malformed_quotes_raise_value_error(tmp_path, content, line_number):
    (tmp_path / CSV_NAME).write_text(content)
    with pytest.raises(ValueError, match=rf"Malformed CSV at line {line_number}"):
        DrillingRiserLoader(tmp_path).load()
