# ABOUTME: Deterministic plan-view (map) field-layout renderer -> SVG.
# ABOUTME: Issue #573 (epic #567) — real coordinates via trig, no new deps.
"""
worldenergydata.field_development.layout
========================================

Renders a **plan-view (map) field layout** to SVG from a :class:`FieldConcept`.
Unlike the block-diagram renderer (which uses arbitrary auto-layout), this view
uses *real coordinates*: the manifold sits at the origin, subsea trees are
placed on a ring around it, and the host is offset north by the actual
``tieback_distance_km`` — so the drawing is to scale, with a north arrow and a
scale bar.

Positions are computed by deterministic trigonometry (documented in
:func:`compute_positions`); no LLM and no randomness are involved, so the same
concept always yields the same SVG. SVG is emitted as plain strings — no
third-party drawing dependency — which keeps output byte-stable and testable.

Node markers are simple placeholder glyphs keyed by ``symbol``; the real subsea
symbol library (#574) will swap in proper artwork without changing this geometry.

Coordinate convention: an internal y-up math frame in kilometres (north = +y),
converted to SVG's y-down pixel frame on output.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from worldenergydata.field_development.graph import (
    GraphSpec,
    NodeType,
    concept_to_graph,
)
from worldenergydata.field_development.models import FieldConcept
from worldenergydata.field_development.symbols import render_symbol

# Marker size (px) per node type for the plan-view symbols.
_SYMBOL_SIZE = {
    NodeType.HOST: 16.0,
    NodeType.ONSHORE_TERMINAL: 16.0,
    NodeType.MANIFOLD: 12.0,
    NodeType.TREE: 8.0,
    NodeType.WELLHEAD: 8.0,
    NodeType.EXPORT: 10.0,
}

DEFAULT_SCALE_PX_PER_KM = 40.0
TREE_RING_RADIUS_KM = 0.5  # subsea trees ringed around their manifold
MANIFOLD_SPACING_KM = 1.2  # spacing between multiple manifolds (east-west)
DEFAULT_HOST_OFFSET_KM = 1.5  # host offset when there is no explicit tieback
EXPORT_BEYOND_HOST_KM = 1.0  # export sink placed beyond the host
MARGIN_PX = 60.0


@dataclass(frozen=True)
class Point:
    """A point in the km math frame (north = +y)."""

    x_km: float
    y_km: float


def compute_positions(
    concept: FieldConcept, graph: GraphSpec | None = None
) -> dict[str, Point]:
    """Assign each graph node a real-world position (km, north = +y).

    Geometry (deterministic):
      * manifolds: spaced east-west, centred on the origin;
      * subsea trees: on a ring of radius ``TREE_RING_RADIUS_KM`` around their
        owning manifold, angle = ``index * 2π / trees_on_that_manifold``;
      * dry-tree wellheads: ringed directly around the host;
      * host: north of the field by ``tieback_distance_km`` (or a default offset
        for a standalone host);
      * export: ``EXPORT_BEYOND_HOST_KM`` north of the host.

    Args:
        concept: The field concept.
        graph: A prebuilt graph spec; if ``None`` it is built from the concept.

    Returns:
        Mapping of node id -> :class:`Point` in km.
    """
    g = graph or concept_to_graph(concept)
    pos: dict[str, Point] = {}

    manifolds = [n for n in g.nodes if n.type == NodeType.MANIFOLD]
    trees = [n for n in g.nodes if n.type == NodeType.TREE]
    wellheads = [n for n in g.nodes if n.type == NodeType.WELLHEAD]

    # Manifolds spaced east-west, centred on x=0.
    n_mf = len(manifolds)
    for i, mf in enumerate(manifolds):
        x = (i - (n_mf - 1) / 2.0) * MANIFOLD_SPACING_KM
        pos[mf.id] = Point(x, 0.0)

    # Subsea trees ringed around their owning manifold (round-robin owner).
    if manifolds:
        owners: dict[str, list[str]] = {mf.id: [] for mf in manifolds}
        for t_idx, tree in enumerate(trees):
            owner = manifolds[t_idx % n_mf]
            owners[owner.id].append(tree.id)
        for mf in manifolds:
            _ring_around(pos, pos[mf.id], owners[mf.id])

    # Host position: north by tieback distance (or default standalone offset).
    host_offset = (
        concept.tieback_distance_km
        if concept.tieback_distance_km and concept.tieback_distance_km > 0
        else DEFAULT_HOST_OFFSET_KM
    )
    pos["host"] = Point(0.0, host_offset)

    # Dry-tree wellheads ring around the host (no manifold).
    if wellheads:
        _ring_around(pos, pos["host"], [w.id for w in wellheads])

    if "export" in g.node_ids():
        pos["export"] = Point(0.0, host_offset + EXPORT_BEYOND_HOST_KM)

    return pos


def _ring_around(pos: dict[str, Point], centre: Point, ids: list[str]) -> None:
    """Place ``ids`` on a ring around ``centre`` (first point due north)."""
    n = len(ids)
    if n == 0:
        return
    for i, node_id in enumerate(ids):
        theta = math.pi / 2 + (2 * math.pi * i / n)  # start north, go CCW
        pos[node_id] = Point(
            centre.x_km + TREE_RING_RADIUS_KM * math.cos(theta),
            centre.y_km + TREE_RING_RADIUS_KM * math.sin(theta),
        )


def compute_pixel_positions(
    concept: FieldConcept,
    graph: GraphSpec | None = None,
    scale_px_per_km: float = DEFAULT_SCALE_PX_PER_KM,
) -> dict[str, tuple[float, float]]:
    """Positions in SVG pixel space (y-down), pre-margin.

    The km frame (north = +y) is flipped to SVG's y-down frame. Returned values
    are not yet translated for the drawing margin; :func:`render_layout` applies
    the final translation. Distances between points are preserved, so
    ``dist(host, manifold) == tieback_distance_km * scale_px_per_km``.
    """
    km = compute_positions(concept, graph)
    return {
        nid: (p.x_km * scale_px_per_km, -p.y_km * scale_px_per_km)
        for nid, p in km.items()
    }


def render_layout(
    concept: FieldConcept,
    graph: GraphSpec | None = None,
    scale_px_per_km: float = DEFAULT_SCALE_PX_PER_KM,
) -> str:
    """Render a to-scale plan-view SVG of the field layout.

    Args:
        concept: The field concept to draw.
        graph: Optional prebuilt graph spec.
        scale_px_per_km: Drawing scale.

    Returns:
        A complete SVG document string (with north arrow + scale bar).
    """
    g = graph or concept_to_graph(concept)
    px = compute_pixel_positions(concept, g, scale_px_per_km)
    types = {n.id: n.type for n in g.nodes}
    symbols = {n.id: n.symbol for n in g.nodes}
    labels = {n.id: n.label for n in g.nodes}

    xs = [p[0] for p in px.values()]
    ys = [p[1] for p in px.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = (max_x - min_x) + 2 * MARGIN_PX
    height = (max_y - min_y) + 2 * MARGIN_PX

    def tx(x: float) -> float:
        return x - min_x + MARGIN_PX

    def ty(y: float) -> float:
        return y - min_y + MARGIN_PX

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" '
        f'height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f"<title>Field layout — {_esc(concept.name)}</title>",
    ]

    # Edges first (under nodes).
    for e in g.edges:
        if e.source in px and e.target in px:
            x1, y1 = tx(px[e.source][0]), ty(px[e.source][1])
            x2, y2 = tx(px[e.target][0]), ty(px[e.target][1])
            dash = ' stroke-dasharray="4 3"' if e.kind.value == "control" else ""
            parts.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="#5a7" stroke-width="1.5"{dash}/>'
            )

    # Nodes: subsea symbol glyph + label.
    for nid, (x, y) in px.items():
        size = _SYMBOL_SIZE.get(types[nid], 9.0)
        gx, gy = tx(x), ty(y)
        parts.append(render_symbol(symbols[nid], gx, gy, size))
        parts.append(
            f'<text x="{gx + size + 3:.1f}" y="{gy + 3:.1f}" '
            f'font-family="sans-serif" font-size="9">{_esc(labels.get(nid, nid))}</text>'
        )

    parts.append(_north_arrow(width))
    parts.append(_scale_bar(scale_px_per_km, height))
    parts.append("</svg>")
    return "\n".join(parts)


def _north_arrow(width: float) -> str:
    x = width - 28
    return (
        f'<g stroke="#222" fill="#222">'
        f'<line x1="{x:.0f}" y1="46" x2="{x:.0f}" y2="20" stroke-width="2"/>'
        f'<polygon points="{x:.0f},14 {x - 5:.0f},24 {x + 5:.0f},24"/>'
        f'<text x="{x - 4:.0f}" y="60" font-family="sans-serif" '
        f'font-size="11" stroke="none">N</text></g>'
    )


def _scale_bar(scale_px_per_km: float, height: float) -> str:
    bar_px = scale_px_per_km  # represents exactly 1 km
    x0, y0 = 20.0, height - 24.0
    return (
        f'<g stroke="#222" fill="#222">'
        f'<line x1="{x0:.0f}" y1="{y0:.0f}" x2="{x0 + bar_px:.0f}" y2="{y0:.0f}" '
        f'stroke-width="2"/>'
        f'<line x1="{x0:.0f}" y1="{y0 - 4:.0f}" x2="{x0:.0f}" y2="{y0 + 4:.0f}" '
        f'stroke-width="2"/>'
        f'<line x1="{x0 + bar_px:.0f}" y1="{y0 - 4:.0f}" x2="{x0 + bar_px:.0f}" '
        f'y2="{y0 + 4:.0f}" stroke-width="2"/>'
        f'<text x="{x0:.0f}" y="{y0 - 8:.0f}" font-family="sans-serif" '
        f'font-size="10" stroke="none">1 km</text></g>'
    )


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
