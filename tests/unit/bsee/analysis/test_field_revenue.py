"""Unit tests for the gross oil revenue atlas (:mod:`field_revenue`).

All fixtures are synthetic (``tmp_path``) and deterministic — they never read
the multi-GB materialized OGOR-A data.  The OGOR fixture deliberately mimics
the real on-disk *header-corruption* (a ``read_csv`` consumed the first data
record as the column header, losing that physical row) so the loader path
under test matches production behaviour.
"""

import pickle
from pathlib import Path

import pandas as pd
import pytest

from tests.test_markers import unit
from worldenergydata.bsee.analysis.field_revenue import (
    apply_field_revenue,
    build_field_oil_revenue,
    load_wti_monthly,
)
from worldenergydata.bsee.data.sources.bin.ogor_production_loader import (
    OGOR_COLUMN_NAMES,
)


def _ogor_row(yyyymm, oil, field):
    """One OGOR-A record in canonical column order with the given knobs."""
    return [
        "G12345",  # LEASE_NUMBER
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
        "BP",  # SORT_NAME
        field,  # BOEM_FIELD
        0.0,  # INJECTION_VOLUME
        "Q01",  # PROD_INTERVAL_CD
        20100101,  # FIRST_PROD_DATE
        "",  # UNIT_AGT_NUMBER
        "",  # UNIT_ALOC_SUFFIX
    ]


def _write_corrupted_bin(path: Path, rows) -> None:
    """Write a header-corrupted OGOR pickle (loses the first physical row).

    Mirrors ``tests/unit/bsee/data/test_ogor_production_loader.py``: the
    pickled frame's *columns* are the first record's values and that record
    is dropped, exactly as the real corrupted ``.bin`` files were produced.
    """
    full = pd.DataFrame(rows, columns=OGOR_COLUMN_NAMES)
    corrupted = pd.DataFrame(full.iloc[1:].values, columns=list(full.iloc[0].values))
    with open(path, "wb") as f:
        pickle.dump(corrupted, f)


@unit
def test_load_wti_monthly_missing_file_returns_empty(tmp_path):
    assert load_wti_monthly(tmp_path / "nope.xlsx") == {}


@unit
def test_load_wti_monthly_reads_real_deck():
    """The committed FDAS_V30 WTI deck loads to a YYYYMM->price map."""
    wti = load_wti_monthly()
    assert isinstance(wti, dict)
    # Real deck spans 1986-01..2025-07.
    assert wti[198601] == pytest.approx(22.93)
    assert wti[202507] == pytest.approx(68.39)
    assert all(isinstance(k, int) for k in wti)


@unit
def test_build_field_oil_revenue_with_explicit_wti(tmp_path):
    """End-to-end with a synthetic WTI deck exercises the join + sum."""
    rows = [
        _ogor_row(202401, 0.0, "DUMMY"),  # lost to corruption
        _ogor_row(202401, 1000.0, "MC807"),
        _ogor_row(202402, 2000.0, "MC807"),
        _ogor_row(202401, 500.0, "GC640"),
    ]
    f = tmp_path / "ogora2024delimit.bin"
    _write_corrupted_bin(f, rows)

    wti_xlsx = tmp_path / "wti.xlsx"
    pd.DataFrame(
        {
            "Month": pd.to_datetime(["2024-01-01", "2024-02-01"]),
            "WTI_USD": [70.0, 80.0],
        }
    ).to_excel(wti_xlsx, index=False)

    df = build_field_oil_revenue(
        data_dir=tmp_path, wti_path=wti_xlsx, start_year=2024, end_year=2024
    )
    rev = dict(zip(df["FIELD_NAME_CODE"], df["GROSS_OIL_REVENUE_MM_USD"]))
    # MC807: 1000*70 + 2000*80 = 230000 -> 0.23 MM
    assert rev["MC807"] == pytest.approx(0.23)
    # GC640: 500*70 = 35000 -> 0.035 MM
    assert rev["GC640"] == pytest.approx(0.035)


