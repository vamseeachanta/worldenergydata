# ABOUTME: Deterministic FieldConcept -> graph spec (nodes + typed edges).
# ABOUTME: Issue #571 (epic #567) — the layout-free IR both renderers consume.
"""
worldenergydata.field_development.graph
=======================================

Maps a :class:`FieldConcept` to a **graph spec** — a layout-free intermediate
representation of the subsea architecture: typed ``nodes`` (host, manifold,
trees, terminations, export) and typed ``edges`` (production flowlines, control
umbilicals, export). Both the block-diagram renderer (#572) and the plan-view
renderer (#573) consume this one structure.

This stage decides *what connects to what* using deterministic domain rules; it
deliberately carries **no coordinates** — placement is the renderers' job. Node
and edge types use a small DEXPI-aligned vocabulary so the Phase-2 DEXPI interop
issue (#578) is an extension, not a rewrite. Each node also carries a ``symbol``
key into the subsea symbol library (#574).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum

from worldenergydata.field_development.enums import ConceptType, Topology, TreeType
from worldenergydata.field_development.models import FieldConcept

# Concepts whose trees sit on the host (dry, surface) rather than the seabed.
_DRY_TREE_CONCEPTS = {
    ConceptType.FIXED_JACKET,
    ConceptType.COMPLIANT_TOWER,
    ConceptType.TLP,
    ConceptType.SPAR,
    ConceptType.NUI,
}


class NodeType(str, Enum):
    """DEXPI-aligned node kinds for the subsea architecture graph."""

    HOST = "host"                      # the production facility (or existing host)
    ONSHORE_TERMINAL = "onshore_terminal"
    MANIFOLD = "manifold"
    TREE = "tree"                      # subsea (wet) tree
    WELLHEAD = "wellhead"              # dry tree / surface wellhead on the host
    PLET = "plet"                      # pipeline end termination
    EXPORT = "export"                  # export sink (pipeline / terminal)


class EdgeKind(str, Enum):
    """Connection kinds between nodes."""

    PRODUCTION = "production"          # flowline / production riser
    CONTROL = "control"               # umbilical (hydraulic/electric/chemical)
    EXPORT = "export"                 # export line


@dataclass(frozen=True)
class Node:
    """A graph node. ``symbol`` keys into the subsea symbol library (#574)."""

    id: str
    type: NodeType
    label: str
    symbol: str


@dataclass(frozen=True)
class Edge:
    """A typed connection between two node ids."""

    source: str
    target: str
    kind: EdgeKind
    label: str = ""


@dataclass
class GraphSpec:
    """The layout-free graph: nodes + edges, plus the originating concept name."""

    field_name: str
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to plain dicts (enum values as strings) for renderers."""
        return {
            "field_name": self.field_name,
            "nodes": [
                {**asdict(n), "type": n.type.value} for n in self.nodes
            ],
            "edges": [
                {**asdict(e), "kind": e.kind.value} for e in self.edges
            ],
        }

    def node_ids(self) -> set[str]:
        return {n.id for n in self.nodes}


def _uses_wet_trees(c: FieldConcept) -> bool:
    """Decide wet vs dry trees: explicit ``tree_type`` wins; else infer from concept."""
    if c.tree_type is not None:
        return c.tree_type == TreeType.WET
    if c.concept_type is None:
        return True  # default to subsea when concept is unspecified
    return c.concept_type not in _DRY_TREE_CONCEPTS


def _host_node(c: FieldConcept) -> Node:
    """Build the host (or existing-host / onshore-terminal) node."""
    if c.concept_type == ConceptType.SUBSEA_TO_SHORE:
        return Node("host", NodeType.ONSHORE_TERMINAL, "Onshore Terminal",
                    "onshore_terminal")
    if c.concept_type == ConceptType.SUBSEA_TIEBACK:
        return Node("host", NodeType.HOST, "Existing Host (tieback)",
                    "existing_host")
    symbol = c.concept_type.value if c.concept_type else "host"
    label = c.concept_type.value.replace("_", " ").upper() if c.concept_type else "Host"
    return Node("host", NodeType.HOST, label, symbol)


def _tree_count(c: FieldConcept) -> int:
    """How many tree/wellhead nodes to draw (≥1 once we know there are wells)."""
    if c.num_wells is not None and c.num_wells > 0:
        return c.num_wells
    return 1


def concept_to_graph(c: FieldConcept) -> GraphSpec:
    """Map a :class:`FieldConcept` to a :class:`GraphSpec` (deterministic).

    Wet-tree fields route trees → manifold(s) → host with control umbilicals;
    dry-tree fields attach wellheads directly to the host. Ids are stable
    (``tree-1``, ``mf-1`` …) so the same concept always yields the same spec.

    Args:
        c: The field concept to map.

    Returns:
        A :class:`GraphSpec` with nodes + typed edges and no coordinates.
    """
    g = GraphSpec(field_name=c.name)
    host = _host_node(c)
    g.nodes.append(host)

    n_trees = _tree_count(c)
    wet = _uses_wet_trees(c)

    if wet:
        _build_subsea(g, c, host, n_trees)
    else:
        _build_dry_tree(g, c, host, n_trees)

    # Export sink (skip for subsea-to-shore: the terminal *is* the export point).
    if c.concept_type != ConceptType.SUBSEA_TO_SHORE:
        g.nodes.append(Node("export", NodeType.EXPORT, "Export", "export"))
        g.edges.append(Edge(host.id, "export", EdgeKind.EXPORT, "export"))

    return g


def _build_subsea(g: GraphSpec, c: FieldConcept, host: Node, n_trees: int) -> None:
    """Wet-tree topology: trees → manifold(s) → host (+ control umbilicals)."""
    n_manifolds = c.num_manifolds if c.num_manifolds and c.num_manifolds > 0 else 1
    manifolds = [
        Node(f"mf-{i + 1}", NodeType.MANIFOLD, f"Manifold {i + 1}", "manifold")
        for i in range(n_manifolds)
    ]
    g.nodes.extend(manifolds)

    # Manifold -> host: production flowline + control umbilical (host -> manifold).
    pigging = c.topology == Topology.PIGGING_LOOP
    for mf in manifolds:
        g.edges.append(Edge(mf.id, host.id, EdgeKind.PRODUCTION,
                            "flowline loop" if pigging else "flowline"))
        g.edges.append(Edge(host.id, mf.id, EdgeKind.CONTROL, "umbilical"))

    # Trees distributed round-robin across manifolds.
    for t in range(n_trees):
        tree = Node(f"tree-{t + 1}", NodeType.TREE, f"XT {t + 1}", "subsea_tree")
        g.nodes.append(tree)
        mf = manifolds[t % n_manifolds]
        g.edges.append(Edge(tree.id, mf.id, EdgeKind.PRODUCTION, "jumper"))
        g.edges.append(Edge(mf.id, tree.id, EdgeKind.CONTROL, "control"))


def _build_dry_tree(g: GraphSpec, c: FieldConcept, host: Node, n_trees: int) -> None:
    """Dry-tree topology: wellheads attach directly to the host (TTR risers)."""
    for t in range(n_trees):
        wh = Node(f"tree-{t + 1}", NodeType.WELLHEAD, f"Well {t + 1}", "dry_tree")
        g.nodes.append(wh)
        g.edges.append(Edge(wh.id, host.id, EdgeKind.PRODUCTION, "TTR riser"))
