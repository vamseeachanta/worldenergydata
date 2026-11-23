# ABOUTME: Tests for the precomputed recommendation grid (issue #644).
# ABOUTME: Determinism, coverage, validator bounds, exact-match == recommend().
"""Tests for ``worldenergydata.field_development.interactive_grid``."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

from worldenergydata.field_development.enums import ConceptType, FluidType
from worldenergydata.field_development.interactive_grid import (
    DEFAULT_DEPTHS,
    DEFAULT_RESERVES,
    DEFAULT_TIEBACKS,
    DEFAULT_WELLS,
    build_recommendation_grid,
    export_grid_json,
    interpolate_nearest_recommendation,
)
from worldenergydata.field_development.models import FieldConcept
from worldenergydata.field_development.recommendation import recommend

_BUILD = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "field_development"
    / "build_interactive_playbook.py"
)


def _load_build_module():
    spec = importlib.util.spec_from_file_location("build_playbook", _BUILD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
def test_grid_build_is_deterministic_bytes():
    a = export_grid_json(build_recommendation_grid(region="us", fluid=FluidType.OIL))
    b = export_grid_json(build_recommendation_grid(region="us", fluid=FluidType.OIL))
    assert a == b


def test_exported_json_parses_and_has_shape():
    grid = build_recommendation_grid(region="us", fluid=FluidType.OIL)
    doc = json.loads(export_grid_json(grid))
    assert set(doc) == {"region", "fluid", "axes", "cells", "index"}
    assert set(doc["axes"]) == {"depth", "reserves", "tieback", "wells"}
    # index is 4-D with the axis lengths.
    assert len(doc["index"]) == len(DEFAULT_DEPTHS)
    assert len(doc["index"][0]) == len(DEFAULT_RESERVES)
    assert len(doc["index"][0][0]) == len(DEFAULT_TIEBACKS)
    assert len(doc["index"][0][0][0]) == len(DEFAULT_WELLS)


def test_cells_are_deduplicated():
    grid = build_recommendation_grid(region="us", fluid=FluidType.OIL)
    n_points = (
        len(DEFAULT_DEPTHS)
        * len(DEFAULT_RESERVES)
        * len(DEFAULT_TIEBACKS)
        * len(DEFAULT_WELLS)
    )
    # Dedup must collapse the mesh well below the raw point count.
    assert len(grid.cells) < n_points
    # Every index entry references a real cell.
    for d_block in grid.index:
        for r_block in d_block:
            for t_block in r_block:
                for cid in t_block:
                    assert 0 <= cid < len(grid.cells)


# --------------------------------------------------------------------------- #
# Coverage — the grid's recommendations span the depth-banded archetypes
# --------------------------------------------------------------------------- #
def _recommended_concepts(grid) -> set[str]:
    return {cell["top"][0]["concept"] for cell in grid.cells if cell["top"]}


def test_shallow_recommends_fixed_jacket():
    grid = build_recommendation_grid(region="us", fluid=FluidType.OIL)
    # Shallow water, scale beyond NUI's niche -> fixed jacket.
    cell = interpolate_nearest_recommendation(
        grid, depth=80.0, reserves=150.0, tieback=0.0, wells=8
    )
    assert cell["top"][0]["concept"] == ConceptType.FIXED_JACKET.value


def test_ultradeep_floater_family_covered():
    grid = build_recommendation_grid(region="us", fluid=FluidType.OIL)
    recs = _recommended_concepts(grid)
    # A GoM grid must surface the moored-floater family across its depth range.
    assert ConceptType.SPAR.value in recs
    assert recs & {
        ConceptType.SEMISUB_FPS.value,
        ConceptType.SPAR.value,
        ConceptType.TLP.value,
    }


def test_grid_covers_multiple_distinct_concepts():
    grid = build_recommendation_grid(region="us", fluid=FluidType.OIL)
    assert len(_recommended_concepts(grid)) >= 3


# --------------------------------------------------------------------------- #
# Exact-match lookup == recommend()
# --------------------------------------------------------------------------- #
def test_exact_match_lookup_equals_recommend():
    region, fluid = "us", FluidType.OIL
    grid = build_recommendation_grid(region=region, fluid=fluid)
    depth, reserves, tieback, wells = 1300.0, 400.0, 60.0, 8
    cell = interpolate_nearest_recommendation(grid, depth, reserves, tieback, wells)
    direct = recommend(
        FieldConcept(
            name="x",
            region=region,
            fluid_type=fluid,
            water_depth_m=depth,
            recoverable_reserves_mmboe=reserves,
            distance_to_host_km=tieback,
            num_wells=wells,
        ),
        top_n=3,
    )
    assert cell["top"][0]["concept"] == direct[0].concept_type.value
    assert cell["top"][0]["score"] == direct[0].total_score
    assert [c["concept"] for c in cell["top"]] == [s.concept_type.value for s in direct]


def test_tieback_zero_excludes_subsea_tieback():
    grid = build_recommendation_grid(region="us", fluid=FluidType.OIL)
    # No reachable host -> subsea tieback is infeasible at that point.
    cell = interpolate_nearest_recommendation(
        grid, depth=1300.0, reserves=50.0, tieback=0.0, wells=4
    )
    concepts = {c["concept"] for c in cell["top"]}
    assert ConceptType.SUBSEA_TIEBACK.value not in concepts


# --------------------------------------------------------------------------- #
# Bounds respect the FieldConcept validators
# --------------------------------------------------------------------------- #
def test_default_axes_are_within_validator_bounds():
    # Building the default grid must never raise a FieldConcept ValidationError.
    grid = build_recommendation_grid(region="brazil", fluid=FluidType.GAS)
    assert grid.cells  # non-empty


def test_axes_are_non_negative():
    for axis in (DEFAULT_DEPTHS, DEFAULT_RESERVES, DEFAULT_TIEBACKS):
        assert all(v >= 0 for v in axis)
    assert all(w >= 1 for w in DEFAULT_WELLS)


# --------------------------------------------------------------------------- #
# Nearest-neighbour edge cases
# --------------------------------------------------------------------------- #
def test_lookup_snaps_out_of_range_to_endpoints():
    grid = build_recommendation_grid(region="us", fluid=FluidType.OIL)
    lo = interpolate_nearest_recommendation(grid, -500, -10, -10, 0)
    hi = interpolate_nearest_recommendation(grid, 99999, 99999, 99999, 99999)
    # Snaps to the corner grid points (== exact recommend at those corners).
    assert lo == interpolate_nearest_recommendation(
        grid,
        DEFAULT_DEPTHS[0],
        DEFAULT_RESERVES[0],
        DEFAULT_TIEBACKS[0],
        DEFAULT_WELLS[0],
    )
    assert hi == interpolate_nearest_recommendation(
        grid,
        DEFAULT_DEPTHS[-1],
        DEFAULT_RESERVES[-1],
        DEFAULT_TIEBACKS[-1],
        DEFAULT_WELLS[-1],
    )


def test_k_greater_than_one_not_implemented():
    grid = build_recommendation_grid(region="us", fluid=FluidType.OIL)
    with pytest.raises(NotImplementedError):
        interpolate_nearest_recommendation(grid, 1000, 100, 30, 8, k=2)


# --------------------------------------------------------------------------- #
# Integration — the playbook HTML builds and its embedded JSON is valid
# --------------------------------------------------------------------------- #
def test_playbook_html_builds(tmp_path, monkeypatch):
    mod = _load_build_module()
    out = tmp_path / "playbook.html"
    monkeypatch.setattr(mod, "OUT", out)
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")
    path = mod.main()
    assert path.exists()
    html = path.read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>")
    assert path.stat().st_size < 5 * 1024 * 1024  # under the 5 MB cap


def test_embedded_json_blocks_parse():
    mod = _load_build_module()
    html = mod.render_html()
    for block_id in ("grids", "svgs", "labels"):
        m = re.search(
            rf'<script type="application/json" id="{block_id}">(.*?)</script>',
            html,
            re.DOTALL,
        )
        assert m, f"missing embedded block {block_id}"
        # The embed escapes '<' as \\u003c; JSON.parse / json.loads handle it.
        doc = json.loads(m.group(1))
        assert doc
    # A real grid is reachable in the embedded structure.
    grids = json.loads(
        re.search(
            r'<script type="application/json" id="grids">(.*?)</script>',
            html,
            re.DOTALL,
        ).group(1)
    )
    assert grids["us"]["oil"]["axes"]["depth"]


def test_html_is_deterministic_with_pinned_date(monkeypatch):
    mod = _load_build_module()
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")
    assert mod.render_html() == mod.render_html()


def test_fluid_does_not_change_ranking():
    # Fluid only drives the processing overlay, never the concept ranking.
    oil = build_recommendation_grid(region="us", fluid=FluidType.OIL)
    gas = build_recommendation_grid(region="us", fluid=FluidType.GAS)
    oil_recs = [
        [c["concept"] for c in cell["top"]]
        for cell in (
            interpolate_nearest_recommendation(oil, d, 150, 60, 8)
            for d in DEFAULT_DEPTHS
        )
    ]
    gas_recs = [
        [c["concept"] for c in cell["top"]]
        for cell in (
            interpolate_nearest_recommendation(gas, d, 150, 60, 8)
            for d in DEFAULT_DEPTHS
        )
    ]
    assert oil_recs == gas_recs
