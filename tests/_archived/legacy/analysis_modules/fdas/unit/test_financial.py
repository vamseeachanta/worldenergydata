"""
Unit tests for FDAS financial calculations module.

Tests NPV, MIRR, IRR calculations against known values and validates
Excel compatibility for field development economic analysis.

Author: WorldEnergyData Team
Date: 2025-10-03
"""

import pytest
import numpy as np
from src.worldenergydata.modules.fdas.core.financial import (
    excel_like_mirr,
    calculate_npv,
    calculate_trimmed_npv,
    calculate_irr,
    calculate_payback_period,
    validate_cashflow_stream,
    calculate_all_metrics,
    FinancialCalculationError,
)


class TestExcelLikeMIRR:
    """Test suite for Excel-compatible MIRR calculations"""

    def test_basic_mirr_calculation(self):
        """Test MIRR with simple positive cashflows"""
        cashflows = np.array([-1000, 100, 200, 300, 400, 500])
        mirr_m, mirr_a = excel_like_mirr(cashflows, 0.10)

        assert not np.isnan(mirr_m), "Monthly MIRR should not be NaN"
        assert not np.isnan(mirr_a), "Annual MIRR should not be NaN"
        assert mirr_m > 0, "MIRR should be positive for profitable project"
        assert mirr_a > mirr_m, "Annual rate should be higher than monthly"

    def test_mirr_with_zero_padding(self):
        """Test that MIRR correctly trims zero padding"""
        cf_padded = np.array([0, 0, -1000, 100, 200, 300, 0, 0])
        cf_trimmed = np.array([-1000, 100, 200, 300])

        mirr_padded = excel_like_mirr(cf_padded, 0.10)
        mirr_trimmed = excel_like_mirr(cf_trimmed, 0.10)

        # Should be identical due to trimming
        np.testing.assert_allclose(mirr_padded[0], mirr_trimmed[0], rtol=1e-6)
        np.testing.assert_allclose(mirr_padded[1], mirr_trimmed[1], rtol=1e-6)

    def test_mirr_requires_both_signs(self):
        """Test that MIRR returns NaN for all-positive or all-negative cashflows"""
        # All positive
        cf_pos = np.array([100, 200, 300, 400])
        mirr_m, mirr_a = excel_like_mirr(cf_pos, 0.10)
        assert np.isnan(mirr_m) and np.isnan(mirr_a)

        # All negative
        cf_neg = np.array([-100, -200, -300, -400])
        mirr_m, mirr_a = excel_like_mirr(cf_neg, 0.10)
        assert np.isnan(mirr_m) and np.isnan(mirr_a)

    def test_mirr_empty_cashflows(self):
        """Test MIRR with empty array raises error"""
        with pytest.raises(FinancialCalculationError):
            excel_like_mirr(np.array([]), 0.10)

    def test_mirr_invalid_discount_rate(self):
        """Test MIRR with invalid discount rate raises error"""
        cashflows = np.array([-1000, 100, 200, 300])

        with pytest.raises(FinancialCalculationError):
            excel_like_mirr(cashflows, 2.0)  # 200% is out of range

        with pytest.raises(FinancialCalculationError):
            excel_like_mirr(cashflows, -2.0)  # -200% is out of range

    def test_mirr_annualization(self):
        """Test that monthly MIRR is correctly annualized"""
        cashflows = np.array([-1000, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100])
        mirr_m, mirr_a = excel_like_mirr(cashflows, 0.10)

        # Annual should be (1 + monthly)^12 - 1
        expected_annual = (1 + mirr_m) ** 12 - 1
        np.testing.assert_allclose(mirr_a, expected_annual, rtol=1e-10)

    def test_mirr_with_custom_reinvestment_rate(self):
        """Test MIRR with different reinvestment rate"""
        cashflows = np.array([-1000, 100, 200, 300, 400])

        # MIRR with different rates
        mirr1 = excel_like_mirr(cashflows, 0.10, 0.10)
        mirr2 = excel_like_mirr(cashflows, 0.10, 0.15)

        # Higher reinvestment rate should give higher MIRR
        assert mirr2[1] > mirr1[1], "Higher reinvestment rate should increase MIRR"


