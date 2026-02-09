"""Tests for vessel fleet constants and enums."""

from __future__ import annotations

import pytest

from worldenergydata.vessel_fleet.constants import (
    VesselCategory,
    RigType,
    VesselType,
    VesselStatus,
    DataSource,
    PipelayMethod,
    PowerType,
    INACTIVE_STATUSES,
    DEEPWATER_THRESHOLD_FT,
    ULTRA_DEEPWATER_THRESHOLD_FT,
    FT_TO_M,
    M_TO_FT,
)


class TestVesselCategory:
    def test_member_count(self):
        assert len(VesselCategory) == 3

    def test_drilling_rig_value(self):
        assert VesselCategory.DRILLING_RIG.value == "drilling_rig"

    def test_is_string(self):
        assert isinstance(VesselCategory.DRILLING_RIG, str)


class TestRigType:
    def test_member_count(self):
        assert len(RigType) == 8

    def test_drillship(self):
        assert RigType.DRILLSHIP.value == "drillship"

    def test_jack_up(self):
        assert RigType.JACK_UP.value == "jack_up"


class TestVesselType:
    def test_member_count(self):
        assert len(VesselType) == 11

    def test_crane_vessel(self):
        assert VesselType.CRANE_VESSEL.value == "crane_vessel"


class TestVesselStatus:
    def test_member_count(self):
        assert len(VesselStatus) == 9

    def test_active(self):
        assert VesselStatus.ACTIVE.value == "active"


class TestDataSource:
    def test_member_count(self):
        assert len(DataSource) == 12

    def test_xls_historical(self):
        assert DataSource.XLS_HISTORICAL.value == "xls_historical"


class TestPipelayMethod:
    def test_member_count(self):
        assert len(PipelayMethod) == 4


class TestPowerType:
    def test_member_count(self):
        assert len(PowerType) == 4


class TestStaticConstants:
    def test_inactive_statuses_is_frozenset(self):
        assert isinstance(INACTIVE_STATUSES, frozenset)

    def test_inactive_statuses_contains_cold_stacked(self):
        assert "cold_stacked" in INACTIVE_STATUSES

    def test_deepwater_threshold(self):
        assert DEEPWATER_THRESHOLD_FT == 4000.0

    def test_ultra_deepwater_threshold(self):
        assert ULTRA_DEEPWATER_THRESHOLD_FT == 7500.0

    def test_ft_to_m_conversion(self):
        assert abs(FT_TO_M - 0.3048) < 1e-6

    def test_m_to_ft_round_trip(self):
        assert abs(100 * FT_TO_M * M_TO_FT - 100) < 1e-6
