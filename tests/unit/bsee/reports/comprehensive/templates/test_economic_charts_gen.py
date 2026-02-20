"""Tests for economic_charts Plotly chart generation functions."""

import pytest

from worldenergydata.bsee.reports.comprehensive.templates.economic_charts import (
    create_empty_chart,
    generate_economic_dashboard,
    generate_production_economics_time_series,
    generate_sensitivity_tornado_chart,
    generate_waterfall_chart,
)
from worldenergydata.bsee.reports.comprehensive.templates.economic_models import (
    WaterfallComponent,
)


# ---------------------------------------------------------------------------
# create_empty_chart
# ---------------------------------------------------------------------------

class TestCreateEmptyChart:
    def test_default_message(self):
        html = create_empty_chart()
        assert isinstance(html, str)
        assert len(html) > 0

    def test_custom_message(self):
        html = create_empty_chart("Custom message")
        assert isinstance(html, str)


# ---------------------------------------------------------------------------
# generate_waterfall_chart
# ---------------------------------------------------------------------------

class TestGenerateWaterfallChart:
    def test_empty_components(self):
        result = generate_waterfall_chart([])
        assert isinstance(result, str)  # Returns empty chart HTML

    def test_basic_waterfall(self):
        components = [
            WaterfallComponent("Oil Revenue", 5000000, "revenue", "hydrocarbon"),
            WaterfallComponent("Gas Revenue", 2000000, "revenue", "hydrocarbon"),
            WaterfallComponent("Operating Costs", -3000000, "cost", "operational"),
            WaterfallComponent("Net Income", 4000000, "profit", "final"),
        ]
        result = generate_waterfall_chart(components)
        assert isinstance(result, str)
        assert "waterfall-chart" in result

    def test_revenue_type(self):
        components = [
            WaterfallComponent("Oil Revenue", 5000000, "revenue", "hydrocarbon"),
        ]
        result = generate_waterfall_chart(components)
        assert isinstance(result, str)

    def test_cost_type(self):
        components = [
            WaterfallComponent("OPEX", -3000000, "cost", "operational"),
            WaterfallComponent("Net", -3000000, "profit", "final"),
        ]
        result = generate_waterfall_chart(components)
        assert isinstance(result, str)

    def test_other_type(self):
        components = [
            WaterfallComponent("Other Item", 1000000, "other", "misc"),
            WaterfallComponent("Net", 1000000, "profit", "final"),
        ]
        result = generate_waterfall_chart(components)
        assert isinstance(result, str)

    def test_many_components_rotates_labels(self):
        components = [
            WaterfallComponent(f"Item {i}", i * 100000, "revenue", "misc")
            for i in range(8)
        ]
        result = generate_waterfall_chart(components)
        assert isinstance(result, str)

    def test_custom_title(self):
        components = [
            WaterfallComponent("Revenue", 1000000, "revenue", "hydrocarbon"),
            WaterfallComponent("Net", 1000000, "profit", "final"),
        ]
        result = generate_waterfall_chart(components, title="My Custom Title")
        assert isinstance(result, str)

    def test_large_and_small_values(self):
        components = [
            WaterfallComponent("Large", 5000000, "revenue", "hydrocarbon"),
            WaterfallComponent("Small", 500, "revenue", "hydrocarbon"),
            WaterfallComponent("Net", 5000500, "profit", "final"),
        ]
        result = generate_waterfall_chart(components)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# generate_economic_dashboard
# ---------------------------------------------------------------------------

class TestGenerateEconomicDashboard:
    def _make_context(self):
        return {
            "profitability_metrics": {"profit_margin": 25.0},
            "revenue_breakdown": {
                "oil_revenue": 5000000,
                "gas_revenue": 2000000,
                "ngl_revenue": 500000,
            },
            "cost_analysis": {
                "operating_costs": 2000000,
                "royalties": 500000,
                "severance_tax": 200000,
                "capital_costs": 1000000,
            },
            "sensitivity_analysis": {
                "oil_price_sensitivity": [
                    {"price_change_pct": -20, "npv": 3000000},
                    {"price_change_pct": 0, "npv": 5000000},
                    {"price_change_pct": 20, "npv": 7000000},
                ]
            },
        }

    def _make_netback(self):
        return {
            "revenue_per_boe_breakdown": {"total_revenue_per_boe": 65.0},
            "cost_per_boe_breakdown": {
                "operating_cost_per_boe": 25.0,
                "royalties_per_boe": 8.0,
            },
            "netback_calculation": {"full_netback_per_boe": 32.0},
        }

    def test_full_dashboard(self):
        result = generate_economic_dashboard(self._make_context(), self._make_netback())
        assert isinstance(result, str)
        assert "economic-dashboard" in result

    def test_empty_context(self):
        result = generate_economic_dashboard({}, self._make_netback())
        assert isinstance(result, str)

    def test_custom_title(self):
        result = generate_economic_dashboard(
            self._make_context(), self._make_netback(), title="Custom Dashboard"
        )
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# generate_sensitivity_tornado_chart
# ---------------------------------------------------------------------------

class TestGenerateSensitivityTornadoChart:
    def test_empty_data(self):
        result = generate_sensitivity_tornado_chart([])
        assert isinstance(result, str)

    def test_basic_tornado(self):
        tornado_data = [
            {"variable": "Oil Price", "low_case": 2000000, "high_case": 8000000},
            {"variable": "Production", "low_case": 3000000, "high_case": 7000000},
            {"variable": "OPEX", "low_case": 4000000, "high_case": 6000000},
        ]
        result = generate_sensitivity_tornado_chart(tornado_data)
        assert isinstance(result, str)
        assert "tornado-chart" in result

    def test_custom_title(self):
        tornado_data = [
            {"variable": "Oil Price", "low_case": 2000000, "high_case": 8000000},
        ]
        result = generate_sensitivity_tornado_chart(tornado_data, title="Custom Tornado")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# generate_production_economics_time_series
# ---------------------------------------------------------------------------

class TestGenerateProductionEconomicsTimeSeries:
    def test_basic(self):
        context = {
            "production_metrics": {
                "oil_bbls": 1000000,
                "gas_mcf": 6000000,
            },
        }
        netback = {
            "netback_calculation": {"full_netback_per_boe": 30.0},
        }
        result = generate_production_economics_time_series(context, netback)
        assert isinstance(result, str)
        assert "time-series-chart" in result

    def test_empty_context(self):
        result = generate_production_economics_time_series(
            {}, {"netback_calculation": {"full_netback_per_boe": 30.0}}
        )
        assert isinstance(result, str)

    def test_custom_title(self):
        context = {"production_metrics": {"oil_bbls": 500000, "gas_mcf": 3000000}}
        netback = {"netback_calculation": {"full_netback_per_boe": 25.0}}
        result = generate_production_economics_time_series(
            context, netback, title="Custom Time Series"
        )
        assert isinstance(result, str)
