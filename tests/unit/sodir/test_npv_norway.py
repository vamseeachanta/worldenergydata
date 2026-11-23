"""Tests for SODIR Norwegian NPV calculator."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.sodir.npv_norway import (
    CashFlowResult,
    NorwayNPVCalculator,
    NorwegianFinancialParameters,
    TaxRegime,
)


class TestTaxRegime:
    """Tests for TaxRegime enum."""

    def test_petroleum_tax(self):
        assert TaxRegime.PETROLEUM_TAX.value == "petroleum_tax"

    def test_special_tax(self):
        assert TaxRegime.SPECIAL_TAX.value == "special_tax"

    def test_temporary_tax(self):
        assert TaxRegime.TEMPORARY_TAX.value == "temporary_tax"


class TestNorwegianFinancialParameters:
    """Tests for NorwegianFinancialParameters."""

    def test_default_values(self):
        params = NorwegianFinancialParameters()
        assert params.discount_rate == 0.08
        assert params.petroleum_tax_rate == 0.78
        assert params.corporate_tax_rate == 0.22
        assert params.special_tax_rate == 0.56
        assert params.uplift_rate == 0.056
        assert params.uplift_years == 4
        assert params.depreciation_years == 6
        assert params.working_interest == 1.0

    def test_custom_values(self):
        params = NorwegianFinancialParameters(
            discount_rate=0.10,
            oil_price_usd=90.0,
        )
        assert params.discount_rate == 0.10
        assert params.oil_price_usd == 90.0

    def test_to_dict(self):
        params = NorwegianFinancialParameters()
        d = params.to_dict()
        assert d["discount_rate"] == 0.08
        assert d["petroleum_tax_rate"] == 0.78
        assert d["oil_price_usd"] == 80.0
        assert "capex_schedule" in d

    def test_capex_schedule_default_empty(self):
        params = NorwegianFinancialParameters()
        assert params.capex_schedule == []


class TestNorwayNPVCalculator:
    """Tests for NorwayNPVCalculator."""

    def setup_method(self):
        self.params = NorwegianFinancialParameters(
            capex_schedule=[500, 500, 0, 0, 0, 0, 0, 0, 0, 0],
        )
        self.calculator = NorwayNPVCalculator(self.params)

    def _make_production_profile(self, years=10):
        """Create synthetic production profile."""
        oil = [0, 0, 10, 15, 12, 10, 8, 6, 4, 2][:years]
        gas = [0, 0, 50, 80, 60, 50, 40, 30, 20, 10][:years]
        return pd.DataFrame(
            {
                "year": list(range(years)),
                "oil_production_mmbbl": oil,
                "gas_production_bcf": gas,
            }
        )

    def test_calculate_taxes_positive_income(self):
        taxes = self.calculator.calculate_taxes(1000000)
        assert taxes["corporate_tax"] == pytest.approx(220000)
        assert taxes["total_tax"] > 0
        assert taxes["effective_rate"] > 0

    def test_calculate_taxes_zero_income(self):
        taxes = self.calculator.calculate_taxes(0)
        assert taxes["total_tax"] == 0
        assert taxes["effective_rate"] == 0

    def test_calculate_uplift(self):
        uplift = self.calculator.calculate_uplift(1000)
        assert len(uplift) == 4
        assert all(u == pytest.approx(56.0) for u in uplift)

    def test_calculate_revenue_oil(self):
        profile = pd.DataFrame({"oil_production_mmbbl": [10, 8, 6]})
        revenue = self.calculator.calculate_revenue(profile)
        assert "oil_revenue" in revenue.columns
        assert "gas_revenue" in revenue.columns
        assert "total_revenue" in revenue.columns
        assert revenue["oil_revenue"].iloc[0] > 0
        assert revenue["gas_revenue"].iloc[0] == 0

    def test_calculate_revenue_gas(self):
        profile = pd.DataFrame(
            {
                "oil_production_mmbbl": [0, 0, 0],
                "gas_production_bcf": [50, 40, 30],
            }
        )
        revenue = self.calculator.calculate_revenue(profile)
        assert revenue["gas_revenue"].iloc[0] > 0
        assert revenue["oil_revenue"].iloc[0] == 0

    def test_calculate_revenue_both(self):
        profile = pd.DataFrame(
            {
                "oil_production_mmbbl": [10, 8],
                "gas_production_bcf": [50, 40],
            }
        )
        revenue = self.calculator.calculate_revenue(profile)
        assert revenue["total_revenue"].iloc[0] > 0

    def test_calculate_opex(self):
        profile = pd.DataFrame(
            {
                "oil_production_mmbbl": [10, 8],
                "gas_production_bcf": [50, 40],
            }
        )
        opex = self.calculator.calculate_opex(profile)
        assert "total_opex" in opex.columns
        assert opex["total_opex"].iloc[0] > 0

    def test_calculate_depreciation(self):
        capex_df = pd.DataFrame({"capex": [600, 0, 0, 0, 0, 0, 0, 0]})
        depreciation = self.calculator.calculate_depreciation(capex_df)
        assert "depreciation" in depreciation.columns
        assert depreciation["depreciation"].iloc[0] == pytest.approx(100.0)

    def test_calculate_uplift_schedule(self):
        capex_df = pd.DataFrame({"capex": [1000, 0, 0, 0, 0, 0]})
        uplift = self.calculator.calculate_uplift_schedule(capex_df)
        assert "uplift" in uplift.columns
        assert uplift["uplift"].iloc[0] == pytest.approx(56.0)
        assert uplift["uplift"].iloc[3] == pytest.approx(56.0)
        assert uplift["uplift"].iloc[4] == pytest.approx(0.0)

    def test_calculate_tax_schedule(self):
        income = pd.Series([100000, -50000, 200000])
        tax_df = self.calculator.calculate_tax_schedule(income)
        assert "corporate_tax" in tax_df.columns
        assert "petroleum_tax" in tax_df.columns
        assert "total_tax" in tax_df.columns
        assert tax_df["total_tax"].iloc[1] == 0  # negative income -> 0 tax

    def test_calculate_npv_full(self):
        profile = self._make_production_profile()
        result = self.calculator.calculate_npv(profile)
        assert isinstance(result, CashFlowResult)
        assert isinstance(result.npv, float)
        assert isinstance(result.cash_flows, pd.DataFrame)
        assert "revenue" in result.cash_flows.columns
        assert "free_cash_flow" in result.cash_flows.columns

    def test_calculate_npv_metrics(self):
        profile = self._make_production_profile()
        result = self.calculator.calculate_npv(profile)
        assert "pi_ratio" in result.metrics
        assert "breakeven_oil_price" in result.metrics
        assert "government_take" in result.metrics

    def test_build_capex_dataframe(self):
        capex_df = self.calculator._build_capex_dataframe([100, 200, 300], 5)
        assert len(capex_df) == 5
        assert capex_df["capex"].iloc[0] == 100
        assert capex_df["capex"].iloc[3] == 0

    def test_calculate_npv_from_cashflows(self):
        cf = pd.Series([-100, 50, 50, 50])
        npv = self.calculator._calculate_npv_from_cashflows(cf, 0.10)
        assert npv > 0

    def test_calculate_payback(self):
        cf = pd.Series([-100, -50, 50, 100, 100])
        payback = self.calculator._calculate_payback(cf)
        assert payback is not None

    def test_calculate_payback_no_positive(self):
        cf = pd.Series([-100, -50, -20])
        payback = self.calculator._calculate_payback(cf)
        assert payback is None

    def test_cash_flow_result_summary(self):
        profile = self._make_production_profile()
        result = self.calculator.calculate_npv(profile)
        summary = result.summary()
        assert "npv_mmusd" in summary
        assert "total_revenue" in summary
        assert "total_opex" in summary
        assert "total_capex" in summary
        assert "total_tax" in summary

    def test_profitability_index_zero_capex(self):
        cf = pd.Series([100, 200, 300])
        pi = self.calculator._calculate_profitability_index(cf, 0)
        assert pi == 0
