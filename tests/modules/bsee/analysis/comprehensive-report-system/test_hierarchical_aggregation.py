"""
Tests for hierarchical aggregation accuracy
Validates aggregation logic from well → lease → field → block levels
"""

import os
import sys
import unittest
from datetime import date
from unittest.mock import MagicMock, Mock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../../src"))

from worldenergydata.modules.bsee.reports.comprehensive.hierarchical_aggregator import (
    BlockAggregator,
    CostStructure,
    FieldAggregator,
    HierarchicalAggregator,
    LeaseAggregator,
    PriceDeck,
    WellAggregator,
)
from worldenergydata.modules.bsee.reports.comprehensive.models import (
    Block,
    Field,
    Lease,
    Well,
)


class TestHierarchicalAggregation(unittest.TestCase):
    """Test suite for hierarchical aggregation accuracy"""

    def setUp(self):
        """Set up test fixtures"""
        # Create price deck and cost structure
        self.price_deck = PriceDeck(oil_price=75.00, gas_price=3.50, ngl_price=30.00)
        self.cost_structure = CostStructure(
            operating_cost_per_bbl=12.50, royalty_rate=0.1875, severance_tax_rate=0.05
        )

        # Create sample hierarchy
        self.block = Block(id="WR_759", number="759", area="WR")
        self.field = Field(id="Jack", name="Jack", block_id="WR_759")
        self.lease1 = Lease(id="OCS-G-12345", number="OCS-G-12345", field_id="Jack")
        self.lease2 = Lease(id="OCS-G-12346", number="OCS-G-12346", field_id="Jack")

        # Create wells with production data
        self.well1 = Well(
            id="API001",
            name="PS001",
            api_number="API001",
            lease_id="OCS-G-12345",
            water_depth_ft=7000,
            total_depth_ft=25000,
            spud_date=date(2020, 1, 15),
            status="active",
        )
        self.well1.set_production_data(
            {"oil_bbls": 100000, "gas_mcf": 50000, "water_bbls": 20000, "days_on": 365}
        )

        self.well2 = Well(
            id="API002",
            name="PS002",
            api_number="API002",
            lease_id="OCS-G-12345",
            water_depth_ft=7000,
            total_depth_ft=26000,
            spud_date=date(2020, 3, 20),
            status="active",
        )
        self.well2.set_production_data(
            {"oil_bbls": 80000, "gas_mcf": 40000, "water_bbls": 15000, "days_on": 300}
        )

        self.well3 = Well(
            id="API003",
            name="PS003",
            api_number="API003",
            lease_id="OCS-G-12346",
            water_depth_ft=7100,
            total_depth_ft=24500,
            spud_date=date(2020, 6, 10),
            status="active",
        )
        self.well3.set_production_data(
            {"oil_bbls": 120000, "gas_mcf": 60000, "water_bbls": 25000, "days_on": 350}
        )

        # Build hierarchy relationships
        self.lease1.add_child(self.well1)
        self.lease1.add_child(self.well2)
        self.lease2.add_child(self.well3)
        self.field.add_child(self.lease1)
        self.field.add_child(self.lease2)
        self.block.add_child(self.field)

    def test_well_aggregation(self):
        """Test well-level aggregation accuracy"""
        aggregator = WellAggregator(
            price_deck=self.price_deck, cost_structure=self.cost_structure
        )

        # Aggregate well 1
        metrics = aggregator.aggregate(self.well1)

        # Verify production data
        self.assertEqual(metrics["oil_production_bbls"], 100000)
        self.assertEqual(metrics["gas_production_mcf"], 50000)
        self.assertEqual(metrics["water_production_bbls"], 20000)
        self.assertEqual(metrics["production_days"], 365)

        # Verify revenue calculations
        expected_oil_revenue = 100000 * 75.00
        expected_gas_revenue = 50000 * 3.50
        expected_gross_revenue = expected_oil_revenue + expected_gas_revenue

        self.assertEqual(metrics["oil_revenue"], expected_oil_revenue)
        self.assertEqual(metrics["gas_revenue"], expected_gas_revenue)
        self.assertEqual(metrics["gross_revenue"], expected_gross_revenue)

        # Verify cost calculations
        boe = 100000 + (50000 / 6)
        expected_operating_cost = boe * 12.50
        expected_royalties = expected_gross_revenue * 0.1875
        expected_severance_tax = expected_gross_revenue * 0.05

        self.assertAlmostEqual(
            metrics["operating_cost"], expected_operating_cost, places=2
        )
        self.assertAlmostEqual(metrics["royalties"], expected_royalties, places=2)
        self.assertAlmostEqual(
            metrics["severance_tax"], expected_severance_tax, places=2
        )

        # Verify daily rates
        self.assertAlmostEqual(metrics["oil_rate_bopd"], 100000 / 365, places=2)
        self.assertAlmostEqual(metrics["gas_rate_mcfd"], 50000 / 365, places=2)

    def test_lease_aggregation(self):
        """Test lease-level aggregation with multiple wells"""
        aggregator = LeaseAggregator(
            price_deck=self.price_deck, cost_structure=self.cost_structure
        )

        # Aggregate lease 1 (contains well1 and well2)
        metrics = aggregator.aggregate(self.lease1)

        # Verify well counts
        self.assertEqual(metrics["total_wells"], 2)
        self.assertEqual(metrics["active_wells"], 2)

        # Verify production summation
        expected_oil = 100000 + 80000  # well1 + well2
        expected_gas = 50000 + 40000
        expected_water = 20000 + 15000

        self.assertEqual(metrics["oil_production_bbls"], expected_oil)
        self.assertEqual(metrics["gas_production_mcf"], expected_gas)
        self.assertEqual(metrics["water_production_bbls"], expected_water)

        # Verify economic summation
        self.assertGreater(metrics["gross_revenue"], 0)
        self.assertGreater(metrics["net_income"], 0)

        # Verify averages
        self.assertEqual(metrics["avg_oil_per_well"], expected_oil / 2)
        self.assertEqual(metrics["avg_gas_per_well"], expected_gas / 2)

    def test_field_aggregation(self):
        """Test field-level aggregation with multiple leases"""
        aggregator = FieldAggregator(
            price_deck=self.price_deck, cost_structure=self.cost_structure
        )

        # Aggregate field (contains lease1 and lease2)
        metrics = aggregator.aggregate(self.field)

        # Verify counts
        self.assertEqual(metrics["total_leases"], 2)
        self.assertEqual(metrics["total_wells"], 3)
        self.assertEqual(metrics["active_wells"], 3)

        # Verify production summation across all wells
        expected_oil = 100000 + 80000 + 120000  # all three wells
        expected_gas = 50000 + 40000 + 60000
        expected_water = 20000 + 15000 + 25000

        self.assertEqual(metrics["oil_production_bbls"], expected_oil)
        self.assertEqual(metrics["gas_production_mcf"], expected_gas)
        self.assertEqual(metrics["water_production_bbls"], expected_water)

        # Verify BOE calculation
        expected_boe = expected_oil + (expected_gas / 6)
        self.assertAlmostEqual(metrics["total_boe"], expected_boe, places=2)

        # Verify field-level averages
        self.assertEqual(metrics["avg_wells_per_lease"], 3 / 2)
        self.assertEqual(metrics["avg_oil_per_well"], expected_oil / 3)

    def test_block_aggregation(self):
        """Test block-level aggregation with complete hierarchy"""
        aggregator = BlockAggregator(
            price_deck=self.price_deck, cost_structure=self.cost_structure
        )

        # Aggregate block (contains entire hierarchy)
        metrics = aggregator.aggregate(self.block)

        # Verify hierarchical counts
        self.assertEqual(metrics["total_fields"], 1)
        self.assertEqual(metrics["total_leases"], 2)
        self.assertEqual(metrics["total_wells"], 3)

        # Verify total production
        expected_oil = 100000 + 80000 + 120000
        expected_gas = 50000 + 40000 + 60000

        self.assertEqual(metrics["oil_production_bbls"], expected_oil)
        self.assertEqual(metrics["gas_production_mcf"], expected_gas)

        # Verify top performers identification
        self.assertEqual(metrics["top_oil_field"], "Jack")
        self.assertEqual(metrics["top_gas_field"], "Jack")
        self.assertEqual(metrics["top_revenue_field"], "Jack")

    def test_revenue_calculation_accuracy(self):
        """Test revenue calculation formulas"""
        aggregator = WellAggregator(
            price_deck=self.price_deck, cost_structure=self.cost_structure
        )

        # Test with known values
        production = {"oil_bbls": 1000, "gas_mcf": 500, "ngl_bbls": 100}

        revenue = aggregator.calculate_revenue(production)

        # Verify calculations
        self.assertEqual(revenue["oil_revenue"], 1000 * 75.00)
        self.assertEqual(revenue["gas_revenue"], 500 * 3.50)
        self.assertEqual(revenue["ngl_revenue"], 100 * 30.00)
        self.assertEqual(
            revenue["gross_revenue"],
            revenue["oil_revenue"] + revenue["gas_revenue"] + revenue["ngl_revenue"],
        )

    def test_cost_allocation_accuracy(self):
        """Test cost allocation across organizational levels"""
        aggregator = WellAggregator(
            price_deck=self.price_deck, cost_structure=self.cost_structure
        )

        production = {"oil_bbls": 1000, "gas_mcf": 600}
        revenue = {"gross_revenue": 10000}

        costs = aggregator.calculate_costs(production, revenue)

        # Verify operating cost calculation
        boe = 1000 + (600 / 6)
        expected_operating = boe * 12.50
        self.assertAlmostEqual(costs["operating_cost"], expected_operating, places=2)

        # Verify royalties
        expected_royalties = 10000 * 0.1875
        self.assertEqual(costs["royalties"], expected_royalties)

        # Verify severance tax
        expected_tax = 10000 * 0.05
        self.assertEqual(costs["severance_tax"], expected_tax)

        # Verify net income
        total_costs = expected_operating + expected_royalties + expected_tax
        expected_net = 10000 - total_costs
        self.assertAlmostEqual(costs["net_income"], expected_net, places=2)

    def test_hierarchical_aggregator_integration(self):
        """Test complete hierarchical aggregation system"""
        aggregator = HierarchicalAggregator(
            price_deck=self.price_deck, cost_structure=self.cost_structure
        )

        # Create mock hierarchy
        hierarchy = {
            "blocks": {"WR_759": self.block},
            "fields": {"Jack": self.field},
            "leases": {"OCS-G-12345": self.lease1, "OCS-G-12346": self.lease2},
            "wells": {"API001": self.well1, "API002": self.well2, "API003": self.well3},
        }

        # Test block-level aggregation
        block_data = aggregator.aggregate_hierarchy(hierarchy, level="block")
        self.assertIn("WR_759", block_data)
        self.assertEqual(block_data["WR_759"]["total_wells"], 3)

        # Test field-level aggregation
        field_data = aggregator.aggregate_hierarchy(hierarchy, level="field")
        self.assertIn("Jack", field_data)
        self.assertEqual(field_data["Jack"]["total_wells"], 3)

        # Test lease-level aggregation
        lease_data = aggregator.aggregate_hierarchy(hierarchy, level="lease")
        self.assertIn("OCS-G-12345", lease_data)
        self.assertIn("OCS-G-12346", lease_data)
        self.assertEqual(lease_data["OCS-G-12345"]["total_wells"], 2)
        self.assertEqual(lease_data["OCS-G-12346"]["total_wells"], 1)

    def test_aggregation_with_missing_data(self):
        """Test aggregation handles missing or incomplete data gracefully"""
        # Create well with no production data
        empty_well = Well(
            id="API004",
            name="PS004",
            api_number="API004",
            lease_id="OCS-G-12347",
            status="inactive",
        )
        empty_well.set_production_data({})

        aggregator = WellAggregator(
            price_deck=self.price_deck, cost_structure=self.cost_structure
        )

        metrics = aggregator.aggregate(empty_well)

        # Should handle missing data with defaults
        self.assertEqual(metrics["oil_production_bbls"], 0)
        self.assertEqual(metrics["gas_production_mcf"], 0)
        self.assertEqual(metrics["gross_revenue"], 0)
        self.assertEqual(metrics["net_income"], 0)

    def test_summary_generation(self):
        """Test summary statistics generation"""
        aggregator = HierarchicalAggregator(
            price_deck=self.price_deck, cost_structure=self.cost_structure
        )

        # Create sample aggregated data
        aggregated_data = {
            "entity1": {
                "oil_production_bbls": 100000,
                "gas_production_mcf": 50000,
                "gross_revenue": 1000000,
                "total_costs": 300000,
                "net_income": 700000,
            },
            "entity2": {
                "oil_production_bbls": 80000,
                "gas_production_mcf": 40000,
                "gross_revenue": 800000,
                "total_costs": 250000,
                "net_income": 550000,
            },
        }

        summary = aggregator._generate_summary(aggregated_data)

        # Verify summary calculations
        self.assertEqual(summary["entity_count"], 2)
        self.assertEqual(summary["total_oil_bbls"], 180000)
        self.assertEqual(summary["total_gas_mcf"], 90000)
        self.assertEqual(summary["total_gross_revenue"], 1800000)
        self.assertEqual(summary["total_net_income"], 1250000)

        # Verify profit margin calculation
        expected_margin = (1250000 / 1800000) * 100
        self.assertAlmostEqual(summary["profit_margin"], expected_margin, places=2)

        # Verify averages
        self.assertEqual(summary["avg_oil_per_entity"], 90000)
        self.assertEqual(summary["avg_revenue_per_entity"], 900000)


if __name__ == "__main__":
    unittest.main()
