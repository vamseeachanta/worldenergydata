"""Tests for BSEE economic reporting models."""

from datetime import date

import pytest

from worldenergydata.bsee.reports.comprehensive.templates.economic_models import (
    CostAnalysis,
    EconomicAnalysis,
    EconomicForecast,
    NPVAnalysis,
    ProfitabilityMetrics,
    ROIMetrics,
    RevenueBreakdown,
    SensitivityAnalysis,
    WaterfallComponent,
)
from worldenergydata.bsee.reports.comprehensive.hierarchical_aggregator import (
    CostStructure,
    PriceDeck,
)
from worldenergydata.bsee.reports.comprehensive.models import ProductionMetrics


class TestRevenueBreakdown:
    def test_total_revenue(self):
        r = RevenueBreakdown(
            oil_revenue=500, gas_revenue=200, ngl_revenue=50,
            water_revenue=10, other_revenue=40,
        )
        assert r.total_revenue == 800

    def test_total_revenue_zeros(self):
        r = RevenueBreakdown()
        assert r.total_revenue == 0

    def test_oil_percentage(self):
        r = RevenueBreakdown(oil_revenue=500, gas_revenue=500)
        assert r.oil_percentage == pytest.approx(50.0)

    def test_oil_percentage_zero_total(self):
        r = RevenueBreakdown()
        assert r.oil_percentage == 0.0

    def test_gas_percentage(self):
        r = RevenueBreakdown(oil_revenue=700, gas_revenue=300)
        assert r.gas_percentage == pytest.approx(30.0)

    def test_ngl_percentage(self):
        r = RevenueBreakdown(oil_revenue=800, ngl_revenue=200)
        assert r.ngl_percentage == pytest.approx(20.0)

    def test_revenue_per_boe_default(self):
        r = RevenueBreakdown()
        assert r.revenue_per_boe == 0.0

    def test_set_production_volumes(self):
        r = RevenueBreakdown(oil_revenue=800000, gas_revenue=200000)
        # 10000 bbl oil + 60000 mcf gas / 6 = 20000 BOE
        r.set_production_volumes(10000, 60000, 0)
        assert r.revenue_per_boe == pytest.approx(50.0)

    def test_set_production_volumes_zero_boe(self):
        r = RevenueBreakdown(oil_revenue=1000)
        r.set_production_volumes(0, 0, 0)
        assert r.revenue_per_boe == 0.0


class TestCostAnalysis:
    def test_total_costs(self):
        c = CostAnalysis(
            operating_costs=100, capital_costs=200, royalties=30,
            severance_tax=10, production_tax=5, transportation_costs=15,
            processing_costs=20, other_costs=5,
        )
        assert c.total_costs == 385

    def test_variable_costs(self):
        c = CostAnalysis(
            operating_costs=100, capital_costs=200, royalties=30,
            severance_tax=10, production_tax=5, transportation_costs=15,
            processing_costs=20, other_costs=5,
        )
        # Variable = total - capital - other
        assert c.variable_costs == 180

    def test_cost_per_boe_default(self):
        c = CostAnalysis()
        assert c.cost_per_boe == 0.0

    def test_set_production_volumes(self):
        c = CostAnalysis(operating_costs=100000)
        c.set_production_volumes(5000, 30000, 0)
        # 5000 + 30000/6 = 10000 BOE; 100000/10000 = 10
        assert c.cost_per_boe == pytest.approx(10.0)


class TestProfitabilityMetrics:
    def test_from_components(self):
        rev = RevenueBreakdown(oil_revenue=1000000, gas_revenue=500000)
        cost = CostAnalysis(
            operating_costs=300000, capital_costs=200000,
            royalties=100000,
        )
        prof = ProfitabilityMetrics.from_components(rev, cost)
        assert prof.gross_revenue == 1500000
        assert prof.net_income == 1500000 - 600000
        assert prof.profit_margin > 0
        assert prof.ebitda == 1500000 - 300000

    def test_from_components_zero_revenue(self):
        rev = RevenueBreakdown()
        cost = CostAnalysis(operating_costs=1000)
        prof = ProfitabilityMetrics.from_components(rev, cost)
        assert prof.profit_margin == 0
        assert prof.operating_margin == 0


