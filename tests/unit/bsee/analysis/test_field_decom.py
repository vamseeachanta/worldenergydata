"""Unit tests for the per-field decommissioning liability view
(:mod:`field_decom`).

All fixtures are synthetic (``tmp_path``) and deterministic — they never read
the multi-GB materialized OGOR-A data nor the real decom totals bin.  The OGOR
fixture deliberately mimics the real on-disk *header-corruption* (a
``read_csv`` consumed the first data record as the column header, losing that
physical row), reusing the pattern from
``tests/unit/bsee/data/test_ogor_production_loader.py`` so the loader path
under test matches production behaviour.

These are BSEE-provided P50/P70/P90 abandonment cost estimates (USD) summed
across cost-category rows per lease, rolled up to field via the OGOR-A
lease->field crosswalk.  Nothing is fabricated: leases that do not map to a
producing field are dropped (and logged), never forced.
"""

import pickle
from pathlib import Path

import pandas as pd
import pytest

from tests.test_markers import unit
from worldenergydata.bsee.analysis.field_decom import (
    apply_field_decom,
    build_field_decom_liability,
    build_lease_to_field,
    load_decom_totals,
)
from worldenergydata.bsee.data.sources.bin.ogor_production_loader import (
    OGOR_COLUMN_NAMES,
)

DECOM_COLUMNS = [
    "AUTH_TYPE_CODE",
    "AUTH_NUMBER",
    "TYPE",
    "CNT",
    "P50_COST",
    "P70_COST",
    "P90_COST",
    "DTR_COST",
]


def _decom_row(auth, type_, p50, p70, p90, auth_type="LSE", cnt=1):
    return [auth_type, auth, type_, cnt, p50, p70, p90, 0]


def _write_decom_bin(path: Path, rows) -> None:
    """Write a synthetic mv_decom_cost_totals pickle (proper headers)."""
    df = pd.DataFrame(rows, columns=DECOM_COLUMNS)
    with open(path, "wb") as f:
        pickle.dump(df, f)


def _ogor_row(lease, field, oil=1000.0, yyyymm=202401):
    """One OGOR-A record in canonical column order with the given knobs."""
    return [
        lease,  # LEASE_NUMBER
        "E001",  # COMPLETION_NAME
        yyyymm,  # PRODUCTION_DATE (YYYYMM int)
        30,  # DAYS_ON_PROD
        "O",  # PRODUCT_CODE
        oil,  # MON_O_PROD_VOL
        5000.0,  # MON_G_PROD_VOL
        200.0,  # MON_WTR_PROD_VOL
        "608054010300",  # API_WELL_NUMBER
        "PR",  # WELL_STAT_CD
        "MC0807",  # AREA_CODE_BLOCK_NUM
        "03151",  # OPERATOR_NUM
        "OPERATOR",  # SORT_NAME
        field,  # BOEM_FIELD
        0.0,  # INJECTION_VOLUME
        "Q01",  # PROD_INTERVAL_CD
        20100101,  # FIRST_PROD_DATE
        "",  # UNIT_AGT_NUMBER
        "",  # UNIT_ALOC_SUFFIX
    ]


def _write_corrupted_ogor_bin(path: Path, rows) -> None:
    """Write a header-corrupted OGOR pickle (loses the first physical row).

    Mirrors ``tests/unit/bsee/data/test_ogor_production_loader.py``: the
    pickled frame's *columns* are the first record's values and that record
    is dropped, exactly as the real corrupted ``.bin`` files were produced.
    """
    full = pd.DataFrame(rows, columns=OGOR_COLUMN_NAMES)
    corrupted = pd.DataFrame(full.iloc[1:].values, columns=list(full.iloc[0].values))
    with open(path, "wb") as f:
        pickle.dump(corrupted, f)


# --------------------------------------------------------------------------
# load_decom_totals
# --------------------------------------------------------------------------
@unit
def test_load_decom_totals_missing_file_returns_empty(tmp_path):
    df = load_decom_totals(data_dir=tmp_path)
    assert df.empty
    assert {"AUTH_NUMBER", "TYPE", "P50_COST", "P70_COST", "P90_COST"} <= set(
        df.columns
    )


@unit
def test_load_decom_totals_lfs_stub_returns_empty(tmp_path):
    f = tmp_path / "mv_decom_cost_totals.bin"
    f.write_bytes(b"version https://git-lfs.github.com/spec/v1\noid sha256:abc\n")
    df = load_decom_totals(data_dir=tmp_path)
    assert df.empty