@unit
def test_build_field_oil_revenue_drops_months_missing_from_wti(tmp_path):
    """Rows whose YYYYMM is absent from the WTI deck are dropped, not faked."""
    rows = [
        _ogor_row(202401, 0.0, "DUMMY"),  # lost to corruption
        _ogor_row(202401, 1000.0, "MC807"),  # priced
        _ogor_row(202403, 9999.0, "MC807"),  # 2024-03 missing from deck
    ]
    f = tmp_path / "ogora2024delimit.bin"
    _write_corrupted_bin(f, rows)

    wti_xlsx = tmp_path / "wti.xlsx"
    pd.DataFrame({"Month": pd.to_datetime(["2024-01-01"]), "WTI_USD": [70.0]}).to_excel(
        wti_xlsx, index=False
    )

    df = build_field_oil_revenue(
        data_dir=tmp_path, wti_path=wti_xlsx, start_year=2024, end_year=2024
    )
    rev = dict(zip(df["FIELD_NAME_CODE"], df["GROSS_OIL_REVENUE_MM_USD"]))
    # Only the priced January row counts: 1000*70 = 70000 -> 0.07 MM.
    assert rev["MC807"] == pytest.approx(0.07)


@unit
def test_build_field_oil_revenue_empty_when_no_data(tmp_path):
    df = build_field_oil_revenue(
        data_dir=tmp_path, wti_path=None, start_year=2024, end_year=2024
    )
    assert df.empty
    assert list(df.columns) == ["FIELD_NAME_CODE", "GROSS_OIL_REVENUE_MM_USD"]


@unit
def test_apply_field_revenue_left_join_on_field_code():
    """Revenue is merged on FIELD_CODE; unmatched fields stay null (honest)."""
    result = pd.DataFrame(
        {
            "FIELD_CODE": ["MC807", "GC640", "VK999"],
            "CUM_OIL_MMBBL": [1000.0, 50.0, 1.0],
        }
    )
    revenue = pd.DataFrame(
        {
            "FIELD_NAME_CODE": ["MC807", "GC640"],
            "GROSS_OIL_REVENUE_MM_USD": [50000.0, 1200.0],
        }
    )
    out = apply_field_revenue(result, revenue)
    assert "GROSS_OIL_REVENUE_MM_USD" in out.columns
    by_code = dict(zip(out["FIELD_CODE"], out["GROSS_OIL_REVENUE_MM_USD"]))
    assert by_code["MC807"] == pytest.approx(50000.0)
    assert by_code["GC640"] == pytest.approx(1200.0)
    # VK999 has no revenue row -> honest null, not zero.
    assert pd.isna(by_code["VK999"])
    # Original is not mutated.
    assert "GROSS_OIL_REVENUE_MM_USD" not in result.columns


@unit
def test_apply_field_revenue_handles_empty():
    empty_result = pd.DataFrame(columns=["FIELD_CODE", "CUM_OIL_MMBBL"])
    revenue = pd.DataFrame(
        {"FIELD_NAME_CODE": ["MC807"], "GROSS_OIL_REVENUE_MM_USD": [1.0]}
    )
    out = apply_field_revenue(empty_result, revenue)
    assert out.empty
    assert "GROSS_OIL_REVENUE_MM_USD" in out.columns

    # Empty revenue against a real result -> column present, all null.
    result = pd.DataFrame({"FIELD_CODE": ["MC807"], "CUM_OIL_MMBBL": [1.0]})
    empty_rev = pd.DataFrame(columns=["FIELD_NAME_CODE", "GROSS_OIL_REVENUE_MM_USD"])
    out2 = apply_field_revenue(result, empty_rev)
    assert "GROSS_OIL_REVENUE_MM_USD" in out2.columns
    assert pd.isna(out2["GROSS_OIL_REVENUE_MM_USD"].iloc[0])
