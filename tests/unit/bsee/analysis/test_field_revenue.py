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
    MCF_TO_MMBTU,
    apply_field_gas_revenue,
    apply_field_revenue,
    build_field_gas_revenue,
    build_field_oil_revenue,
    load_hh_monthly,
    load_wti_monthly,
)
from worldenergydata.bsee.data.sources.bin.ogor_production_loader import (
    OGOR_COLUMN_NAMES,
)


def _ogor_row(yyyymm, oil, field, gas=5000.0):
    """One OGOR-A record in canonical column order with the given knobs."""
    return [
        "G12345",  # LEASE_NUMBER
        "E001",  # COMPLETION_NAME
        yyyymm,  # PRODUCTION_DATE (YYYYMM int)
        30,  # DAYS_ON_PROD
        "O",  # PRODUCT_CODE
        oil,  # MON_O_PROD_VOL
        gas,  # MON_G_PROD_VOL
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


# --------------------------------------------------------------------------- #
# Gas revenue (Henry Hub x 1.037 MMBtu/Mcf)                                    #
# --------------------------------------------------------------------------- #


@unit
def test_constant_mcf_to_mmbtu():
    """The heat-content conversion is the documented EIA average."""
    assert MCF_TO_MMBTU == pytest.approx(1.037)


@unit
def test_load_hh_monthly_missing_file_returns_empty(tmp_path):
    assert load_hh_monthly(tmp_path / "nope.xlsx") == {}


@unit
def test_load_hh_monthly_reads_real_deck():
    """The committed FDAS_V30 Henry Hub deck loads to a YYYYMM->price map."""
    hh = load_hh_monthly()
    assert isinstance(hh, dict)
    # Real deck starts 1997-01.
    assert hh[199701] == pytest.approx(3.45)
    assert all(isinstance(k, int) for k in hh)


@unit
def test_build_field_gas_revenue_applies_heat_content(tmp_path):
    """Gas revenue = sum(gas * 1.037 * HH) / 1e6 per field."""
    rows = [
        _ogor_row(202401, 0.0, "DUMMY", gas=0.0),  # lost to corruption
        _ogor_row(202401, 0.0, "MC807", gas=1000.0),
        _ogor_row(202402, 0.0, "MC807", gas=2000.0),
        _ogor_row(202401, 0.0, "GC640", gas=500.0),
    ]
    f = tmp_path / "ogora2024delimit.bin"
    _write_corrupted_bin(f, rows)

    hh_xlsx = tmp_path / "hh.xlsx"
    pd.DataFrame(
        {
            "Month": pd.to_datetime(["2024-01-01", "2024-02-01"]),
            "HH_USD": [3.0, 4.0],
        }
    ).to_excel(hh_xlsx, index=False)

    df = build_field_gas_revenue(
        data_dir=tmp_path, hh_path=hh_xlsx, start_year=2024, end_year=2024
    )
    rev = dict(zip(df["FIELD_NAME_CODE"], df["GROSS_GAS_REVENUE_MM_USD"]))
    # MC807: (1000*1.037*3 + 2000*1.037*4)/1e6
    exp_mc = (1000 * 1.037 * 3 + 2000 * 1.037 * 4) / 1e6
    assert rev["MC807"] == pytest.approx(exp_mc)
    # GC640: 500*1.037*3/1e6
    assert rev["GC640"] == pytest.approx(500 * 1.037 * 3 / 1e6)
    # Sanity: without the 1.037 factor the value would differ.
    assert rev["MC807"] != pytest.approx((1000 * 3 + 2000 * 4) / 1e6)


@unit
def test_build_field_gas_revenue_drops_predeck_months(tmp_path):
    """Months absent from the HH deck (e.g. pre-1997) are dropped, not faked."""
    f = tmp_path / "ogora1996delimit.bin"
    _write_corrupted_bin(
        f,
        [
            _ogor_row(199601, 0.0, "DUMMY", gas=0.0),  # lost to corruption
            _ogor_row(199601, 0.0, "MC807", gas=9999.0),  # pre-deck -> dropped
        ],
    )
    g = tmp_path / "ogora1997delimit.bin"
    _write_corrupted_bin(
        g,
        [
            _ogor_row(199701, 0.0, "DUMMY", gas=0.0),  # lost to corruption
            _ogor_row(199701, 0.0, "MC807", gas=1000.0),  # priced
        ],
    )

    hh_xlsx = tmp_path / "hh.xlsx"
    pd.DataFrame({"Month": pd.to_datetime(["1997-01-01"]), "HH_USD": [3.0]}).to_excel(
        hh_xlsx, index=False
    )

    df = build_field_gas_revenue(
        data_dir=tmp_path, hh_path=hh_xlsx, start_year=1996, end_year=1997
    )
    rev = dict(zip(df["FIELD_NAME_CODE"], df["GROSS_GAS_REVENUE_MM_USD"]))
    # Only the priced 1997 row counts (1000*1.037*3/1e6); 1996 row dropped.
    assert rev["MC807"] == pytest.approx(1000 * 1.037 * 3 / 1e6)


@unit
def test_build_field_gas_revenue_empty_when_no_deck(tmp_path):
    df = build_field_gas_revenue(
        data_dir=tmp_path,
        hh_path=tmp_path / "nope.xlsx",
        start_year=2024,
        end_year=2024,
    )
    assert df.empty
    assert list(df.columns) == ["FIELD_NAME_CODE", "GROSS_GAS_REVENUE_MM_USD"]


@unit
def test_apply_field_gas_revenue_adds_gas_and_total():
    """Gas column + derived total follow the documented total rule."""
    # VK999 has oil but no gas -> total = oil + 0. ZZ111 has no oil -> NaN.
    result = pd.DataFrame(
        {
            "FIELD_CODE": ["MC807", "GC640", "VK999", "ZZ111"],
            "GROSS_OIL_REVENUE_MM_USD": [100.0, 50.0, 10.0, pd.NA],
        }
    )
    gas = pd.DataFrame(
        {
            "FIELD_NAME_CODE": ["MC807", "GC640", "ZZ111"],
            "GROSS_GAS_REVENUE_MM_USD": [20.0, 5.0, 7.0],
        }
    )
    out = apply_field_gas_revenue(result, gas)
    assert "GROSS_GAS_REVENUE_MM_USD" in out.columns
    assert "GROSS_TOTAL_REVENUE_MM_USD" in out.columns
    by_code = out.set_index("FIELD_CODE")
    # Oil + gas where both present.
    assert by_code.loc["MC807", "GROSS_TOTAL_REVENUE_MM_USD"] == pytest.approx(120.0)
    assert by_code.loc["GC640", "GROSS_TOTAL_REVENUE_MM_USD"] == pytest.approx(55.0)
    # Oil present, gas missing -> gas treated as 0 in the total.
    assert pd.isna(by_code.loc["VK999", "GROSS_GAS_REVENUE_MM_USD"])
    assert by_code.loc["VK999", "GROSS_TOTAL_REVENUE_MM_USD"] == pytest.approx(10.0)
    # No oil -> total NaN even though gas exists.
    assert pd.isna(by_code.loc["ZZ111", "GROSS_TOTAL_REVENUE_MM_USD"])
    # Original not mutated.
    assert "GROSS_GAS_REVENUE_MM_USD" not in result.columns


@unit
def test_apply_field_gas_revenue_handles_empty_gas():
    """Empty gas frame -> gas column null, total = oil (gas treated as 0)."""
    result = pd.DataFrame(
        {"FIELD_CODE": ["MC807"], "GROSS_OIL_REVENUE_MM_USD": [100.0]}
    )
    empty_gas = pd.DataFrame(columns=["FIELD_NAME_CODE", "GROSS_GAS_REVENUE_MM_USD"])
    out = apply_field_gas_revenue(result, empty_gas)
    assert pd.isna(out["GROSS_GAS_REVENUE_MM_USD"].iloc[0])
    assert out["GROSS_TOTAL_REVENUE_MM_USD"].iloc[0] == pytest.approx(100.0)


@unit
def test_apply_field_gas_revenue_without_oil_column_warns():
    """If oil column absent, total is all-null (gas-only total not reported)."""
    result = pd.DataFrame({"FIELD_CODE": ["MC807"], "CUM_OIL_MMBBL": [1.0]})
    gas = pd.DataFrame(
        {"FIELD_NAME_CODE": ["MC807"], "GROSS_GAS_REVENUE_MM_USD": [20.0]}
    )
    out = apply_field_gas_revenue(result, gas)
    assert out["GROSS_GAS_REVENUE_MM_USD"].iloc[0] == pytest.approx(20.0)
    assert pd.isna(out["GROSS_TOTAL_REVENUE_MM_USD"].iloc[0])
