"""Tests for fdas.core.financial calculation functions."""

import numpy as np
import pytest

from worldenergydata.fdas.core.financial import (
    FinancialCalculationError,
    calculate_all_metrics,
    calculate_irr,
    calculate_npv,
    calculate_payback_period,
    calculate_trimmed_npv,
    excel_like_mirr,
    validate_cashflow_stream,
)

# ---------------------------------------------------------------------------
# excel_like_mirr
# ---------------------------------------------------------------------------


class TestExcelLikeMirr:
    def test_basic_cashflows(self):
        cf = np.array([-1000, 100, 200, 300, 400, 500])
        mirr_m, mirr_a = excel_like_mirr(cf, 0.10)
        assert isinstance(mirr_m, float)
        assert isinstance(mirr_a, float)
        assert not np.isnan(mirr_m)
        assert mirr_a > 0

    def test_empty_cashflows_raises(self):
        with pytest.raises(FinancialCalculationError, match="empty"):
            excel_like_mirr(np.array([]), 0.10)

    def test_invalid_discount_rate(self):
        cf = np.array([-1000, 500])
        with pytest.raises(FinancialCalculationError, match="Invalid discount rate"):
            excel_like_mirr(cf, 2.0)

    def test_all_zeros_returns_nan(self):
        cf = np.array([0, 0, 0, 0])
        mirr_m, mirr_a = excel_like_mirr(cf, 0.10)
        assert np.isnan(mirr_m)
        assert np.isnan(mirr_a)

    def test_all_positive_returns_nan(self):
        cf = np.array([100, 200, 300])
        mirr_m, mirr_a = excel_like_mirr(cf, 0.10)
        assert np.isnan(mirr_m)
        assert np.isnan(mirr_a)

    def test_all_negative_returns_nan(self):
        cf = np.array([-100, -200, -300])
        mirr_m, mirr_a = excel_like_mirr(cf, 0.10)
        assert np.isnan(mirr_m)
        assert np.isnan(mirr_a)

    def test_custom_reinvestment_rate(self):
        cf = np.array([-1000, 100, 200, 300, 400, 500])
        mirr_m, mirr_a = excel_like_mirr(cf, 0.10, reinvestment_rate_annual=0.05)
        assert not np.isnan(mirr_m)
        assert mirr_a > 0

    def test_trimming_leading_trailing_zeros(self):
        cf = np.array([0, 0, -1000, 200, 300, 400, 500, 0, 0])
        mirr_m, mirr_a = excel_like_mirr(cf, 0.10)
        assert not np.isnan(mirr_m)

    def test_annualization(self):
        cf = np.array([-1000, 100, 200, 300, 400, 500])
        mirr_m, mirr_a = excel_like_mirr(cf, 0.10)
        # Annual should be approximately (1 + monthly)^12 - 1
        expected_annual = (1 + mirr_m) ** 12 - 1
        assert mirr_a == pytest.approx(expected_annual, abs=1e-10)


# ---------------------------------------------------------------------------
# calculate_npv
# ---------------------------------------------------------------------------


class TestCalculateNpv:
    def test_basic_monthly(self):
        cf = np.array([-1000, 100, 200, 300, 400, 500])
        npv = calculate_npv(cf, 0.10, period="monthly")
        assert isinstance(npv, float)
        # With positive net cashflows and small discount rate, NPV should be positive
        assert npv > 0

    def test_basic_annual(self):
        cf = np.array([-1000, 100, 200, 300, 400, 500])
        npv = calculate_npv(cf, 0.10, period="annual")
        assert isinstance(npv, float)

    def test_empty_raises(self):
        with pytest.raises(FinancialCalculationError, match="empty"):
            calculate_npv(np.array([]), 0.10)

    def test_invalid_discount_rate(self):
        with pytest.raises(FinancialCalculationError, match="Invalid discount rate"):
            calculate_npv(np.array([-1000, 500]), 1.5)

    def test_invalid_period(self):
        with pytest.raises(FinancialCalculationError, match="Invalid period"):
            calculate_npv(np.array([-1000, 500]), 0.10, period="weekly")

    def test_zero_discount_rate(self):
        cf = np.array([-1000, 300, 300, 300, 300])
        npv = calculate_npv(cf, 0.0, period="monthly")
        # With 0% discount rate, NPV = sum of cashflows
        assert npv == pytest.approx(200.0, abs=1e-6)

    def test_higher_discount_reduces_npv(self):
        cf = np.array([-1000, 200, 200, 200, 200, 200, 200])
        npv_low = calculate_npv(cf, 0.05, period="monthly")
        npv_high = calculate_npv(cf, 0.20, period="monthly")
        assert npv_low > npv_high


# ---------------------------------------------------------------------------
# calculate_trimmed_npv
# ---------------------------------------------------------------------------


