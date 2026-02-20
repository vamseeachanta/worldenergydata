"""Tests for US federal + state fiscal regimes (royalties, severance tax)."""

import pytest

from worldenergydata.eia_us.analysis.us_fiscal import (
    FederalOnshoreFiscal,
    TexasFiscal,
    NorthDakotaFiscal,
    GoMCrosscheck,
    USFiscalResult,
    FEDERAL_ONSHORE_ROYALTY_RATE,
    TEXAS_OIL_SEVERANCE_RATE,
    TEXAS_GAS_SEVERANCE_RATE,
    ND_OIL_EXTRACTION_RATE,
    ND_OIL_PRODUCTION_RATE,
)


# ── Rate constants ─────────────────────────────────────────────────────────────

class TestFiscalRateConstants:
    def test_federal_onshore_royalty_16_67_percent(self):
        assert FEDERAL_ONSHORE_ROYALTY_RATE == pytest.approx(0.1667, abs=0.001)

    def test_texas_oil_severance_4_6_percent(self):
        assert TEXAS_OIL_SEVERANCE_RATE == pytest.approx(0.046, abs=0.001)

    def test_texas_gas_severance_7_5_percent(self):
        assert TEXAS_GAS_SEVERANCE_RATE == pytest.approx(0.075, abs=0.001)

    def test_nd_oil_extraction_5_percent(self):
        assert ND_OIL_EXTRACTION_RATE == pytest.approx(0.05, abs=0.001)

    def test_nd_oil_production_6_5_percent(self):
        assert ND_OIL_PRODUCTION_RATE == pytest.approx(0.065, abs=0.001)


# ── Federal Onshore ────────────────────────────────────────────────────────────

class TestFederalOnshoreFiscal:
    @pytest.fixture
    def regime(self):
        return FederalOnshoreFiscal()

    def test_calculate_returns_fiscal_result(self, regime):
        result = regime.calculate(gross_revenue=10_000_000.0, opex=3_000_000.0)
        assert isinstance(result, USFiscalResult)

    def test_royalty_is_16_67_pct_of_gross(self, regime):
        result = regime.calculate(gross_revenue=10_000_000.0, opex=0.0)
        assert result.royalty == pytest.approx(10_000_000.0 * 0.1667, abs=1000)

    def test_royalty_zero_on_zero_revenue(self, regime):
        result = regime.calculate(gross_revenue=0.0, opex=0.0)
        assert result.royalty == 0.0

    def test_net_income_positive_for_profitable_field(self, regime):
        result = regime.calculate(gross_revenue=10_000_000.0, opex=2_000_000.0)
        assert result.net_income > 0.0

    def test_government_take_includes_royalty(self, regime):
        result = regime.calculate(gross_revenue=10_000_000.0, opex=2_000_000.0)
        assert result.total_government_take >= result.royalty

    def test_severance_tax_zero_for_federal(self, regime):
        """Federal onshore regime uses royalty, not state severance."""
        result = regime.calculate(gross_revenue=5_000_000.0, opex=1_000_000.0)
        assert result.severance_tax == 0.0


# ── Texas ──────────────────────────────────────────────────────────────────────

class TestTexasFiscal:
    @pytest.fixture
    def regime(self):
        return TexasFiscal()

    def test_oil_severance_4_6_pct(self, regime):
        result = regime.calculate_oil(gross_revenue=1_000_000.0, opex=0.0)
        assert result.severance_tax == pytest.approx(46_000.0, rel=0.01)

    def test_gas_severance_7_5_pct(self, regime):
        result = regime.calculate_gas(gross_revenue=1_000_000.0, opex=0.0)
        assert result.severance_tax == pytest.approx(75_000.0, rel=0.01)

    def test_oil_net_income_positive(self, regime):
        result = regime.calculate_oil(gross_revenue=5_000_000.0, opex=1_000_000.0)
        assert result.net_income > 0.0

    def test_zero_revenue_zero_tax(self, regime):
        result = regime.calculate_oil(gross_revenue=0.0, opex=0.0)
        assert result.severance_tax == 0.0

    def test_returns_fiscal_result(self, regime):
        result = regime.calculate_oil(gross_revenue=2_000_000.0, opex=500_000.0)
        assert isinstance(result, USFiscalResult)

    def test_government_take_is_severance_only(self, regime):
        """Texas has severance but no state income tax on extraction per se."""
        result = regime.calculate_oil(gross_revenue=1_000_000.0, opex=0.0)
        assert result.total_government_take == pytest.approx(result.severance_tax)


# ── North Dakota ───────────────────────────────────────────────────────────────

class TestNorthDakotaFiscal:
    @pytest.fixture
    def regime(self):
        return NorthDakotaFiscal()

    def test_combined_rate_approx_11_5_pct(self, regime):
        """ND: 5% extraction + 6.5% production = 11.5% combined."""
        result = regime.calculate(gross_revenue=1_000_000.0, opex=0.0)
        combined = result.severance_tax
        assert combined == pytest.approx(115_000.0, rel=0.01)

    def test_extraction_tax_5_pct(self, regime):
        result = regime.calculate(gross_revenue=1_000_000.0, opex=0.0)
        assert result.extraction_tax == pytest.approx(50_000.0, rel=0.01)

    def test_production_tax_6_5_pct(self, regime):
        result = regime.calculate(gross_revenue=1_000_000.0, opex=0.0)
        assert result.production_tax == pytest.approx(65_000.0, rel=0.01)

    def test_zero_revenue_zero_tax(self, regime):
        result = regime.calculate(gross_revenue=0.0, opex=0.0)
        assert result.severance_tax == 0.0

    def test_net_income_after_tax(self, regime):
        result = regime.calculate(gross_revenue=5_000_000.0, opex=1_000_000.0)
        expected_net = 5_000_000.0 - 1_000_000.0 - result.total_government_take
        assert result.net_income == pytest.approx(expected_net, rel=1e-6)

    def test_returns_fiscal_result(self, regime):
        result = regime.calculate(gross_revenue=2_000_000.0, opex=400_000.0)
        assert isinstance(result, USFiscalResult)


# ── GoM Crosscheck ─────────────────────────────────────────────────────────────

class TestGoMCrosscheck:
    @pytest.fixture
    def checker(self):
        return GoMCrosscheck()

    def test_crosscheck_returns_dict(self, checker):
        result = checker.compare(
            eia_production_kbd=1800.0,
            bsee_production_kbd=1750.0,
        )
        assert isinstance(result, dict)

    def test_crosscheck_has_difference_key(self, checker):
        result = checker.compare(
            eia_production_kbd=1800.0,
            bsee_production_kbd=1750.0,
        )
        assert "difference_kbd" in result

    def test_crosscheck_has_pct_difference(self, checker):
        result = checker.compare(
            eia_production_kbd=1800.0,
            bsee_production_kbd=1750.0,
        )
        assert "pct_difference" in result

    def test_crosscheck_within_tolerance_flag(self, checker):
        result = checker.compare(
            eia_production_kbd=1800.0,
            bsee_production_kbd=1800.0,
        )
        assert result["within_tolerance"] is True

    def test_crosscheck_outside_tolerance_flag(self, checker):
        result = checker.compare(
            eia_production_kbd=1800.0,
            bsee_production_kbd=1000.0,
        )
        assert result["within_tolerance"] is False

    def test_difference_is_eia_minus_bsee(self, checker):
        result = checker.compare(
            eia_production_kbd=2000.0,
            bsee_production_kbd=1900.0,
        )
        assert result["difference_kbd"] == pytest.approx(100.0)
