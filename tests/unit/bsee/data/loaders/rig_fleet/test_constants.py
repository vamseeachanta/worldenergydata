"""Tests for BSEE rig fleet constants and classification."""

from worldenergydata.bsee.data.loaders.rig_fleet.constants import (
    DataSource,
    RigStatus,
    RigType,
    classify_rig_type,
)


class TestRigTypeEnum:
    def test_all_members(self):
        names = {m.name for m in RigType}
        assert "DRILLSHIP" in names
        assert "SEMI_SUBMERSIBLE" in names
        assert "JACK_UP" in names
        assert "PLATFORM_RIG" in names
        assert "UNKNOWN" in names

    def test_string_enum(self):
        assert isinstance(RigType.DRILLSHIP, str)
        assert RigType.DRILLSHIP == "drillship"

    def test_member_count(self):
        assert len(RigType) == 16


class TestRigStatusEnum:
    def test_all_members(self):
        names = {m.name for m in RigStatus}
        assert "ACTIVE" in names
        assert "STACKED_COLD" in names
        assert "STACKED_WARM" in names
        assert "SCRAPPED" in names
        assert "UNKNOWN" in names

    def test_string_enum(self):
        assert isinstance(RigStatus.ACTIVE, str)
        assert RigStatus.ACTIVE == "active"


class TestDataSourceEnum:
    def test_all_members(self):
        names = {m.name for m in DataSource}
        assert "BSEE_WAR" in names
        assert "MANUAL_OVERRIDE" in names
        assert "XLS_HISTORICAL" in names
        assert "UNKNOWN" in names


class TestClassifyRigTypeDrillship:
    def test_deepwater(self):
        assert classify_rig_type("DEEPWATER ASGARD") == RigType.DRILLSHIP

    def test_discoverer(self):
        assert classify_rig_type("Discoverer Inspiration") == RigType.DRILLSHIP

    def test_explorer(self):
        assert classify_rig_type("Explorer II") == RigType.DRILLSHIP

    def test_stena(self):
        assert classify_rig_type("Stena DrillMAX") == RigType.DRILLSHIP

    def test_noble_globetrotter(self):
        assert classify_rig_type("Noble Globetrotter II") == RigType.DRILLSHIP


class TestClassifyRigTypeSemiSub:
    def test_development_driller(self):
        assert classify_rig_type("Development Driller III") == RigType.SEMI_SUBMERSIBLE

    def test_transocean(self):
        assert classify_rig_type("Transocean Leader") == RigType.SEMI_SUBMERSIBLE

    def test_ocean(self):
        assert classify_rig_type("Ocean Valor") == RigType.SEMI_SUBMERSIBLE

    def test_scarabeo(self):
        assert classify_rig_type("Scarabeo 9") == RigType.SEMI_SUBMERSIBLE

    def test_q4000(self):
        assert classify_rig_type("Q4000") == RigType.SEMI_SUBMERSIBLE


class TestClassifyRigTypeJackUp:
    def test_rowan(self):
        assert classify_rig_type("Rowan Mississippi") == RigType.JACK_UP

    def test_ensco(self):
        assert classify_rig_type("ENSCO 75") == RigType.JACK_UP

    def test_spartan(self):
        assert classify_rig_type("Spartan 151") == RigType.JACK_UP

    def test_hercules(self):
        assert classify_rig_type("HERCULES 120") == RigType.JACK_UP


class TestClassifyRigTypePlatformRig:
    def test_helmerich(self):
        assert classify_rig_type("Helmerich & Payne 100") == RigType.PLATFORM_RIG

    def test_nabors(self):
        assert classify_rig_type("NABORS 770") == RigType.PLATFORM_RIG

    def test_platform_rig(self):
        assert classify_rig_type("PLATFORM RIG #5") == RigType.PLATFORM_RIG

    def test_parker(self):
        assert classify_rig_type("PARKER 22") == RigType.PLATFORM_RIG


class TestClassifyRigTypeInlandBarge:
    def test_inland(self):
        assert classify_rig_type("INLAND 200") == RigType.INLAND_BARGE

    def test_barge(self):
        assert classify_rig_type("BARGE RIG 50") == RigType.INLAND_BARGE


class TestClassifyRigTypeIntervention:
    def test_wireline(self):
        assert classify_rig_type("WIRELINE UNIT 5") == RigType.WIRELINE_UNIT

    def test_slickline(self):
        assert classify_rig_type("SLICKLINE") == RigType.WIRELINE_UNIT

    def test_coil_tubing(self):
        assert classify_rig_type("COILED TUBING UNIT") == RigType.COIL_TUBING_UNIT

    def test_ct_unit(self):
        assert classify_rig_type("CT UNIT 3") == RigType.COIL_TUBING_UNIT

    def test_snubbing(self):
        assert classify_rig_type("SNUBBING UNIT") == RigType.SNUBBING_UNIT

    def test_hydraulic_workover(self):
        assert classify_rig_type("HYDRAULIC WORKOVER UNIT") == RigType.SNUBBING_UNIT

    def test_lift_boat(self):
        assert classify_rig_type("LIFT BOAT ELEVATING") == RigType.LIFT_BOAT

    def test_liftboat(self):
        assert classify_rig_type("LIFTBOAT 5") == RigType.LIFT_BOAT

    def test_pumping_unit(self):
        assert classify_rig_type("PUMPING UNIT 10") == RigType.PUMPING_UNIT

    def test_support_vessel(self):
        assert classify_rig_type("DIVE SUPPORT VESSEL") == RigType.SUPPORT_VESSEL

    def test_workover_rig(self):
        assert classify_rig_type("WORKOVER 33") == RigType.WORKOVER_RIG


class TestClassifyRigTypeUnknown:
    def test_unknown_name(self):
        assert classify_rig_type("RANDOM NAME") == RigType.UNKNOWN

    def test_empty(self):
        assert classify_rig_type("") == RigType.UNKNOWN

    def test_case_insensitive(self):
        assert classify_rig_type("deepwater horizon") == RigType.DRILLSHIP
