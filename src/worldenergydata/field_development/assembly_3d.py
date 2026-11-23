# ABOUTME: Parametric 3D (STEP/B-rep) subsea ASSEMBLIES via CadQuery (issue #580).
# ABOUTME: Mooring spreads + manifold/tree skids — companion to equipment_3d.py.
"""
worldenergydata.field_development.assembly_3d
=============================================

Parametric **3D assemblies** (STEP / B-rep) of field-scale subsea hardware via
CadQuery — a companion to :mod:`worldenergydata.field_development.equipment_3d`
(which builds individual jumper components). Two builders live here:

* :func:`build_mooring_spread` — N mooring lines radiating evenly from a host's
  fairlead circle down to seabed anchors.
* :func:`build_manifold_assembly` — a manifold skid box with N vertical tree
  stubs on a row.

Like ``equipment_3d``, this module **requires CadQuery** (OCCT) and is
deliberately **not** re-exported from the package ``__init__`` so the 2D
pipeline keeps importing without the heavy OCCT stack. Import it explicitly.

Builders return :class:`cadquery.Assembly` objects (each part is a named child),
which export to a multi-part STEP. Lengths/positions are supplied in **metres**
and converted to **mm** internally (STEP convention), consistent with v1.
"""

from __future__ import annotations

import math
from pathlib import Path

import cadquery as cq
from cadquery import Solid, Vector
from cadquery.occ_impl.exporters.assembly import exportAssembly

_M_TO_MM = 1000.0


def _save_assembly_step(assy: cq.Assembly, path: str | Path) -> Path:
    """Export an assembly to a multi-part STEP file and return the path.

    Uses :func:`exportAssembly` (the non-deprecated STEP assembly writer) so the
    named ``skid``/``tree_<i>``/``line_<i>`` parts survive into the STEP product
    hierarchy.
    """
    out = Path(path)
    exportAssembly(assy, str(out))
    return out


# --------------------------------------------------------------------------- #
# Mooring spread
# --------------------------------------------------------------------------- #
def mooring_total_length_m(
    n_lines: int,
    radius_m: float,
    fairlead_z_m: float,
    anchor_radius_m: float,
    depth_m: float,
) -> float:
    """Total straight-line length (m) of all mooring lines combined.

    Each line runs from a fairlead at ``(radius_m, z=fairlead_z_m)`` to an anchor
    at ``(anchor_radius_m, z=-depth_m)``; the per-line length is the 2D hypot of
    the radial offset and the vertical drop (catenary sag is not modelled).
    """
    horiz = anchor_radius_m - radius_m
    vert = fairlead_z_m - (-depth_m)
    return float(n_lines * math.hypot(horiz, vert))


def build_mooring_spread(
    n_lines: int,
    radius_m: float,
    fairlead_z_m: float,
    anchor_radius_m: float,
    depth_m: float,
    line_diameter_m: float = 0.2,
) -> cq.Assembly:
    """Build a mooring spread: N lines radiating evenly from fairleads to anchors.

    Lines are equally spaced in azimuth (``360 / n_lines`` degrees). Each is a
    thin solid cylinder from its fairlead point on the host's fairlead circle
    (radius ``radius_m``, elevation ``fairlead_z_m``) down to its seabed anchor
    (radius ``anchor_radius_m``, elevation ``-depth_m``).

    Args:
        n_lines: Number of mooring lines (≥1).
        radius_m: Fairlead circle radius (m).
        fairlead_z_m: Fairlead elevation (m; negative = below waterline).
        anchor_radius_m: Anchor circle radius (m).
        depth_m: Water depth (m); anchors sit at ``z = -depth_m``.
        line_diameter_m: Rendered line diameter (m) for the solid cylinder.

    Returns:
        A :class:`cadquery.Assembly` with one named ``line_<i>`` child per line.

    Raises:
        ValueError: if ``n_lines < 1``.
    """
    if n_lines < 1:
        raise ValueError(f"n_lines must be >= 1 (got {n_lines})")

    r_line_mm = (line_diameter_m / 2.0) * _M_TO_MM
    assy = cq.Assembly(name="mooring_spread")
    for i in range(n_lines):
        az = math.radians(360.0 / n_lines * i)
        fair = Vector(
            radius_m * math.cos(az) * _M_TO_MM,
            radius_m * math.sin(az) * _M_TO_MM,
            fairlead_z_m * _M_TO_MM,
        )
        anchor = Vector(
            anchor_radius_m * math.cos(az) * _M_TO_MM,
            anchor_radius_m * math.sin(az) * _M_TO_MM,
            -depth_m * _M_TO_MM,
        )
        span = anchor - fair
        height = span.Length
        direction = span.normalized()
        cyl = Solid.makeCylinder(r_line_mm, height, fair, direction)
        assy.add(cyl, name=f"line_{i}")
    return assy


