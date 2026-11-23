"""
Tests for DataAggregator abstract base class and concrete implementations
"""

import sys
from abc import ABC, abstractmethod
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

from src.worldenergydata.modules.bsee.reports.comprehensive.models import (
    Block,
    EconomicMetrics,
    Field,
    HierarchyLevel,
    Lease,
    ProductionMetrics,
    Well,
)


class TestDataAggregatorABC:
    """Test DataAggregator abstract base class"""

    def test_abstract_base_class_cannot_be_instantiated(self):
        """Test that ABC cannot be directly instantiated"""
        from src.worldenergydata.modules.bsee.reports.comprehensive.aggregators.base import (
            DataAggregator,
        )

        with pytest.raises(TypeError):
            DataAggregator()

    def test_abstract_methods_required(self):
        """Test that subclasses must implement abstract methods"""
        from src.worldenergydata.modules.bsee.reports.comprehensive.aggregators.base import (
            DataAggregator,
        )

        class IncompleteAggregator(DataAggregator):
            pass

        with pytest.raises(TypeError):
            IncompleteAggregator()

    def test_complete_implementation_works(self):
        """Test that properly implemented subclass can be instantiated"""
        from src.worldenergydata.modules.bsee.reports.comprehensive.aggregators.base import (
            DataAggregator,
        )

        class CompleteAggregator(DataAggregator):
            def aggregate(self, data: Dict[str, Any]) -> Dict[str, Any]:
                return {}

            def validate(self, data: Dict[str, Any]) -> bool:
                return True

            def calculate_metrics(self, data: Dict[str, Any]) -> ProductionMetrics:
                return ProductionMetrics()

            def get_hierarchy_level(self) -> HierarchyLevel:
                return HierarchyLevel.FIELD

        aggregator = CompleteAggregator()
        assert aggregator is not None
        assert aggregator.get_hierarchy_level() == HierarchyLevel.FIELD


class TestBlockAggregator:
    """Test BlockAggregator implementation"""

    def setup_method(self):
        """Set up test data"""
        # Create test hierarchy
        self.block = Block("B1", "Walker Ridge 759", "Walker Ridge")
        self.field1 = Field("F1", "Jack", "B1")
        self.field2 = Field("F2", "St. Malo", "B1")

        self.block.add_child(self.field1)
        self.block.add_child(self.field2)

        # Add production data to fields
        self.field1.total_production = {
            "oil_bbls": 1000000,
            "gas_mcf": 500000,
            "water_bbls": 200000,
        }
        self.field2.total_production = {
            "oil_bbls": 800000,
            "gas_mcf": 400000,
            "water_bbls": 150000,
        }

    def test_block_aggregator_initialization(self):
        """Test BlockAggregator can be initialized"""
        from src.worldenergydata.modules.bsee.reports.comprehensive.aggregators.block_aggregator import (
            BlockAggregator,
        )

        aggregator = BlockAggregator()
        assert aggregator is not None
        assert aggregator.get_hierarchy_level() == HierarchyLevel.BLOCK

    def test_block_production_summation(self):
        """Test production summation across fields"""
        from src.worldenergydata.modules.bsee.reports.comprehensive.aggregators.block_aggregator import (
            BlockAggregator,
        )

        aggregator = BlockAggregator()
        result = aggregator.aggregate({"block": self.block})

        assert result["oil_bbls"] == 1800000
        assert result["gas_mcf"] == 900000
        assert result["water_bbls"] == 350000

    def test_block_field_count(self):
        """Test field counting in block"""
        from src.worldenergydata.modules.bsee.reports.comprehensive.aggregators.block_aggregator import (
            BlockAggregator,
        )

        aggregator = BlockAggregator()
        result = aggregator.aggregate({"block": self.block})

        assert result["field_count"] == 2

    def test_block_metrics_calculation(self):
        """Test metrics calculation for block"""
        from src.worldenergydata.modules.bsee.reports.comprehensive.aggregators.block_aggregator import (
            BlockAggregator,
        )

        aggregator = BlockAggregator()
        aggregator.aggregate({"block": self.block})
        metrics = aggregator.calculate_metrics({"block": self.block})

        assert metrics.oil_production_bbls == 1800000
        assert metrics.gas_production_mcf == 900000
        assert metrics.entity_type == "block"


class TestFieldAggregator:
    """Test FieldAggregator implementation"""

    def setup_method(self):
        """Set up test data"""
        self.field = Field("F1", "Jack", "B1")
        self.lease1 = Lease("L1", "OCS-G-12345", "F1")
        self.lease2 = Lease("L2", "OCS-G-12346", "F1")

        self.field.add_child(self.lease1)
        self.field.add_child(self.lease2)

        # Add production data to leases
        self.lease1.total_production = {
            "oil_bbls": 600000,
            "gas_mcf": 300000,
            "water_bbls": 100000,
        }
        self.lease2.total_production = {
            "oil_bbls": 400000,
            "gas_mcf": 200000,
            "water_bbls": 100000,
        }

    def test_field_aggregator_initialization(self):
        """Test FieldAggregator can be initialized"""
        from src.worldenergydata.modules.bsee.reports.comprehensive.aggregators.field_aggregator import (
            FieldAggregator,
        )

        aggregator = FieldAggregator()
        assert aggregator is not None
        assert aggregator.get_hierarchy_level() == HierarchyLevel.FIELD

    def test_field_lease_aggregation(self):
        """Test aggregation of leases to field level"""
        from src.worldenergydata.modules.bsee.reports.comprehensive.aggregators.field_aggregator import (
            FieldAggregator,
        )

        aggregator = FieldAggregator()
        result = aggregator.aggregate({"field": self.field})

        assert result["oil_bbls"] == 1000000
        assert result["gas_mcf"] == 500000
        assert result["water_bbls"] == 200000
        assert result["lease_count"] == 2


