"""Tests for BSEE deepwater structure domain model."""

from worldenergydata.bsee.data.models.deepwater_structure import DeepwaterStructure


class TestDeepwaterStructure:
    """Tests for DeepwaterStructure dataclass."""

    def test_create_with_required_fields(self):
        ds = DeepwaterStructure(
            area_code="GC",
            block_number="640",
            structure_number="A001",
        )
        assert ds.area_code == "GC"
        assert ds.block_number == "640"

    def test_create_with_all_fields(self):
        ds = DeepwaterStructure(
            area_code="GC",
            block_number="640",
            structure_number="A001",
            complex_id_num="C001",
            structure_name="Test Platform",
            struc_type_code="FP",
            water_depth=3000.0,
            install_date="2005-01-01",
            removal_date=None,
            deck_count=3,
            slot_count=24,
            latitude=28.5,
            longitude=-89.2,
            permit_number="P-001",
            bus_asc_name="Energy Co",
        )
        assert ds.structure_name == "Test Platform"
        assert ds.permit_number == "P-001"

    def test_is_active_no_removal_date(self):
        ds = DeepwaterStructure(
            area_code="GC", block_number="640", structure_number="A001"
        )
        assert ds.is_active is True

    def test_is_active_with_removal_date(self):
        ds = DeepwaterStructure(
            area_code="GC",
            block_number="640",
            structure_number="A001",
            removal_date="2020-01-01",
        )
        assert ds.is_active is False

    def test_structure_key(self):
        ds = DeepwaterStructure(
            area_code="GC", block_number="640", structure_number="A001"
        )
        assert ds.structure_key == "GC_640_A001"

    def test_structure_type_fixed_platform(self):
        ds = DeepwaterStructure(
            area_code="GC",
            block_number="640",
            structure_number="A001",
            struc_type_code="FP",
        )
        assert ds.structure_type == "Fixed Platform"

    def test_structure_type_spar(self):
        ds = DeepwaterStructure(
            area_code="GC",
            block_number="640",
            structure_number="A001",
            struc_type_code="SPAR",
        )
        assert ds.structure_type == "Spar"

    def test_structure_type_fpso(self):
        ds = DeepwaterStructure(
            area_code="GC",
            block_number="640",
            structure_number="A001",
            struc_type_code="FPSO",
        )
        assert ds.structure_type == "FPSO"

    def test_structure_type_unknown(self):
        ds = DeepwaterStructure(
            area_code="GC",
            block_number="640",
            structure_number="A001",
            struc_type_code="XYZ",
        )
        assert ds.structure_type == "Unknown"

    def test_structure_type_none(self):
        ds = DeepwaterStructure(
            area_code="GC",
            block_number="640",
            structure_number="A001",
            struc_type_code=None,
        )
        assert ds.structure_type == "Unknown"
