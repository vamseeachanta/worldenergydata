# ABOUTME: Tests for the plan-view field-layout renderer (issue #573).
# ABOUTME: Verifies to-scale geometry, determinism, and SVG structure.
"""Tests for ``worldenergydata.field_development.layout``."""

from __future__ import annotations

import math

from worldenergydata.field_development import (
    ConceptType,
    FieldConcept,
    compute_pixel_positions,
    compute_positions,
    render_layout,
)
from worldenergydata.field_development.layout import DEFAULT_SCALE_PX_PER_KM


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


# --------------------------------------------------------------------------- #
# To-scale geometry (the defining property of the plan view)
# --------------------------------------------------------------------------- #
def test_host_to_manifold_pixel_distance_equals_tieback_times_scale():
    scale = 50.0
    c = FieldConcept(
        name="Mensa",
        concept_type=ConceptType.SUBSEA_TIEBACK,
        tieback_distance_km=12.0,
        num_wells=3,
        num_manifolds=1,
    )
    px = compute_pixel_positions(c, scale_px_per_km=scale)
    measured = _dist(px["host"], px["mf-1"])
    assert measured == 12.0 * scale


def test_standalone_host_uses_default_offset_not_zero():
    c = FieldConcept(name="Stand", concept_type=ConceptType.FPSO, num_wells=2)
    pos = compute_positions(c)
    # No tieback distance -> host is offset north by the default, not on top of field.
    assert pos["host"].y_km > 0


def test_trees_lie_on_ring_around_their_manifold():
    c = FieldConcept(
        name="X", concept_type=ConceptType.FPSO, num_wells=4, num_manifolds=1
    )
    pos = compute_positions(c)
    mf = pos["mf-1"]
    for tid in [f"tree-{i}" for i in range(1, 5)]:
        r = math.hypot(pos[tid].x_km - mf.x_km, pos[tid].y_km - mf.y_km)
        assert math.isclose(r, 0.5, rel_tol=1e-9)  # TREE_RING_RADIUS_KM


def test_dry_tree_wellheads_ring_around_host():
    c = FieldConcept(name="Perdido", concept_type=ConceptType.SPAR, num_wells=3)
    pos = compute_positions(c)
    host = pos["host"]
    for tid in [f"tree-{i}" for i in range(1, 4)]:
        r = math.hypot(pos[tid].x_km - host.x_km, pos[tid].y_km - host.y_km)
        assert math.isclose(r, 0.5, rel_tol=1e-9)


# --------------------------------------------------------------------------- #
# SVG structure
# --------------------------------------------------------------------------- #
def test_render_returns_svg_with_north_arrow_and_scale_bar():
    svg = render_layout(
        FieldConcept(name="X", concept_type=ConceptType.FPSO, num_wells=2)
    )
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    assert ">N<" in svg  # north arrow label
    assert "1 km" in svg  # scale bar label


def test_render_includes_field_name_escaped():
    svg = render_layout(
        FieldConcept(name="A & B <field>", concept_type=ConceptType.FPSO, num_wells=1)
    )
    assert "A &amp; B &lt;field&gt;" in svg
    assert "<field>" not in svg.split("<title>")[1].split("</title>")[0]


def test_render_draws_a_line_per_edge_referencing_known_nodes():
    c = FieldConcept(
        name="X",
        concept_type=ConceptType.SUBSEA_TIEBACK,
        tieback_distance_km=20.0,
        num_wells=3,
        num_manifolds=1,
    )
    svg = render_layout(c)
    assert svg.count("<line") >= 3  # at least the production/control/export lines


def test_deterministic_same_concept_same_svg():
    c = FieldConcept(
        name="X",
        concept_type=ConceptType.SEMISUB_FPS,
        num_wells=5,
        num_manifolds=2,
        tieback_distance_km=0.0,
    )
    assert render_layout(c) == render_layout(c)


def test_default_scale_constant_used_when_unspecified():
    c = FieldConcept(
        name="X",
        concept_type=ConceptType.SUBSEA_TIEBACK,
        tieback_distance_km=10.0,
        num_wells=1,
        num_manifolds=1,
    )
    px = compute_pixel_positions(c)  # default scale
    assert _dist(px["host"], px["mf-1"]) == 10.0 * DEFAULT_SCALE_PX_PER_KM
