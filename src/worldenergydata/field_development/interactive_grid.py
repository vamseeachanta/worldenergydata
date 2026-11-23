# ABOUTME: Precomputed recommendation grid for the interactive HTML playbook.
# ABOUTME: Issue #644 (epic #567) — mesh recommend() offline; JS does nearest lookup.
"""
worldenergydata.field_development.interactive_grid
==================================================

The interactive playbook (issue #644) is a single static HTML file with **no
server and no CDN**: the recommendation engine cannot run in the browser, so it
is run *offline* over a parameter mesh and the results are embedded as JSON. The
client-side JS then snaps the user's slider values to the nearest grid point and
shows the precomputed recommendation — guaranteeing the browser shows exactly
what :func:`recommendation.recommend` would produce (no re-implementation in JS).

A :class:`Grid` covers one ``(region, fluid)`` combination over four numeric
axes — ``water_depth_m``, ``recoverable_reserves_mmboe``, ``distance_to_host_km``
(tieback), and ``num_wells``. Region and fluid are dropdowns in the UI; the build
script builds one grid per combination.

Why per-axis snapping is exact nearest-neighbour: the mesh is a *rectangular*
grid with independent axes, so the closest grid point under any axis-separable
distance is found by snapping each coordinate to its nearest axis value
independently. ``k=1`` lookup is therefore the true 1-NN.

Outcome cells are **deduplicated**: many mesh points share the same ranked
shortlist (rationale/warnings only change at threshold crossings), so the grid
stores a small table of unique cells plus an integer index — keeping the embedded
JSON small enough for a self-contained file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from worldenergydata.field_development.enums import FluidType
from worldenergydata.field_development.models import FieldConcept
from worldenergydata.field_development.recommendation import (
    CriteriaWeights,
    ScoredConcept,
    Thresholds,
    recommend,
)

# Default mesh axes. Chosen to bracket each concept's sweet-spot depth band and
# the engine's decision thresholds (tieback marginal = 50 MMboe, tieback pivot =
# 60 km, NUI max wells = 6) so the grid resolves the key transitions.
DEFAULT_DEPTHS: tuple[float, ...] = (
    0.0,
    100.0,
    300.0,
    600.0,
    900.0,
    1300.0,
    1500.0,
    1800.0,
    2200.0,
    2600.0,
    3000.0,
)
DEFAULT_RESERVES: tuple[float, ...] = (10.0, 50.0, 150.0, 400.0, 800.0)
DEFAULT_TIEBACKS: tuple[float, ...] = (0.0, 20.0, 60.0, 120.0, 200.0)
DEFAULT_WELLS: tuple[int, ...] = (1, 4, 8, 16, 30)

# How many ranked concepts to keep per cell (recommended + shortlist).
TOP_N = 3


@dataclass(frozen=True)
class Grid:
    """A precomputed recommendation mesh for one ``(region, fluid)`` pair.

    ``index`` is a 4-D nested list ``[depth][reserves][tieback][wells]`` of
    integer ids into ``cells`` (the deduplicated outcome table). Each cell is a
    dict ``{"top": [<scored concept dict>, ...]}`` with the top-``TOP_N`` ranked
    concepts (the first is the recommendation).
    """

    region: Optional[str]
    fluid: Optional[str]
    depths: tuple[float, ...]
    reserves: tuple[float, ...]
    tiebacks: tuple[float, ...]
    wells: tuple[int, ...]
    cells: list[dict] = field(default_factory=list)
    index: list = field(default_factory=list)


def _nearest_idx(axis: tuple[float, ...], value: float) -> int:
    """Index of the axis value closest to ``value`` (ties -> lower index)."""
    best_i = 0
    best_d = abs(axis[0] - value)
    for i in range(1, len(axis)):
        d = abs(axis[i] - value)
        if d < best_d:
            best_d, best_i = d, i
    return best_i


def _make_concept(
    region: Optional[str],
    fluid: Optional[FluidType],
    depth: float,
    reserves: float,
    tieback: float,
    wells: int,
) -> FieldConcept:
    """Build the :class:`FieldConcept` for one mesh point.

    A ``tieback`` of 0 means *no reachable host* (standalone field), so
    ``distance_to_host_km`` is left ``None`` — which makes the subsea-tieback
    concept infeasible, exactly as the engine intends. A positive tieback sets
    the distance and leaves host spare capacity unknown (treated as possible).
    """
    return FieldConcept(
        name="grid-point",
        region=region or None,
        fluid_type=fluid,
        water_depth_m=depth,
        recoverable_reserves_mmboe=reserves,
        distance_to_host_km=(tieback if tieback > 0 else None),
        num_wells=wells,
    )


def _scored_to_dict(s: ScoredConcept) -> dict:
    """Serialize one ranked concept to a compact, JSON-safe dict."""
    return {
        "concept": s.concept_type.value,
        "score": s.total_score,
        "tree": s.tree_type.value,
        "topology": s.topology.value if s.topology is not None else None,
        "processing": list(s.processing),
        "rationale": list(s.rationale),
        "warnings": list(s.warnings),
    }


def _cell_for(
    region: Optional[str],
    fluid: Optional[FluidType],
    depth: float,
    reserves: float,
    tieback: float,
    wells: int,
    weights: Optional[CriteriaWeights],
    thresholds: Optional[Thresholds],
) -> dict:
    """Run :func:`recommend` for one mesh point and build its outcome cell."""
    concept = _make_concept(region, fluid, depth, reserves, tieback, wells)
    scored = recommend(concept, weights=weights, thresholds=thresholds, top_n=TOP_N)
    return {"top": [_scored_to_dict(s) for s in scored]}


def build_recommendation_grid(
    region: Optional[str] = None,
    fluid: Optional[FluidType] = None,
    depths: tuple[float, ...] = DEFAULT_DEPTHS,
    reserves: tuple[float, ...] = DEFAULT_RESERVES,
    tiebacks: tuple[float, ...] = DEFAULT_TIEBACKS,
    wells: tuple[int, ...] = DEFAULT_WELLS,
    weights: Optional[CriteriaWeights] = None,
    thresholds: Optional[Thresholds] = None,
) -> Grid:
    """Precompute the recommendation mesh for one ``(region, fluid)`` pair.

    Runs :func:`recommend` over the cartesian product of the four numeric axes,
    deduplicating identical outcome cells. The result is fully deterministic:
    the same arguments always yield byte-identical :func:`export_grid_json`.

    Args:
        region: Region/country string fed to the basin prior (``None`` = unknown).
        fluid: Reservoir fluid (affects the processing overlay, not the ranking).
        depths, reserves, tiebacks, wells: Sorted-ascending mesh axes.
        weights, thresholds: Engine overrides (defaults match :func:`recommend`).

    Returns:
        A :class:`Grid` with a deduplicated ``cells`` table and a 4-D ``index``.
    """
    cells: list[dict] = []
    cell_ids: dict[str, int] = {}
    index: list = []

    for d in depths:
        d_block = []
        for r in reserves:
            r_block = []
            for t in tiebacks:
                t_block = []
                for w in wells:
                    cell = _cell_for(region, fluid, d, r, t, w, weights, thresholds)
                    key = json.dumps(cell, sort_keys=True, separators=(",", ":"))
                    cid = cell_ids.get(key)
                    if cid is None:
                        cid = len(cells)
                        cell_ids[key] = cid
                        cells.append(cell)
                    t_block.append(cid)
                r_block.append(t_block)
            d_block.append(r_block)
        index.append(d_block)

    return Grid(
        region=region or None,
        fluid=fluid.value if isinstance(fluid, FluidType) else fluid,
        depths=tuple(depths),
        reserves=tuple(reserves),
        tiebacks=tuple(tiebacks),
        wells=tuple(wells),
        cells=cells,
        index=index,
    )


def interpolate_nearest_recommendation(
    grid: Grid,
    depth: float,
    reserves: float,
    tieback: float,
    wells: float,
    k: int = 1,
) -> dict:
    """Look up the recommendation for arbitrary inputs by nearest grid point.

    For a rectangular grid the 1-nearest neighbour is the per-axis nearest value,
    so ``k=1`` is exact. Only ``k=1`` is implemented (the playbook snaps to the
    grid); ``k>1`` averaging is intentionally out of scope.

    Args:
        grid: A :class:`Grid` from :func:`build_recommendation_grid`.
        depth, reserves, tieback, wells: Query coordinates.
        k: Number of neighbours; must be 1.

    Returns:
        The outcome cell dict ``{"top": [...]}`` at the nearest grid point.
    """
    if k != 1:
        raise NotImplementedError("only k=1 (nearest-point) lookup is supported")
    di = _nearest_idx(grid.depths, depth)
    ri = _nearest_idx(grid.reserves, reserves)
    ti = _nearest_idx(grid.tiebacks, tieback)
    wi = _nearest_idx(tuple(float(x) for x in grid.wells), float(wells))
    return grid.cells[grid.index[di][ri][ti][wi]]


def grid_to_dict(grid: Grid) -> dict:
    """Plain-dict view of a grid (axes + deduped cells + integer index)."""
    return {
        "region": grid.region,
        "fluid": grid.fluid,
        "axes": {
            "depth": list(grid.depths),
            "reserves": list(grid.reserves),
            "tieback": list(grid.tiebacks),
            "wells": list(grid.wells),
        },
        "cells": grid.cells,
        "index": grid.index,
    }


def export_grid_json(grid: Grid) -> str:
    """Serialize a grid to compact, deterministic JSON (stable byte output)."""
    return json.dumps(grid_to_dict(grid), sort_keys=True, separators=(",", ":"))
