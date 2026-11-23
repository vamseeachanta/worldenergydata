"""Tests for BSEE platform structure domain model."""

from worldenergydata.bsee.data.models.platform import PlatformStructure


class TestPlatformStructure:
    """Tests for PlatformStructure dataclass."""

    def test_create_with_required_fields(self):
        ps = PlatformStructure(
            area_code="EI",
            block_number="330",
            structure_number="A001",
        )
        assert ps.area_code == "EI"

    def test_create_with_all_fields(self):
        ps = PlatformStructure(
            area_code="EI",
            block_number="330",
            structure_number="A001",
            complex_id_num="C001",
            structure_name="Platform Alpha",
            struc_type_code="FP",
            water_depth=500.0,
            install_date="1990-01-01",
            removal_date=None,
            deck_count=2,
            slot_count=12,
            latitude=29.0,
            longitude=-88.5,
        )
        assert ps.structure_name == "Platform Alpha"
        assert ps.water_depth == 500.0

    def test_is_active_no_removal(self):
        ps = PlatformStructure(
            area_code="EI", block_number="330", structure_number="A001"
        )
        assert ps.is_active is True

    def test_is_active_with_removal(self):
        ps = PlatformStructure(
            area_code="EI",
            block_number="330",
            structure_number="A001",
            removal_date="2020-06-15",
        )
        assert ps.is_active is False

    def test_structure_key(self):
        ps = PlatformStructure(
            area_code="EI", block_number="330", structure_number="A001"
        )
        assert ps.structure_key == "EI_330_A001"

    def test_structure_type_caisson(self):
        ps = PlatformStructure(
            area_code="EI",
            block_number="330",
            structure_number="A001",
            struc_type_code="CT",
        )
        assert ps.structure_type == "Caisson"

    def test_structure_type_tlp(self):
        ps = PlatformStructure(
            area_code="EI",
            block_number="330",
            structure_number="A001",
            struc_type_code="TLP",
        )
        assert ps.structure_type == "Tension Leg Platform"

    def test_structure_type_subsea(self):
        ps = PlatformStructure(
            area_code="EI",
            block_number="330",
            structure_number="A001",
            struc_type_code="SS",
        )
        assert ps.structure_type == "Subsea Structure"

    def test_structure_type_unknown(self):
        ps = PlatformStructure(
            area_code="EI",
            block_number="330",
            structure_number="A001",
            struc_type_code="ZZZ",
        )
        assert ps.structure_type == "Unknown"

    def test_structure_type_none(self):
        ps = PlatformStructure(
            area_code="EI",
            block_number="330",
            structure_number="A001",
            struc_type_code=None,
        )
        assert ps.structure_type == "Unknown"