class TestNPVAnalysis:
    def test_npv_empty(self):
        npv = NPVAnalysis()
        assert npv.npv == 0.0

    def test_npv_simple(self):
        npv = NPVAnalysis(
            cash_flows=[-1000, 300, 300, 300, 300],
            discount_rate=0.10,
        )
        assert npv.npv != 0.0

    def test_present_value_inflows(self):
        npv = NPVAnalysis(
            cash_flows=[-1000, 500, 500, 500],
            discount_rate=0.10,
        )
        assert npv.present_value_inflows > 0

    def test_present_value_outflows(self):
        npv = NPVAnalysis(
            cash_flows=[-1000, 500, 500, 500],
            discount_rate=0.10,
        )
        assert npv.present_value_outflows > 0

    def test_irr_calculation(self):
        npv = NPVAnalysis(
            cash_flows=[-1000, 400, 400, 400],
            discount_rate=0.10,
        )
        irr = npv.calculate_irr()
        assert irr != 0.0

    def test_irr_empty(self):
        npv = NPVAnalysis()
        assert npv.calculate_irr() == 0.0

    def test_irr_single_flow(self):
        npv = NPVAnalysis(cash_flows=[1000])
        assert npv.calculate_irr() == 0.0

    def test_sensitivity_analysis(self):
        npv = NPVAnalysis(
            cash_flows=[-1000, 300, 300, 300, 300],
            discount_rate=0.10,
        )
        result = npv.sensitivity_analysis([0.05, 0.10, 0.15])
        assert len(result) == 3
        assert 0.05 in result
        assert 0.10 in result
        assert 0.15 in result
        # Lower discount rate -> higher NPV
        assert result[0.05] > result[0.15]

    def test_sensitivity_empty(self):
        npv = NPVAnalysis()
        result = npv.sensitivity_analysis([0.05, 0.10])
        assert all(v == 0.0 for v in result.values())


class TestROIMetrics:
    def test_total_roi(self):
        roi = ROIMetrics(
            initial_investment=100000,
            annual_net_income=20000,
            project_years=10,
        )
        # (200000 - 100000) / 100000 = 1.0
        assert roi.total_roi == pytest.approx(1.0)

    def test_total_roi_zero_investment(self):
        roi = ROIMetrics(initial_investment=0, annual_net_income=20000)
        assert roi.total_roi == 0.0

    def test_annual_roi(self):
        roi = ROIMetrics(
            initial_investment=100000,
            annual_net_income=20000,
            project_years=10,
        )
        assert roi.annual_roi == pytest.approx(0.1)

    def test_annual_roi_zero_years(self):
        roi = ROIMetrics(project_years=0)
        assert roi.annual_roi == 0.0

    def test_payback_period(self):
        roi = ROIMetrics(
            initial_investment=100000,
            annual_net_income=25000,
        )
        assert roi.payback_period_years == pytest.approx(4.0)

    def test_payback_period_zero_income(self):
        roi = ROIMetrics(
            initial_investment=100000,
            annual_net_income=0,
        )
        assert roi.payback_period_years == float("inf")

    def test_payback_period_negative_income(self):
        roi = ROIMetrics(
            initial_investment=100000,
            annual_net_income=-10000,
        )
        assert roi.payback_period_years == float("inf")


class TestEconomicForecast:
    def test_forecast_production_empty(self):
        f = EconomicForecast()
        assert f.forecast_production([]) == []

    def test_forecast_production_basic(self):
        historical = [
            {"year": 2023, "oil_bbls": 100000, "gas_mcf": 500000},
        ]
        f = EconomicForecast()
        result = f.forecast_production(historical, forecast_years=3, decline_rate=0.10)
        assert len(result) == 3
        assert result[0]["year"] == 2024
        assert result[1]["year"] == 2025
        assert result[2]["year"] == 2026
        # Oil declines at 10% per year
        assert result[0]["oil_bbls"] == pytest.approx(90000.0)
        assert result[1]["oil_bbls"] == pytest.approx(81000.0)

    def test_forecast_production_non_negative(self):
        historical = [
            {"year": 2023, "oil_bbls": 100, "gas_mcf": 100},
        ]
        f = EconomicForecast()
        result = f.forecast_production(historical, forecast_years=100, decline_rate=0.5)
        for r in result:
            assert r["oil_bbls"] >= 0
            assert r["gas_mcf"] >= 0


class TestWaterfallComponent:
    def test_positive(self):
        w = WaterfallComponent(
            name="Oil Revenue", value=1000000,
            component_type="revenue",
        )
        assert w.is_positive() is True

    def test_negative(self):
        w = WaterfallComponent(
            name="OPEX", value=-500000,
            component_type="cost",
        )
        assert w.is_positive() is False

    def test_zero(self):
        w = WaterfallComponent(
            name="Break Even", value=0,
            component_type="profit",
        )
        assert w.is_positive() is True

    def test_category_default(self):
        w = WaterfallComponent(
            name="Test", value=100, component_type="revenue",
        )
        assert w.category == "general"