class TestLeaseAggregator:
    """Test LeaseAggregator implementation"""

    def setup_method(self):
        """Set up test data"""
        self.lease = Lease("L1", "OCS-G-12345", "F1")
        self.well1 = Well("W1", "PS001", lease_id="L1")
        self.well2 = Well("W2", "PS002", lease_id="L1")

        self.lease.add_child(self.well1)
        self.lease.add_child(self.well2)

        # Add production data to wells
        self.well1.set_production_data(
            {"oil_bbls": 350000, "gas_mcf": 175000, "water_bbls": 50000}
        )
        self.well2.set_production_data(
            {"oil_bbls": 250000, "gas_mcf": 125000, "water_bbls": 50000}
        )

    def test_lease_aggregator_initialization(self):
        """Test LeaseAggregator can be initialized"""
        from src.worldenergydata.modules.bsee.reports.comprehensive.aggregators.lease_aggregator import (
            LeaseAggregator,
        )

        aggregator = LeaseAggregator()
        assert aggregator is not None
        assert aggregator.get_hierarchy_level() == HierarchyLevel.LEASE

    def test_lease_well_metrics(self):
        """Test well-level metrics aggregation"""
        from src.worldenergydata.modules.bsee.reports.comprehensive.aggregators.lease_aggregator import (
            LeaseAggregator,
        )

        aggregator = LeaseAggregator()
        result = aggregator.aggregate({"lease": self.lease})

        assert result["oil_bbls"] == 600000
        assert result["gas_mcf"] == 300000
        assert result["water_bbls"] == 100000
        assert result["well_count"] == 2
        assert result["oil_per_well"] == 300000


class TestDataValidation:
    """Test data validation in aggregators"""

    def test_validation_empty_data(self):
        """Test validation with empty data"""
        from src.worldenergydata.modules.bsee.reports.comprehensive.aggregators.field_aggregator import (
            FieldAggregator,
        )

        aggregator = FieldAggregator()
        assert aggregator.validate({}) == False

    def test_validation_missing_required_fields(self):
        """Test validation with missing required fields"""
        from src.worldenergydata.modules.bsee.reports.comprehensive.aggregators.field_aggregator import (
            FieldAggregator,
        )

        aggregator = FieldAggregator()
        invalid_data = {"wrong_key": "value"}
        assert aggregator.validate(invalid_data) == False

    def test_validation_valid_data(self):
        """Test validation with valid data"""
        from src.worldenergydata.modules.bsee.reports.comprehensive.aggregators.field_aggregator import (
            FieldAggregator,
        )

        field = Field("F1", "Jack", "B1")
        aggregator = FieldAggregator()
        assert aggregator.validate({"field": field}) == True


class TestAggregationAccuracy:
    """Test aggregation accuracy and edge cases"""

    def test_zero_production_handling(self):
        """Test handling of zero production values"""
        from src.worldenergydata.modules.bsee.reports.comprehensive.aggregators.lease_aggregator import (
            LeaseAggregator,
        )

        lease = Lease("L1", "OCS-G-12345", "F1")
        well = Well("W1", "PS001", lease_id="L1")
        well.set_production_data({"oil_bbls": 0, "gas_mcf": 0, "water_bbls": 0})
        lease.add_child(well)

        aggregator = LeaseAggregator()
        result = aggregator.aggregate({"lease": lease})

        assert result["oil_bbls"] == 0
        assert result["gas_mcf"] == 0
        assert result["water_bbls"] == 0

    def test_partial_data_handling(self):
        """Test handling of partial production data"""
        from src.worldenergydata.modules.bsee.reports.comprehensive.aggregators.lease_aggregator import (
            LeaseAggregator,
        )

        lease = Lease("L1", "OCS-G-12345", "F1")
        well = Well("W1", "PS001", lease_id="L1")
        # Only oil data available
        well.set_production_data({"oil_bbls": 100000})
        lease.add_child(well)

        aggregator = LeaseAggregator()
        result = aggregator.aggregate({"lease": lease})

        assert result["oil_bbls"] == 100000
        assert result["gas_mcf"] == 0  # Should default to 0
        assert result["water_bbls"] == 0  # Should default to 0

    def test_large_dataset_aggregation(self):
        """Test aggregation with large number of wells"""
        from src.worldenergydata.modules.bsee.reports.comprehensive.aggregators.lease_aggregator import (
            LeaseAggregator,
        )

        lease = Lease("L1", "OCS-G-12345", "F1")

        # Create 100 wells
        for i in range(100):
            well = Well(f"W{i}", f"PS{i:03d}", lease_id="L1")
            well.set_production_data(
                {"oil_bbls": 10000, "gas_mcf": 5000, "water_bbls": 2000}
            )
            lease.add_child(well)

        aggregator = LeaseAggregator()
        result = aggregator.aggregate({"lease": lease})

        assert result["oil_bbls"] == 1000000
        assert result["gas_mcf"] == 500000
        assert result["water_bbls"] == 200000
        assert result["well_count"] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
