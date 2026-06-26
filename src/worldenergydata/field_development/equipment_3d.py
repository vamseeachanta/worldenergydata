# ABOUTME: Parametric 3D (STEP/B-rep) of subsea catalog hardware via CadQuery.
# ABOUTME: Issue #580 (epic #567) — separate track from the 2D schematic pipeline.
"""
worldenergydata.field_development.equipment_3d
==============================================

Generates parametric **3D solid models** (STEP / B-rep) of subsea equipment from
the curated hardware catalogs — a *separate track* from the 2D schematic pipeline
(it produces geometry of individual components, not field diagrams).

This module **requires CadQuery** (OCCT-based B-rep kernel, Apache-2.0). It is
deliberately **not** re-exported from :mod:`worldenergydata.field_development`'s
package ``__init__`` — so ``import field_development`` and the entire 2D pipeline
keep working in a minimal environment without the heavy OCCT stack. Import this
module explicitly (``from worldenergydata.field_development.equipment_3d import
build_jumper_solid``) when you want 3D.

v1 builds a straight hollow pipe segment dimensioned from a rigid-jumper catalog
spec (OD, wall thickness, length); multi-bend M/U spool geometry is a follow-on.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import cadquery as cq

from worldenergydata.subsea.models.rigid_jumper import (
    RigidJumperSpec,
    load_rigid_jumpers,
)

_IN_TO_MM = 25.4
_FT_TO_MM = 304.8


def _curated_jumper_csv() -> Path:
    return (
        Path(__file__).parents[3]
        / "data"
        / "modules"
        / "subsea"
        / "curated"
        / "rigid_jumper_specs.csv"
    )


def build_jumper_solid(spec: RigidJumperSpec) -> cq.Workplane:
    """Build a parametric 3D solid (hollow pipe) for a rigid-jumper spec.

    Dimensions come straight from the catalog (inches/feet → mm): outer diameter
    ``od_in``, bore = OD − 2·``wall_thickness_in``, length ``length_ft``.

    Args:
        spec: A :class:`RigidJumperSpec` from the curated catalog.

    Returns:
        A CadQuery ``Workplane`` containing the solid (export with
        :func:`export_jumper_step`).
    """
    od = spec.od_in * _IN_TO_MM
    wall = spec.wall_thickness_in * _IN_TO_MM
    length = spec.length_ft * _FT_TO_MM
    bore = od - 2 * wall
    if bore <= 0:
        raise ValueError(
            f"{spec.component_id}: wall thickness {spec.wall_thickness_in} in "
            f">= radius for OD {spec.od_in} in"
        )
    # Annulus (OD outer circle, bore inner circle) extruded into a hollow tube.
    return cq.Workplane("XY").circle(od / 2.0).circle(bore / 2.0).extrude(length)


def export_jumper_step(spec: RigidJumperSpec, path: str | Path) -> Path:
    """Build and export a rigid jumper to a STEP file. Returns the path."""
    solid = build_jumper_solid(spec)
    out = Path(path)
    cq.exporters.export(solid, str(out))
    return out


def build_jumper_from_catalog(
    component_id: str, csv_path: Optional[Path] = None
) -> cq.Workplane:
    """Build the 3D solid for a catalog jumper by its ``component_id``.

    Args:
        component_id: e.g. ``"RJ-06-CAM-10K"``.
        csv_path: Override for the curated catalog CSV.

    Returns:
        A CadQuery ``Workplane``.

    Raises:
        KeyError: if no catalog entry matches ``component_id``.
    """
    specs = load_rigid_jumpers(csv_path or _curated_jumper_csv())
    for s in specs:
        if s.component_id == component_id:
            return build_jumper_solid(s)
    raise KeyError(f"no rigid jumper with component_id {component_id!r} in catalog")


def jumper_volume_mm3(spec: RigidJumperSpec) -> float:
    """Solid volume (mm³) of a jumper — handy for steel-weight cross-checks."""
    return float(build_jumper_solid(spec).val().Volume())
