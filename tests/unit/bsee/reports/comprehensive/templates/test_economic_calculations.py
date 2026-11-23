"""Tests for economic calculation utilities."""

from worldenergydata.bsee.reports.comprehensive.templates.economic_calculations import (
    calculate_cost_structure_analysis,
    calculate_enhanced_netback_analysis,
    calculate_revenue_optimization_analysis,
    get_economic_kpis,
    identify_revenue_optimization_opportunities,
    prepare_tornado_chart_data,
)


class TestEnhancedNetbackAnalysis:
    def test_basic_calculation(self):
        context = {
            "revenue_breakdown": {
                "oil_revenue": 1000000,
                "gas_revenue": 500000,
                "ngl_revenue": 100000,
                "total_revenue": 1600000,
            },
            "cost_analysis": {
                "operating_costs": 200000,
                "royalties": 100000,
                "severance_tax": 50000,
                "transportation_costs": 30000,
                "processing_costs": 20000,
                "variable_costs": 400000,
            },
            "production_metrics": {
                "oil_bbls": 20000,
                "gas_mcf": 60000,
            },
        }
        result = calculate_enhanced_netback_analysis(context)
        assert "revenue_per_boe_breakdown" in result
        assert "cost_per_boe_breakdown" in result
        assert "netback_calculation" in result
        assert "netback_percentages" in result
        assert "total_boe" in result
        # 20000 + 60000/6 = 30000 BOE
        assert result["total_boe"] == 30000

    def test_empty_context(self):
        result = calculate_enhanced_netback_analysis({})
        assert result["total_boe"] == 1  # fallback when no production

    def test_netback_decreasing(self):
        context = {
            "revenue_breakdown": {
                "total_revenue": 1000,
                "oil_revenue": 800,
                "gas_revenue": 200,
                "ngl_revenue": 0,
            },
            "cost_analysis": {
                "operating_costs": 200,
                "royalties": 100,
                "severance_tax": 0,
                "transportation_costs": 0,
                "processing_costs": 0,
                "variable_costs": 300,
            },
            "production_metrics": {"oil_bbls": 100, "gas_mcf": 0},
        }
        result = calculate_enhanced_netback_analysis(context)
        nc = result["netback_calculation"]
        assert nc["gross_netback_per_boe"] >= nc["operating_netback_per_boe"]
        assert nc["operating_netback_per_boe"] >= nc["royalty_netback_per_boe"]

    def test_netback_percentages_with_revenue(self):
        context = {
            "revenue_breakdown": {
                "total_revenue": 1000,
                "oil_revenue": 1000,
                "gas_revenue": 0,
                "ngl_revenue": 0,
            },
            "cost_analysis": {
                "operating_costs": 200,
                "royalties": 100,
                "severance_tax": 0,
                "transportation_costs": 0,
                "processing_costs": 0,
                "variable_costs": 300,
            },
            "production_metrics": {"oil_bbls": 100, "gas_mcf": 0},
        }
        result = calculate_enhanced_netback_analysis(context)
        assert "operating_netback_pct" in result["netback_percentages"]
        assert "full_netback_pct" in result["netback_percentages"]


class TestCostStructureAnalysis:
    def test_basic(self):
        context = {
            "cost_analysis": {
                "total_costs": 500000,
                "operating_costs": 200000,
                "capital_costs": 150000,
                "royalties": 50000,
                "severance_tax": 50000,
                "other_costs": 50000,
                "variable_costs": 300000,
            },
            "revenue_breakdown": {"total_revenue": 1000000},
        }
        result = calculate_cost_structure_analysis(context)
        assert "cost_breakdown_percentages" in result
        assert "cost_as_revenue_percentages" in result
        assert "cost_efficiency_metrics" in result
        assert "absolute_costs" in result
        assert result["cost_breakdown_percentages"]["operating_costs_pct"] == 40.0

    def test_zero_costs(self):
        context = {
            "cost_analysis": {"total_costs": 0},
            "revenue_breakdown": {"total_revenue": 0},
        }
        result = calculate_cost_structure_analysis(context)
        assert result["cost_breakdown_percentages"] == {}
        assert result["cost_as_revenue_percentages"] == {}

    def test_efficiency_index(self):
        context = {
            "cost_analysis": {
                "total_costs": 400,
                "operating_costs": 200,
                "variable_costs": 200,
            },
            "revenue_breakdown": {"total_revenue": 1000},
        }
        result = calculate_cost_structure_analysis(context)
        # 1 - (400/1000) = 0.6
        assert result["cost_efficiency_metrics"]["cost_efficiency_index"] == 0.6


