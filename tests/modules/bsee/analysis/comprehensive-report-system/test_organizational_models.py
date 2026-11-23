"""
Tests for Organizational Unit data models
Following TDD approach - tests written before implementation
"""

import sys
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from worldenergydata.modules.bsee.reports.comprehensive.models import (
    Block,
    Field,
    HierarchyLevel,
    Lease,
    OrganizationalUnit,
    Well,
)


class TestOrganizationalUnit:
    """Test base OrganizationalUnit class"""

    def test_organizational_unit_initialization(self):
        """Test basic initialization of OrganizationalUnit"""
        unit = OrganizationalUnit(
            id="TEST-001",
            name="Test Unit",
            level=HierarchyLevel.WELL,
            parent_id="PARENT-001",
        )

        assert unit.id == "TEST-001"
        assert unit.name == "Test Unit"
        assert unit.level == HierarchyLevel.WELL
        assert unit.parent_id == "PARENT-001"
        assert unit.children == []
        assert unit.attributes == {}
        assert unit.metrics == {}

    def test_organizational_unit_with_attributes(self):
        """Test OrganizationalUnit with custom attributes"""
        unit = OrganizationalUnit(
            id="TEST-002",
            name="Test Unit 2",
            level=HierarchyLevel.LEASE,
            attributes={"operator": "Test Corp", "area": 1000},
        )

        assert unit.attributes["operator"] == "Test Corp"
        assert unit.attributes["area"] == 1000

    def test_add_child_relationship(self):
        """Test adding child relationships"""
        parent = OrganizationalUnit(
            id="PARENT-001", name="Parent Unit", level=HierarchyLevel.FIELD
        )

        child = OrganizationalUnit(
            id="CHILD-001",
            name="Child Unit",
            level=HierarchyLevel.LEASE,
            parent_id="PARENT-001",
        )

        parent.add_child(child)
        assert len(parent.children) == 1
        assert parent.children[0].id == "CHILD-001"

    def test_hierarchy_validation(self):
        """Test that hierarchy levels are properly validated"""
        # Block should not have a parent
        block = OrganizationalUnit(
            id="BLOCK-001", name="Test Block", level=HierarchyLevel.BLOCK
        )
        assert block.parent_id is None

        # Well must have a parent (lease)
        with pytest.raises(ValueError, match="Well must have a parent"):
            Well(
                id="WELL-001", name="Test Well", api_number="1234567890", parent_id=None
            )


class TestWellModel:
    """Test Well data model"""

    def test_well_initialization(self):
        """Test Well model initialization with required fields"""
        well = Well(
            id="WELL-001",
            name="PS001",
            api_number="1234567890",
            parent_id="LEASE-001",
            spud_date=date(2020, 1, 15),
            water_depth_ft=7000,
            total_depth_ft=25000,
        )

        assert well.id == "WELL-001"
        assert well.name == "PS001"
        assert well.api_number == "1234567890"
        assert well.level == HierarchyLevel.WELL
        assert well.spud_date == date(2020, 1, 15)
        assert well.water_depth_ft == 7000
        assert well.total_depth_ft == 25000

    def test_well_construction_days_calculation(self):
        """Test calculation of construction days"""
        well = Well(
            id="WELL-002",
            name="PS002",
            api_number="1234567891",
            parent_id="LEASE-001",
            spud_date=date(2020, 1, 1),
            last_activity_date=date(2020, 3, 31),
        )

        assert well.calculate_construction_days() == 90

    def test_well_status_tracking(self):
        """Test well status options"""
        well = Well(
            id="WELL-003",
            name="PS003",
            api_number="1234567892",
            parent_id="LEASE-001",
            wellbore_status="ACTIVE",
        )

        assert well.wellbore_status == "ACTIVE"

        # Test status update
        well.update_status("SUSPENDED")
        assert well.wellbore_status == "SUSPENDED"

    def test_well_with_production_metrics(self):
        """Test well with production metrics"""
        well = Well(
            id="WELL-004", name="PS004", api_number="1234567893", parent_id="LEASE-001"
        )

        well.set_metric("daily_production", 5000)
        well.set_metric("cumulative_production", 1500000)
        well.set_metric("peak_rate", 8000)

        assert well.metrics["daily_production"] == 5000
        assert well.metrics["cumulative_production"] == 1500000
        assert well.metrics["peak_rate"] == 8000


class TestLeaseModel:
    """Test Lease data model"""

    def test_lease_initialization(self):
        """Test Lease model initialization"""
        lease = Lease(
            id="LEASE-001",
            name="Test Lease",
            lease_number="OCS-G-12345",
            parent_id="FIELD-001",
            operator="Test Oil Corp",
            lease_area_acres=5000,
        )

        assert lease.id == "LEASE-001"
        assert lease.lease_number == "OCS-G-12345"
        assert lease.level == HierarchyLevel.LEASE
        assert lease.operator == "Test Oil Corp"
        assert lease.lease_area_acres == 5000

    def test_lease_well_aggregation(self):
        """Test aggregating wells under a lease"""
        lease = Lease(
            id="LEASE-002",
            name="Test Lease 2",
            lease_number="OCS-G-12346",
            parent_id="FIELD-001",
        )

        # Add wells
        for i in range(3):
            well = Well(
                id=f"WELL-{i}",
                name=f"PS00{i}",
                api_number=f"123456789{i}",
                parent_id="LEASE-002",
            )
            well.set_metric("daily_production", 1000 * (i + 1))
            lease.add_child(well)

        # Test aggregation
        total_production = lease.aggregate_metric("daily_production")
        assert total_production == 6000  # 1000 + 2000 + 3000
        assert lease.get_well_count() == 3


