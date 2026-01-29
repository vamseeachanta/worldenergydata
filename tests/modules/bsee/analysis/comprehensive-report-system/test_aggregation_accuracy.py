"""
Tests for aggregation accuracy, edge cases, and data validation
"""

import sys
from datetime import date, datetime
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

from worldenergydata.modules.bsee.reports.comprehensive.aggregators import (
    BlockAggregator,
    FieldAggregator,
    LeaseAggregator,
)
from worldenergydata.modules.bsee.reports.comprehensive.data_loader import (
    HierarchicalDataLoader,
)
from worldenergydata.modules.bsee.reports.comprehensive.models import (
    Block,
    Field,
    Lease,
    ProductionMetrics,
    Well,
)


class TestAggregationAccuracy:
    """Test aggregation accuracy across different scenarios"""

    def test_multilevel_aggregation_consistency(self):
        """Test that aggregation is consistent across hierarchy levels"""
        # Create hierarchy
        block = Block("B1", "WR 759", "WR")
        field = Field("F1", "Jack", "B1")
        lease1 = Lease("L1", "OCS-G-12345", "F1")
        lease2 = Lease("L2", "OCS-G-12346", "F1")

        block.add_child(field)
        field.add_child(lease1)
        field.add_child(lease2)

        # Add wells with production
        total_oil = 0
        total_gas = 0

        for i in range(5):
            well = Well(f"W{i}", f"PS00{i}", lease_id="L1")
            oil = 10000 * (i + 1)
            gas = 5000 * (i + 1)
            well.set_production_data(
                {"oil_bbls": oil, "gas_mcf": gas, "water_bbls": 2000}
            )
            lease1.add_child(well)
            total_oil += oil
            total_gas += gas

        for i in range(3):
            well = Well(f"W{i+5}", f"PS00{i+5}", lease_id="L2")
            oil = 8000 * (i + 1)
            gas = 4000 * (i + 1)
            well.set_production_data(
                {"oil_bbls": oil, "gas_mcf": gas, "water_bbls": 1500}
            )
            lease2.add_child(well)
            total_oil += oil
            total_gas += gas

        # Aggregate at each level
        lease_agg = LeaseAggregator()
        field_agg = FieldAggregator()
        block_agg = BlockAggregator()

        lease1_result = lease_agg.aggregate({"lease": lease1})
        lease2_result = lease_agg.aggregate({"lease": lease2})
        field_result = field_agg.aggregate({"field": field})
        block_result = block_agg.aggregate({"block": block})

        # Verify consistency
        assert (
            lease1_result["oil_bbls"] + lease2_result["oil_bbls"]
            == field_result["oil_bbls"]
        )
        assert field_result["oil_bbls"] == block_result["oil_bbls"]
        assert block_result["oil_bbls"] == total_oil
        assert block_result["gas_mcf"] == total_gas

    def test_revenue_calculation_accuracy(self):
        """Test revenue and cost calculations"""
        lease = Lease("L1", "OCS-G-12345", "F1")
        well = Well("W1", "PS001", lease_id="L1")
        well.set_production_data(
            {"oil_bbls": 100000, "gas_mcf": 50000, "water_bbls": 20000}
        )
        lease.add_child(well)

        aggregator = LeaseAggregator()
        aggregator.aggregate({"lease": lease})

        price_deck = {
            "oil": 75.0,
            "gas": 3.5,
            "ngl": 25.0,
            "operating_cost_per_bbl": 12.5,
            "water_disposal_cost_per_bbl": 2.0,
            "gas_processing_cost_per_mcf": 0.5,
            "royalty_rate": 0.1875,
            "severance_tax_rate": 0.05,
        }

        economics = aggregator.aggregate_revenue_costs(lease, price_deck)

        # Verify calculations
        expected_oil_revenue = 100000 * 75.0
        expected_gas_revenue = 50000 * 3.5
        expected_ngl_revenue = 50000 * 0.01 * 25.0
        expected_gross = (
            expected_oil_revenue + expected_gas_revenue + expected_ngl_revenue
        )

        assert economics["oil_revenue"] == expected_oil_revenue
        assert economics["gas_revenue"] == expected_gas_revenue
        assert economics["gross_revenue"] == expected_gross

        # Verify costs
        expected_oil_cost = 100000 * 12.5
        expected_water_cost = 20000 * 2.0
        expected_gas_cost = 50000 * 0.5
        expected_total_cost = (
            expected_oil_cost + expected_water_cost + expected_gas_cost
        )

        assert economics["oil_operating_cost"] == expected_oil_cost
        assert economics["water_disposal_cost"] == expected_water_cost
        assert economics["total_operating_cost"] == expected_total_cost

        # Verify government take
        expected_royalties = expected_gross * 0.1875
        expected_severance = expected_gross * 0.05

        assert abs(economics["royalties"] - expected_royalties) < 0.01
        assert abs(economics["severance_tax"] - expected_severance) < 0.01

    def test_missing_data_handling(self):
        """Test handling of missing or incomplete data"""
        lease = Lease("L1", "OCS-G-12345", "F1")

        # Well with partial data
        well1 = Well("W1", "PS001", lease_id="L1")
        well1.set_production_data({"oil_bbls": 50000})  # Missing gas and water

        # Well with no production data
        well2 = Well("W2", "PS002", lease_id="L1")
        well2.set_production_data({})

        lease.add_child(well1)
        lease.add_child(well2)

        aggregator = LeaseAggregator()
        result = aggregator.aggregate({"lease": lease})

        # Should handle missing data gracefully
        assert result["oil_bbls"] == 50000
        assert result["gas_mcf"] == 0
        assert result["water_bbls"] == 0
        assert result["well_count"] == 2

    def test_large_number_aggregation(self):
        """Test aggregation with large numbers to check for overflow"""
        field = Field("F1", "BigField", "B1")

        # Create 100 leases with 10 wells each
        for lease_num in range(100):
            lease = Lease(f"L{lease_num}", f"OCS-G-{20000+lease_num}", "F1")
            field.add_child(lease)

            for well_num in range(10):
                well = Well(
                    f"W{lease_num}_{well_num}",
                    f"PS{lease_num:03d}{well_num:02d}",
                    lease_id=lease.id,
                )
                well.set_production_data(
                    {
                        "oil_bbls": 1000000,  # 1 million bbls per well
                        "gas_mcf": 500000,
                        "water_bbls": 200000,
                    }
                )
                lease.add_child(well)

        aggregator = FieldAggregator()
        result = aggregator.aggregate({"field": field})

        # 100 leases * 10 wells * 1M bbls = 1 billion bbls
        assert result["oil_bbls"] == 1000000000
        assert result["gas_mcf"] == 500000000
        assert result["total_well_count"] == 1000
        assert result["lease_count"] == 100

    def test_date_range_filtering(self):
        """Test filtering by production date ranges"""
        lease = Lease("L1", "OCS-G-12345", "F1")

        # Wells with different spud dates
        well1 = Well("W1", "PS001", lease_id="L1", spud_date=date(2020, 1, 15))
        well1.set_production_data({"oil_bbls": 50000, "gas_mcf": 25000})

        well2 = Well("W2", "PS002", lease_id="L1", spud_date=date(2021, 6, 20))
        well2.set_production_data({"oil_bbls": 30000, "gas_mcf": 15000})

        well3 = Well("W3", "PS003", lease_id="L1", spud_date=date(2022, 3, 10))
        well3.set_production_data({"oil_bbls": 20000, "gas_mcf": 10000})

        lease.add_child(well1)
        lease.add_child(well2)
        lease.add_child(well3)

        aggregator = LeaseAggregator()
        result = aggregator.aggregate({"lease": lease})

        # All wells should be included
        assert result["oil_bbls"] == 100000
        assert result["well_count"] == 3

        # Test date range calculation
        assert result["first_production_date"] == date(2020, 1, 15)
        assert result["last_production_date"] == date(2022, 3, 10)