class TestRevenueOptimizationAnalysis:
    def test_basic(self):
        context = {
            "revenue_breakdown": {
                "oil_revenue": 800000,
                "gas_revenue": 150000,
                "ngl_revenue": 50000,
                "total_revenue": 1000000,
                "oil_percentage": 80,
                "gas_percentage": 15,
                "ngl_percentage": 5,
            },
            "production_metrics": {
                "oil_bbls": 10000,
                "gas_mcf": 50000,
            },
        }
        result = calculate_revenue_optimization_analysis(context)
        assert "revenue_per_unit" in result
        assert "revenue_mix" in result
        assert "revenue_quality_metrics" in result
        assert "optimization_opportunities" in result

    def test_revenue_per_unit(self):
        context = {
            "revenue_breakdown": {
                "oil_revenue": 100000,
                "gas_revenue": 50000,
                "total_revenue": 150000,
                "oil_percentage": 67,
                "gas_percentage": 33,
                "ngl_percentage": 0,
            },
            "production_metrics": {
                "oil_bbls": 1000,
                "gas_mcf": 10000,
            },
        }
        result = calculate_revenue_optimization_analysis(context)
        assert result["revenue_per_unit"]["oil_revenue_per_bbl"] == 100.0
        assert result["revenue_per_unit"]["gas_revenue_per_mcf"] == 5.0

    def test_empty_context(self):
        result = calculate_revenue_optimization_analysis({})
        assert result["revenue_per_unit"] == {}
        assert result["revenue_mix"] == {}


class TestIdentifyRevenueOptimizationOpportunities:
    def test_high_gas_dependency(self):
        opp = identify_revenue_optimization_opportunities(
            {}, {"gas_revenue_dependency": 0.7}
        )
        assert any("gas dependence" in o for o in opp)

    def test_low_diversification(self):
        opp = identify_revenue_optimization_opportunities(
            {}, {"revenue_diversification_index": 0.2}
        )
        assert any("diversification" in o.lower() for o in opp)

    def test_low_ngl(self):
        opp = identify_revenue_optimization_opportunities(
            {"ngl_revenue_percentage": 2}, {}
        )
        assert any("NGL" in o for o in opp)

    def test_high_concentration(self):
        opp = identify_revenue_optimization_opportunities(
            {}, {"revenue_concentration_risk": 0.9}
        )
        assert any("concentration" in o.lower() for o in opp)

    def test_no_issues(self):
        opp = identify_revenue_optimization_opportunities(
            {"ngl_revenue_percentage": 10},
            {
                "gas_revenue_dependency": 0.3,
                "revenue_diversification_index": 0.5,
                "revenue_concentration_risk": 0.5,
            },
        )
        assert opp == []


class TestGetEconomicKpis:
    def test_basic(self):
        context = {
            "profitability_metrics": {
                "net_income": 500000,
                "profit_margin": 30,
                "operating_margin": 40,
                "ebitda": 600000,
            },
            "npv_analysis": {"npv": 1000000, "irr": 0.15},
            "roi_metrics": {"annual_roi": 0.25, "payback_period_years": 4},
        }
        netback = {
            "netback_calculation": {
                "full_netback_per_boe": 50,
                "operating_netback_per_boe": 60,
            },
            "revenue_per_boe_breakdown": {"total_revenue_per_boe": 80},
            "cost_per_boe_breakdown": {
                "total_variable_cost_per_boe": 30,
                "operating_cost_per_boe": 20,
                "royalties_per_boe": 5,
            },
            "netback_percentages": {"full_netback_pct": 62.5},
        }
        result = get_economic_kpis(context, netback)
        assert result["primary_kpis"]["net_income"] == 500000
        assert result["primary_kpis"]["npv"] == 1000000
        assert result["secondary_kpis"]["irr"] == 0.15

    def test_empty_context(self):
        context = {}
        netback = {
            "netback_calculation": {},
            "revenue_per_boe_breakdown": {},
            "cost_per_boe_breakdown": {},
            "netback_percentages": {},
        }
        result = get_economic_kpis(context, netback)
        assert result["primary_kpis"]["net_income"] == 0


class TestPrepareTornadoChartData:
    def test_basic(self):
        oil = [{"npv": 800}, {"npv": 1200}]
        prod = [{"npv": 900}, {"npv": 1100}]
        cost = [{"npv": 950}, {"npv": 1050}]
        result = prepare_tornado_chart_data(oil, prod, cost)
        assert len(result) == 3
        # Sorted by impact range descending: oil(400) > prod(200) > cost(100)
        assert result[0]["variable"] == "Oil Price"
        assert result[0]["impact_range"] == 400
        assert result[1]["variable"] == "Production Volume"
        assert result[2]["variable"] == "Operating Costs"

    def test_low_high_cases(self):
        oil = [{"npv": 500}, {"npv": 1500}]
        prod = [{"npv": 700}, {"npv": 1300}]
        cost = [{"npv": 800}, {"npv": 1200}]
        result = prepare_tornado_chart_data(oil, prod, cost)
        assert result[0]["low_case"] == 500
        assert result[0]["high_case"] == 1500