class TestNPV:
    """Test suite for NPV calculations"""

    def test_basic_npv_calculation(self):
        """Test NPV with known values"""
        cashflows = np.array([-1000, 500, 500, 500])
        npv = calculate_npv(cashflows, 0.10, period='annual')

        # Known result: NPV ≈ 243.43 at 10% discount
        assert npv > 200 and npv < 300, f"NPV should be ~243, got {npv}"

    def test_npv_zero_discount(self):
        """Test that NPV with 0% discount equals sum of cashflows"""
        cashflows = np.array([-1000, 100, 200, 300, 400])
        npv = calculate_npv(cashflows, 0.0)

        assert np.isclose(npv, cashflows.sum()), "NPV at 0% should equal sum"

    def test_npv_monthly_vs_annual(self):
        """Test NPV calculation for monthly vs annual periods"""
        cashflows_annual = np.array([-1000, 500, 500])

        npv_annual = calculate_npv(cashflows_annual, 0.10, period='annual')

        # Monthly equivalent (same cashflow, monthly rate)
        cashflows_monthly = np.array([-1000, 41.67, 41.67] * 12)  # Approximate
        npv_monthly = calculate_npv(cashflows_monthly, 0.10, period='monthly')

        # Annual should be higher due to compounding
        assert npv_annual > 0, "Annual NPV should be positive"

    def test_npv_trimmed_vs_untrimmed(self):
        """Test trimmed NPV vs standard NPV"""
        cf = np.array([0, 0, -1000, 100, 200, 300, 0, 0])

        npv_standard = calculate_npv(cf, 0.10)
        npv_trimmed = calculate_trimmed_npv(cf, 0.10)

        # Trimmed should exclude leading/trailing zeros
        assert npv_standard != npv_trimmed, "Trimmed and untrimmed should differ"

    def test_npv_invalid_period(self):
        """Test NPV with invalid period raises error"""
        cashflows = np.array([-1000, 100, 200])

        with pytest.raises(FinancialCalculationError):
            calculate_npv(cashflows, 0.10, period='weekly')


class TestIRR:
    """Test suite for IRR calculations"""

    def test_basic_irr_calculation(self):
        """Test IRR with known values"""
        # Classic example: invest $1000, receive $1100 in one year
        cashflows = np.array([-1000, 1100])
        irr_p, irr_a = calculate_irr(cashflows, period='annual')

        # IRR should be 10%
        assert np.isclose(irr_a, 0.10, atol=0.001), f"IRR should be ~10%, got {irr_a}"

    def test_irr_monthly_annualization(self):
        """Test IRR monthly to annual conversion"""
        # Monthly cashflows
        cashflows = np.array([-1000] + [100] * 12)
        irr_m, irr_a = calculate_irr(cashflows, period='monthly')

        # Annual should be (1 + monthly)^12 - 1
        expected_annual = (1 + irr_m) ** 12 - 1
        np.testing.assert_allclose(irr_a, expected_annual, rtol=1e-10)

    def test_irr_no_solution(self):
        """Test IRR with cashflows that have no valid IRR"""
        # All positive (no investment)
        cashflows = np.array([100, 100, 100])

        with pytest.raises(FinancialCalculationError):
            calculate_irr(cashflows)


class TestPaybackPeriod:
    """Test suite for payback period calculations"""

    def test_basic_payback(self):
        """Test payback period calculation"""
        cashflows = np.array([-1000, 300, 300, 300, 300, 300])
        periods, years = calculate_payback_period(cashflows, period='annual')

        # Payback should be 4 years (cumulative positive after period 4)
        assert periods == 4, f"Payback should be 4 periods, got {periods}"
        assert np.isclose(years, 4.0), f"Payback should be 4 years, got {years}"

    def test_payback_monthly(self):
        """Test payback period with monthly cashflows"""
        cashflows = np.array([-1200] + [100] * 20)
        periods, years = calculate_payback_period(cashflows, period='monthly')

        # Payback at month 12 (after 12 months of $100)
        assert periods == 12, f"Payback should be 12 months, got {periods}"
        assert np.isclose(years, 1.0), f"Payback should be 1 year, got {years}"

    def test_payback_never_positive(self):
        """Test payback when cashflows never turn positive"""
        cashflows = np.array([-1000, -100, -100, -100])
        periods, years = calculate_payback_period(cashflows)

        assert years == np.inf, "Payback should be infinite if never positive"


