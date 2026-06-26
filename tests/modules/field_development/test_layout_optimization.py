# ABOUTME: Tests for subsea layout optimization (issue #579).
# ABOUTME: Clustering correctness, objective improvement vs naive, determinism.
"""Tests for ``worldenergydata.field_development.layout_optimization``."""

from __future__ import annotations

import math

from worldenergydata.field_development import (
    LayoutSolution,
    Well,
    improvement_vs_naive,
    naive_layout,
    optimize_layout,
)


def _two_clusters():
    # Cluster A near (0,0), cluster B near (10,10).
    return [
        Well("a1", 0.0, 0.0),
        Well("a2", 1.0, 0.0),
        Well("a3", 0.0, 1.0),
        Well("b1", 10.0, 10.0),
        Well("b2", 11.0, 10.0),
        Well("b3", 10.0, 11.0),
    ]


# --------------------------------------------------------------------------- #
# Clustering correctness
# --------------------------------------------------------------------------- #
def test_two_manifolds_separate_two_clusters():
    sol = optimize_layout(_two_clusters(), n_manifolds=2)
    assert sol.n_manifolds == 2
    # The three A-wells share one manifold, the three B-wells the other.
    a_mf = {sol.assignment[w] for w in ("a1", "a2", "a3")}
    b_mf = {sol.assignment[w] for w in ("b1", "b2", "b3")}
    assert len(a_mf) == 1 and len(b_mf) == 1 and a_mf != b_mf


def test_manifold_sits_at_cluster_centroid():
    sol = optimize_layout(_two_clusters(), n_manifolds=2)
    # Cluster A centroid is (1/3, 1/3); one manifold should be there.
    positions = list(sol.manifolds.values())
    assert any(
        math.isclose(p[0], 1 / 3, abs_tol=1e-6)
        and math.isclose(p[1], 1 / 3, abs_tol=1e-6)
        for p in positions
    )


def test_each_well_assigned_to_nearest_manifold():
    sol = optimize_layout(_two_clusters(), n_manifolds=2)
    for w in _two_clusters():
        assigned = sol.manifolds[sol.assignment[w.id]]
        nearest = min(
            sol.manifolds.values(), key=lambda p: math.hypot(w.x - p[0], w.y - p[1])
        )
        assert math.isclose(
            math.hypot(w.x - assigned[0], w.y - assigned[1]),
            math.hypot(w.x - nearest[0], w.y - nearest[1]),
        )


# --------------------------------------------------------------------------- #
# Objective: optimization beats the naive baseline
# --------------------------------------------------------------------------- #
def test_two_manifolds_reduce_total_length_vs_one():
    wells = _two_clusters()
    one = optimize_layout(wells, n_manifolds=1).total_length_km
    two = optimize_layout(wells, n_manifolds=2).total_length_km
    assert two < one


def test_improvement_vs_naive_positive_for_clustered_field():
    assert improvement_vs_naive(_two_clusters(), n_manifolds=2) > 0.0


def test_naive_is_single_manifold():
    sol = naive_layout(_two_clusters())
    assert sol.n_manifolds == 1
    assert len(set(sol.assignment.values())) == 1


# --------------------------------------------------------------------------- #
# Host handling
# --------------------------------------------------------------------------- #
def test_given_host_is_used():
    sol = optimize_layout(_two_clusters(), n_manifolds=2, host=(5.0, 50.0))
    assert sol.host == (5.0, 50.0)


def test_standalone_host_at_manifolds_centroid():
    sol = optimize_layout(_two_clusters(), n_manifolds=2)
    cx = sum(p[0] for p in sol.manifolds.values()) / len(sol.manifolds)
    cy = sum(p[1] for p in sol.manifolds.values()) / len(sol.manifolds)
    assert math.isclose(sol.host[0], cx) and math.isclose(sol.host[1], cy)


# --------------------------------------------------------------------------- #
# Robustness + determinism
# --------------------------------------------------------------------------- #
def test_empty_wells_is_graceful():
    sol = optimize_layout([], n_manifolds=3)
    assert isinstance(sol, LayoutSolution) and sol.n_manifolds == 0


def test_n_manifolds_capped_at_well_count():
    sol = optimize_layout([Well("a", 0, 0), Well("b", 1, 1)], n_manifolds=5)
    assert sol.n_manifolds == 2


def test_deterministic_same_wells_same_solution():
    wells = _two_clusters()
    a = optimize_layout(wells, n_manifolds=2)
    b = optimize_layout(wells, n_manifolds=2)
    assert a.manifolds == b.manifolds
    assert a.assignment == b.assignment
    assert a.total_length_km == b.total_length_km
