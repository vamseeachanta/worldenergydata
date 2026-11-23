# ABOUTME: Tests for DEXPI-aligned export/import of the GraphSpec (issue #578).
# ABOUTME: Round-trip fidelity + DEXPI structural shape + subsea extension attrs.
"""Tests for ``worldenergydata.field_development.dexpi``."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from worldenergydata.field_development import (
    ConceptType,
    FieldConcept,
    concept_to_graph,
    dexpi_mapping,
    dexpi_to_graph,
    graph_to_dexpi,
)
from worldenergydata.field_development.graph import EdgeKind, NodeType


def _graph(concept=None):
    c = concept or FieldConcept(
        name="Mensa-like",
        concept_type=ConceptType.SUBSEA_TIEBACK,
        tieback_distance_km=20.0,
        num_wells=4,
        num_manifolds=2,
    )
    return concept_to_graph(c)


# --------------------------------------------------------------------------- #
# DEXPI structural shape
# --------------------------------------------------------------------------- #
def test_export_has_dexpi_structure():
    xml = graph_to_dexpi(_graph())
    root = ET.fromstring(xml)
    assert root.tag == "PlantModel"
    assert root.find("PlantInformation") is not None
    assert root.findall("Equipment"), "expected Equipment elements"
    assert root.find("PipingNetworkSystem") is not None
    assert root.findall("./PipingNetworkSystem/PipingNetworkSegment")


def test_equipment_carries_subsea_extension_attributes():
    xml = graph_to_dexpi(_graph())
    root = ET.fromstring(xml)
    tree = next(
        e for e in root.findall("Equipment") if e.get("ComponentClass") == "SubseaTree"
    )
    attrs = {
        a.get("Name"): a.get("Value")
        for a in tree.findall("./GenericAttributes/GenericAttribute")
    }
    assert attrs["FieldDevNodeType"] == "tree"
    assert attrs["FieldDevSymbol"] == "subsea_tree"


def test_mapping_covers_all_node_types():
    mapping = dexpi_mapping()
    # Every node type the graph mapper can emit must have a DEXPI component class.
    for nt in (
        NodeType.HOST,
        NodeType.MANIFOLD,
        NodeType.TREE,
        NodeType.WELLHEAD,
        NodeType.EXPORT,
        NodeType.ONSHORE_TERMINAL,
    ):
        assert nt.value in mapping


# --------------------------------------------------------------------------- #
# Round-trip fidelity (the lossless-interop property)
# --------------------------------------------------------------------------- #
def test_roundtrip_preserves_nodes_and_edges():
    g = _graph()
    back = dexpi_to_graph(graph_to_dexpi(g))
    assert back.field_name == g.field_name
    assert back.node_ids() == g.node_ids()
    # node type/label/symbol preserved
    orig = {n.id: (n.type, n.label, n.symbol) for n in g.nodes}
    for n in back.nodes:
        assert orig[n.id] == (n.type, n.label, n.symbol)

    # edges preserved (as sets of tuples)
    def edge_set(graph):
        return {(e.source, e.target, e.kind, e.label) for e in graph.edges}

    assert edge_set(back) == edge_set(g)


def test_roundtrip_dry_tree_concept():
    g = _graph(FieldConcept(name="Spar", concept_type=ConceptType.SPAR, num_wells=3))
    back = dexpi_to_graph(graph_to_dexpi(g))
    assert {n.type for n in back.nodes} == {n.type for n in g.nodes}
    assert any(n.type == NodeType.WELLHEAD for n in back.nodes)
    assert not any(n.type == NodeType.MANIFOLD for n in back.nodes)


def test_roundtrip_preserves_edge_kinds():
    g = _graph()
    back = dexpi_to_graph(graph_to_dexpi(g))
    assert {e.kind for e in back.edges} == {e.kind for e in g.edges}
    assert EdgeKind.CONTROL in {e.kind for e in back.edges}


def test_export_is_deterministic():
    g = _graph()
    assert graph_to_dexpi(g) == graph_to_dexpi(g)


def test_to_dict_graph_also_roundtrips_via_dexpi():
    # The DEXPI graph reproduces the same to_dict() topology as the original.
    g = _graph()
    back = dexpi_to_graph(graph_to_dexpi(g))
    assert back.to_dict() == g.to_dict()
