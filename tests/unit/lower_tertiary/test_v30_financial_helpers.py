"""Tests for v30 financial reproducer helper functions."""

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
    def _make_assumptions(self, data=None):
        if data is None:
            data = {
                "DEV_SYSTEM": ["subsea15", "subsea20", "dry", "default"],
                "MODU_LOADED_DAYRATE_MM": [0.8, 0.9, 0.7, 0.75],
                "ROYALTY_RATE": [0.1875, 0.1875, 0.1875, 0.1875],
            }
        return pd.DataFrame(data)

    def test_exact_match(self):
        assumptions = self._make_assumptions()
        result = _get_assumption(assumptions, "subsea15", "MODU_LOADED_DAYRATE_MM")
        assert result == 0.8

    def test_fallback_to_default(self):
        assumptions = self._make_assumptions()
        result = _get_assumption(assumptions, "unknown_system", "MODU_LOADED_DAYRATE_MM")
        assert result == 0.75

    def test_missing_metric_returns_default(self):
        assumptions = self._make_assumptions()
        result = _get_assumption(assumptions, "subsea15", "NONEXISTENT_METRIC", 99.0)
        assert result == 99.0

    def test_case_insensitive_metric(self):
        assumptions = self._make_assumptions()
        result = _get_assumption(assumptions, "subsea15", "modu_loaded_dayrate_mm")
        assert result == 0.8

    def test_nan_value_returns_default(self):
        assumptions = pd.DataFrame({
            "DEV_SYSTEM": ["subsea15"],
            "METRIC_A": [float("nan")],
        })
        result = _get_assumption(assumptions, "subsea15", "METRIC_A", 42.0)
        assert result == 42.0

    def test_no_default_row_and_no_match(self):
        assumptions = pd.DataFrame({
            "DEV_SYSTEM": ["subsea15"],
            "RATE": [0.5],
        })
        result = _get_assumption(assumptions, "unknown", "RATE", 0.0)
        assert result == 0.0

    def test_non_numeric_value(self):
        assumptions = pd.DataFrame({
            "DEV_SYSTEM": ["subsea15"],
            "LABEL": ["text_value"],
        })
        result = _get_assumption(assumptions, "subsea15", "LABEL", -1.0)
        assert result == -1.0


# ---------------------------------------------------------------------------
# _excel_like_mirr
# ---------------------------------------------------------------------------

class TestExcelLikeMirr:
    def test_basic_mirr(self):
        # Investment followed by positive returns
        cf = np.array([-1000.0, 300.0, 300.0, 300.0, 300.0])
        mirr = _excel_like_mirr(cf, 0.10)
        assert not math.isnan(mirr)
        assert mirr > 0

    def test_all_zeros_returns_nan(self):
        cf = np.array([0.0, 0.0, 0.0])
        mirr = _excel_like_mirr(cf, 0.10)
        assert math.isnan(mirr)

    def test_all_positive_returns_nan(self):
        cf = np.array([100.0, 200.0, 300.0])
        mirr = _excel_like_mirr(cf, 0.10)
        assert math.isnan(mirr)

    def test_all_negative_returns_nan(self):
        cf = np.array([-100.0, -200.0, -300.0])
        mirr = _excel_like_mirr(cf, 0.10)
        assert math.isnan(mirr)

    def test_single_period(self):
        cf = np.array([-100.0, 200.0])
        mirr = _excel_like_mirr(cf, 0.10)
        assert not math.isnan(mirr)
        # With a single period, MIRR should be close to (200/100) - 1 = 1.0
        # but adjusted by discount rate
        assert mirr > 0

    def test_leading_zeros_trimmed(self):
        cf = np.array([0.0, 0.0, -1000.0, 500.0, 500.0, 500.0, 0.0, 0.0])
        mirr = _excel_like_mirr(cf, 0.10)
        assert not math.isnan(mirr)

    def test_zero_discount_rate(self):
        cf = np.array([-1000.0, 400.0, 400.0, 400.0])
        mirr = _excel_like_mirr(cf, 0.0)
        assert not math.isnan(mirr)


# ---------------------------------------------------------------------------
# _month_floor
# ---------------------------------------------------------------------------

class TestMonthFloor:
    def test_basic(self):
        ts = pd.Timestamp("2024-06-15 14:30:00")
        result = _month_floor(ts)
        assert result == pd.Timestamp("2024-06-01")

    def test_first_of_month(self):
        ts = pd.Timestamp("2024-01-01")
        result = _month_floor(ts)
        assert result == pd.Timestamp("2024-01-01")

    def test_last_of_month(self):
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
    def test_basic(self):
        assert _norm_name("Thunder Horse") == "Thunder Horse"

    def test_strips_whitespace(self):
        assert _norm_name("  Thunder Horse  ") == "Thunder Horse"

    def test_collapses_whitespace(self):
        assert _norm_name("Thunder   Horse") == "Thunder Horse"

    def test_st_malo_fix(self):
        assert _norm_name("St. Malo") == "St Malo"

    def test_nan_returns_nan(self):
        result = _norm_name(float("nan"))
        assert result != result  # NaN check

    def test_none_returns_none(self):
        result = _norm_name(None)
        assert result is None