def mooring_line_count(assy: cq.Assembly) -> int:
    """Number of mooring-line children in a spread assembly."""
    return sum(1 for c in assy.children if c.name and c.name.startswith("line_"))


def export_mooring_spread_step(assy: cq.Assembly, path: str | Path) -> Path:
    """Export a mooring-spread assembly to a STEP file. Returns the path."""
    return _save_assembly_step(assy, path)


# --------------------------------------------------------------------------- #
# Manifold + trees assembly
# --------------------------------------------------------------------------- #
def build_manifold_assembly(
    n_slots: int,
    spacing_m: float,
    tree_height_m: float = 3.0,
    skid_width_m: float = 4.0,
    skid_height_m: float = 2.0,
    tree_diameter_m: float = 0.8,
) -> cq.Assembly:
    """Build a manifold skid box with N vertical tree stubs on a row.

    The skid is a box of length ``n_slots * spacing_m`` (+ one spacing margin),
    width ``skid_width_m`` and height ``skid_height_m``, centred on the origin
    with its base at ``z = 0``. ``n_slots`` tree stubs (vertical cylinders of
    height ``tree_height_m``) sit on top, evenly spaced along the skid length.

    Args:
        n_slots: Number of tree slots / stubs (≥1).
        spacing_m: Centre-to-centre slot spacing (m).
        tree_height_m: Height of each tree stub (m).
        skid_width_m: Skid box width (m).
        skid_height_m: Skid box height (m).
        tree_diameter_m: Tree stub diameter (m).

    Returns:
        A :class:`cadquery.Assembly`: a ``skid`` child plus one ``tree_<i>``
        child per slot.

    Raises:
        ValueError: if ``n_slots < 1``.
    """
    if n_slots < 1:
        raise ValueError(f"n_slots must be >= 1 (got {n_slots})")

    length_mm = (n_slots * spacing_m + spacing_m) * _M_TO_MM
    width_mm = skid_width_m * _M_TO_MM
    height_mm = skid_height_m * _M_TO_MM
    r_tree_mm = (tree_diameter_m / 2.0) * _M_TO_MM
    tree_h_mm = tree_height_m * _M_TO_MM

    assy = cq.Assembly(name="manifold")
    # Skid box centred in X/Y, base on z = 0.
    box = Solid.makeBox(
        length_mm, width_mm, height_mm, Vector(-length_mm / 2.0, -width_mm / 2.0, 0.0)
    )
    assy.add(box, name="skid")

    # Evenly spaced tree stubs along the skid length, centred about x = 0.
    span_mm = (n_slots - 1) * spacing_m * _M_TO_MM
    x0 = -span_mm / 2.0
    for i in range(n_slots):
        x = x0 + i * spacing_m * _M_TO_MM
        base = Vector(x, 0.0, height_mm)
        tree = Solid.makeCylinder(r_tree_mm, tree_h_mm, base, Vector(0.0, 0.0, 1.0))
        assy.add(tree, name=f"tree_{i}")
    return assy


def manifold_n_trees(assy: cq.Assembly) -> int:
    """Number of tree-stub children in a manifold assembly."""
    return sum(1 for c in assy.children if c.name and c.name.startswith("tree_"))


def export_manifold_step(assy: cq.Assembly, path: str | Path) -> Path:
    """Export a manifold assembly to a STEP file. Returns the path."""
    return _save_assembly_step(assy, path)
