# ABOUTME: DEXPI-aligned (Proteus-XML) export/import for the subsea GraphSpec.
# ABOUTME: Issue #578 (epic #567) — interop layer over the graph, zero new deps.
"""
worldenergydata.field_development.dexpi
=======================================

Maps the layout-free :class:`GraphSpec` (#571) to a **DEXPI-aligned** Proteus-XML
document and back, so the playbook's subsea architecture can interoperate with
commercial P&ID tooling (which reads DEXPI / Proteus).

This is an *interop layer*, not a rewrite: the graph stays the source of truth,
and this module translates it to/from DEXPI's structural conventions —
``PlantModel`` → ``Equipment`` (with ``GenericAttribute``s) and
``PipingNetworkSystem`` → ``PipingNetworkSegment``.

**Subsea hardware is not native to DEXPI's process-plant class library**
(there is no standard ``SubseaTree`` / ``SubseaManifold`` / ``Spar`` class), so
each node is exported as a generic ``Equipment`` whose subsea identity is carried
in ``GenericAttribute``s (``FieldDevNodeType``, ``FieldDevSymbol``). That is the
documented *extension* — it keeps the document DEXPI-shaped while preserving all
field-development semantics, which makes the round-trip lossless.

Scope: this targets DEXPI's *structure* (element/attribute shapes) using the
standard library only. It is not full ISO-15926 conformance — a downstream DEXPI
tool will read the topology and the generic attributes; mapping the subsea
extension attributes to that tool's own class library is the integration step.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from worldenergydata.field_development.graph import (
    Edge,
    EdgeKind,
    GraphSpec,
    Node,
    NodeType,
)

# Node type -> DEXPI ComponentClass (generic where subsea has no native class).
_NODE_TO_COMPONENT: dict[NodeType, str] = {
    NodeType.HOST: "ProductionHost",
    NodeType.ONSHORE_TERMINAL: "OnshoreTerminal",
    NodeType.MANIFOLD: "SubseaManifold",
    NodeType.TREE: "SubseaTree",
    NodeType.WELLHEAD: "DryTree",
    NodeType.PLET: "PipingEndTermination",
    NodeType.EXPORT: "ExportPoint",
}
_COMPONENT_TO_NODE: dict[str, NodeType] = {v: k for k, v in _NODE_TO_COMPONENT.items()}

_NS_NOTE = "DEXPI-aligned subset; subsea types carried as GenericAttributes."


def dexpi_mapping() -> dict[str, str]:
    """Return the NodeType→ComponentClass mapping (for docs / tests)."""
    return {nt.value: cc for nt, cc in _NODE_TO_COMPONENT.items()}


def _attr(parent: ET.Element, name: str, value: str) -> None:
    ET.SubElement(parent, "GenericAttribute", {"Name": name, "Value": value})


def graph_to_dexpi(graph: GraphSpec) -> str:
    """Serialize a :class:`GraphSpec` to a DEXPI-aligned Proteus-XML string."""
    root = ET.Element("PlantModel")
    info = ET.SubElement(root, "PlantInformation")
    info.set("Application", "worldenergydata.field_development")
    info.set("SchemaVersion", "dexpi-aligned-1.0")
    info.set("Project", graph.field_name)
    info.set("Note", _NS_NOTE)

    # Equipment (one per node).
    for n in graph.nodes:
        eq = ET.SubElement(
            root,
            "Equipment",
            {
                "ID": n.id,
                "ComponentClass": _NODE_TO_COMPONENT.get(n.type, "Equipment"),
                "ComponentName": n.label,
            },
        )
        ga = ET.SubElement(eq, "GenericAttributes")
        _attr(ga, "FieldDevNodeType", n.type.value)
        _attr(ga, "FieldDevSymbol", n.symbol)

    # Piping (one segment per edge), grouped in a single network system.
    pns = ET.SubElement(root, "PipingNetworkSystem", {"ID": "PNS-1"})
    for i, e in enumerate(graph.edges):
        ET.SubElement(
            pns,
            "PipingNetworkSegment",
            {
                "ID": f"SEG-{i + 1}",
                "FromID": e.source,
                "ToID": e.target,
                "FieldDevKind": e.kind.value,
                "ComponentName": e.label,
            },
        )

    ET.indent(root)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def dexpi_to_graph(xml: str) -> GraphSpec:
    """Parse a DEXPI-aligned Proteus-XML string back into a :class:`GraphSpec`."""
    root = ET.fromstring(xml)
    info = root.find("PlantInformation")
    field_name = info.get("Project", "") if info is not None else ""
    graph = GraphSpec(field_name=field_name)

    for eq in root.findall("Equipment"):
        ga = {
            a.get("Name"): a.get("Value")
            for a in eq.findall("./GenericAttributes/GenericAttribute")
        }
        ntype_raw = ga.get("FieldDevNodeType")
        ntype = (
            NodeType(ntype_raw)
            if ntype_raw
            else _COMPONENT_TO_NODE.get(eq.get("ComponentClass", ""), NodeType.HOST)
        )
        graph.nodes.append(
            Node(
                id=eq.get("ID", ""),
                type=ntype,
                label=eq.get("ComponentName", ""),
                symbol=ga.get("FieldDevSymbol", ""),
            )
        )

    for seg in root.findall("./PipingNetworkSystem/PipingNetworkSegment"):
        graph.edges.append(
            Edge(
                source=seg.get("FromID", ""),
                target=seg.get("ToID", ""),
                kind=EdgeKind(seg.get("FieldDevKind", "production")),
                label=seg.get("ComponentName", ""),
            )
        )
    return graph