@unit
def test_load_decom_totals_coerces_costs_numeric(tmp_path):
    rows = [
        _decom_row("G100", "Wells Decom Cost", "1000", "1500", "2000"),
        _decom_row("G100", "Platforms Decom Cost", 500, 700, 900),
        _decom_row("G100", "Bad Cost", "not-a-number", "", None),
    ]
    f = tmp_path / "mv_decom_cost_totals.bin"
    _write_decom_bin(f, rows)
    df = load_decom_totals(data_dir=tmp_path)
    assert len(df) == 3
    # Strings coerced to numbers; non-numeric -> 0 (NaN->0).
    assert df["P50_COST"].sum() == pytest.approx(1500.0)
    assert df["P70_COST"].sum() == pytest.approx(2200.0)
    assert df["P90_COST"].sum() == pytest.approx(2900.0)


# --------------------------------------------------------------------------
# build_lease_to_field
# --------------------------------------------------------------------------
@unit
def test_build_lease_to_field_dominant_mapping_and_normalization(tmp_path):
    """Lease maps to the field with the most rows; lease formats normalized."""
    rows = [
        _ogor_row("DUMMY", "DUMMY"),  # lost to corruption
        # Lease with a leading-space shelf format -> normalizes to "00016".
        _ogor_row(" 00016", "SHELF1"),
        _ogor_row(" 00016", "SHELF1"),
        _ogor_row(" 00016", "SHELF2"),  # SHELF1 dominates (2 vs 1)
        # Clean deepwater lease.
        _ogor_row("G23740", "DEEP1"),
    ]
    f = tmp_path / "ogora2024delimit.bin"
    _write_corrupted_ogor_bin(f, rows)

    mapping = build_lease_to_field(data_dir=tmp_path, start_year=2024, end_year=2024)
    # Normalized key (no leading space) maps to the dominant field.
    assert mapping["00016"] == "SHELF1"
    assert mapping["G23740"] == "DEEP1"
    # Keys are normalized (no leading-space variant survives).
    assert " 00016" not in mapping


@unit
def test_build_lease_to_field_empty_when_no_data(tmp_path):
    mapping = build_lease_to_field(data_dir=tmp_path, start_year=2024, end_year=2024)
    assert mapping == {}


# --------------------------------------------------------------------------
# build_field_decom_liability
# --------------------------------------------------------------------------
@unit
def test_build_field_decom_liability_rollup(tmp_path):
    """Per-lease sum across TYPE rows, lease->field map, field rollup /1e6."""
    decom_rows = [
        # Lease G100 -> two TYPE rows, summed per lease.
        _decom_row("G100", "Wells Decom Cost", 1_000_000, 1_500_000, 2_000_000),
        _decom_row("G100", "Platforms Decom Cost", 500_000, 700_000, 900_000),
        # Lease 00016 (shelf) -> one TYPE row.
        _decom_row("00016", "Wells Decom Cost", 250_000, 300_000, 400_000),
        # Lease G999 -> not in OGOR crosswalk -> dropped + logged.
        _decom_row("G999", "Wells Decom Cost", 9_000_000, 9_000_000, 9_000_000),
    ]
    decom_f = tmp_path / "mv_decom_cost_totals.bin"
    _write_decom_bin(decom_f, decom_rows)

    ogor_rows = [
        _ogor_row("DUMMY", "DUMMY"),  # lost to corruption
        _ogor_row("G100", "FIELDA"),
        _ogor_row("G100", "FIELDA"),
        # Leading-space lease format normalizes to "00016".
        _ogor_row(" 00016", "FIELDA"),
        _ogor_row("G200", "FIELDB"),
    ]
    ogor_dir = tmp_path / "ogor"
    ogor_dir.mkdir()
    _write_corrupted_ogor_bin(ogor_dir / "ogora2024delimit.bin", ogor_rows)

    df = build_field_decom_liability(
        data_dir=tmp_path,
        ogor_dir=ogor_dir,
        start_year=2024,
        end_year=2024,
    )
    assert list(df.columns) == [
        "FIELD_NAME_CODE",
        "DECOM_P50_MM_USD",
        "DECOM_P70_MM_USD",
        "DECOM_P90_MM_USD",
    ]
    by_field = df.set_index("FIELD_NAME_CODE")
    # FIELDA = G100 (1.0M+0.5M=1.5M P50) + 00016 (0.25M P50) = 1.75M -> 1.75 MM
    assert by_field.loc["FIELDA", "DECOM_P50_MM_USD"] == pytest.approx(1.75)
    # P70: (1.5M+0.7M) + 0.3M = 2.5M -> 2.5 MM
    assert by_field.loc["FIELDA", "DECOM_P70_MM_USD"] == pytest.approx(2.5)
    # P90: (2.0M+0.9M) + 0.4M = 3.3M -> 3.3 MM
    assert by_field.loc["FIELDA", "DECOM_P90_MM_USD"] == pytest.approx(3.3)
    # G999 is unmapped -> dropped, not present anywhere.
    assert "FIELDB" not in by_field.index  # FIELDB had no decom lease either
    assert by_field["DECOM_P50_MM_USD"].sum() == pytest.approx(1.75)


