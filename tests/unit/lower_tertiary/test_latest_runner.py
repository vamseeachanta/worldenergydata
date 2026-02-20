"""Tests for lower_tertiary.latest_runner pure functions."""

import pandas as pd
import pytest

from worldenergydata.lower_tertiary.latest_runner import (
    FIRST_OIL_CORRECTIONS,
    _compute_development_revenue,
    _generate_explanation,
)


# ---------------------------------------------------------------------------
# FIRST_OIL_CORRECTIONS constant
# ---------------------------------------------------------------------------

class TestFirstOilCorrections:
    def test_is_dict(self):
        assert isinstance(FIRST_OIL_CORRECTIONS, dict)

    def test_cascade_chinook_present(self):
        assert "Cascade Chinook" in FIRST_OIL_CORRECTIONS
        assert FIRST_OIL_CORRECTIONS["Cascade Chinook"] == "2012-09-01"


# ---------------------------------------------------------------------------
# _generate_explanation
# ---------------------------------------------------------------------------

class TestGenerateExplanation:
    def test_not_significant(self):
        result = _generate_explanation(3.0, False)
        assert result == ""

    def test_large_positive(self):
        result = _generate_explanation(60.0, True)
        assert "Ramping" in result

    def test_moderate_positive(self):
        result = _generate_explanation(10.0, True)
        assert "Active producing" in result

    def test_negative_significant(self):
        result = _generate_explanation(-10.0, True)
        assert "decline" in result.lower()

    def test_boundary_positive(self):
        # Exactly 5.01% => "Active producing field"
        result = _generate_explanation(5.01, True)
        assert "Active producing" in result

    def test_boundary_large(self):
        # Exactly 50.01% => "Ramping field"
        result = _generate_explanation(50.01, True)
        assert "Ramping" in result


# ---------------------------------------------------------------------------
# _compute_development_revenue
# ---------------------------------------------------------------------------

class TestComputeDevelopmentRevenue:
    def test_basic_revenue(self):
        prod = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]),
            "oil_bbl": [1000.0, 2000.0, 3000.0],
        })
        wti = pd.DataFrame({
            "Month": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]),
            "WTI_USD": [75.0, 80.0, 70.0],
        })
        revenue = _compute_development_revenue(prod, wti)
        # 1000*75 + 2000*80 + 3000*70 = 75000 + 160000 + 210000 = 445000
        assert revenue == pytest.approx(445000.0)

    def test_empty_production(self):
        prod = pd.DataFrame({"date": [], "oil_bbl": []})
        wti = pd.DataFrame({"Month": [], "WTI_USD": []})
        revenue = _compute_development_revenue(prod, wti)
        assert revenue == 0.0

    def test_missing_wti_produces_nan(self):
        prod = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01"]),
            "oil_bbl": [1000.0],
        })
        wti = pd.DataFrame({
            "Month": pd.to_datetime(["2024-06-01"]),
            "WTI_USD": [75.0],
        })
        # Left join => WTI_USD will be NaN for Jan => revenue NaN
        revenue = _compute_development_revenue(prod, wti)
        # NaN * 1000 = NaN, sum of NaN = 0 (pandas default)
        assert revenue == 0.0 or pd.isna(revenue)

    def test_single_month(self):
        prod = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01"]),
            "oil_bbl": [500.0],
        })
        wti = pd.DataFrame({
            "Month": pd.to_datetime(["2024-01-01"]),
            "WTI_USD": [80.0],
        })
        revenue = _compute_development_revenue(prod, wti)
        assert revenue == pytest.approx(40000.0)
