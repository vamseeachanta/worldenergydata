"""Tests for drilling riser domain models."""

import pytest

from worldenergydata.vessel_fleet.constants import FT_TO_M
from worldenergydata.vessel_fleet.models.drilling_riser import (
    BOPEntry,
    FlexJointEntry,
    LMRPEntry,
    RiserJointEntry,
    TelescopicJointEntry,
)


class TestRiserJointEntry:
    def test_required(self):
        r = RiserJointEntry(component_id="RJ-001")
        assert r.component_id == "RJ-001"
        assert r.component_type == "riser_joint"

    def test_od_m(self):
        r = RiserJointEntry(component_id="RJ-001", od_in=21.0)
        assert r.od_m == pytest.approx(21.0 * 0.0254)

    def test_od_m_none(self):
        r = RiserJointEntry(component_id="RJ-001")
        assert r.od_m is None

    def test_length_m(self):
        r = RiserJointEntry(component_id="RJ-001", length_ft=75.0)
        assert r.length_m == pytest.approx(75.0 * FT_TO_M)

    def test_length_m_none(self):
        r = RiserJointEntry(component_id="RJ-001")
        assert r.length_m is None

    def test_has_buoyancy_true(self):
        r = RiserJointEntry(
            component_id="RJ-001",
            buoyancy_coverage_pct=90.0,
        )
        assert r.has_buoyancy is True

    def test_has_buoyancy_false(self):
        r = RiserJointEntry(component_id="RJ-001")
        assert r.has_buoyancy is False

    def test_has_buoyancy_zero(self):
        r = RiserJointEntry(
            component_id="RJ-001",
            buoyancy_coverage_pct=0.0,
        )
        assert r.has_buoyancy is False

    def test_is_pup_joint_true(self):
        r = RiserJointEntry(component_id="RJ-001", length_ft=30.0)
        assert r.is_pup_joint is True

    def test_is_pup_joint_false(self):
        r = RiserJointEntry(component_id="RJ-001", length_ft=75.0)
        assert r.is_pup_joint is False

    def test_is_pup_joint_boundary(self):
        r = RiserJointEntry(component_id="RJ-001", length_ft=60.0)
        assert r.is_pup_joint is False

    def test_is_pup_joint_none(self):
        r = RiserJointEntry(component_id="RJ-001")
        assert r.is_pup_joint is False


class TestBOPEntry:
    def test_required(self):
        b = BOPEntry(component_id="BOP-001")
        assert b.component_type == "bop"

    def test_is_subsea_true(self):
        b = BOPEntry(component_id="BOP-001", bop_type="subsea")
        assert b.is_subsea is True

    def test_is_subsea_uppercase(self):
        b = BOPEntry(component_id="BOP-001", bop_type="Subsea")
        assert b.is_subsea is True

    def test_is_subsea_false(self):
        b = BOPEntry(component_id="BOP-001", bop_type="surface")
        assert b.is_subsea is False

    def test_is_subsea_none(self):
        b = BOPEntry(component_id="BOP-001")
        assert b.is_subsea is False

    def test_total_ram_count(self):
        b = BOPEntry(
            component_id="BOP-001",
            shear_ram_count=2,
            pipe_ram_count=3,
        )
        assert b.total_ram_count == 5

    def test_total_ram_count_none(self):
        b = BOPEntry(component_id="BOP-001")
        assert b.total_ram_count == 0

    def test_height_m(self):
        b = BOPEntry(component_id="BOP-001", height_ft=50.0)
        assert b.height_m == pytest.approx(50.0 * FT_TO_M)

    def test_height_m_none(self):
        b = BOPEntry(component_id="BOP-001")
        assert b.height_m is None

    def test_weight_air_tonnes(self):
        b = BOPEntry(component_id="BOP-001", weight_air_kips=500.0)
        assert b.weight_air_tonnes == pytest.approx(500.0 * 0.453592)

    def test_weight_air_tonnes_none(self):
        b = BOPEntry(component_id="BOP-001")
        assert b.weight_air_tonnes is None


class TestLMRPEntry:
    def test_required(self):
        l = LMRPEntry(component_id="LMRP-001")
        assert l.component_type == "lmrp"

    def test_height_m(self):
        l = LMRPEntry(component_id="LMRP-001", height_ft=25.0)
        assert l.height_m == pytest.approx(25.0 * FT_TO_M)

    def test_height_m_none(self):
        l = LMRPEntry(component_id="LMRP-001")
        assert l.height_m is None


class TestFlexJointEntry:
    def test_required(self):
        f = FlexJointEntry(component_id="FJ-001")
        assert f.component_type == "flex_joint"

    def test_is_upper_true(self):
        f = FlexJointEntry(component_id="FJ-001", position="upper")
        assert f.is_upper is True

    def test_is_upper_case_insensitive(self):
        f = FlexJointEntry(component_id="FJ-001", position="Upper")
        assert f.is_upper is True

    def test_is_upper_false(self):
        f = FlexJointEntry(component_id="FJ-001", position="lower")
        assert f.is_upper is False

    def test_is_upper_none(self):
        f = FlexJointEntry(component_id="FJ-001")
        assert f.is_upper is False

    def test_height_m(self):
        f = FlexJointEntry(component_id="FJ-001", height_ft=10.0)
        assert f.height_m == pytest.approx(10.0 * FT_TO_M)


class TestTelescopicJointEntry:
    def test_required(self):
        t = TelescopicJointEntry(component_id="TJ-001")
        assert t.component_type == "telescopic_joint"

    def test_stroke_m(self):
        t = TelescopicJointEntry(component_id="TJ-001", stroke_ft=50.0)
        assert t.stroke_m == pytest.approx(50.0 * FT_TO_M)

    def test_stroke_m_none(self):
        t = TelescopicJointEntry(component_id="TJ-001")
        assert t.stroke_m is None

    def test_total_length_ft(self):
        t = TelescopicJointEntry(
            component_id="TJ-001",
            outer_barrel_length_ft=60.0,
            inner_barrel_length_ft=50.0,
        )
        assert t.total_length_ft == 110.0

    def test_total_length_ft_no_inner(self):
        t = TelescopicJointEntry(
            component_id="TJ-001",
            outer_barrel_length_ft=60.0,
        )
        assert t.total_length_ft == 60.0

    def test_total_length_ft_none(self):
        t = TelescopicJointEntry(component_id="TJ-001")
        assert t.total_length_ft is None
