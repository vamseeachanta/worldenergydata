"""Tests for hierarchical aggregator PriceDeck, CostStructure, and BaseAggregator."""

import pytest

from worldenergydata.bsee.reports.comprehensive.hierarchical_aggregator import (
    CostStructure,
    PriceDeck,
)


class TestPriceDeck:
    def test_defaults(self):
        pd = PriceDeck()
        assert pd.oil_price == 75.00
        assert pd.gas_price == 3.50
        assert pd.ngl_price == 30.00

    def test_custom_prices(self):
        pd = PriceDeck(oil_price=80.0, gas_price=4.0, ngl_price=35.0)
        assert pd.oil_price == 80.0
        assert pd.gas_price == 4.0
        assert pd.ngl_price == 35.0

    def test_get_oil_revenue(self):
        pd = PriceDeck(oil_price=75.0)
        assert pd.get_oil_revenue(1000) == 75000.0

    def test_get_oil_revenue_zero(self):
        pd = PriceDeck()
        assert pd.get_oil_revenue(0) == 0.0

    def test_get_gas_revenue(self):
        pd = PriceDeck(gas_price=3.50)
        assert pd.get_gas_revenue(10000) == 35000.0

    def test_get_ngl_revenue(self):
        pd = PriceDeck(ngl_price=30.0)
        assert pd.get_ngl_revenue(500) == 15000.0


class TestCostStructure:
    def test_defaults(self):
        cs = CostStructure()
        assert cs.operating_cost_per_bbl == 12.50
        assert cs.royalty_rate == 0.1875
        assert cs.severance_tax_rate == 0.05

    def test_custom(self):
        cs = CostStructure(
            operating_cost_per_bbl=15.0,
            royalty_rate=0.20,
            severance_tax_rate=0.06,
        )
        assert cs.operating_cost_per_bbl == 15.0
        assert cs.royalty_rate == 0.20

    def test_get_operating_cost_oil_only(self):
        cs = CostStructure(operating_cost_per_bbl=10.0)
        # 1000 bbl oil + 0 gas = 1000 BOE
        assert cs.get_operating_cost(1000, 0) == 10000.0

    def test_get_operating_cost_with_gas(self):
        cs = CostStructure(operating_cost_per_bbl=10.0)
        # 1000 bbl oil + 6000 mcf gas = 1000 + 1000 = 2000 BOE
        assert cs.get_operating_cost(1000, 6000) == 20000.0

    def test_get_royalties(self):
        cs = CostStructure(royalty_rate=0.1875)
        assert cs.get_royalties(100000) == 18750.0

    def test_get_severance_tax(self):
        cs = CostStructure(severance_tax_rate=0.05)
        assert cs.get_severance_tax(100000) == 5000.0


class TestBaseAggregatorCalculateRevenue:
    """Test calculate_revenue via PriceDeck directly since BaseAggregator
    imports HierarchicalDataLoader which we want to avoid."""

    def test_oil_only_revenue(self):
        pd = PriceDeck(oil_price=75.0)
        production = {"oil_bbls": 1000}
        revenue = {
            "oil_revenue": pd.get_oil_revenue(production.get("oil_bbls", 0)),
            "gas_revenue": pd.get_gas_revenue(production.get("gas_mcf", 0)),
            "ngl_revenue": pd.get_ngl_revenue(production.get("ngl_bbls", 0)),
        }
        revenue["gross_revenue"] = sum(revenue.values())
        assert revenue["oil_revenue"] == 75000.0
        assert revenue["gas_revenue"] == 0.0
        assert revenue["ngl_revenue"] == 0.0
        assert revenue["gross_revenue"] == 75000.0

    def test_mixed_revenue(self):
        pd = PriceDeck(oil_price=75.0, gas_price=3.50, ngl_price=30.0)
        production = {"oil_bbls": 1000, "gas_mcf": 5000, "ngl_bbls": 200}
        oil_rev = pd.get_oil_revenue(production["oil_bbls"])
        gas_rev = pd.get_gas_revenue(production["gas_mcf"])
        ngl_rev = pd.get_ngl_revenue(production["ngl_bbls"])
        gross = oil_rev + gas_rev + ngl_rev
        assert oil_rev == 75000.0
        assert gas_rev == 17500.0
        assert ngl_rev == 6000.0
        assert gross == 98500.0


class TestCostCalculation:
    def test_full_cost_calculation(self):
        cs = CostStructure(
            operating_cost_per_bbl=12.50,
            royalty_rate=0.1875,
            severance_tax_rate=0.05,
        )
        production = {"oil_bbls": 1000, "gas_mcf": 6000}
        gross_revenue = 100000.0

        op_cost = cs.get_operating_cost(production["oil_bbls"], production["gas_mcf"])
        royalties = cs.get_royalties(gross_revenue)
        sev_tax = cs.get_severance_tax(gross_revenue)
        total_costs = op_cost + royalties + sev_tax
        net_income = gross_revenue - total_costs

        # 1000 + 1000 BOE * 12.50 = 25000
        assert op_cost == 25000.0
        assert royalties == 18750.0
        assert sev_tax == 5000.0
        assert total_costs == 48750.0
        assert net_income == 51250.0

    def test_zero_production(self):
        cs = CostStructure()
        assert cs.get_operating_cost(0, 0) == 0.0
        assert cs.get_royalties(0) == 0.0
        assert cs.get_severance_tax(0) == 0.0


# ---------------------------------------------------------------------------
# BaseAggregator (actual class instance)
# ---------------------------------------------------------------------------