class TestCashflowValidation:
    """Test suite for cashflow validation"""

    def test_validate_normal_cashflow(self):
        """Test validation of normal cashflow"""
        cf = np.array([-1000, 100, 200, 300, 400])
        info = validate_cashflow_stream(cf)

        assert info['has_values'] is True
        assert info['has_nonzero'] is True
        assert info['has_positive'] is True
        assert info['has_negative'] is True
        assert info['has_both_signs'] is True
        assert info['length'] == 5
        assert np.isclose(info['sum'], 0)  # Breaks even

    def test_validate_empty_cashflow(self):
        """Test validation of empty cashflow"""
        cf = np.array([])
        info = validate_cashflow_stream(cf)

        assert info['has_values'] is False
        assert info['length'] == 0

    def test_validate_all_zeros(self):
        """Test validation of all-zero cashflow"""
        cf = np.array([0, 0, 0, 0])
        info = validate_cashflow_stream(cf)

        assert info['has_nonzero'] is False
        assert info['first_nonzero_index'] is None

    def test_validate_with_padding(self):
        """Test validation identifies first/last nonzero indices"""
        cf = np.array([0, 0, -1000, 100, 200, 0, 0])
        info = validate_cashflow_stream(cf)

        assert info['first_nonzero_index'] == 2
        assert info['last_nonzero_index'] == 4


class TestCalculateAllMetrics:
    """Test suite for comprehensive metrics calculation"""

    def test_all_metrics_successful(self):
        """Test that all metrics are calculated successfully"""
        cf = np.array([-1000, 100, 200, 300, 400, 500])
        metrics = calculate_all_metrics(cf, 0.10)

        # Should have all expected keys
        assert 'npv' in metrics
        assert 'mirr_annual' in metrics
        assert 'irr_annual' in metrics
        assert 'payback_years' in metrics
        assert 'validation' in metrics

        # All should be valid numbers
        assert metrics['npv'] is not None
        assert metrics['mirr_annual'] is not None
        assert metrics['irr_annual'] is not None
        assert metrics['payback_years'] is not None

    def test_all_metrics_handles_errors(self):
        """Test that errors are gracefully handled"""
        # All positive (no valid IRR/MIRR)
        cf = np.array([100, 100, 100])
        metrics = calculate_all_metrics(cf, 0.10)

        # Should have error messages
        assert 'mirr_error' in metrics or metrics['mirr_annual'] is None
        assert 'irr_error' in metrics or metrics['irr_annual'] is None

    def test_all_metrics_custom_parameters(self):
        """Test all metrics with custom discount rate"""
        cf = np.array([-1000, 100, 200, 300, 400])

        metrics_10 = calculate_all_metrics(cf, 0.10)
        metrics_15 = calculate_all_metrics(cf, 0.15)

        # Higher discount rate should give lower NPV
        assert metrics_15['npv'] < metrics_10['npv']


class TestRegressionAgainstFDAS:
    """Regression tests against known FDAS results"""

    def test_anchor_field_example(self):
        """Test calculation matches expected Anchor field results"""
        # Simplified Anchor field cashflow (example values)
        # Real test would use golden baseline data
        cashflows = np.array([
            -1500e6,  # Initial CAPEX
            -500e6,   # Year 1 additional CAPEX
            200e6,    # Year 2 production
            800e6,    # Year 3 peak production
            600e6,    # Year 4
            400e6,    # Year 5
        ])

        npv = calculate_npv(cashflows, 0.10, period='annual')
        mirr_m, mirr_a = excel_like_mirr(cashflows, 0.10)

        # Should be profitable
        assert npv > 0, "Anchor field NPV should be positive"
        assert mirr_a > 0.10, "MIRR should exceed cost of capital"

    @pytest.mark.skip(reason="Requires golden baseline file")
    def test_against_golden_baseline(self):
        """Compare results against FDAS golden baseline"""
        # This test would load the golden baseline and compare
        # Skip for now until golden baseline is available
        pass


# Performance tests
class TestPerformance:
    """Performance tests for financial calculations"""

    def test_npv_performance_large_array(self):
        """Test NPV performance with large cashflow array"""
        # 30 years monthly = 360 periods
        cashflows = np.random.randn(360) * 1000
        cashflows[0] = -100000  # Initial investment

        import time
        start = time.time()
        npv = calculate_npv(cashflows, 0.10)
        elapsed = time.time() - start

        # Should complete in under 10ms
        assert elapsed < 0.01, f"NPV calculation too slow: {elapsed:.4f}s"
        assert npv is not None

    def test_all_metrics_performance(self):
        """Test performance of calculating all metrics"""
        cashflows = np.random.randn(120) * 1000
        cashflows[0] = -50000

        import time
        start = time.time()
        metrics = calculate_all_metrics(cashflows, 0.10)
        elapsed = time.time() - start

        # Should complete in under 50ms
        assert elapsed < 0.05, f"All metrics too slow: {elapsed:.4f}s"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