class TestDataValidation:
    """Test data validation and quality checks"""

    def test_negative_production_detection(self):
        """Test detection of negative production values"""
        from worldenergydata.modules.bsee.reports.comprehensive.aggregators.base import (
            DataAggregator,
        )

        class TestAggregator(DataAggregator):
            def aggregate(self, data):
                return data

            def validate(self, data):
                return True

            def calculate_metrics(self, data):
                return ProductionMetrics()

            def get_hierarchy_level(self):
                return "test"

        aggregator = TestAggregator()

        invalid_data = {"oil_bbls": -1000, "gas_mcf": 5000, "water_bbls": 2000}

        quality = aggregator.validate_data_quality(invalid_data)

        assert len(quality["issues"]) > 0
        assert "Negative oil production detected" in quality["issues"]
        assert quality["accuracy"] < 1.0

    def test_data_completeness_check(self):
        """Test data completeness validation"""
        from worldenergydata.modules.bsee.reports.comprehensive.aggregators.field_aggregator import (
            FieldAggregator,
        )

        aggregator = FieldAggregator()

        complete_data = {"oil_bbls": 100000, "gas_mcf": 50000, "water_bbls": 20000}

        incomplete_data = {"oil_bbls": 100000}

        complete_quality = aggregator.validate_data_quality(complete_data)
        incomplete_quality = aggregator.validate_data_quality(incomplete_data)

        assert complete_quality["completeness"] == 1.0
        assert incomplete_quality["completeness"] < 1.0

    def test_outlier_detection(self):
        """Test detection of outlier values"""
        field = Field("F1", "TestField", "B1")

        # Normal wells
        for i in range(10):
            lease = Lease(f"L{i}", f"OCS-G-{12345+i}", "F1")
            field.add_child(lease)
            well = Well(f"W{i}", f"PS00{i}", lease_id=lease.id)
            well.set_production_data(
                {
                    "oil_bbls": 50000 + (i * 1000),
                    "gas_mcf": 25000 + (i * 500),
                    "water_bbls": 10000,
                }
            )
            lease.add_child(well)

        # Outlier well (10x production)
        outlier_lease = Lease("L_OUT", "OCS-G-99999", "F1")
        field.add_child(outlier_lease)
        outlier_well = Well("W_OUT", "PS999", lease_id="L_OUT")
        outlier_well.set_production_data(
            {
                "oil_bbls": 5000000,  # 100x normal
                "gas_mcf": 2500000,
                "water_bbls": 1000000,
            }
        )
        outlier_lease.add_child(outlier_well)

        aggregator = FieldAggregator()
        result = aggregator.aggregate({"field": field})

        # Outlier should still be included in totals
        assert result["oil_bbls"] > 5000000
        assert result["lease_count"] == 11


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_hierarchy(self):
        """Test aggregation with empty hierarchy"""
        block = Block("B1", "Empty", "EM")

        aggregator = BlockAggregator()
        result = aggregator.aggregate({"block": block})

        assert result["oil_bbls"] == 0
        assert result["gas_mcf"] == 0
        assert result["field_count"] == 0

    def test_single_well_hierarchy(self):
        """Test hierarchy with single well"""
        block = Block("B1", "Single", "SI")
        field = Field("F1", "SingleField", "B1")
        lease = Lease("L1", "OCS-G-00001", "F1")
        well = Well("W1", "PS001", lease_id="L1")

        well.set_production_data({"oil_bbls": 100, "gas_mcf": 50})

        block.add_child(field)
        field.add_child(lease)
        lease.add_child(well)

        block_agg = BlockAggregator()
        result = block_agg.aggregate({"block": block})

        assert result["oil_bbls"] == 100
        assert result["gas_mcf"] == 50
        assert result["field_count"] == 1
        assert result["total_lease_count"] == 1
        assert result["total_well_count"] == 1

    def test_unicode_names(self):
        """Test handling of unicode characters in names"""
        field = Field("F1", "São Paulo Field", "B1")
        lease = Lease("L1", "OCS-G-ñ1234", "F1")
        well = Well("W1", "PS-α001", lease_id="L1")

        well.set_production_data({"oil_bbls": 1000})
        lease.add_child(well)
        field.add_child(lease)

        aggregator = FieldAggregator()
        result = aggregator.aggregate({"field": field})

        assert result["oil_bbls"] == 1000
        assert result["lease_count"] == 1

    def test_very_long_timespan(self):
        """Test aggregation over very long time periods"""
        lease = Lease("L1", "OCS-G-12345", "F1")

        # Well producing for 50 years
        well = Well(
            "W1",
            "PS001",
            lease_id="L1",
            spud_date=date(1970, 1, 1),
            last_activity_date=date(2020, 12, 31),
        )

        days_producing = (date(2020, 12, 31) - date(1970, 1, 1)).days
        total_oil = days_producing * 100  # 100 bbl/day

        well.set_production_data(
            {
                "oil_bbls": total_oil,
                "gas_mcf": total_oil * 0.5,
                "days_on": days_producing,
            }
        )
        lease.add_child(well)

        aggregator = LeaseAggregator()
        result = aggregator.aggregate({"lease": lease})
        metrics = aggregator.calculate_metrics({"lease": lease})

        assert result["oil_bbls"] == total_oil
        assert metrics.days_in_period == days_producing
        assert abs(metrics.daily_oil_rate - 100) < 1  # ~100 bbl/day


class TestDataLoader:
    """Test hierarchical data loader"""

    def test_data_loader_initialization(self):
        """Test data loader can be initialized"""
        loader = HierarchicalDataLoader()
        assert loader is not None
        assert loader.blocks == {}
        assert loader.fields == {}

    def test_sample_data_loading(self):
        """Test loading sample data"""
        loader = HierarchicalDataLoader()
        hierarchy = loader.load_hierarchy(block_number="759")

        assert len(hierarchy["blocks"]) > 0
        assert len(hierarchy["fields"]) > 0
        assert len(hierarchy["wells"]) > 0

    def test_hierarchy_statistics(self):
        """Test hierarchy statistics"""
        loader = HierarchicalDataLoader()
        hierarchy = loader.load_hierarchy()
        stats = loader.get_hierarchy_stats()

        assert "blocks" in stats
        assert "fields" in stats
        assert "leases" in stats
        assert "wells" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
