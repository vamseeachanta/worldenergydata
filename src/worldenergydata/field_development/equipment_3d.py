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
from typing import Optional, Sequence, Tuple

import cadquery as cq
from cadquery import Edge, Vector, Wire

from worldenergydata.subsea.models.rigid_jumper import (
    RigidJumperSpec,
    load_rigid_jumpers,
)

_IN_TO_MM = 25.4
_FT_TO_MM = 304.8
_M_TO_MM = 1000.0

Waypoint = Tuple[float, float, float]


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


# --------------------------------------------------------------------------- #
# Multi-bend (M/U-spool) jumper — hollow pipe swept along a 3D polyline
# --------------------------------------------------------------------------- #
def _waypoints_mm(waypoints: Sequence[Waypoint]) -> list[Vector]:
    """Validate ≥2 waypoints and convert (x, y, z) metres → mm vectors."""
    if waypoints is None or len(waypoints) < 2:
        raise ValueError(
            "build_multibend_jumper needs at least 2 waypoints (got "
            f"{0 if waypoints is None else len(waypoints)})"
        )
    return [
        Vector(p[0] * _M_TO_MM, p[1] * _M_TO_MM, p[2] * _M_TO_MM) for p in waypoints
    ]


def multibend_jumper_bends(waypoints: Sequence[Waypoint]) -> int:
    """Number of bends = interior vertices of the polyline (``len - 2``)."""
    if waypoints is None or len(waypoints) < 2:
        raise ValueError("need at least 2 waypoints to count bends")
    return len(waypoints) - 2


def multibend_jumper_length_mm(waypoints: Sequence[Waypoint]) -> float:
    """Total centreline length (mm) = sum of polyline segment lengths."""
    pts = _waypoints_mm(waypoints)
    return float(sum((pts[i + 1] - pts[i]).Length for i in range(len(pts) - 1)))


def build_multibend_jumper(
    waypoints: Sequence[Waypoint], od_in: float, wall_in: float
) -> cq.Workplane:
    """Build a hollow pipe swept along a 3D polyline (multi-bend M/U spool).

    The jumper centreline follows ``waypoints`` (``(x, y, z)`` in **metres**);
    a circular annulus (OD ``od_in``, bore = OD − 2·``wall_in``) is swept along
    the assembled wire, yielding a single hollow B-rep tube that turns through
    every interior vertex.

    Args:
        waypoints: ≥2 ``(x, y, z)`` points in metres.
        od_in: Outer diameter (inches).
        wall_in: Wall thickness (inches).

    Returns:
        A CadQuery ``Workplane`` holding the swept hollow solid.

    Raises:
        ValueError: if <2 waypoints, or the wall is ≥ the radius (bore ≤ 0).
    """
    pts = _waypoints_mm(waypoints)
    od = od_in * _IN_TO_MM
    bore = od - 2 * wall_in * _IN_TO_MM
    if bore <= 0:
        raise ValueError(
            f"wall thickness {wall_in} in >= radius for OD {od_in} in (bore <= 0)"
        )

    edges = [Edge.makeLine(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    path = Wire.assembleEdges(edges)

    start_dir = (pts[1] - pts[0]).normalized()
    plane = cq.Plane(
        origin=pts[0].toTuple(), normal=(start_dir.x, start_dir.y, start_dir.z)
    )
    profile = cq.Workplane(plane).circle(od / 2.0).circle(bore / 2.0)
    return profile.sweep(cq.Workplane(obj=path), isFrenet=True)


def multibend_jumper_volume_mm3(
    waypoints: Sequence[Waypoint], od_in: float, wall_in: float
) -> float:
    """Solid (steel) volume (mm³) of a swept multi-bend jumper."""
    return float(build_multibend_jumper(waypoints, od_in, wall_in).val().Volume())


def export_multibend_jumper_step(
    waypoints: Sequence[Waypoint],
    path: str | Path,
    od_in: float,
    wall_in: float,
) -> Path:
    """Build and export a multi-bend jumper to a STEP file. Returns the path."""
    solid = build_multibend_jumper(waypoints, od_in, wall_in)
    out = Path(path)
    cq.exporters.export(solid, str(out))
    return out
