"""Tests for vessel fleet constants."""

from worldenergydata.vessel_fleet.constants import (
    DEEPWATER_THRESHOLD_FT,
    FT_TO_M,
    INACTIVE_STATUSES,
    M_TO_FT,
    ULTRA_DEEPWATER_THRESHOLD_FT,
    DataSource,
    PipelayMethod,
    PowerType,
    RigType,
    VesselCategory,
    VesselStatus,
    VesselType,
)


class TestVesselCategory:
    def test_all_members(self):
        expected = {
            "DRILLING_RIG",
            "CONSTRUCTION_VESSEL",
            "SERVICE_VESSEL",
            "INTERVENTION_VESSEL",
        }
        assert {m.name for m in VesselCategory} == expected

    def test_string_enum(self):
        assert isinstance(VesselCategory.DRILLING_RIG, str)
        assert VesselCategory.DRILLING_RIG == "drilling_rig"


class TestRigType:
    def test_all_members(self):
        expected = {
            "DRILLSHIP",
            "SEMI_SUBMERSIBLE",
            "JACK_UP",
            "PLATFORM_RIG",
            "TENDER_ASSISTED",
            "INLAND_BARGE",
            "SUBMERSIBLE",
            "LAND_RIG",
        }
        assert {m.name for m in RigType} == expected


class TestVesselType:
    def test_all_members(self):
        expected = {
            "CRANE_VESSEL",
            "PIPELAY_VESSEL",
            "HEAVY_LIFT",
            "HEAVY_TRANSPORT",
            "WIND_INSTALLATION",
            "CABLE_LAY",
            "SURF_VESSEL",
            "AHTS",
            "PSV",
            "DIVE_SUPPORT",
            "FPSO",
            "RLWI_MONOHULL",
            "HEAVY_INTERVENTION_SEMI",
            "MPSV",
        }
        assert {m.name for m in VesselType} == expected


class TestVesselStatus:
    def test_all_members(self):
        expected = {
            "ACTIVE",
            "UNDER_CONTRACT",
            "WARM_STACKED",
            "COLD_STACKED",
            "UNDER_CONSTRUCTION",
            "IN_TRANSIT",
            "IN_YARD",
            "SCRAPPED",
            "RETIRED",
        }
        assert {m.name for m in VesselStatus} == expected


class TestDataSource:
    def test_all_members(self):
        expected = {
            "XLS_HISTORICAL",
            "BSEE_WAR",
            "CONTRACTOR_FLEET_PAGE",
            "CONTRACTOR_SPEC_PDF",
            "CONTRACTOR_FSR",
            "EQUASIS",
            "ABS_REGISTER",
            "DNV_REGISTER",
            "LLOYD_REGISTER",
            "BOEM",
            "BAKER_HUGHES",
            "MANUAL",
        }
        assert {m.name for m in DataSource} == expected


class TestPipelayMethod:
    def test_all_members(self):
        expected = {"S_LAY", "J_LAY", "REEL_LAY", "FLEX_LAY"}
        assert {m.name for m in PipelayMethod} == expected


class TestPowerType:
    def test_all_members(self):
        expected = {"AC", "SCR", "MECHANICAL", "AC_VFD"}
        assert {m.name for m in PowerType} == expected


class TestInactiveStatuses:
    def test_is_frozenset(self):
        assert isinstance(INACTIVE_STATUSES, frozenset)

    def test_contains_expected(self):
        assert "warm_stacked" in INACTIVE_STATUSES
        assert "cold_stacked" in INACTIVE_STATUSES
        assert "scrapped" in INACTIVE_STATUSES
        assert "retired" in INACTIVE_STATUSES

    def test_active_not_included(self):
        assert "active" not in INACTIVE_STATUSES
        assert "under_contract" not in INACTIVE_STATUSES


class TestThresholds:
    def test_deepwater(self):
        assert DEEPWATER_THRESHOLD_FT == 4000.0

    def test_ultra_deepwater(self):
        assert ULTRA_DEEPWATER_THRESHOLD_FT == 7500.0

    def test_ordering(self):
        assert DEEPWATER_THRESHOLD_FT < ULTRA_DEEPWATER_THRESHOLD_FT


class TestConversions:
    def test_ft_to_m(self):
        assert FT_TO_M == 0.3048

    def test_m_to_ft(self):
        assert abs(M_TO_FT - (1.0 / 0.3048)) < 1e-10

    def test_roundtrip(self):
        value_ft = 100.0
        value_m = value_ft * FT_TO_M
        roundtrip = value_m * M_TO_FT
        assert abs(roundtrip - value_ft) < 1e-10