class TestRevenueBreakdownFromProduction:
    def test_from_production_basic(self):
        pd_obj = PriceDeck(oil_price=75.0, gas_price=3.50, ngl_price=30.0)
        production = {"oil_bbls": 1000, "gas_mcf": 5000, "ngl_bbls": 200}
        rb = RevenueBreakdown.from_production(production, pd_obj)
        assert rb.oil_revenue == pytest.approx(75000.0)
        assert rb.gas_revenue == pytest.approx(17500.0)
        assert rb.ngl_revenue == pytest.approx(6000.0)
        assert rb.total_revenue == pytest.approx(98500.0)

    def test_from_production_zero_volumes(self):
        pd_obj = PriceDeck(oil_price=75.0, gas_price=3.50, ngl_price=30.0)
        production = {}
        rb = RevenueBreakdown.from_production(production, pd_obj)
        assert rb.total_revenue == 0.0

    def test_from_production_sets_revenue_per_boe(self):
        pd_obj = PriceDeck(oil_price=75.0, gas_price=3.50, ngl_price=30.0)
        production = {"oil_bbls": 1000, "gas_mcf": 6000}
        rb = RevenueBreakdown.from_production(production, pd_obj)
        # BOE = 1000 + 6000/6 = 2000
        expected_per_boe = rb.total_revenue / 2000
        assert rb.revenue_per_boe == pytest.approx(expected_per_boe)


class TestCostAnalysisFromProduction:
    def test_from_production_basic(self):
        cs = CostStructure(
            operating_cost_per_bbl=12.50,
            royalty_rate=0.1875,
            severance_tax_rate=0.05,
        )
        production = {"oil_bbls": 1000, "gas_mcf": 6000}
        revenue_data = {"total_revenue": 100000.0}
        ca = CostAnalysis.from_production(production, revenue_data, cs)
        # BOE = 1000 + 1000 = 2000; opex = 2000 * 12.50 = 25000
        assert ca.operating_costs == pytest.approx(25000.0)
        assert ca.royalties == pytest.approx(18750.0)
        assert ca.severance_tax == pytest.approx(5000.0)

    def test_from_production_zero(self):
        cs = CostStructure()
        production = {}
        revenue_data = {"total_revenue": 0}
        ca = CostAnalysis.from_production(production, revenue_data, cs)
        assert ca.operating_costs == 0.0
        assert ca.royalties == 0.0

    def test_from_production_sets_cost_per_boe(self):
        cs = CostStructure(operating_cost_per_bbl=10.0, royalty_rate=0, severance_tax_rate=0)
        production = {"oil_bbls": 1000, "gas_mcf": 0}
        revenue_data = {"total_revenue": 0}
        ca = CostAnalysis.from_production(production, revenue_data, cs)
        # BOE = 1000; total_costs = 10000; cost_per_boe = 10
        assert ca.cost_per_boe == pytest.approx(10.0)


class TestEconomicForecastRevenue:
    def test_forecast_revenue_basic(self):
        pd_obj = PriceDeck(oil_price=75.0, gas_price=3.50)
        production_forecast = [
            {"year": 2024, "oil_bbls": 100000, "gas_mcf": 500000},
            {"year": 2025, "oil_bbls": 90000, "gas_mcf": 450000},
        ]
        f = EconomicForecast()
        result = f.forecast_revenue(production_forecast, pd_obj, price_escalation=0.02)
        assert len(result) == 2
        assert result[0]["year"] == 2024
        # Year 0: no escalation
        assert result[0]["oil_revenue"] == pytest.approx(100000 * 75.0)
        assert result[0]["gas_revenue"] == pytest.approx(500000 * 3.50)
        # Year 1: 2% escalation
        assert result[1]["oil_price"] == pytest.approx(75.0 * 1.02)

    def test_forecast_revenue_empty(self):
        pd_obj = PriceDeck()
        f = EconomicForecast()
        result = f.forecast_revenue([], pd_obj)
        assert result == []

    def test_forecast_revenue_has_all_fields(self):
        pd_obj = PriceDeck(oil_price=80.0, gas_price=4.0)
        production_forecast = [
            {"year": 2024, "oil_bbls": 50000, "gas_mcf": 200000},
        ]
        f = EconomicForecast()
        result = f.forecast_revenue(production_forecast, pd_obj)
        entry = result[0]
        assert "oil_revenue" in entry
        assert "gas_revenue" in entry
        assert "total_revenue" in entry
        assert "oil_price" in entry
        assert "gas_price" in entry
        assert entry["total_revenue"] == entry["oil_revenue"] + entry["gas_revenue"]


