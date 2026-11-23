"""Tests for vessel fleet base model."""

from worldenergydata.vessel_fleet.constants import M_TO_FT
from worldenergydata.vessel_fleet.models.base import BaseVesselEntry


class TestBaseVesselEntryBasic:
    def test_minimal(self):
        v = BaseVesselEntry(vessel_name="Test Vessel")
        assert v.vessel_name == "Test Vessel"
        assert v.vessel_category is None
        assert v.status is None
        assert v.loa_m is None

    def test_all_fields(self):
        v = BaseVesselEntry(
            vessel_name="Sleipnir",
            vessel_category="construction_vessel",
            vessel_type="crane_vessel",
            owner="Heerema",
            operator="Heerema Marine Contractors",
            imo_number="9781400",
            status="active",
            loa_m=220.0,
            beam_m=102.0,
            draft_m=12.0,
            year_built=2019,
            dp_class=3,
        )
        assert v.vessel_name == "Sleipnir"
        assert v.imo_number == "9781400"
        assert v.dp_class == 3


class TestIsActive:
    def test_none_status_is_active(self):
        v = BaseVesselEntry(vessel_name="V")
        assert v.is_active is True

    def test_active_status(self):
        v = BaseVesselEntry(vessel_name="V", status="active")
        assert v.is_active is True

    def test_warm_stacked_not_active(self):
        v = BaseVesselEntry(vessel_name="V", status="warm_stacked")
        assert v.is_active is False

    def test_cold_stacked_not_active(self):
        v = BaseVesselEntry(vessel_name="V", status="cold_stacked")
        assert v.is_active is False

    def test_scrapped_not_active(self):
        v = BaseVesselEntry(vessel_name="V", status="scrapped")
        assert v.is_active is False

    def test_retired_not_active(self):
        v = BaseVesselEntry(vessel_name="V", status="retired")
        assert v.is_active is False

    def test_under_contract_is_active(self):
        v = BaseVesselEntry(vessel_name="V", status="under_contract")
        assert v.is_active is True


class TestVesselKey:
    def test_basic(self):
        v = BaseVesselEntry(vessel_name="Sleipnir")
        assert v.vessel_key == "sleipnir"

    def test_spaces_to_underscores(self):
        v = BaseVesselEntry(vessel_name="Seven Borealis")
        assert v.vessel_key == "seven_borealis"

    def test_strips_whitespace(self):
        v = BaseVesselEntry(vessel_name="  Sleipnir  ")
        assert v.vessel_key == "sleipnir"


class TestNormalisedName:
    def test_basic(self):
        v = BaseVesselEntry(vessel_name="Sleipnir")
        assert v.normalised_name == "SLEIPNIR"

    def test_strips_mv_prefix(self):
        v = BaseVesselEntry(vessel_name="MV Sleipnir")
        assert v.normalised_name == "SLEIPNIR"

    def test_strips_m_slash_v_prefix(self):
        v = BaseVesselEntry(vessel_name="M/V Blue Marlin")
        assert v.normalised_name == "BLUE MARLIN"

    def test_strips_ss_prefix(self):
        v = BaseVesselEntry(vessel_name="SS Enterprise")
        assert v.normalised_name == "ENTERPRISE"

    def test_no_prefix(self):
        v = BaseVesselEntry(vessel_name="Thialf")
        assert v.normalised_name == "THIALF"


class TestUnitConversions:
    def test_loa_ft_conversion(self):
        v = BaseVesselEntry(vessel_name="V", loa_m=100.0)
        assert v.loa_ft is not None
        assert abs(v.loa_ft - 100.0 * M_TO_FT) < 0.01

    def test_loa_ft_none(self):
        v = BaseVesselEntry(vessel_name="V")
        assert v.loa_ft is None

    def test_beam_ft_conversion(self):
        v = BaseVesselEntry(vessel_name="V", beam_m=50.0)
        assert v.beam_ft is not None
        assert abs(v.beam_ft - 50.0 * M_TO_FT) < 0.01

    def test_beam_ft_none(self):
        v = BaseVesselEntry(vessel_name="V")
        assert v.beam_ft is None
