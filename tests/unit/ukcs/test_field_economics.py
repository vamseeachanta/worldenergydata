"""Tests for UK fiscal regime: RFCT, SC, EPL, Investment Allowance."""

import pytest

from worldenergydata.ukcs.analysis.field_economics import (
    UKFiscalRegime,
    UKFiscalResult,
    RFCT_RATE,
    SC_RATE,
    EPL_RATE,
    IA_RATE,
    calculate_rfct,
    calculate_supplementary_charge,
    calculate_epl,
    calculate_investment_allowance,
)


class TestFiscalRateConstants:
    def test_rfct_rate_30_percent(self):
        assert RFCT_RATE == pytest.approx(0.30, abs=0.001)

    def test_sc_rate_10_percent(self):
        assert SC_RATE == pytest.approx(0.10, abs=0.001)

    def test_epl_rate_35_percent(self):
        assert EPL_RATE == pytest.approx(0.35, abs=0.001)

    def test_ia_rate_29_percent(self):
        assert IA_RATE == pytest.approx(0.29, abs=0.001)


class TestRFCT:
    def test_rfct_on_positive_profit(self):
        tax = calculate_rfct(ring_fenced_profit=10_000_000.0)
        assert tax == pytest.approx(3_000_000.0)

    def test_rfct_zero_on_zero_profit(self):
        assert calculate_rfct(0.0) == 0.0

    def test_rfct_zero_on_loss(self):
        assert calculate_rfct(-5_000_000.0) == 0.0

    def test_rfct_30_percent(self):
        tax = calculate_rfct(100_000_000.0)
        assert tax / 100_000_000.0 == pytest.approx(0.30)


class TestSupplementaryCharge:
    def test_sc_on_positive_profit(self):
        tax = calculate_supplementary_charge(ring_fenced_profit=10_000_000.0)
        assert tax == pytest.approx(1_000_000.0)

    def test_sc_zero_on_zero_profit(self):
        assert calculate_supplementary_charge(0.0) == 0.0

    def test_sc_zero_on_loss(self):
        assert calculate_supplementary_charge(-1_000_000.0) == 0.0

    def test_sc_10_percent(self):
        tax = calculate_supplementary_charge(100_000_000.0)
        assert tax / 100_000_000.0 == pytest.approx(0.10)


class TestEPL:
    def test_epl_on_positive_profit(self):
        tax = calculate_epl(ring_fenced_profit=10_000_000.0)
        assert tax == pytest.approx(3_500_000.0)

    def test_epl_zero_on_zero_profit(self):
        assert calculate_epl(0.0) == 0.0

    def test_epl_zero_on_loss(self):
        assert calculate_epl(-5_000_000.0) == 0.0

    def test_epl_35_percent(self):
        tax = calculate_epl(100_000_000.0)
        assert tax / 100_000_000.0 == pytest.approx(0.35)

    def test_epl_reduced_by_investment_allowance(self):
        epl_no_ia = calculate_epl(100_000_000.0, qualifying_capex=0.0)
        epl_with_ia = calculate_epl(100_000_000.0, qualifying_capex=10_000_000.0)
        assert epl_with_ia < epl_no_ia


class TestInvestmentAllowance:
    def test_ia_29_percent_of_capex(self):
        ia = calculate_investment_allowance(qualifying_capex=10_000_000.0)
        assert ia == pytest.approx(2_900_000.0)

    def test_ia_zero_for_zero_capex(self):
        assert calculate_investment_allowance(0.0) == 0.0

    def test_ia_non_negative(self):
        ia = calculate_investment_allowance(50_000_000.0)
        assert ia >= 0.0


class TestUKFiscalRegime:
    @pytest.fixture
    def regime(self):
        return UKFiscalRegime()

    def test_calculate_returns_fiscal_result(self, regime):
        result = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=30_000_000.0,
            capex=20_000_000.0,
        )
        assert isinstance(result, UKFiscalResult)

    def test_rfct_positive_for_profitable_field(self, regime):
        result = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=10_000_000.0,
        )
        assert result.rfct >= 0.0

    def test_sc_positive_for_profitable_field(self, regime):
        result = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=10_000_000.0,
        )
        assert result.supplementary_charge >= 0.0

    def test_epl_positive_for_profitable_field(self, regime):
        result = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=10_000_000.0,
        )
        assert result.epl >= 0.0

    def test_ia_reduces_epl(self, regime):
        no_ia = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=0.0,
        )
        with_ia = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=20_000_000.0,
        )
        assert with_ia.epl <= no_ia.epl

    def test_effective_marginal_rate_near_78_percent(self, regime):
        """Combined RFCT+SC+EPL approaches ~78% on incremental barrel."""
        result = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=0.0,
        )
        effective_rate = result.total_government_take / result.ring_fenced_profit
        assert 0.60 < effective_rate < 0.85

    def test_net_income_positive_for_profitable_field(self, regime):
        result = regime.calculate(
            gross_revenue=200_000_000.0,
            opex=40_000_000.0,
            capex=20_000_000.0,
        )
        assert result.net_income > 0.0

    def test_zero_taxes_on_loss_making_field(self, regime):
        result = regime.calculate(
            gross_revenue=10_000_000.0,
            opex=60_000_000.0,
            capex=20_000_000.0,
        )
        assert result.rfct == 0.0
        assert result.supplementary_charge == 0.0
        assert result.epl == 0.0

    def test_government_take_includes_all_components(self, regime):
        result = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=5_000_000.0,
        )
        expected = result.rfct + result.supplementary_charge + result.epl
        assert result.total_government_take == pytest.approx(expected, rel=1e-6)

    def test_investment_allowance_amount_reported(self, regime):
        result = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=10_000_000.0,
        )
        assert result.investment_allowance >= 0.0
        assert result.investment_allowance == pytest.approx(
            calculate_investment_allowance(10_000_000.0), rel=1e-6
        )
