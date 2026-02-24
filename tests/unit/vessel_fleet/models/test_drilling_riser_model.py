"""Tests for drilling riser component domain models."""

import pytest

from worldenergydata.vessel_fleet.models.drilling_riser import (
    BOPEntry,
    FlexJointEntry,
    LMRPEntry,
    RiserJointEntry,
    TelescopicJointEntry,
)


class TestRiserJointEntry:
    def test_od_m_conversion(self):
        rj = RiserJointEntry(component_id="RJ-1", od_in=21.0)
        assert rj.od_m == pytest.approx(0.5334, abs=0.001)

    def test_length_m_conversion(self):
        rj = RiserJointEntry(component_id="RJ-1", length_ft=75.0)
        assert rj.length_m == pytest.approx(22.86, abs=0.01)

    def test_has_buoyancy_true(self):
        rj = RiserJointEntry(component_id="RJ-1", buoyancy_coverage_pct=100.0)
        assert rj.has_buoyancy is True

    def test_has_buoyancy_false(self):
        rj = RiserJointEntry(component_id="RJ-1", buoyancy_coverage_pct=0)
        assert rj.has_buoyancy is False

    def test_has_buoyancy_none(self):
        rj = RiserJointEntry(component_id="RJ-1")
        assert rj.has_buoyancy is False

    def test_is_pup_joint_true(self):
        rj = RiserJointEntry(component_id="RJ-1", length_ft=50.0)
        assert rj.is_pup_joint is True

    def test_is_pup_joint_false(self):
        rj = RiserJointEntry(component_id="RJ-1", length_ft=75.0)
        assert rj.is_pup_joint is False

    def test_is_pup_joint_no_length(self):
        rj = RiserJointEntry(component_id="RJ-1")
        assert rj.is_pup_joint is False

    def test_od_m_none_when_missing(self):
        rj = RiserJointEntry(component_id="RJ-1")
        assert rj.od_m is None


class TestBOPEntry:
    def test_is_subsea(self):
        bop = BOPEntry(component_id="BOP-1", bop_type="subsea")
        assert bop.is_subsea is True

    def test_is_not_subsea(self):
        bop = BOPEntry(component_id="BOP-1", bop_type="surface")
        assert bop.is_subsea is False

    def test_total_ram_count(self):
        bop = BOPEntry(
            component_id="BOP-1",
            shear_ram_count=1, pipe_ram_count=3,
        )
        assert bop.total_ram_count == 4

    def test_total_ram_count_partial(self):
        bop = BOPEntry(component_id="BOP-1", pipe_ram_count=2)
        assert bop.total_ram_count == 2

    def test_height_m_conversion(self):
        bop = BOPEntry(component_id="BOP-1", height_ft=35.0)
        assert bop.height_m == pytest.approx(10.668, abs=0.01)

    def test_weight_air_tonnes(self):
        bop = BOPEntry(component_id="BOP-1", weight_air_kips=400.0)
        assert bop.weight_air_tonnes == pytest.approx(181.437, abs=0.1)


class TestLMRPEntry:
    def test_height_m_conversion(self):
        lmrp = LMRPEntry(component_id="LMRP-1", height_ft=18.0)
        assert lmrp.height_m == pytest.approx(5.486, abs=0.01)

    def test_height_m_none(self):
        lmrp = LMRPEntry(component_id="LMRP-1")
        assert lmrp.height_m is None


class TestFlexJointEntry:
    def test_is_upper(self):
        fj = FlexJointEntry(component_id="FJ-1", position="upper")
        assert fj.is_upper is True

    def test_is_not_upper(self):
        fj = FlexJointEntry(component_id="FJ-1", position="lower")
        assert fj.is_upper is False

    def test_height_m_conversion(self):
        fj = FlexJointEntry(component_id="FJ-1", height_ft=10.0)
        assert fj.height_m == pytest.approx(3.048, abs=0.01)


class TestTelescopicJointEntry:
    def test_stroke_m_conversion(self):
        tj = TelescopicJointEntry(component_id="TJ-1", stroke_ft=50.0)
        assert tj.stroke_m == pytest.approx(15.24, abs=0.01)

    def test_total_length_ft(self):
        tj = TelescopicJointEntry(
            component_id="TJ-1",
            outer_barrel_length_ft=65.0,
            inner_barrel_length_ft=45.0,
        )
        assert tj.total_length_ft == 110.0

    def test_total_length_ft_outer_only(self):
        tj = TelescopicJointEntry(
            component_id="TJ-1", outer_barrel_length_ft=65.0,
        )
        assert tj.total_length_ft == 65.0

    def test_total_length_ft_none(self):
        tj = TelescopicJointEntry(component_id="TJ-1")
        assert tj.total_length_ft is None
