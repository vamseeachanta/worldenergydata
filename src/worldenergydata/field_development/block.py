# ABOUTME: Pure-Python layered block-diagram renderer for the subsea graph -> SVG.
# ABOUTME: Issue #572 (epic #567) — zero-dependency Sugiyama-lite layout.
"""
worldenergydata.field_development.block
=======================================

Renders a :class:`GraphSpec` as a **block diagram** (architecture schematic):
labelled boxes for nodes, typed connectors for edges, arranged in horizontal
*layers* by logical rank (production flows up: export → host → manifold →
trees). Unlike the plan-view (#573), positions here are logical, not geographic.

The layout is a deterministic "Sugiyama-lite": rank each node by its type, then
spread nodes evenly within each rank ordered by node id. For the small graphs
this playbook produces (one host, a few manifolds, a handful of trees) this is
clean and collision-free without pulling in an external layout engine (D2/ELK/
Graphviz). SVG is emitted as plain strings, so output is byte-deterministic and
testable. Edge kinds are visually distinct: production solid, control dashed,
export bold.
"""

from __future__ import annotations

from worldenergydata.field_development.graph import (
    EdgeKind,
    GraphSpec,
    NodeType,
    concept_to_graph,
)
from worldenergydata.field_development.models import FieldConcept

# Rank (layer) per node type — smaller rank is drawn higher on the canvas.
# Production flows upward: trees (bottom) → manifold → host → export (top).
_RANK = {
    NodeType.EXPORT: 0,
    NodeType.HOST: 1,
    NodeType.ONSHORE_TERMINAL: 1,
    NodeType.MANIFOLD: 2,
    NodeType.TREE: 3,
    NodeType.WELLHEAD: 2,  # dry trees attach directly to the host (no manifold)
}

_FILL = {
    NodeType.EXPORT: "#eeeeee",
    NodeType.HOST: "#cde2f7",
    NodeType.ONSHORE_TERMINAL: "#cde2f7",
    NodeType.MANIFOLD: "#ffe9c7",
    NodeType.TREE: "#eccff2",
    NodeType.WELLHEAD: "#eccff2",
}
_STROKE = {
    NodeType.EXPORT: "#555555",
    NodeType.HOST: "#234e78",
    NodeType.ONSHORE_TERMINAL: "#234e78",
    NodeType.MANIFOLD: "#a8620a",
    NodeType.TREE: "#6a1b80",
    NodeType.WELLHEAD: "#6a1b80",
}

BOX_H = 30.0
CHAR_W = 6.4
BOX_PAD = 14.0
MIN_BOX_W = 60.0
LAYER_GAP_Y = 90.0
NODE_GAP_X = 34.0
MARGIN = 40.0


def _box_w(label: str) -> float:
    return max(MIN_BOX_W, len(label) * CHAR_W + 2 * BOX_PAD)


def _as_graph(source: FieldConcept | GraphSpec) -> GraphSpec:
    return source if isinstance(source, GraphSpec) else concept_to_graph(source)


def render_block_diagram(source: FieldConcept | GraphSpec) -> str:
    """Render a subsea-architecture block diagram to SVG.

    Args:
        source: A :class:`GraphSpec`, or a :class:`FieldConcept` (mapped to one).

    Returns:
        A complete SVG document string. Deterministic for a given graph.
    """
    g = _as_graph(source)
    type_of = {n.id: n.type for n in g.nodes}
    label_of = {n.id: n.label for n in g.nodes}

    # Group node ids by rank, ordered by id for determinism.
    ranks: dict[int, list[str]] = {}
    for n in sorted(g.nodes, key=lambda n: n.id):
        ranks.setdefault(_RANK.get(n.type, 9), []).append(n.id)

    # Width of each rank row, to centre rows against the widest row.
    row_widths = {
        r: sum(_box_w(label_of[i]) for i in ids) + NODE_GAP_X * (len(ids) - 1)
        for r, ids in ranks.items()
    }
    canvas_w = max(row_widths.values()) + 2 * MARGIN

    # Assign each node a centre position.
    centre: dict[str, tuple[float, float]] = {}
    for r in sorted(ranks):
        ids = ranks[r]
        y = MARGIN + r * LAYER_GAP_Y + BOX_H / 2
        x = MARGIN + (canvas_w - 2 * MARGIN - row_widths[r]) / 2
        for i in ids:
            w = _box_w(label_of[i])
            centre[i] = (x + w / 2, y)
            x += w + NODE_GAP_X

    max_rank = max(ranks)
    canvas_h = MARGIN + max_rank * LAYER_GAP_Y + BOX_H + MARGIN

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w:.0f}" '
        f'height="{canvas_h:.0f}" viewBox="0 0 {canvas_w:.0f} {canvas_h:.0f}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f"<title>Subsea architecture — {_esc(g.field_name)}</title>",
        _arrow_defs(),
    ]

    # Edges first (under boxes).
    for e in g.edges:
        if e.source in centre and e.target in centre:
            parts.append(_edge(centre[e.source], centre[e.target], e.kind, e.label))

    # Boxes.
    for nid, (cx, cy) in centre.items():
        parts.append(_box(type_of[nid], cx, cy, label_of[nid]))

    parts.append("</svg>")
    return "\n".join(parts)


def _box(ntype: NodeType, cx: float, cy: float, label: str) -> str:
    w = _box_w(label)
    x, y = cx - w / 2, cy - BOX_H / 2
    fill = _FILL.get(ntype, "#eeeeee")
    stroke = _STROKE.get(ntype, "#555555")
    return (
        f'<g><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{BOX_H:.1f}" '
        f'rx="5" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
        f'<text x="{cx:.1f}" y="{cy + 3.5:.1f}" text-anchor="middle" '
        f'font-family="sans-serif" font-size="11">{_esc(label)}</text></g>'
    )


def _edge(
    src: tuple[float, float], tgt: tuple[float, float], kind: EdgeKind, label: str
) -> str:
    x1, y1 = src
    x2, y2 = tgt
    if kind == EdgeKind.CONTROL:
        style = 'stroke="#888" stroke-width="1.2" stroke-dasharray="5 3"'
    elif kind == EdgeKind.EXPORT:
        style = 'stroke="#234e78" stroke-width="2.4"'
    else:  # production
        style = 'stroke="#3a8f5a" stroke-width="1.8"'
    line = (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'{style} marker-end="url(#ah)"/>'
    )
    txt = ""
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        txt = (
            f'<text x="{mx + 3:.1f}" y="{my:.1f}" font-family="sans-serif" '
            f'font-size="8" fill="#444">{_esc(label)}</text>'
        )
    return line + txt


def _arrow_defs() -> str:
    return (
        '<defs><marker id="ah" markerWidth="8" markerHeight="8" refX="6" '
        'refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#666"/>'
        "</marker></defs>"
    )


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
