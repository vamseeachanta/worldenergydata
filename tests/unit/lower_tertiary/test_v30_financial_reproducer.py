"""Tests for v30_financial_reproducer pure helper functions."""

import math

import numpy as np
import pandas as pd
import pytest

from worldenergydata.lower_tertiary.v30_financial_reproducer import (
    _excel_like_mirr,
    _get_assumption,
    _month_floor,
    _norm_name,
)


# ---------------------------------------------------------------------------
# _get_assumption
# ---------------------------------------------------------------------------

class TestGetAssumption:
    def setup_method(self):
        self.assumptions = pd.DataFrame({
            "DEV_SYSTEM": ["subsea15", "subsea20", "dry", "default"],
            "MODU_LOADED_DAYRATE_MM": [0.8, 1.0, 0.6, 0.5],
            "HOST_CAPEX_MM": [100.0, 120.0, 80.0, 50.0],
        })

    def test_exact_match(self):
        result = _get_assumption(self.assumptions, "subsea15", "MODU_LOADED_DAYRATE_MM")
        assert result == 0.8

    def test_falls_back_to_default(self):
        result = _get_assumption(self.assumptions, "unknown_system", "HOST_CAPEX_MM")
        assert result == 50.0

    def test_missing_metric_returns_default(self):
        result = _get_assumption(self.assumptions, "subsea15", "NONEXISTENT", 99.0)
        assert result == 99.0

    def test_nan_returns_default(self):
        df = pd.DataFrame({
            "DEV_SYSTEM": ["test"],
            "METRIC_A": [float("nan")],
        })
        result = _get_assumption(df, "test", "METRIC_A", 42.0)
        assert result == 42.0

    def test_non_numeric_returns_default(self):
        df = pd.DataFrame({
            "DEV_SYSTEM": ["test"],
            "METRIC_A": ["not_a_number"],
        })
        result = _get_assumption(df, "test", "METRIC_A", 10.0)
        assert result == 10.0

    def test_no_matching_row_no_default_row(self):
        df = pd.DataFrame({
            "DEV_SYSTEM": ["subsea15"],
            "METRIC_A": [1.0],
        })
        result = _get_assumption(df, "unknown", "METRIC_A", 5.0)
        assert result == 5.0

    def test_case_insensitive_metric(self):
        result = _get_assumption(self.assumptions, "subsea15", "modu_loaded_dayrate_mm")
        assert result == 0.8


# ---------------------------------------------------------------------------
# _month_floor
# ---------------------------------------------------------------------------

class TestMonthFloor:
    def test_mid_month(self):
        ts = pd.Timestamp("2024-03-15")
        result = _month_floor(ts)
        assert result == pd.Timestamp("2024-03-01")

    def test_first_day(self):
        ts = pd.Timestamp("2024-01-01")
        result = _month_floor(ts)
        assert result == pd.Timestamp("2024-01-01")

    def test_last_day(self):
        ts = pd.Timestamp("2024-12-31")
        result = _month_floor(ts)
        assert result == pd.Timestamp("2024-12-01")

    def test_nat_returns_nat(self):
        result = _month_floor(pd.NaT)
        assert pd.isna(result)


# ---------------------------------------------------------------------------
# _norm_name
# ---------------------------------------------------------------------------

class TestNormName:
    def test_strips(self):
        assert _norm_name("  Hello  ") == "Hello"

    def test_collapses_spaces(self):
        assert _norm_name("St.   Malo   Field") == "St Malo Field"

    def test_st_malo_replacement(self):
        assert _norm_name("St. Malo") == "St Malo"

    def test_nan_returns_nan(self):
        result = _norm_name(float("nan"))
        assert math.isnan(result)

    def test_none_passthrough(self):
        # pd.isna(None) is True
        result = _norm_name(None)
        assert result is None


# ---------------------------------------------------------------------------
# _excel_like_mirr
# ---------------------------------------------------------------------------

class TestExcelLikeMirr:
    def test_simple_investment(self):
        # Initial investment -100, then +50 each period for 4 periods
        cf = np.array([-100.0, 50.0, 50.0, 50.0, 50.0])
        result = _excel_like_mirr(cf, 0.10)
        assert not math.isnan(result)
        assert result > 0

    def test_all_zeros_returns_nan(self):
        cf = np.array([0.0, 0.0, 0.0])
        result = _excel_like_mirr(cf, 0.10)
        assert math.isnan(result)

    def test_all_positive_returns_nan(self):
        cf = np.array([10.0, 20.0, 30.0])
        result = _excel_like_mirr(cf, 0.10)
        assert math.isnan(result)

    def test_all_negative_returns_nan(self):
        cf = np.array([-10.0, -20.0, -30.0])
        result = _excel_like_mirr(cf, 0.10)
        assert math.isnan(result)

    def test_single_period(self):
        cf = np.array([-100.0, 200.0])
        result = _excel_like_mirr(cf, 0.10)
        assert not math.isnan(result)