class TestCalculateTrimmedNpv:
    def test_basic(self):
        cf = np.array([0, 0, -1000, 200, 300, 0, 0])
        npv = calculate_trimmed_npv(cf, 0.10)
        assert isinstance(npv, float)

    def test_all_zeros_returns_zero(self):
        cf = np.array([0, 0, 0, 0])
        npv = calculate_trimmed_npv(cf, 0.10)
        assert npv == 0.0

    def test_no_leading_trailing_zeros(self):
        cf = np.array([-1000, 200, 300])
        npv_trimmed = calculate_trimmed_npv(cf, 0.10)
        npv_regular = calculate_npv(cf, 0.10)
        assert npv_trimmed == pytest.approx(npv_regular)


# ---------------------------------------------------------------------------
# calculate_irr
# ---------------------------------------------------------------------------


class TestCalculateIrr:
    def test_basic_monthly(self):
        cf = np.array([-1000, 100, 200, 300, 400, 500])
        irr_p, irr_a = calculate_irr(cf, period="monthly")
        assert isinstance(irr_p, float)
        assert isinstance(irr_a, float)
        assert irr_a > irr_p  # Annual should be larger

    def test_basic_annual(self):
        cf = np.array([-1000, 100, 200, 300, 400, 500])
        irr_p, irr_a = calculate_irr(cf, period="annual")
        assert irr_p == pytest.approx(irr_a)

    def test_no_sign_change_raises(self):
        cf = np.array([100, 200, 300])
        with pytest.raises(FinancialCalculationError):
            calculate_irr(cf)


# ---------------------------------------------------------------------------
# calculate_payback_period
# ---------------------------------------------------------------------------


class TestCalculatePaybackPeriod:
    def test_basic_monthly(self):
        cf = np.array([-1000, 200, 200, 200, 200, 200, 200])
        periods, years = calculate_payback_period(cf, "monthly")
        assert periods == 5  # cumsum at idx 5 = -1000+5*200 = 0
        assert years == pytest.approx(5 / 12.0)

    def test_basic_annual(self):
        cf = np.array([-1000, 400, 400, 400])
        periods, years = calculate_payback_period(cf, "annual")
        assert periods == 3
        assert years == 3.0

    def test_never_pays_back(self):
        cf = np.array([-1000, 10, 10, 10])
        periods, years = calculate_payback_period(cf, "monthly")
        assert periods == len(cf)
        assert years == np.inf

    def test_immediate_payback(self):
        cf = np.array([100, 200, 300])
        periods, years = calculate_payback_period(cf, "monthly")
        assert periods == 0
        assert years == 0.0


# ---------------------------------------------------------------------------
# validate_cashflow_stream
# ---------------------------------------------------------------------------


class TestValidateCashflowStream:
    def test_empty(self):
        result = validate_cashflow_stream(np.array([]))
        assert result["length"] == 0
        assert result["has_values"] is False
        assert result["has_both_signs"] is False

    def test_normal_stream(self):
        cf = np.array([-1000, 100, 200, 300])
        result = validate_cashflow_stream(cf)
        assert result["length"] == 4
        assert result["has_values"] is True
        assert result["has_nonzero"] is True
        assert result["has_positive"] is True
        assert result["has_negative"] is True
        assert result["has_both_signs"] is True
        assert result["sum"] == pytest.approx(-400.0)
        assert result["min"] == pytest.approx(-1000.0)
        assert result["max"] == pytest.approx(300.0)
        assert result["first_nonzero_index"] == 0
        assert result["last_nonzero_index"] == 3

    def test_all_zeros(self):
        result = validate_cashflow_stream(np.array([0, 0, 0]))
        assert result["has_nonzero"] is False
        assert result["first_nonzero_index"] is None

    def test_only_positive(self):
        result = validate_cashflow_stream(np.array([100, 200]))
        assert result["has_positive"] is True
        assert result["has_negative"] is False
        assert result["has_both_signs"] is False


# ---------------------------------------------------------------------------
# calculate_all_metrics
# ---------------------------------------------------------------------------


class TestCalculateAllMetrics:
    def test_basic(self):
        cf = np.array([-1000, 100, 200, 300, 400, 500])
        result = calculate_all_metrics(cf, 0.10, "monthly")
        assert "npv" in result
        assert "npv_trimmed" in result
        assert "mirr_monthly" in result
        assert "mirr_annual" in result
        assert "irr_period" in result
        assert "irr_annual" in result
        assert "payback_periods" in result
        assert "payback_years" in result
        assert "validation" in result
        assert result["npv"] is not None
        assert result["irr_annual"] is not None

    def test_annual_period(self):
        cf = np.array([-5000, 1000, 1500, 2000, 2500])
        result = calculate_all_metrics(cf, 0.10, "annual")
        assert result["period"] == "annual"
        assert result["npv"] is not None

    def test_with_bad_cashflows(self):
        cf = np.array([100, 200, 300])  # No negative -> IRR/MIRR will fail
        result = calculate_all_metrics(cf, 0.10, "monthly")
        # NPV should still work
        assert result["npv"] is not None
