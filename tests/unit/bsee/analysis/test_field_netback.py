"""Unit tests for the per-field netback / break-even sensitivity.

All fixtures are pure synthetic DataFrames — no I/O, no materialized data.
The module under test (:mod:`field_netback`) is pure-derived from columns that
already live on the AllFieldsRunner+revenue result, so every expectation is an
exact arithmetic identity, not a tolerance against real data.

This is a *sensitivity*, not an NPV: we assert the opex *band* behaviour
(NETBACK_HIGH >= NETBACK_LOW), the royalty math, the realized price ratio, and
the break-even opex.  Missing inputs must produce honest ``NaN`` (never 0).
"""

import math

import numpy as np
import pandas as pd

from tests.test_markers import unit
from worldenergydata.bsee.analysis.field_netback import (
    OPEX_BAND_HIGH_USD_BBL,
    OPEX_BAND_LOW_USD_BBL,
    ROYALTY_RATE_DEFAULT,
    compute_field_netback,
)


def _base_df():
    """Two well-formed fields with known oil and revenue."""
    return pd.DataFrame(
        {
            "FIELD_CODE": ["MC807", "GC640"],
            "CUM_OIL_MMBBL": [1000.0, 100.0],
            "GROSS_OIL_REVENUE_MM_USD": [55000.0, 4000.0],
        }
    )


@unit
def test_realized_price_is_revenue_over_oil():
    out = compute_field_netback(_base_df())
    # both in millions -> ratio is $/bbl
    assert out.loc[0, "REALIZED_OIL_PRICE_USD_BBL"] == 55.0
    assert out.loc[1, "REALIZED_OIL_PRICE_USD_BBL"] == 40.0


@unit
def test_net_revenue_after_royalty_uses_default_rate():
    out = compute_field_netback(_base_df())
    # gross x (1 - 0.1875) == gross x 0.8125
    assert ROYALTY_RATE_DEFAULT == 0.1875
    assert out.loc[0, "NET_REVENUE_AFTER_ROYALTY_MM_USD"] == 55000.0 * 0.8125
    assert out.loc[1, "NET_REVENUE_AFTER_ROYALTY_MM_USD"] == 4000.0 * 0.8125


@unit
def test_opex_band_columns():
    out = compute_field_netback(_base_df())
    # MMBBL x $/bbl == $MM
    assert out.loc[0, "OPEX_LOW_MM_USD"] == OPEX_BAND_LOW_USD_BBL * 1000.0
    assert out.loc[0, "OPEX_HIGH_MM_USD"] == OPEX_BAND_HIGH_USD_BBL * 1000.0


@unit
def test_netback_high_uses_low_opex_and_is_ge_netback_low():
    out = compute_field_netback(_base_df())
    net = 55000.0 * 0.8125
    assert out.loc[0, "NETBACK_HIGH_MM_USD"] == net - OPEX_BAND_LOW_USD_BBL * 1000.0
    assert out.loc[0, "NETBACK_LOW_MM_USD"] == net - OPEX_BAND_HIGH_USD_BBL * 1000.0
    # low opex => high netback; band ordering must hold for every row
    assert (out["NETBACK_HIGH_MM_USD"] >= out["NETBACK_LOW_MM_USD"]).all()


@unit
def test_breakeven_opex_is_realized_times_one_minus_royalty():
    out = compute_field_netback(_base_df())
    # opex $/bbl at which netback == 0
    assert out.loc[0, "BREAKEVEN_OPEX_USD_BBL"] == 55.0 * (1 - 0.1875)
    assert out.loc[1, "BREAKEVEN_OPEX_USD_BBL"] == 40.0 * (1 - 0.1875)


@unit
def test_breakeven_zeros_netback_at_that_opex():
    """The break-even opex really is the opex where netback hits zero."""
    out = compute_field_netback(_base_df())
    be = out.loc[0, "BREAKEVEN_OPEX_USD_BBL"]
    at_be = compute_field_netback(_base_df(), opex_low=be, opex_high=be)
    assert math.isclose(at_be.loc[0, "NETBACK_HIGH_MM_USD"], 0.0, abs_tol=1e-6)
    assert math.isclose(at_be.loc[0, "NETBACK_LOW_MM_USD"], 0.0, abs_tol=1e-6)


