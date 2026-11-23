# ABOUTME: Tests for multi-bend jumper + mooring/manifold 3D assemblies (issue #580).
# ABOUTME: Skips cleanly if CadQuery/OCCT is unavailable in the environment.
"""Tests for the deepened 3D equipment / assembly geometry (epic #567)."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

# Skip the whole module (incl. the cadquery-importing modules under test) if the
# OCCT stack isn't installed, rather than erroring at collection.
pytest.importorskip("cadquery")

from worldenergydata.field_development.assembly_3d import (  # noqa: E402
    build_manifold_assembly,
    build_mooring_spread,
    export_manifold_step,
    export_mooring_spread_step,
    manifold_n_trees,
    mooring_line_count,
    mooring_total_length_m,
)
from worldenergydata.field_development.equipment_3d import (  # noqa: E402
    build_multibend_jumper,
    export_multibend_jumper_step,
    multibend_jumper_bends,
    multibend_jumper_length_mm,
    multibend_jumper_volume_mm3,
)

_IN = 25.4
_M_TO_MM = 1000.0

# An L-bend (1 bend) and a U-spool (2 bends), waypoints in metres.
_L_BEND = [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (10.0, 0.0, 10.0)]
_U_SPOOL = [(0.0, 0.0, 0.0), (0.0, 0.0, -5.0), (20.0, 0.0, -5.0), (20.0, 0.0, 0.0)]


# --------------------------------------------------------------------------- #
# Multi-bend jumper
# --------------------------------------------------------------------------- #
def test_multibend_jumper_valid_and_bend_count():
    """L-bend and U-spool build valid hollow solids with the right bend counts."""
    for wp, n_bends in ((_L_BEND, 1), (_U_SPOOL, 2)):
        solid = build_multibend_jumper(wp, od_in=8.625, wall_in=0.5).val()
        assert solid.isValid()
        assert solid.Volume() > 0
        assert multibend_jumper_bends(wp) == n_bends


def test_multibend_jumper_length_and_hollow_volume():
    """Path length is the polyline length; volume ~= annulus area * length."""
    wp = _L_BEND
    expected_len = 20.0 * _M_TO_MM  # 10 m + 10 m
    assert math.isclose(multibend_jumper_length_mm(wp), expected_len, rel_tol=1e-9)

    od, wall = 8.625 * _IN, 0.5 * _IN
    bore = od - 2 * wall
    annulus = math.pi * ((od / 2) ** 2 - (bore / 2) ** 2)
    vol = multibend_jumper_volume_mm3(wp, od_in=8.625, wall_in=0.5)
    # ~5% tolerance: mitred corners differ slightly from area*length.
    assert math.isclose(vol, annulus * expected_len, rel_tol=0.05)

    # A hollow tube has less volume than the equivalent solid sweep.
    solid_sweep = math.pi * (od / 2) ** 2 * expected_len
    assert vol < solid_sweep


def test_multibend_jumper_requires_two_waypoints():
    with pytest.raises(ValueError):
        build_multibend_jumper([(0.0, 0.0, 0.0)], od_in=8.0, wall_in=0.5)


def test_multibend_jumper_wall_too_thick_raises():
    with pytest.raises(ValueError):
        build_multibend_jumper(_L_BEND, od_in=6.0, wall_in=3.5)  # bore <= 0


def test_multibend_jumper_step_export(tmp_path: Path):
    out = export_multibend_jumper_step(
        _U_SPOOL, tmp_path / "spool.step", od_in=8.625, wall_in=0.5
    )
    assert out.exists() and out.stat().st_size > 0
    assert "ISO-10303" in out.read_text(encoding="utf-8", errors="ignore")[:200]


# --------------------------------------------------------------------------- #
# Mooring spread
# --------------------------------------------------------------------------- #
def test_mooring_spread_line_count_and_extent():
    assy = build_mooring_spread(
        n_lines=8,
        radius_m=40.0,
        fairlead_z_m=-20.0,
        anchor_radius_m=1500.0,
        depth_m=2000.0,
    )
    assert mooring_line_count(assy) == 8
    bb = assy.toCompound().BoundingBox()
    # Anchors sit on a ~1500 m radius circle -> ~3000 m span across (in mm).
    assert bb.xlen > 2.9e6
    # Vertical extent spans fairlead (-20 m) down to seabed (-2000 m).
    assert bb.zlen > 1.9e6


def test_mooring_total_length_matches_geometry():
    total = mooring_total_length_m(
        n_lines=4,
        radius_m=40.0,
        fairlead_z_m=-20.0,
        anchor_radius_m=1500.0,
        depth_m=2000.0,
    )
    horiz = 1500.0 - 40.0
    vert = 2000.0 - 20.0
    per_line = math.hypot(horiz, vert)
    assert math.isclose(total, 4 * per_line, rel_tol=1e-9)


def test_mooring_invalid_line_count_raises():
    with pytest.raises(ValueError):
        build_mooring_spread(
            n_lines=0,
            radius_m=40.0,
            fairlead_z_m=-20.0,
            anchor_radius_m=1500.0,
            depth_m=2000.0,
        )


def test_mooring_step_export(tmp_path: Path):
    assy = build_mooring_spread(
        n_lines=6,
        radius_m=40.0,
        fairlead_z_m=-20.0,
        anchor_radius_m=1200.0,
        depth_m=1500.0,
    )
    out = export_mooring_spread_step(assy, tmp_path / "mooring.step")
    assert out.exists() and out.stat().st_size > 0
    assert "ISO-10303" in out.read_text(encoding="utf-8", errors="ignore")[:200]


# --------------------------------------------------------------------------- #
# Manifold + trees assembly
# --------------------------------------------------------------------------- #
def test_manifold_assembly_tree_count_and_validity():
    assy = build_manifold_assembly(n_slots=4, spacing_m=3.0, tree_height_m=4.0)
    assert manifold_n_trees(assy) == 4
    assert assy.toCompound().isValid()
    assert assy.toCompound().Volume() > 0


def test_manifold_invalid_slot_count_raises():
    with pytest.raises(ValueError):
        build_manifold_assembly(n_slots=0, spacing_m=3.0)


def test_manifold_step_export(tmp_path: Path):
    assy = build_manifold_assembly(n_slots=6, spacing_m=2.5)
    out = export_manifold_step(assy, tmp_path / "manifold.step")
    assert out.exists() and out.stat().st_size > 0
    assert "ISO-10303" in out.read_text(encoding="utf-8", errors="ignore")[:200]
