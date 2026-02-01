from __future__ import annotations

from worldenergydata.modules.bsee.data.models.platform import PlatformStructure


class TestPlatformStructure:
    """Tests for PlatformStructure dataclass."""

    def _make_platform(self, **overrides) -> PlatformStructure:
        """Helper to create a PlatformStructure with sensible defaults."""
        defaults = {
            "area_code": "WC",
            "block_number": "168",
            "structure_number": "A001",
            "complex_id_num": None,
            "structure_name": "Test Platform",
            "struc_type_code": "FP",
            "maj_struc_flag": "Y",
            "field_name_code": None,
            "water_depth": 150.0,
            "install_date": "1990-05-15",
            "removal_date": None,
            "deck_count": 2,
            "slot_count": 12,
            "latitude": 28.5,
            "longitude": -89.5,
            "lease_number": "G12345",
            "district_code": "3",
        }
        defaults.update(overrides)
        return PlatformStructure(**defaults)

    def test_is_active_no_removal_date(self):
        """Platform is active when removal_date is None."""
        platform = self._make_platform(removal_date=None)
        assert platform.is_active is True

    def test_is_active_with_removal_date(self):
        """Platform is inactive when removal_date is set."""
        platform = self._make_platform(removal_date="2020-01-15")
        assert platform.is_active is False

    def test_structure_key(self):
        """Structure key is area_code_block_number_structure_number."""
        platform = self._make_platform(
            area_code="WC",
            block_number="168",
            structure_number="A001",
        )
        assert platform.structure_key == "WC_168_A001"

    def test_structure_key_different_values(self):
        """Structure key changes with different input values."""
        platform = self._make_platform(
            area_code="GC",
            block_number="640",
            structure_number="B002",
        )
        assert platform.structure_key == "GC_640_B002"

    def test_type_classification_fixed_platform(self):
        """FP code classifies as Fixed Platform."""
        platform = self._make_platform(struc_type_code="FP")
        assert platform.structure_type == "Fixed Platform"

    def test_type_classification_caisson(self):
        """CT code classifies as Caisson."""
        platform = self._make_platform(struc_type_code="CT")
        assert platform.structure_type == "Caisson"

    def test_type_classification_tlp(self):
        """TLP code classifies as Tension Leg Platform."""
        platform = self._make_platform(struc_type_code="TLP")
        assert platform.structure_type == "Tension Leg Platform"

    def test_type_classification_spar(self):
        """SPAR code classifies as Spar."""
        platform = self._make_platform(struc_type_code="SPAR")
        assert platform.structure_type == "Spar"

    def test_type_classification_fps(self):
        """FPS code classifies as Floating Production System."""
        platform = self._make_platform(struc_type_code="FPS")
        assert platform.structure_type == "Floating Production System"

    def test_type_classification_fpso(self):
        """FPSO code classifies as FPSO."""
        platform = self._make_platform(struc_type_code="FPSO")
        assert platform.structure_type == "FPSO"

    def test_type_classification_subsea(self):
        """SS code classifies as Subsea Structure."""
        platform = self._make_platform(struc_type_code="SS")
        assert platform.structure_type == "Subsea Structure"

    def test_type_classification_unknown(self):
        """Unknown code classifies as Unknown."""
        platform = self._make_platform(struc_type_code="XYZ")
        assert platform.structure_type == "Unknown"

    def test_type_classification_none(self):
        """None code classifies as Unknown."""
        platform = self._make_platform(struc_type_code=None)
        assert platform.structure_type == "Unknown"