class TestBaseAggregatorInstance:
    def test_default_init(self):
        from worldenergydata.bsee.reports.comprehensive.hierarchical_aggregator import (
            BaseAggregator,
        )

        agg = BaseAggregator()
        assert isinstance(agg.price_deck, PriceDeck)
        assert isinstance(agg.cost_structure, CostStructure)

    def test_custom_init(self):
        from worldenergydata.bsee.reports.comprehensive.hierarchical_aggregator import (
            BaseAggregator,
        )

        pd_custom = PriceDeck(oil_price=80.0)
        cs_custom = CostStructure(royalty_rate=0.20)
        agg = BaseAggregator(price_deck=pd_custom, cost_structure=cs_custom)
        assert agg.price_deck.oil_price == 80.0
        assert agg.cost_structure.royalty_rate == 0.20

    def test_calculate_revenue(self):
        from worldenergydata.bsee.reports.comprehensive.hierarchical_aggregator import (
            BaseAggregator,
        )

        agg = BaseAggregator(
            price_deck=PriceDeck(oil_price=75.0, gas_price=3.5, ngl_price=30.0)
        )
        production = {"oil_bbls": 1000, "gas_mcf": 5000, "ngl_bbls": 200}
        rev = agg.calculate_revenue(production)
        assert rev["oil_revenue"] == 75000.0
        assert rev["gas_revenue"] == 17500.0
        assert rev["ngl_revenue"] == 6000.0
        assert rev["gross_revenue"] == 98500.0

    def test_calculate_revenue_empty(self):
        from worldenergydata.bsee.reports.comprehensive.hierarchical_aggregator import (
            BaseAggregator,
        )

        agg = BaseAggregator()
        rev = agg.calculate_revenue({})
        assert rev["oil_revenue"] == 0.0
        assert rev["gross_revenue"] == 0.0

    def test_calculate_costs(self):
        from worldenergydata.bsee.reports.comprehensive.hierarchical_aggregator import (
            BaseAggregator,
        )

        agg = BaseAggregator(
            cost_structure=CostStructure(
                operating_cost_per_bbl=10.0,
                royalty_rate=0.10,
                severance_tax_rate=0.05,
            )
        )
        production = {"oil_bbls": 1000, "gas_mcf": 0}
        revenue = {"gross_revenue": 75000.0}
        costs = agg.calculate_costs(production, revenue)
        assert costs["operating_cost"] == 10000.0
        assert costs["royalties"] == 7500.0
        assert costs["severance_tax"] == 3750.0
        assert costs["total_costs"] == 21250.0
        assert costs["net_income"] == 53750.0

    def test_aggregate_raises(self):
        from worldenergydata.bsee.reports.comprehensive.hierarchical_aggregator import (
            BaseAggregator,
        )

        agg = BaseAggregator()
        with pytest.raises(NotImplementedError):
            agg.aggregate(None)


# ---------------------------------------------------------------------------
# HierarchicalAggregator._generate_summary
# ---------------------------------------------------------------------------


class TestGenerateSummary:
    def test_empty_data(self):
        from worldenergydata.bsee.reports.comprehensive.hierarchical_aggregator import (
            HierarchicalAggregator,
        )

        ha = HierarchicalAggregator()
        result = ha._generate_summary({})
        assert result == {}

    def test_single_entity(self):
        from worldenergydata.bsee.reports.comprehensive.hierarchical_aggregator import (
            HierarchicalAggregator,
        )

        ha = HierarchicalAggregator()
        data = {
            "block1": {
                "oil_production_bbls": 10000,
                "gas_production_mcf": 60000,
                "water_production_bbls": 5000,
                "gross_revenue": 750000,
                "total_costs": 200000,
                "net_income": 550000,
            }
        }
        result = ha._generate_summary(data)
        assert result["entity_count"] == 1
        assert result["total_oil_bbls"] == 10000
        assert result["total_gas_mcf"] == 60000
        assert result["total_gross_revenue"] == 750000
        assert result["total_net_income"] == 550000
        assert result["avg_oil_per_entity"] == 10000
        assert result["profit_margin"] == pytest.approx(73.33, abs=0.1)

    def test_multiple_entities(self):
        from worldenergydata.bsee.reports.comprehensive.hierarchical_aggregator import (
            HierarchicalAggregator,
        )

        ha = HierarchicalAggregator()
        data = {
            "b1": {
                "oil_production_bbls": 1000,
                "gas_production_mcf": 6000,
                "water_production_bbls": 500,
                "gross_revenue": 75000,
                "total_costs": 25000,
                "net_income": 50000,
            },
            "b2": {
                "oil_production_bbls": 2000,
                "gas_production_mcf": 12000,
                "water_production_bbls": 1000,
                "gross_revenue": 150000,
                "total_costs": 50000,
                "net_income": 100000,
            },
        }
        result = ha._generate_summary(data)
        assert result["entity_count"] == 2
        assert result["total_oil_bbls"] == 3000
        assert result["total_gas_mcf"] == 18000
        assert result["avg_oil_per_entity"] == 1500

    def test_zero_revenue_profit_margin(self):
        from worldenergydata.bsee.reports.comprehensive.hierarchical_aggregator import (
            HierarchicalAggregator,
        )

        ha = HierarchicalAggregator()
        data = {
            "b1": {
                "oil_production_bbls": 0,
                "gas_production_mcf": 0,
                "water_production_bbls": 0,
                "gross_revenue": 0,
                "total_costs": 0,
                "net_income": 0,
            }
        }
        result = ha._generate_summary(data)
        assert result["profit_margin"] == 0

    def test_aggregate_hierarchy_invalid_level(self):
        from worldenergydata.bsee.reports.comprehensive.hierarchical_aggregator import (
            HierarchicalAggregator,
        )

        ha = HierarchicalAggregator()
        with pytest.raises(ValueError, match="Invalid aggregation level"):
            ha.aggregate_hierarchy({}, level="invalid")
