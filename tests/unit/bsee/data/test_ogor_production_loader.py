"""Unit tests for the OGOR-A ``.bin`` production loader.

Uses a synthetic *header-corrupted* pickle fixture (never the 3.5 GB real
data) so the tests are deterministic and run anywhere, including CI without
the materialized data mount.
"""

import pickle
from pathlib import Path

import pandas as pd
import pytest

from tests.test_markers import unit
from worldenergydata.bsee.analysis.all_fields_runner import AllFieldsRunner
from worldenergydata.bsee.data.sources.bin.ogor_production_loader import (
    OGOR_COLUMN_NAMES,
    load_all_fields_production,
    load_ogor_bin,
    to_runner_schema,
)


def _canonical_rows():
    """Two production records in canonical OGOR-A column order."""
    return [
        # lease, comp, YYYYMM, days, prod, oil, gas, wtr, api, stat,
        # block, opnum, sortname, BOEM_FIELD, inj, interval, firstprod, unit, suffix
        [
            "G12345",
            "E001",
            202401,
            30,
            "O",
            1000.0,
            5000.0,
            200.0,
            "608054010300",
            "PR",
            "MC0807",
            "03151",
            "BP",
            "MC807",
            0.0,
            "Q01",
            20100101,
            "",
            "",
        ],
        [
            "G12345",
            "E002",
            202402,
            28,
            "O",
            2_000_000.0,
            6000.0,
            250.0,
            "608054010301",
            "PR",
            "MC0807",
            "03151",
            "BP",
            "MC807",
            0.0,
            "Q01",
            20100101,
            "",
            "",
        ],
    ]


def _write_corrupted_bin(path: Path, rows=None) -> None:
    """Write a header-corrupted OGOR pickle.

    Mimics the real on-disk artefact: a ``read_csv`` consumed the first data
    record as the header, so the pickled frame's *columns* are that first
    record's values and the frame is missing that first physical row.
    """
    if rows is None:
        rows = _canonical_rows()
    full = pd.DataFrame(rows, columns=OGOR_COLUMN_NAMES)
    corrupted = pd.DataFrame(full.iloc[1:].values, columns=list(full.iloc[0].values))
    with open(path, "wb") as f:
        pickle.dump(corrupted, f)


@unit
def test_load_ogor_bin_relabels_columns(tmp_path):
    """load_ogor_bin restores the canonical 19-column schema."""
    f = tmp_path / "ogora2024delimit.bin"
    _write_corrupted_bin(f)

    df = load_ogor_bin(f)

    assert list(df.columns) == OGOR_COLUMN_NAMES
    # One row survives (row0 lost to source header-corruption — documented).
    assert len(df) == 1
    assert df.iloc[0]["BOEM_FIELD"] == "MC807"
    assert df.iloc[0]["API_WELL_NUMBER"] == "608054010301"


@unit
def test_load_ogor_bin_missing_file_returns_empty(tmp_path):
    df = load_ogor_bin(tmp_path / "nope.bin")
    assert df.empty
    assert list(df.columns) == OGOR_COLUMN_NAMES


@unit
def test_load_ogor_bin_wrong_column_count_skipped(tmp_path):
    f = tmp_path / "bad.bin"
    with open(f, "wb") as fh:
        pickle.dump(pd.DataFrame({"a": [1], "b": [2]}), fh)
    df = load_ogor_bin(f)
    assert df.empty


@unit
def test_to_runner_schema_maps_and_types():
    raw = pd.DataFrame(_canonical_rows(), columns=OGOR_COLUMN_NAMES)
    out = to_runner_schema(raw)

    assert list(out.columns) == [
        "FIELD_NAME_CODE",
        "LEASE_NUMBER",
        "API_WELL_NUMBER",
        "PROD_YEAR",
        "MON_O_PROD_VOL",
        "MON_G_PROD_VOL",
        "MON_WTR_PROD_VOL",
        "DAYS_ON_PROD",
    ]
    assert out.iloc[0]["FIELD_NAME_CODE"] == "MC807"  # from BOEM_FIELD
    assert out.iloc[0]["PROD_YEAR"] == 2024  # from 202401
    assert out["MON_O_PROD_VOL"].sum() == pytest.approx(2_001_000.0)


@unit
def test_to_runner_schema_empty():
    out = to_runner_schema(pd.DataFrame())
    assert out.empty
    assert "FIELD_NAME_CODE" in out.columns


@unit
def test_to_runner_schema_strips_quotes_and_whitespace():
    rows = [
        [
            '" G99 "',
            "E",
            202012,
            31,
            "O",
            10.0,
            0.0,
            0.0,
            " 60805 ",
            "PR",
            "B",
            "1",
            "OP",
            " GC640 ",
            0.0,
            "Q",
            0,
            "",
            "",
        ]
    ]
    out = to_runner_schema(pd.DataFrame(rows, columns=OGOR_COLUMN_NAMES))
    assert out.iloc[0]["FIELD_NAME_CODE"] == "GC640"
    assert out.iloc[0]["LEASE_NUMBER"] == "G99"
    assert out.iloc[0]["API_WELL_NUMBER"] == "60805"


@unit
def test_load_all_fields_production_concats_year_range(tmp_path):
    _write_corrupted_bin(tmp_path / "ogora2023delimit.bin")
    _write_corrupted_bin(tmp_path / "ogora2024delimit.bin")

    df = load_all_fields_production(data_dir=tmp_path, start_year=2023, end_year=2024)

    # 1 surviving row per file x 2 files
    assert len(df) == 2
    assert set(df["FIELD_NAME_CODE"]) == {"MC807"}


@unit
def test_load_all_fields_production_no_files(tmp_path):
    df = load_all_fields_production(data_dir=tmp_path, start_year=2023, end_year=2024)
    assert df.empty
    assert "FIELD_NAME_CODE" in df.columns


@unit
def test_end_to_end_feeds_all_fields_runner(tmp_path):
    """Loader output is consumable by AllFieldsRunner without adaptation."""
    _write_corrupted_bin(tmp_path / "ogora2024delimit.bin")
    prod = load_all_fields_production(data_dir=tmp_path, start_year=2024, end_year=2024)

    class _StubResolver:
        def resolve(self, code):
            return {"MC807": "Thunder Horse"}.get(code, code)

    class _StubEra:
        def classify_field(self, apis):
            return "Miocene"

    result = AllFieldsRunner(_StubResolver(), _StubEra()).run(prod)

    assert len(result) == 1
    row = result.iloc[0]
    assert row["FIELD_CODE"] == "MC807"
    assert row["FIELD_NAME"] == "Thunder Horse"
    assert row["GEOLOGICAL_ERA"] == "Miocene"
    # Only the second canonical row survives the header-corruption (2.0 MMbbl).
    assert row["CUM_OIL_MMBBL"] == pytest.approx(2.0, rel=1e-6)
