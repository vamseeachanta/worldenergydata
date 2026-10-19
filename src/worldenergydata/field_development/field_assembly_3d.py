# ABOUTME: Named full-field CadQuery scenes from optimized planar layouts.
# ABOUTME: Optional CAD sibling; no equipment design dimensions are assumed.
"""Compose conceptual equipment envelopes and route solids in a named assembly.

Import explicitly with the ``cad`` extra installed; this module is deliberately
absent from package ``__init__`` exports. Plan coordinates use the optimizer's
kilometres in a consistent local Cartesian frame. Elevations, dimensions and
umbilical landing offsets are caller-supplied metres. STEP geometry is in mm.

Trees are vertical cylinders, manifolds and the host are boxes. Routes are solid
circular sweeps with sharp mitred turns: a straight leg at ``seabed_z_m`` then a
vertical riser to ``host_z_m``. These are visualization envelopes, not designed
pipes. Bathymetry, bend radius, wall thickness, clearance, stress, hydraulics and
installation feasibility are NOT_EVALUATED. The caller must choose landing
offsets; overlapping envelopes are permitted and are not collision checked.

Geometry API reference: CadQuery 2.8, class reference, Solid.makeCylinder,
Solid.makeBox, Workplane.sweep and exportAssembly:
https://cadquery.readthedocs.io/en/latest/classreference.html
Elementary geometry (half-side placement, radius = diameter / 2): OpenStax,
Prealgebra 2e (2020), section 9.6, rectangular solids and cylinders.
https://openstax.org/books/prealgebra-2e/pages/9-6-solve-geometry-applications-volume-and-surface-area
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import cadquery as cq
from cadquery.occ_impl.exporters.assembly import exportAssembly

from worldenergydata.field_development.layout_optimization import LayoutSolution, Well

# NIST, Metric (SI) Prefixes (2025), table: kilo=10**3, milli=10**-3.
# https://www.nist.gov/pml/owm/metric-si-prefixes
_KM_TO_M = 1000.0
_M_TO_MM = 1000.0

Point = tuple[float, float, float]


@dataclass(frozen=True)
class FieldDimensions:
    """Required visualization dimensions in metres; box sizes are (X, Y, Z)."""

    tree_diameter_m: float
    tree_height_m: float
    manifold_size_m: tuple[float, float, float]
    host_size_m: tuple[float, float, float]
    flowline_diameter_m: float
    umbilical_diameter_m: float


def _finite(value: float, name: str, *, positive: bool = False) -> None:
    # Zero is the geometric degeneracy boundary, not an engineering limit.
    if not math.isfinite(value) or (positive and value <= 0):
        raise ValueError(
            f"{name} must be finite" + (" and positive" if positive else "")
        )


def _coordinates(values: Sequence[float], size: int, name: str) -> None:
    if len(values) != size:
        raise ValueError(f"{name} must contain {size} coordinates")
    for value in values:
        _finite(value, name)


def _validate(
    layout: LayoutSolution,
    wells: Sequence[Well],
    dimensions: FieldDimensions,
    seabed_z_m: float,
    host_z_m: float,
    offset: tuple[float, float],
) -> None:
    for name in (
        "tree_diameter_m",
        "tree_height_m",
        "flowline_diameter_m",
        "umbilical_diameter_m",
    ):
        _finite(getattr(dimensions, name), name, positive=True)
    for name in ("manifold_size_m", "host_size_m"):
        sizes = getattr(dimensions, name)
        _coordinates(sizes, 3, name)
        for value in sizes:
            _finite(value, name, positive=True)
    _finite(seabed_z_m, "seabed_z_m")
    _finite(host_z_m, "host_z_m")
    if host_z_m <= seabed_z_m:
        raise ValueError("host_z_m must be above seabed_z_m")
    _coordinates(offset, 2, "umbilical_offset_m")
    ids = [well.id for well in wells]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("wells must be nonempty with unique IDs")
    if not layout.manifolds or layout.n_manifolds != len(layout.manifolds):
        raise ValueError("n_manifolds must match the nonempty manifold mapping")
    if set(layout.assignment) != set(ids):
        raise ValueError("assignment must contain exactly the supplied well IDs")
    if not set(layout.assignment.values()) <= set(layout.manifolds):
        raise ValueError("assignment refers to an unknown manifold")
    _coordinates(layout.host, 2, "host")
    for position in layout.manifolds.values():
        _coordinates(position, 2, "manifold")
    for well in wells:
        _coordinates((well.x, well.y), 2, "well")


def _vector(point_m: Point) -> cq.Vector:
    return cq.Vector(*(value * _M_TO_MM for value in point_m))


def _box(size_m: Point, base_m: Point) -> cq.Solid:
    x, y, z = (value * _M_TO_MM for value in size_m)
    base = _vector(base_m)
    # Box centre in X/Y: half each side; base elevation is unchanged.
    return cq.Solid.makeBox(x, y, z, base - cq.Vector(x / 2, y / 2, 0))


def _waypoints(
    manifold: tuple[float, float],
    host: tuple[float, float],
    seabed_z_m: float,
    host_z_m: float,
    offset: tuple[float, float],
) -> tuple[Point, ...]:
    mx, my = (coordinate * _KM_TO_M for coordinate in manifold)
    hx, hy = (coordinate * _KM_TO_M for coordinate in host)
    dx, dy = offset
    points = (
        (mx + dx, my + dy, seabed_z_m),
        (hx + dx, hy + dy, seabed_z_m),
        (hx + dx, hy + dy, host_z_m),
    )
    # Exact coincident plan endpoints are valid (a vertical-only tieback).
    return tuple(
        point for i, point in enumerate(points) if i == 0 or point != points[i - 1]
    )


def _route(points_m: tuple[Point, ...], diameter_m: float) -> cq.Shape:
    points = [_vector(point) for point in points_m]
    # Build near the origin: sweeping a small profile at field-scale absolute
    # coordinates can produce an invalid OCCT corner. Translate the result.
    origin = points[0]
    local = [point - origin for point in points]
    path = cq.Wire.makePolygon(local)
    plane = cq.Plane(origin=local[0], normal=local[1] - local[0])
    # Radius = diameter / 2 by circle definition; no bend-radius assumption.
    return (
        cq.Workplane(plane)
        .circle(diameter_m * _M_TO_MM / 2)
        .sweep(cq.Workplane(obj=path), isFrenet=True, transition="right")
        .val()
        .translate(origin)
    )


def build_field_assembly(
    layout_solution: LayoutSolution,
    wells: Sequence[Well],
    *,
    dimensions: FieldDimensions,
    seabed_z_m: float,
    host_z_m: float,
    umbilical_offset_m: tuple[float, float],
) -> cq.Assembly:
    """Build a named field scene without recomputing or mutating the layout.

    ``wells`` must be the original wells used by ``optimize_layout``; the layout
    stores assignments but does not retain their coordinates. Trees are placed
    at those wells and manifolds at the solution coordinates. Group names are
    ``trees``, ``manifolds``, ``flowlines`` and ``umbilicals``, plus ``host``.
    Each manifold has one flowline and one umbilical, including its riser.
    Umbilical endpoints are translated by ``umbilical_offset_m`` in plan metres
    relative to the manifold and host centres. Zero offset is permitted.

    Child names use sorted-ID indices; original IDs and route waypoints are in
    child metadata. Equipment bases sit at the specified elevations; route
    *centrelines* sit at the seabed elevation. All dimensions are required.
    Invalid dimensions, nonfinite coordinates and inconsistent assignments raise
    ValueError before CAD construction. An empty field is rejected.
    """
    layout = layout_solution
    _validate(layout, wells, dimensions, seabed_z_m, host_z_m, umbilical_offset_m)
    scene = cq.Assembly(name="field")
    trees = cq.Assembly(name="trees")
    for i, well in enumerate(sorted(wells, key=lambda well: well.id)):
        tree = cq.Solid.makeCylinder(
            dimensions.tree_diameter_m * _M_TO_MM / 2,
            dimensions.tree_height_m * _M_TO_MM,
            _vector((well.x * _KM_TO_M, well.y * _KM_TO_M, seabed_z_m)),
        )
        trees.add(tree, name=f"tree_{i}", metadata={"well_id": well.id})
    scene.add(trees)
    manifolds = cq.Assembly(name="manifolds")
    flowlines = cq.Assembly(name="flowlines")
    umbilicals = cq.Assembly(name="umbilicals")
    for i, (mid, position) in enumerate(sorted(layout.manifolds.items())):
        base = (position[0] * _KM_TO_M, position[1] * _KM_TO_M, seabed_z_m)
        manifolds.add(
            _box(dimensions.manifold_size_m, base),
            name=f"manifold_{i}",
            metadata={"manifold_id": mid},
        )
        for group, prefix, diameter, offset in (
            (flowlines, "flowline", dimensions.flowline_diameter_m, (0, 0)),
            (
                umbilicals,
                "umbilical",
                dimensions.umbilical_diameter_m,
                umbilical_offset_m,
            ),
        ):
            points = _waypoints(position, layout.host, seabed_z_m, host_z_m, offset)
            group.add(
                _route(points, diameter),
                name=f"{prefix}_{i}",
                metadata={"manifold_id": mid, "waypoints_m": points},
            )
    scene.add(manifolds)
    scene.add(
        _box(
            dimensions.host_size_m,
            (layout.host[0] * _KM_TO_M, layout.host[1] * _KM_TO_M, host_z_m),
        ),
        name="host",
    )
    scene.add(flowlines)
    scene.add(umbilicals)
    return scene


def export_field_step(assembly: cq.Assembly, path: str | Path) -> Path:
    """Export the named hierarchy using the nondeprecated STEP assembly writer."""
    output = Path(path)
    exportAssembly(assembly, str(output))
    return output