class TestSensitivityAnalysisOilPrice:
    def _make_metrics(self, **kwargs):
        defaults = {
            "oil_production_bbls": 10000,
            "gas_production_mcf": 50000,
            "oil_price_usd": 75.0,
            "gas_price_usd": 3.50,
            "operating_cost_usd": 200000,
        }
        defaults.update(kwargs)
        return ProductionMetrics(**defaults)

    def test_oil_price_sensitivity(self):
        metrics = self._make_metrics()
        sa = SensitivityAnalysis()
        result = sa.analyze_oil_price_sensitivity(metrics, [-20, 0, 20])
        assert len(result) == 3
        assert result[0]["price_change_pct"] == -20
        assert result[1]["price_change_pct"] == 0
        assert result[2]["price_change_pct"] == 20
        # Higher oil price -> higher revenue
        assert result[2]["total_revenue"] > result[0]["total_revenue"]

    def test_oil_price_sensitivity_fields(self):
        metrics = self._make_metrics()
        sa = SensitivityAnalysis()
        result = sa.analyze_oil_price_sensitivity(metrics, [0])
        entry = result[0]
        assert "new_oil_price" in entry
        assert "total_revenue" in entry
        assert "net_income" in entry
        assert "npv" in entry


class TestSensitivityAnalysisProduction:
    def _make_metrics(self, **kwargs):
        defaults = {
            "oil_production_bbls": 10000,
            "gas_production_mcf": 50000,
            "oil_price_usd": 75.0,
            "gas_price_usd": 3.50,
            "operating_cost_usd": 200000,
        }
        defaults.update(kwargs)
        return ProductionMetrics(**defaults)

    def test_production_sensitivity(self):
        metrics = self._make_metrics()
        sa = SensitivityAnalysis()
        result = sa.analyze_production_sensitivity(metrics, [-10, 0, 10])
        assert len(result) == 3
        # Higher production -> higher revenue
        assert result[2]["total_revenue"] > result[0]["total_revenue"]

    def test_production_sensitivity_fields(self):
        metrics = self._make_metrics()
        sa = SensitivityAnalysis()
        result = sa.analyze_production_sensitivity(metrics, [0])
        entry = result[0]
        assert "new_oil_production" in entry
        assert "new_gas_production" in entry
        assert "net_income" in entry


class TestSensitivityAnalysisCost:
    def _make_metrics(self, **kwargs):
        defaults = {
            "oil_production_bbls": 10000,
            "gas_production_mcf": 50000,
            "oil_price_usd": 75.0,
            "gas_price_usd": 3.50,
            "operating_cost_usd": 200000,
        }
        defaults.update(kwargs)
        return ProductionMetrics(**defaults)

    def test_cost_sensitivity(self):
        metrics = self._make_metrics()
        sa = SensitivityAnalysis()
        result = sa.analyze_cost_sensitivity(metrics, [-10, 0, 10])
        assert len(result) == 3
        # Higher cost -> lower net income
        assert result[0]["net_income"] > result[2]["net_income"]

    def test_cost_sensitivity_fields(self):
        metrics = self._make_metrics()
        sa = SensitivityAnalysis()
        result = sa.analyze_cost_sensitivity(metrics, [0])
        entry = result[0]
        assert "cost_change_pct" in entry
        assert "new_operating_cost" in entry
        assert "npv" in entry


class TestEconomicAnalysisFromProductionMetrics:
    def test_from_production_metrics(self):
        metrics = ProductionMetrics(
            entity_id="FIELD-001",
            oil_production_bbls=10000,
            gas_production_mcf=50000,
        )
        pd_obj = PriceDeck(oil_price=75.0, gas_price=3.50)
        cs = CostStructure(operating_cost_per_bbl=12.50, royalty_rate=0.1875)
        analysis = EconomicAnalysis.from_production_metrics(
            metrics, pd_obj, cs, entity_id="FIELD-001",
        )
        assert analysis.entity_id == "FIELD-001"
        assert analysis.entity_type == "field"
        assert analysis.revenue_breakdown.oil_revenue == pytest.approx(750000.0)
        assert analysis.profitability_metrics.gross_revenue > 0

    def test_from_production_metrics_default_entity_id(self):
        metrics = ProductionMetrics(
            entity_id="WELL-X",
            oil_production_bbls=1000,
        )
        pd_obj = PriceDeck()
        cs = CostStructure()
        analysis = EconomicAnalysis.from_production_metrics(
            metrics, pd_obj, cs,
        )
        assert analysis.entity_id == "WELL-X"

    def test_from_production_metrics_no_entity_id(self):
        metrics = ProductionMetrics(oil_production_bbls=1000)
        pd_obj = PriceDeck()
        cs = CostStructure()
        analysis = EconomicAnalysis.from_production_metrics(
            metrics, pd_obj, cs,
        )
        assert analysis.entity_id == "unknown"
