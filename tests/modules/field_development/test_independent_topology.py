"""Independent contract examples; synthetic inputs, no engineering qualification.

Basis: graph.py concept_to_graph/_build_subsea/_build_dry_tree and dexpi.py
module contract, repository revision f82ff2f1 (2026). These are software
conventions, not requirements from a published engineering standard.
"""

from xml.etree import ElementTree as ET

import pytest

from worldenergydata.field_development.dexpi import dexpi_to_graph, graph_to_dexpi
from worldenergydata.field_development.enums import ConceptType
from worldenergydata.field_development.graph import EdgeKind, concept_to_graph
from worldenergydata.field_development.models import FieldConcept


def test_populated_wet_tree_connections():
    """Hand count: 3 trees + 2 manifolds + host + export = 7 nodes.

    Round-robin allocation is tree 1 -> mf 1, tree 2 -> mf 2, tree 3 -> mf 1.
    Production = 3 jumpers + 2 flowlines = 5; control reverses those 5;
    export adds 1, giving 11 edges. Inputs are synthetic given counts.
    """
    graph = concept_to_graph(
        FieldConcept(
            name="Synthetic example",
            concept_type=ConceptType.SUBSEA_TIEBACK,
            num_wells=3,
            num_manifolds=2,
        )
    )
    production = {
        ("tree-1", "mf-1"),
        ("tree-2", "mf-2"),
        ("tree-3", "mf-1"),
        ("mf-1", "host"),
        ("mf-2", "host"),
    }
    assert graph.node_ids() == {
        "tree-1",
        "tree-2",
        "tree-3",
        "mf-1",
        "mf-2",
        "host",
        "export",
    }
    assert len(graph.nodes) == 7
    assert len(graph.edges) == 11
    assert {
        (e.source, e.target) for e in graph.edges if e.kind == EdgeKind.PRODUCTION
    } == production
    assert {
        (e.target, e.source) for e in graph.edges if e.kind == EdgeKind.CONTROL
    } == production
    assert [(e.source, e.target) for e in graph.edges if e.kind == EdgeKind.EXPORT] == [
        ("host", "export")
    ]


def test_populated_dry_tree_connections():
    """Hand count: 2 wellheads + host + export = 4 nodes, 2 risers + 1 export.

    No manifold or control edge is specified by the dry-tree software contract.
    """
    graph = concept_to_graph(
        FieldConcept(
            name="Synthetic example",
            concept_type=ConceptType.FIXED_JACKET,
            num_wells=2,
        )
    )
    assert [(n.id, n.type.value) for n in graph.nodes] == [
        ("host", "host"),
        ("tree-1", "wellhead"),
        ("tree-2", "wellhead"),
        ("export", "export"),
    ]
    assert [(e.source, e.target, e.kind.value) for e in graph.edges] == [
        ("tree-1", "host", "production"),
        ("tree-2", "host", "production"),
        ("host", "export", "export"),
    ]


def test_export_independent_xml_consumer():
    """Hand oracle: 1 terminal + 1 manifold + 1 tree; 2 directed pairs.

    A terminal is already the export sink, so no separate export is expected.
    ElementTree reads exported bytes without using the module's importer.
    """
    graph = concept_to_graph(
        FieldConcept(
            name="Synthetic & <example>",
            concept_type=ConceptType.SUBSEA_TO_SHORE,
            num_wells=1,
            num_manifolds=1,
        )
    )
    root = ET.fromstring(graph_to_dexpi(graph))
    assert root.find("PlantInformation").get("Project") == "Synthetic & <example>"
    assert [
        (e.get("ID"), e.get("ComponentClass")) for e in root.findall("Equipment")
    ] == [
        ("host", "OnshoreTerminal"),
        ("mf-1", "SubseaManifold"),
        ("tree-1", "SubseaTree"),
    ]
    segments = root.findall("./PipingNetworkSystem/PipingNetworkSegment")
    assert len(segments) == 4
    assert {
        (e.get("FromID"), e.get("ToID"), e.get("FieldDevKind")) for e in segments
    } == {
        ("mf-1", "host", "production"),
        ("host", "mf-1", "control"),
        ("tree-1", "mf-1", "production"),
        ("mf-1", "tree-1", "control"),
    }


def test_import_independently_authored_xml():
    """Literal input bypasses exporter; expected endpoints are read by hand."""
    graph = dexpi_to_graph(
        """<PlantModel>
      <PlantInformation Project="Synthetic example"/>
      <Equipment ID="a" ComponentClass="SubseaTree" ComponentName="Tree"/>
      <Equipment ID="b" ComponentClass="SubseaManifold" ComponentName="Manifold"/>
      <PipingNetworkSystem><PipingNetworkSegment FromID="a" ToID="b"
        FieldDevKind="production" ComponentName="jumper"/></PipingNetworkSystem>
    </PlantModel>"""
    )
    assert graph.field_name == "Synthetic example"
    assert [(n.id, n.type.value, n.label, n.symbol) for n in graph.nodes] == [
        ("a", "tree", "Tree", ""),
        ("b", "manifold", "Manifold", ""),
    ]
    assert [(e.source, e.target, e.kind.value, e.label) for e in graph.edges] == [
        ("a", "b", "production", "jumper"),
    ]


@pytest.mark.parametrize("count", [None, 0])
def test_sparse_graph_substitutes_schematic_hardware(count):
    """Contract limitation: missing/zero counts draw 1 tree and 1 manifold.

    This pins a substitution, not an evaluated hardware inventory. Source:
    graph.py _tree_count and _build_subsea, revision cited above.
    """
    graph = concept_to_graph(
        FieldConcept(
            name="Synthetic example",
            num_wells=count,
            num_manifolds=count,
        )
    )
    assert graph.node_ids() == {"host", "mf-1", "tree-1", "export"}