@unit
def test_build_field_decom_liability_drops_unmapped_lease(tmp_path):
    """A decom lease with no producing field is dropped (honest coverage)."""
    decom_rows = [
        _decom_row("G100", "Wells Decom Cost", 1_000_000, 1_000_000, 1_000_000),
        _decom_row("ROWXYZ", "Pipelines Decom Cost", 5_000_000, 5_000_000, 5_000_000),
    ]
    decom_f = tmp_path / "mv_decom_cost_totals.bin"
    _write_decom_bin(decom_f, decom_rows)

    ogor_rows = [
        _ogor_row("DUMMY", "DUMMY"),
        _ogor_row("G100", "FIELDA"),
    ]
    ogor_dir = tmp_path / "ogor"
    ogor_dir.mkdir()
    _write_corrupted_ogor_bin(ogor_dir / "ogora2024delimit.bin", ogor_rows)

    df = build_field_decom_liability(
        data_dir=tmp_path,
        ogor_dir=ogor_dir,
        start_year=2024,
        end_year=2024,
    )
    # Only FIELDA survives; ROWXYZ pipeline lease is dropped.
    assert set(df["FIELD_NAME_CODE"]) == {"FIELDA"}
    assert df["DECOM_P50_MM_USD"].sum() == pytest.approx(1.0)


@unit
def test_build_field_decom_liability_empty_when_no_decom_file(tmp_path):
    ogor_dir = tmp_path / "ogor"
    ogor_dir.mkdir()
    df = build_field_decom_liability(
        data_dir=tmp_path,
        ogor_dir=ogor_dir,
        start_year=2024,
        end_year=2024,
    )
    assert df.empty
    assert list(df.columns) == [
        "FIELD_NAME_CODE",
        "DECOM_P50_MM_USD",
        "DECOM_P70_MM_USD",
        "DECOM_P90_MM_USD",
    ]


# --------------------------------------------------------------------------
# apply_field_decom
# --------------------------------------------------------------------------
@unit
def test_apply_field_decom_left_join_on_field_code():
    """Decom is merged on FIELD_CODE; unmatched fields stay null (honest)."""
    result = pd.DataFrame(
        {
            "FIELD_CODE": ["FIELDA", "FIELDB", "VK999"],
            "CUM_OIL_MMBBL": [1000.0, 50.0, 1.0],
        }
    )
    decom = pd.DataFrame(
        {
            "FIELD_NAME_CODE": ["FIELDA", "FIELDB"],
            "DECOM_P50_MM_USD": [1.75, 0.5],
            "DECOM_P70_MM_USD": [2.5, 0.7],
            "DECOM_P90_MM_USD": [3.3, 0.9],
        }
    )
    out = apply_field_decom(result, decom)
    for col in ("DECOM_P50_MM_USD", "DECOM_P70_MM_USD", "DECOM_P90_MM_USD"):
        assert col in out.columns
    by_code = out.set_index("FIELD_CODE")
    assert by_code.loc["FIELDA", "DECOM_P50_MM_USD"] == pytest.approx(1.75)
    assert by_code.loc["FIELDB", "DECOM_P90_MM_USD"] == pytest.approx(0.9)
    # VK999 has no decom row -> honest null, not zero.
    assert pd.isna(by_code.loc["VK999", "DECOM_P50_MM_USD"])
    # Original is not mutated.
    assert "DECOM_P50_MM_USD" not in result.columns


@unit
def test_apply_field_decom_handles_empty():
    empty_result = pd.DataFrame(columns=["FIELD_CODE", "CUM_OIL_MMBBL"])
    decom = pd.DataFrame(
        {
            "FIELD_NAME_CODE": ["FIELDA"],
            "DECOM_P50_MM_USD": [1.0],
            "DECOM_P70_MM_USD": [1.0],
            "DECOM_P90_MM_USD": [1.0],
        }
    )
    out = apply_field_decom(empty_result, decom)
    assert out.empty
    assert "DECOM_P50_MM_USD" in out.columns

    # Empty decom against a real result -> columns present, all null.
    result = pd.DataFrame({"FIELD_CODE": ["FIELDA"], "CUM_OIL_MMBBL": [1.0]})
    empty_decom = pd.DataFrame(
        columns=[
            "FIELD_NAME_CODE",
            "DECOM_P50_MM_USD",
            "DECOM_P70_MM_USD",
            "DECOM_P90_MM_USD",
        ]
    )
    out2 = apply_field_decom(result, empty_decom)
    assert "DECOM_P50_MM_USD" in out2.columns
    assert pd.isna(out2["DECOM_P50_MM_USD"].iloc[0])
