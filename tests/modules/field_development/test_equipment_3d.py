# ABOUTME: Tests for parametric 3D equipment generation via CadQuery (issue #580).
# ABOUTME: Skips cleanly if CadQuery/OCCT is unavailable in the environment.
"""Tests for ``worldenergydata.field_development.equipment_3d``."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

# Skip the whole module (incl. the cadquery-importing module under test) if the
# OCCT stack isn't installed, rather than erroring at collection.
pytest.importorskip("cadquery")

from worldenergydata.field_development.equipment_3d import (  # noqa: E402
    _curated_jumper_csv,
    build_jumper_from_catalog,
    build_jumper_solid,
    export_jumper_step,
    jumper_volume_mm3,
)
from worldenergydata.subsea.models.rigid_jumper import (  # noqa: E402
    RigidJumperSpec,
    load_rigid_jumpers,
)

_IN = 25.4
_FT = 304.8


def _spec(od_in=8.0, wall_in=0.5, length_ft=50.0):
    return RigidJumperSpec(
        component_id="RJ-TEST",
        manufacturer="Test",
        od_in=od_in,
        wall_thickness_in=wall_in,
        length_ft=length_ft,
        material_grade="X-65",
        pressure_rating_psi=10000.0,
        data_source="unit-test",
    )


# --------------------------------------------------------------------------- #
def test_builds_a_valid_solid():
    solid = build_jumper_solid(_spec()).val()
    assert solid.isValid()
    assert solid.Volume() > 0


def test_volume_matches_hollow_pipe_formula():
    spec = _spec(od_in=8.0, wall_in=0.5, length_ft=50.0)
    od, wall, length = (
        spec.od_in * _IN,
        spec.wall_thickness_in * _IN,
        spec.length_ft * _FT,
    )
    bore = od - 2 * wall
    expected = math.pi * ((od / 2) ** 2 - (bore / 2) ** 2) * length
    assert math.isclose(jumper_volume_mm3(spec), expected, rel_tol=1e-3)


def test_is_hollow_less_than_solid_cylinder():
    spec = _spec()
    od, length = spec.od_in * _IN, spec.length_ft * _FT
    solid_cyl = math.pi * (od / 2) ** 2 * length
    assert jumper_volume_mm3(spec) < solid_cyl


def test_wall_too_thick_raises():
    with pytest.raises(ValueError):
        build_jumper_solid(_spec(od_in=6.0, wall_in=3.0))  # bore <= 0


def test_export_writes_step_file(tmp_path: Path):
    out = export_jumper_step(_spec(), tmp_path / "jumper.step")
    assert out.exists() and out.stat().st_size > 0
    head = out.read_text(encoding="utf-8", errors="ignore")[:200]
    assert "ISO-10303" in head  # STEP file header


# --------------------------------------------------------------------------- #
# Catalog-driven build
# --------------------------------------------------------------------------- #
def test_build_from_catalog():
    specs = load_rigid_jumpers(_curated_jumper_csv())
    assert specs, "expected curated rigid jumpers"
    cid = specs[0].component_id
    solid = build_jumper_from_catalog(cid).val()
    assert solid.isValid() and solid.Volume() > 0


def test_unknown_component_raises_keyerror():
    with pytest.raises(KeyError):
        build_jumper_from_catalog("RJ-DOES-NOT-EXIST")
