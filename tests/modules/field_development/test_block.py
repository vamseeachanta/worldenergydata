# ABOUTME: Tests for the layered block-diagram renderer (issue #572).
# ABOUTME: Verifies layering order, edge styling, determinism, SVG structure.
"""Tests for ``worldenergydata.field_development.block``."""

from __future__ import annotations

import re

from worldenergydata.field_development import (
    ConceptType,
    FieldConcept,
    concept_to_graph,
    render_block_diagram,
)


def _box_y(svg: str, label: str) -> float:
    """Return the y of the <rect> immediately preceding the box's label text."""
    # Each box is "<rect ... y="Y" ...><text ...>LABEL</text>"
    m = re.search(
        r'<rect[^>]*\by="([\d.]+)"[^>]*/>'
        r'<text[^>]*>' + re.escape(label) + r'</text>',
        svg,
    )
    assert m, f"box for {label!r} not found"
    return float(m.group(1))


# --------------------------------------------------------------------------- #
# SVG structure
# --------------------------------------------------------------------------- #
def test_returns_well_formed_svg():
    svg = render_block_diagram(
        FieldConcept(name="X", concept_type=ConceptType.FPSO, num_wells=2)
    )
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")


def test_accepts_both_concept_and_graphspec():
    c = FieldConcept(name="X", concept_type=ConceptType.FPSO, num_wells=2)
    from_concept = render_block_diagram(c)
    from_graph = render_block_diagram(concept_to_graph(c))
    assert from_concept == from_graph


def test_box_per_node_with_labels():
    c = FieldConcept(name="X", concept_type=ConceptType.SUBSEA_TIEBACK,
                     tieback_distance_km=20.0, num_wells=3, num_manifolds=1)
    svg = render_block_diagram(c)
    for label in ("Manifold 1", "XT 1", "XT 2", "XT 3", "Export"):
        assert f">{label}</text>" in svg


# --------------------------------------------------------------------------- #
# Layering: export above host above manifold above trees
# --------------------------------------------------------------------------- #
def test_layer_order_top_to_bottom():
    c = FieldConcept(name="X", concept_type=ConceptType.SUBSEA_TIEBACK,
                     tieback_distance_km=20.0, num_wells=2, num_manifolds=1)
    svg = render_block_diagram(c)
    y_export = _box_y(svg, "Export")
    y_host = _box_y(svg, "Existing Host (tieback)")
    y_manifold = _box_y(svg, "Manifold 1")
    y_tree = _box_y(svg, "XT 1")
    assert y_export < y_host < y_manifold < y_tree


def test_dry_tree_has_no_manifold_and_wellheads_below_host():
    c = FieldConcept(name="Spar", concept_type=ConceptType.SPAR, num_wells=2)
    svg = render_block_diagram(c)
    assert "Manifold" not in svg
    y_host = _box_y(svg, "SPAR")
    y_well = _box_y(svg, "Well 1")
    assert y_host < y_well


# --------------------------------------------------------------------------- #
# Edge styling distinguishes kinds
# --------------------------------------------------------------------------- #
def test_control_edges_dashed_production_solid():
    c = FieldConcept(name="X", concept_type=ConceptType.SUBSEA_TIEBACK,
                     tieback_distance_km=20.0, num_wells=2, num_manifolds=1)
    svg = render_block_diagram(c)
    assert "stroke-dasharray" in svg            # control umbilicals dashed
    assert 'stroke="#3a8f5a"' in svg            # production solid green


def test_edges_use_arrowhead_marker():
    svg = render_block_diagram(
        FieldConcept(name="X", concept_type=ConceptType.FPSO, num_wells=1)
    )
    assert 'id="ah"' in svg and "marker-end" in svg


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
def test_deterministic():
    c = FieldConcept(name="X", concept_type=ConceptType.SEMISUB_FPS,
                     num_wells=5, num_manifolds=2)
    assert render_block_diagram(c) == render_block_diagram(c)
