"""Tests for Brazilian fiscal regime models (concession + PSA)."""

import pytest

from worldenergydata.brazil_anp.analysis.field_economics import (
    ConcessionRegime,
    PSARegime,
    FiscalResult,
    calculate_royalties_concession,
    calculate_special_participation,
    calculate_psa_government_take,
)


class TestConcessionRoyalties:
    def test_minimum_royalty_rate(self):
        result = calculate_royalties_concession(
            gross_revenue=1_000_000.0, production_rate_bpd=500.0
        )
        assert result >= 1_000_000.0 * 0.05

    def test_maximum_royalty_rate(self):
        result = calculate_royalties_concession(
            gross_revenue=1_000_000.0, production_rate_bpd=100_000.0
        )
        assert result <= 1_000_000.0 * 0.15

    def test_sliding_scale(self):
        low = calculate_royalties_concession(
            gross_revenue=1_000_000.0, production_rate_bpd=1_000.0
        )
        high = calculate_royalties_concession(
            gross_revenue=1_000_000.0, production_rate_bpd=50_000.0
        )
        assert high > low

    def test_zero_revenue(self):
        result = calculate_royalties_concession(
            gross_revenue=0.0, production_rate_bpd=10_000.0
        )
        assert result == 0.0


class TestSpecialParticipation:
    def test_zero_for_small_fields(self):
        result = calculate_special_participation(net_revenue=100_000.0)
        assert result == 0.0

    def test_positive_for_large_fields(self):
        result = calculate_special_participation(net_revenue=500_000_000.0)
        assert result > 0.0

    def test_progressive(self):
        low = calculate_special_participation(net_revenue=100_000_000.0)
        high = calculate_special_participation(net_revenue=1_000_000_000.0)
        assert high > low

    def test_max_rate_40_percent(self):
        result = calculate_special_participation(net_revenue=10_000_000_000.0)
        assert result <= 10_000_000_000.0 * 0.40


class TestConcessionRegime:
    @pytest.fixture
    def regime(self):
        return ConcessionRegime()

    def test_calculate_returns_fiscal_result(self, regime):
        result = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=30_000_000.0,
            capex=20_000_000.0,
            production_rate_bpd=20_000.0,
        )
        assert isinstance(result, FiscalResult)

    def test_royalties_present(self, regime):
        result = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=30_000_000.0,
            capex=20_000_000.0,
            production_rate_bpd=20_000.0,
        )
        assert result.royalties > 0.0

    def test_corporate_tax_34_percent(self, regime):
        result = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=30_000_000.0,
            capex=20_000_000.0,
            production_rate_bpd=20_000.0,
        )
        assert result.corporate_tax_rate == pytest.approx(0.34, abs=0.01)

    def test_net_income_positive_for_profitable_field(self, regime):
        result = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=10_000_000.0,
            production_rate_bpd=20_000.0,
        )
        assert result.net_income > 0.0

    def test_government_take_reasonable(self, regime):
        result = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=10_000_000.0,
            production_rate_bpd=20_000.0,
        )
        gov_take_pct = result.total_government_take / 100_000_000.0
        assert 0.30 < gov_take_pct < 0.80


class TestPSAGovernmentTake:
    def test_fixed_royalty_15_percent(self):
        result = calculate_psa_government_take(
            gross_revenue=100_000_000.0,
            cost_oil=30_000_000.0,
            profit_oil_gov_share=0.50,
        )
        assert result["royalties"] == pytest.approx(15_000_000.0)

    def test_profit_oil_split(self):
        result = calculate_psa_government_take(
            gross_revenue=100_000_000.0,
            cost_oil=30_000_000.0,
            profit_oil_gov_share=0.50,
        )
        assert result["government_profit_oil"] > 0.0

    def test_petrobras_minimum_30_percent(self):
        result = calculate_psa_government_take(
            gross_revenue=100_000_000.0,
            cost_oil=30_000_000.0,
            profit_oil_gov_share=0.50,
        )
        assert result["petrobras_share"] >= 0.30


class TestPSARegime:
    @pytest.fixture
    def regime(self):
        return PSARegime()

    def test_calculate_returns_fiscal_result(self, regime):
        result = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=15_000_000.0,
            profit_oil_gov_share=0.50,
        )
        assert isinstance(result, FiscalResult)

    def test_no_special_participation(self, regime):
        result = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=15_000_000.0,
            profit_oil_gov_share=0.50,
        )
        assert result.special_participation == 0.0

    def test_royalties_at_15_percent(self, regime):
        result = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=15_000_000.0,
            profit_oil_gov_share=0.50,
        )
        assert result.royalties == pytest.approx(15_000_000.0)

    def test_higher_gov_share_more_take(self, regime):
        low = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=15_000_000.0,
            profit_oil_gov_share=0.30,
        )
        high = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=15_000_000.0,
            profit_oil_gov_share=0.70,
        )
        assert high.total_government_take > low.total_government_take
