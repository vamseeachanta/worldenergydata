# ABOUTME: Optimize manifold/host placement to minimize flowline length.
# ABOUTME: Issue #579 (epic #567) — deterministic k-means clustering, zero deps.
"""
worldenergydata.field_development.layout_optimization
=====================================================

Computes an *optimized* subsea field layout: given real well coordinates, where
should the manifold(s) and host sit so total **flowline + jumper length** is
minimized? This is the inverse of the plan-view renderer (#573), which *draws*
given coordinates — here we *compute* them.

Approach (after "A framework for early-stage automated layout design of subsea
production systems", Ocean Engineering 2024): cluster wells into drill
centers / manifolds, place each manifold at its cluster centroid, and place a
standalone host at the manifolds' centroid (or use the given tieback host). The
objective is the sum of tree→manifold jumpers plus manifold→host flowlines —
length is a direct CAPEX driver (flowline steel scales with metres laid).

**Deterministic**: the clustering uses farthest-point seeding (ties broken by
well id) and Lloyd iterations — the same wells always yield the same layout, so
it is reproducible and testable, and feeds the renderer without randomness.

Keep this out of v1 of the visual pipeline (the deterministic renderer must be
trusted first); it is an optional Phase-2 module. Constraints like a per-manifold
well cap are noted but not enforced in this first cut.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Well:
    """A well with a real seabed coordinate (km, any consistent planar frame)."""

    id: str
    x: float
    y: float


@dataclass
class LayoutSolution:
    """An optimized layout: manifold positions, assignments, host, total length."""

    manifolds: dict[str, tuple[float, float]] = field(default_factory=dict)
    assignment: dict[str, str] = field(default_factory=dict)  # well id -> manifold id
    host: tuple[float, float] = (0.0, 0.0)
    total_length_km: float = 0.0
    n_manifolds: int = 0


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    n = len(points)
    return (sum(p[0] for p in points) / n, sum(p[1] for p in points) / n)


def _seed_centroids(wells: list[Well], k: int) -> list[tuple[float, float]]:
    """Deterministic farthest-point seeding (k-means++ without randomness)."""
    pts = {w.id: (w.x, w.y) for w in wells}
    all_pts = [(w.x, w.y) for w in wells]
    # First seed: the well nearest the global centroid (ties → lowest id).
    g = _centroid(all_pts)
    first = min(wells, key=lambda w: (_dist((w.x, w.y), g), w.id))
    seeds = [(first.x, first.y)]
    while len(seeds) < k:
        # Add the well farthest from its nearest existing seed (ties → lowest id).
        nxt = max(
            wells,
            key=lambda w: (min(_dist(pts[w.id], s) for s in seeds), w.id),
        )
        seeds.append((nxt.x, nxt.y))
    return seeds


def optimize_layout(
    wells: list[Well],
    n_manifolds: int = 1,
    host: tuple[float, float] | None = None,
    max_iterations: int = 50,
) -> LayoutSolution:
    """Place ``n_manifolds`` manifolds (+ host) to minimize total flowline length.

    Args:
        wells: Wells with seabed coordinates.
        n_manifolds: Number of manifolds / drill centers to place.
        host: Fixed host position (e.g. an existing tieback host). If None, a
            standalone host is placed at the manifolds' centroid.
        max_iterations: Lloyd-iteration cap.

    Returns:
        A :class:`LayoutSolution`.
    """
    if not wells:
        return LayoutSolution(host=host or (0.0, 0.0), n_manifolds=0)
    k = max(1, min(n_manifolds, len(wells)))
    mids = [f"mf-{i + 1}" for i in range(k)]
    centroids = _seed_centroids(wells, k)

    assignment: dict[str, int] = {}
    for _ in range(max_iterations):
        # Assign each well to the nearest centroid (ties → lowest centroid index).
        new_assign = {
            w.id: min(range(k), key=lambda c: (_dist((w.x, w.y), centroids[c]), c))
            for w in wells
        }
        if new_assign == assignment:
            break
        assignment = new_assign
        # Recompute centroids; keep the old centroid for an empty cluster.
        for c in range(k):
            members = [(w.x, w.y) for w in wells if assignment[w.id] == c]
            if members:
                centroids[c] = _centroid(members)

    manifolds = {mids[c]: centroids[c] for c in range(k)}
    host_pos = host if host is not None else _centroid(list(manifolds.values()))

    jumpers = sum(_dist((w.x, w.y), manifolds[mids[assignment[w.id]]]) for w in wells)
    flowlines = sum(_dist(pos, host_pos) for pos in manifolds.values())
    return LayoutSolution(
        manifolds=manifolds,
        assignment={w.id: mids[assignment[w.id]] for w in wells},
        host=host_pos,
        total_length_km=round(jumpers + flowlines, 6),
        n_manifolds=k,
    )


def naive_layout(
    wells: list[Well], host: tuple[float, float] | None = None
) -> LayoutSolution:
    """Baseline: a single manifold at the field centroid (no clustering)."""
    return optimize_layout(wells, n_manifolds=1, host=host)


def improvement_vs_naive(
    wells: list[Well], n_manifolds: int, host: tuple[float, float] | None = None
) -> float:
    """Fractional reduction in total length vs the single-manifold baseline."""
    base = naive_layout(wells, host=host).total_length_km
    opt = optimize_layout(wells, n_manifolds=n_manifolds, host=host).total_length_km
    if base == 0:
        return 0.0
    return round((base - opt) / base, 6)
