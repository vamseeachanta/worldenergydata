"""Tests for rig fleet constants and classification utilities."""

from __future__ import annotations

import pytest

from worldenergydata.bsee.data.loaders.rig_fleet.constants import (
    DataSource,
    RigStatus,
    RigType,
    classify_rig_type,
)


class TestRigTypeEnum:
    """Tests for RigType enumeration."""

    def test_rig_type_enum_values(self):
        """All 9 rig types have expected string values."""
        assert RigType.DRILLSHIP.value == "drillship"
        assert RigType.SEMI_SUBMERSIBLE.value == "semi_submersible"
        assert RigType.JACK_UP.value == "jack_up"
        assert RigType.PLATFORM_RIG.value == "platform_rig"
        assert RigType.TENDER_ASSISTED.value == "tender_assisted"
        assert RigType.INLAND_BARGE.value == "inland_barge"
        assert RigType.SUBMERSIBLE.value == "submersible"
        assert RigType.LAND_RIG.value == "land_rig"
        assert RigType.UNKNOWN.value == "unknown"
        assert len(RigType) == 9


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


class TestDataSourceEnum:
    """Tests for DataSource enumeration."""

    def test_data_source_enum_values(self):
        """All 4 data sources have expected string values."""
        assert DataSource.BSEE_WAR.value == "bsee_war"
        assert DataSource.MANUAL_OVERRIDE.value == "manual_override"
        assert DataSource.XLS_HISTORICAL.value == "xls_historical"
        assert DataSource.UNKNOWN.value == "unknown"
        assert len(DataSource) == 4


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

    @pytest.mark.parametrize(
        "rig_name,expected",
        [
            # Drillships
            ("NOBLE GLOBETROTTER II", RigType.DRILLSHIP),
            ("PACIFIC KHAMSIN", RigType.DRILLSHIP),
            ("COBALT EXPLORER", RigType.DRILLSHIP),
            ("BULLY I", RigType.DRILLSHIP),
            ("T.O. DEEPWATER NAUTILUS", RigType.DRILLSHIP),
            ("STENA ICEMAX", RigType.DRILLSHIP),
            ("DISCOVERER CLEAR LEADER", RigType.DRILLSHIP),
            # Semi-submersibles
            ("TRANSOCEAN ENDURANCE", RigType.SEMI_SUBMERSIBLE),
            ("NAUTILUS", RigType.SEMI_SUBMERSIBLE),
            ("SEDCO 711", RigType.SEMI_SUBMERSIBLE),
            ("SCARABEO 9", RigType.SEMI_SUBMERSIBLE),
            ("MAERSK DEVELOPER", RigType.SEMI_SUBMERSIBLE),
            ("OCEAN CONFIDENCE", RigType.SEMI_SUBMERSIBLE),
            ("Q4000", RigType.SEMI_SUBMERSIBLE),
            # Jack-ups
            ("HERCULES 205", RigType.JACK_UP),
            ("KEY SINGAPORE", RigType.JACK_UP),
            ("KEY MANHATTAN", RigType.JACK_UP),
            ("SEAHAWK 2000", RigType.JACK_UP),
            ("CECIL PROVINE", RigType.JACK_UP),
            ("SUNDOWNER", RigType.JACK_UP),
            ("ENSCO 87", RigType.JACK_UP),
            ("SPARTAN 303", RigType.JACK_UP),
            # Platform rigs
            ("NABORS F27", RigType.PLATFORM_RIG),
            ("HELMERICH & PAYNE 201", RigType.PLATFORM_RIG),
            ("H&P RIG 100", RigType.PLATFORM_RIG),
            ("PARKER 55B", RigType.PLATFORM_RIG),
            ("FLEX RIG 201", RigType.PLATFORM_RIG),
            ("PLATFORM RIG 99", RigType.PLATFORM_RIG),
            # Inland barge
            ("INLAND BARGE 5", RigType.INLAND_BARGE),
            ("DELTA BARGE II", RigType.INLAND_BARGE),
        ],
    )
    def test_classify_expanded_keywords(self, rig_name: str, expected: RigType):
        """Expanded keyword coverage classifies known GOM rigs correctly."""
        assert classify_rig_type(rig_name) == expected
