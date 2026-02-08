"""Tests for rig fleet constants and classification utilities."""

from __future__ import annotations

from worldenergydata.modules.bsee.data.loaders.rig_fleet.constants import (
    RigStatus,
    RigType,
    classify_rig_type,
)


class TestRigTypeEnum:
    """Tests for RigType enumeration."""

    def test_rig_type_enum_values(self):
        """All 8 rig types have expected string values."""
        assert RigType.DRILLSHIP.value == "drillship"
        assert RigType.SEMI_SUBMERSIBLE.value == "semi_submersible"
        assert RigType.JACK_UP.value == "jack_up"
        assert RigType.PLATFORM_RIG.value == "platform_rig"
        assert RigType.TENDER_ASSISTED.value == "tender_assisted"
        assert RigType.INLAND_BARGE.value == "inland_barge"
        assert RigType.SUBMERSIBLE.value == "submersible"
        assert RigType.UNKNOWN.value == "unknown"
        assert len(RigType) == 8


class TestRigStatusEnum:
    """Tests for RigStatus enumeration."""

    def test_rig_status_enum_values(self):
        """All 9 statuses have expected string values."""
        assert RigStatus.ACTIVE.value == "active"
        assert RigStatus.STACKED_COLD.value == "stacked_cold"
        assert RigStatus.STACKED_WARM.value == "stacked_warm"
        assert RigStatus.UNDER_CONTRACT.value == "under_contract"
        assert RigStatus.AVAILABLE.value == "available"
        assert RigStatus.IN_TRANSIT.value == "in_transit"
        assert RigStatus.IN_SHIPYARD.value == "in_shipyard"
        assert RigStatus.SCRAPPED.value == "scrapped"
        assert RigStatus.UNKNOWN.value == "unknown"
        assert len(RigStatus) == 9


class TestClassifyRigType:
    """Tests for classify_rig_type heuristic function."""

    def test_classify_drillship(self):
        """Drillship keyword in name yields DRILLSHIP type."""
        assert classify_rig_type("T.O. DEEPWATER TITAN") == RigType.DRILLSHIP

    def test_classify_semi_sub(self):
        """Semi-submersible keyword in name yields SEMI_SUBMERSIBLE type."""
        assert classify_rig_type("DEVELOPMENT DRILLER III") == RigType.SEMI_SUBMERSIBLE

    def test_classify_jack_up(self):
        """Jack-up keyword in name yields JACK_UP type."""
        assert classify_rig_type("ROWAN MISSISSIPPI") == RigType.JACK_UP

    def test_classify_platform_rig(self):
        """Platform rig keyword in name yields PLATFORM_RIG type."""
        assert classify_rig_type("PLATFORM RIG 42") == RigType.PLATFORM_RIG

    def test_classify_unknown(self):
        """Unrecognised name yields UNKNOWN type."""
        assert classify_rig_type("SOME RANDOM NAME") == RigType.UNKNOWN

    def test_classify_case_insensitive(self):
        """Classification is case-insensitive."""
        assert classify_rig_type("deepwater titan") == RigType.DRILLSHIP