class TestFieldModel:
    """Test Field data model"""

    def test_field_initialization(self):
        """Test Field model initialization"""
        field = Field(
            id="FIELD-001",
            name="Jack",
            field_code="JAC",
            parent_id="BLOCK-001",
            discovery_date=date(2004, 6, 1),
            water_depth_ft=7000,
            field_type="Oil",
        )

        assert field.id == "FIELD-001"
        assert field.name == "Jack"
        assert field.field_code == "JAC"
        assert field.level == HierarchyLevel.FIELD
        assert field.discovery_date == date(2004, 6, 1)
        assert field.water_depth_ft == 7000
        assert field.field_type == "Oil"

    def test_field_lease_aggregation(self):
        """Test aggregating leases under a field"""
        field = Field(
            id="FIELD-002", name="Julia", field_code="JUL", parent_id="BLOCK-001"
        )

        # Add leases
        for i in range(2):
            lease = Lease(
                id=f"LEASE-{i}",
                name=f"Lease {i}",
                lease_number=f"OCS-G-1234{i}",
                parent_id="FIELD-002",
            )
            lease.set_metric("total_wells", 5 * (i + 1))
            lease.set_metric("daily_production", 10000 * (i + 1))
            field.add_child(lease)

        # Test aggregation
        assert field.aggregate_metric("total_wells") == 15  # 5 + 10
        assert field.aggregate_metric("daily_production") == 30000  # 10000 + 20000
        assert field.get_lease_count() == 2


class TestBlockModel:
    """Test Block data model"""

    def test_block_initialization(self):
        """Test Block model initialization"""
        block = Block(
            id="BLOCK-001",
            name="Walker Ridge 759",
            block_number="759",
            protraction_area="Walker Ridge",
            block_area_acres=5760,
            water_depth_range=(6500, 7500),
        )

        assert block.id == "BLOCK-001"
        assert block.block_number == "759"
        assert block.protraction_area == "Walker Ridge"
        assert block.level == HierarchyLevel.BLOCK
        assert block.parent_id is None  # Blocks have no parent
        assert block.block_area_acres == 5760
        assert block.water_depth_range == (6500, 7500)

    def test_block_field_aggregation(self):
        """Test aggregating fields under a block"""
        block = Block(
            id="BLOCK-002",
            name="Walker Ridge 758",
            block_number="758",
            protraction_area="Walker Ridge",
        )

        # Add fields
        fields_data = [("Jack", 50000), ("St. Malo", 45000)]

        for name, production in fields_data:
            field = Field(
                id=f"FIELD-{name}",
                name=name,
                field_code=name[:3].upper(),
                parent_id="BLOCK-002",
            )
            field.set_metric("daily_production", production)
            block.add_child(field)

        # Test aggregation
        assert block.aggregate_metric("daily_production") == 95000
        assert block.get_field_count() == 2

    def test_block_hierarchy_traversal(self):
        """Test traversing the full hierarchy from block to well"""
        # Create block
        block = Block(
            id="BLOCK-003",
            name="Test Block",
            block_number="003",
            protraction_area="Test Area",
        )

        # Create field
        field = Field(
            id="FIELD-003", name="Test Field", field_code="TST", parent_id="BLOCK-003"
        )
        block.add_child(field)

        # Create lease
        lease = Lease(
            id="LEASE-003",
            name="Test Lease",
            lease_number="OCS-G-99999",
            parent_id="FIELD-003",
        )
        field.add_child(lease)

        # Create well
        well = Well(
            id="WELL-003",
            name="Test Well",
            api_number="9999999999",
            parent_id="LEASE-003",
        )
        lease.add_child(well)

        # Test traversal
        assert block.get_total_well_count() == 1
        assert block.get_all_wells()[0].id == "WELL-003"


class TestHierarchyLevel:
    """Test HierarchyLevel enum"""

    def test_hierarchy_level_ordering(self):
        """Test that hierarchy levels are properly ordered"""
        assert HierarchyLevel.WELL.value < HierarchyLevel.LEASE.value
        assert HierarchyLevel.LEASE.value < HierarchyLevel.FIELD.value
        assert HierarchyLevel.FIELD.value < HierarchyLevel.BLOCK.value

    def test_hierarchy_level_names(self):
        """Test hierarchy level string representations"""
        assert str(HierarchyLevel.WELL) == "HierarchyLevel.WELL"
        assert HierarchyLevel.WELL.name == "WELL"
        assert HierarchyLevel.LEASE.name == "LEASE"
        assert HierarchyLevel.FIELD.name == "FIELD"
        assert HierarchyLevel.BLOCK.name == "BLOCK"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