@unit
def test_missing_revenue_yields_nan_not_zero():
    df = _base_df()
    df.loc[1, "GROSS_OIL_REVENUE_MM_USD"] = np.nan
    out = compute_field_netback(df)
    for col in (
        "REALIZED_OIL_PRICE_USD_BBL",
        "NET_REVENUE_AFTER_ROYALTY_MM_USD",
        "NETBACK_HIGH_MM_USD",
        "NETBACK_LOW_MM_USD",
        "BREAKEVEN_OPEX_USD_BBL",
    ):
        assert pd.isna(out.loc[1, col]), f"{col} should be NaN, not fabricated"
    # row 0 (well-formed) is unaffected
    assert out.loc[0, "REALIZED_OIL_PRICE_USD_BBL"] == 55.0


@unit
def test_zero_oil_yields_nan_not_zero_or_error():
    df = _base_df()
    df.loc[1, "CUM_OIL_MMBBL"] = 0.0
    out = compute_field_netback(df)
    assert pd.isna(out.loc[1, "REALIZED_OIL_PRICE_USD_BBL"])
    assert pd.isna(out.loc[1, "BREAKEVEN_OPEX_USD_BBL"])
    # opex columns depend only on oil -> 0 oil => 0 opex is correct, not fabricated
    assert out.loc[1, "OPEX_LOW_MM_USD"] == 0.0


@unit
def test_negative_oil_treated_as_missing():
    df = _base_df()
    df.loc[1, "CUM_OIL_MMBBL"] = -5.0
    out = compute_field_netback(df)
    assert pd.isna(out.loc[1, "REALIZED_OIL_PRICE_USD_BBL"])
    assert pd.isna(out.loc[1, "BREAKEVEN_OPEX_USD_BBL"])


@unit
def test_custom_royalty_and_opex_params_honored():
    out = compute_field_netback(_base_df(), royalty=0.25, opex_low=10.0, opex_high=30.0)
    assert out.loc[0, "NET_REVENUE_AFTER_ROYALTY_MM_USD"] == 55000.0 * 0.75
    assert out.loc[0, "OPEX_LOW_MM_USD"] == 10.0 * 1000.0
    assert out.loc[0, "OPEX_HIGH_MM_USD"] == 30.0 * 1000.0
    assert out.loc[0, "BREAKEVEN_OPEX_USD_BBL"] == 55.0 * 0.75


@unit
def test_input_not_mutated():
    df = _base_df()
    before = df.copy(deep=True)
    _ = compute_field_netback(df)
    pd.testing.assert_frame_equal(df, before)
    # derived columns must not have leaked onto the input
    assert "NETBACK_HIGH_MM_USD" not in df.columns


@unit
def test_empty_df_handled():
    df = pd.DataFrame(
        columns=["FIELD_CODE", "CUM_OIL_MMBBL", "GROSS_OIL_REVENUE_MM_USD"]
    )
    out = compute_field_netback(df)
    assert len(out) == 0
    # the derived columns are still declared on an empty frame
    for col in (
        "REALIZED_OIL_PRICE_USD_BBL",
        "NET_REVENUE_AFTER_ROYALTY_MM_USD",
        "OPEX_LOW_MM_USD",
        "OPEX_HIGH_MM_USD",
        "NETBACK_HIGH_MM_USD",
        "NETBACK_LOW_MM_USD",
        "BREAKEVEN_OPEX_USD_BBL",
    ):
        assert col in out.columns


@unit
def test_missing_source_columns_yield_nan_columns():
    """A result frame lacking the source columns gets honest NaN, not a crash."""
    df = pd.DataFrame({"FIELD_CODE": ["X", "Y"]})
    out = compute_field_netback(df)
    assert out["REALIZED_OIL_PRICE_USD_BBL"].isna().all()
    assert out["NET_REVENUE_AFTER_ROYALTY_MM_USD"].isna().all()
