"""Tests for go-by economic report calculations."""

import pytest

from worldenergydata.bsee.reports.comprehensive.templates.economic_goby import (
    calculate_goby_14_row_structure,
    integrate_goby_field_economics,
)


# ---------------------------------------------------------------------------
# calculate_goby_14_row_structure
# ---------------------------------------------------------------------------

class TestCalculateGoby14RowStructure:
    def test_basic(self):
        prod = {"oil_bbls": 10000, "gas_mcf": 60000, "water_bbls": 5000}
        rev = {"oil_revenue": 750000, "gas_revenue": 180000, "ngl_revenue": 0, "gross_revenue": 930000}
        costs = {"operating_cost": 200000, "royalties": 100000, "severance_tax": 50000, "total_costs": 350000, "net_income": 580000}

        result = calculate_goby_14_row_structure(prod, rev, costs)

        assert result["row_1_oil_production_bbls"] == 10000
        assert result["row_2_gas_production_mcf"] == 60000
        assert result["row_3_water_production_bbls"] == 5000
        assert result["row_4_total_boe"] == 10000 + (60000 / 6)
        assert result["row_8_gross_revenue_usd"] == 930000
        assert result["row_13_net_income_usd"] == 580000

    def test_profit_margin(self):
        prod = {"oil_bbls": 100}
        rev = {"gross_revenue": 1000}
        costs = {"net_income": 200}
        result = calculate_goby_14_row_structure(prod, rev, costs)
        assert result["row_14_profit_margin_pct"] == pytest.approx(20.0)

    def test_zero_revenue_profit_margin(self):
        prod = {"oil_bbls": 100}
        rev = {"gross_revenue": 0}
        costs = {"net_income": 0}
        result = calculate_goby_14_row_structure(prod, rev, costs)
        assert result["row_14_profit_margin_pct"] == 0

    def test_per_boe_calculations(self):
        prod = {"oil_bbls": 10000, "gas_mcf": 0}
        rev = {"gross_revenue": 750000}
        costs = {"operating_cost": 200000, "royalties": 50000, "net_income": 500000, "total_costs": 250000}
        result = calculate_goby_14_row_structure(prod, rev, costs)
        assert result["revenue_per_boe"] == pytest.approx(75.0)
        assert result["operating_cost_per_boe"] == pytest.approx(20.0)

    def test_zero_boe_no_per_boe(self):
        prod = {"oil_bbls": 0, "gas_mcf": 0}
        rev = {"gross_revenue": 0}
        costs = {}
        result = calculate_goby_14_row_structure(prod, rev, costs)
        assert "revenue_per_boe" not in result

    def test_gas_oil_ratio(self):
        prod = {"oil_bbls": 1000, "gas_mcf": 5000, "water_bbls": 200}
        rev = {}
        costs = {}
        result = calculate_goby_14_row_structure(prod, rev, costs)
        assert result["gas_oil_ratio"] == pytest.approx(5.0)

    def test_water_cut(self):
        prod = {"oil_bbls": 7000, "gas_mcf": 0, "water_bbls": 3000}
        rev = {}
        costs = {}
        result = calculate_goby_14_row_structure(prod, rev, costs)
        assert result["water_cut_pct"] == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# integrate_goby_field_economics
# ---------------------------------------------------------------------------

class TestIntegrateGobyFieldEconomics:
    def test_basic(self):
        metrics = {
            "total_wells": 10,
            "active_wells": 8,
            "total_leases": 5,
            "oil_production_bbls": 50000,
            "gas_production_mcf": 200000,
            "water_production_bbls": 20000,
            "total_boe": 83333,
            "gross_revenue": 5000000,
            "operating_cost": 1000000,
            "royalties": 500000,
            "severance_tax": 200000,
            "total_costs": 1700000,
            "net_income": 3300000,
        }
        result = integrate_goby_field_economics(metrics)
        assert result["field_summary"]["total_wells"] == 10
        assert result["field_economics"]["gross_revenue"] == 5000000
        assert result["field_performance"]["avg_revenue_per_well"] == pytest.approx(500000.0)

    def test_empty_metrics(self):
        result = integrate_goby_field_economics({})
        assert result["field_summary"]["total_wells"] == 0
        assert result["field_economics"]["gross_revenue"] == 0
