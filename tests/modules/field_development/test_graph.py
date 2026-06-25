# ABOUTME: Tests for the concept -> graph-spec mapper (issue #571).
# ABOUTME: Verifies topology, connectivity, symbols, determinism, serialization.
"""Tests for ``worldenergydata.field_development.graph``."""

from __future__ import annotations

from worldenergydata.field_development import (
    ConceptType,
    EdgeKind,
    FieldConcept,
    NodeType,
    TreeType,
    concept_to_graph,
)
from worldenergydata.field_development.enums import Topology


def _nodes_of(g, ntype):
    return [n for n in g.nodes if n.type == ntype]


# --------------------------------------------------------------------------- #
# Wet-tree (subsea) topology
# --------------------------------------------------------------------------- #
def test_subsea_tieback_builds_host_manifold_trees():
    c = FieldConcept(
        name="Penguins",
        concept_type=ConceptType.SUBSEA_TIEBACK,
        tieback_distance_km=65.0,
        num_wells=4,
        num_manifolds=1,
    )
    g = concept_to_graph(c)
    assert len(_nodes_of(g, NodeType.HOST)) == 1
    assert len(_nodes_of(g, NodeType.MANIFOLD)) == 1
    assert len(_nodes_of(g, NodeType.TREE)) == 4


def test_every_tree_connects_to_a_manifold():
    c = FieldConcept(
        name="X", concept_type=ConceptType.SEMISUB_FPS, num_wells=6, num_manifolds=2
    )
    g = concept_to_graph(c)
    manifold_ids = {n.id for n in _nodes_of(g, NodeType.MANIFOLD)}
    for tree in _nodes_of(g, NodeType.TREE):
        prod_targets = {
            e.target
            for e in g.edges
            if e.source == tree.id and e.kind == EdgeKind.PRODUCTION
        }
        assert (
            len(prod_targets & manifold_ids) == 1
        ), f"{tree.id} must connect to exactly one manifold"


def test_trees_distributed_across_manifolds_round_robin():
    c = FieldConcept(
        name="X", concept_type=ConceptType.FPSO, num_wells=4, num_manifolds=2
    )
    g = concept_to_graph(c)
    # 4 trees over 2 manifolds -> each manifold receives 2 production edges in.
    for mf in _nodes_of(g, NodeType.MANIFOLD):
        incoming = [
            e for e in g.edges if e.target == mf.id and e.kind == EdgeKind.PRODUCTION
        ]
        assert len(incoming) == 2


def test_control_umbilicals_present_for_subsea():
    c = FieldConcept(
        name="X",
        concept_type=ConceptType.SUBSEA_TIEBACK,
        tieback_distance_km=20.0,
        num_wells=2,
    )
    g = concept_to_graph(c)
    assert any(e.kind == EdgeKind.CONTROL for e in g.edges)


def test_pigging_loop_labels_flowline_loop():
    c = FieldConcept(
        name="X",
        concept_type=ConceptType.SUBSEA_TIEBACK,
        tieback_distance_km=20.0,
        num_wells=2,
        topology=Topology.PIGGING_LOOP,
    )
    g = concept_to_graph(c)
    assert any("loop" in e.label for e in g.edges if e.kind == EdgeKind.PRODUCTION)


# --------------------------------------------------------------------------- #
# Dry-tree topology
# --------------------------------------------------------------------------- #
def test_dry_tree_spar_attaches_wellheads_to_host_no_manifold():
    c = FieldConcept(name="Perdido", concept_type=ConceptType.SPAR, num_wells=3)
    g = concept_to_graph(c)
    assert _nodes_of(g, NodeType.MANIFOLD) == []
    wellheads = _nodes_of(g, NodeType.WELLHEAD)
    assert len(wellheads) == 3
    for wh in wellheads:
        targets = {e.target for e in g.edges if e.source == wh.id}
        assert "host" in targets


def test_explicit_tree_type_overrides_concept_default():
    # A semisub (normally wet) explicitly declared dry -> wellheads, no manifold.
    c = FieldConcept(
        name="X",
        concept_type=ConceptType.SEMISUB_FPS,
        tree_type=TreeType.DRY,
        num_wells=2,
    )
    g = concept_to_graph(c)
    assert _nodes_of(g, NodeType.MANIFOLD) == []
    assert len(_nodes_of(g, NodeType.WELLHEAD)) == 2


# --------------------------------------------------------------------------- #
# Export sink + subsea-to-shore special case
# --------------------------------------------------------------------------- #
def test_export_node_present_by_default():
    g = concept_to_graph(
        FieldConcept(name="X", concept_type=ConceptType.FPSO, num_wells=1)
    )
    assert len(_nodes_of(g, NodeType.EXPORT)) == 1


def test_subsea_to_shore_uses_terminal_and_no_export_sink():
    g = concept_to_graph(
        FieldConcept(
            name="Snohvit", concept_type=ConceptType.SUBSEA_TO_SHORE, num_wells=2
        )
    )
    assert len(_nodes_of(g, NodeType.ONSHORE_TERMINAL)) == 1
    assert _nodes_of(g, NodeType.EXPORT) == []


# --------------------------------------------------------------------------- #
# Robustness, symbols, determinism, serialization
# --------------------------------------------------------------------------- #
def test_unknown_well_count_yields_single_tree():
    g = concept_to_graph(FieldConcept(name="X", concept_type=ConceptType.FPSO))
    assert len(_nodes_of(g, NodeType.TREE)) == 1


def test_every_node_has_a_symbol():
    g = concept_to_graph(
        FieldConcept(name="X", concept_type=ConceptType.SPAR, num_wells=2)
    )
    assert all(n.symbol for n in g.nodes)


def test_edges_reference_existing_nodes():
    g = concept_to_graph(
        FieldConcept(
            name="X", concept_type=ConceptType.FPSO, num_wells=3, num_manifolds=1
        )
    )
    ids = g.node_ids()
    for e in g.edges:
        assert e.source in ids and e.target in ids


def test_deterministic_same_concept_same_graph():
    c = FieldConcept(
        name="X", concept_type=ConceptType.SEMISUB_FPS, num_wells=5, num_manifolds=2
    )
    a = concept_to_graph(c).to_dict()
    b = concept_to_graph(c).to_dict()
    assert a == b


def test_to_dict_serializes_enums_to_strings():
    g = concept_to_graph(
        FieldConcept(name="X", concept_type=ConceptType.FPSO, num_wells=1)
    )
    d = g.to_dict()
    assert all(isinstance(n["type"], str) for n in d["nodes"])
    assert all(isinstance(e["kind"], str) for e in d["edges"])
    assert d["field_name"] == "X"
