"""Synthetic, hand-checkable examples for the depth slice of issue 1090.

Fixture basis (independent of the resolver): (1, 1) lies inside the regional
box [-2, 2] on both axes; (3, 1) lies outside it and inside the global box.
Selection copies the declared 120.5 m or 900.0 m without arithmetic. All
other numeric literals deliberately exercise zero, invalid values or box
edges; none represents a measured site or a source ranking.
"""

from copy import deepcopy
from typing import Any

import pytest

from worldenergydata.field_development.site_environment import resolve_depth


@pytest.fixture
def regional() -> dict[str, Any]:
    return {
        "depth_m": 120.5,
        "units": "m",
        "source_id": "synthetic-regional",
        "source_url": "https://example.org/regional-depth",
        "vintage": "synthetic-regional-release",
        "coverage": (-2.0, -2.0, 2.0, 2.0),
    }


@pytest.fixture
def global_depth() -> dict[str, Any]:
    return {
        "depth_m": 900.0,
        "units": "m",
        "source_id": "synthetic-global",
        "source_url": "https://example.org/global-depth",
        "vintage": "synthetic-global-release",
        "coverage": (-180.0, -90.0, 180.0, 90.0),
    }


def test_regional_depth_precedes_global(regional, global_depth) -> None:
    before = deepcopy([global_depth, regional])
    result = resolve_depth(
        "synthetic-field",
        1.0,
        1.0,
        ("synthetic-regional", "synthetic-global"),
        [global_depth, regional],
    )
    assert result.field_id == "synthetic-field"
    assert (result.longitude, result.latitude) == (1.0, 1.0)
    assert result.depth_m == 120.5
    assert result.candidate == {
        "depth_m": 120.5,
        "units": "m",
        "source_id": "synthetic-regional",
        "source_url": "https://example.org/regional-depth",
        "vintage": "synthetic-regional-release",
        "coverage": (-2.0, -2.0, 2.0, 2.0),
    }
    assert result.candidate is regional
    assert result.reason is None
    assert [global_depth, regional] == before


def test_uncovered_regional_depth_uses_global(regional, global_depth) -> None:
    result = resolve_depth(
        "synthetic-field",
        3.0,
        1.0,
        ("synthetic-regional", "synthetic-global"),
        [regional, global_depth],
    )
    assert result.depth_m == 900.0
    assert result.candidate == {
        "depth_m": 900.0,
        "units": "m",
        "source_id": "synthetic-global",
        "source_url": "https://example.org/global-depth",
        "vintage": "synthetic-global-release",
        "coverage": (-180.0, -90.0, 180.0, 90.0),
    }
    assert result.reason is None


def test_source_preference_is_caller_policy(regional, global_depth) -> None:
    result = resolve_depth(
        "synthetic-field",
        1.0,
        1.0,
        ("synthetic-global", "synthetic-regional"),
        iter([regional, global_depth]),
    )
    assert result.depth_m == 900.0
    assert result.candidate is global_depth


@pytest.mark.parametrize(
    "patch",
    [
        {"depth_m": None},
        {"depth_m": float("nan")},
        {"depth_m": float("inf")},
        {"depth_m": -float("inf")},
        {"depth_m": -1.0},
        {"depth_m": True},
        {"depth_m": "120.5"},
        {"units": "ft"},
        {"source_id": None},
        {"source_id": ""},
        {"source_id": "not-preferred"},
        {"source_url": None},
        {"source_url": "   "},
        {"source_url": "not-a-url"},
        {"source_url": "https:// "},
        {"source_url": "https://example.org/has space"},
        {"source_url": "file:///depth"},
        {"source_url": "https://[invalid"},
        {"vintage": None},
        {"vintage": "   "},
        {"coverage": None},
        {"coverage": (3.0, 3.0, 4.0, 4.0)},
        {"coverage": (2.0, -2.0, -2.0, 2.0)},
        {"coverage": (-2.0, 2.0, 2.0, -2.0)},
        {"coverage": (-2.0, -2.0, 2.0)},
        {"coverage": (-181.0, -2.0, 2.0, 2.0)},
        {"coverage": (-2.0, -91.0, 2.0, 2.0)},
        {"coverage": (-2.0, -2.0, float("nan"), 2.0)},
        {"coverage": (-2.0, -2.0, float("inf"), 2.0)},
        {"coverage": (-2.0, -2.0, True, 2.0)},
    ],
)
def test_unqualified_candidates_return_unknown(regional, patch) -> None:
    regional.update(patch)
    result = resolve_depth(
        "synthetic-field", 1.0, 1.0, ("synthetic-regional",), [regional]
    )
    assert result.depth_m is None
    assert result.candidate is None
    assert result.reason
    assert result.field_id == "synthetic-field"


@pytest.mark.parametrize(
    "missing", ("depth_m", "units", "source_id", "source_url", "vintage", "coverage")
)
def test_missing_evidence_returns_unknown(regional, missing) -> None:
    del regional[missing]
    result = resolve_depth(
        "synthetic-field", 1.0, 1.0, ("synthetic-regional",), [regional]
    )
    assert result.depth_m is None
    assert result.candidate is None
    assert result.reason


def test_unqualified_preferred_candidate_falls_back(regional, global_depth) -> None:
    regional["vintage"] = None
    result = resolve_depth(
        "synthetic-field",
        1.0,
        1.0,
        ("synthetic-regional", "synthetic-global"),
        [regional, global_depth],
    )
    assert result.depth_m == 900.0
    assert result.candidate is global_depth


def test_no_available_candidates_returns_unknown() -> None:
    result = resolve_depth("synthetic-field", 1.0, 1.0, ("synthetic-regional",), [])
    assert result.depth_m is None
    assert result.candidate is None
    assert result.reason


def test_empty_preference_returns_unknown(regional) -> None:
    result = resolve_depth("synthetic-field", 1.0, 1.0, (), [regional])
    assert result.depth_m is None
    assert result.candidate is None
    assert result.reason


def test_zero_is_a_known_depth(regional) -> None:
    regional["depth_m"] = 0.0
    result = resolve_depth(
        "synthetic-field", 1.0, 1.0, ("synthetic-regional",), [regional]
    )
    assert result.depth_m == 0.0
    assert result.candidate is regional
    assert result.reason is None


@pytest.mark.parametrize("duplicate_depth", [120.5, None])
def test_duplicate_source_is_rejected(regional, duplicate_depth) -> None:
    duplicate = dict(regional, depth_m=duplicate_depth)
    with pytest.raises(ValueError, match="duplicate.*source"):
        resolve_depth(
            "synthetic-field",
            1.0,
            1.0,
            ("synthetic-regional",),
            [regional, duplicate],
        )


def test_lower_priority_duplicate_is_rejected(regional, global_depth) -> None:
    with pytest.raises(ValueError, match="duplicate.*source"):
        resolve_depth(
            "synthetic-field",
            1.0,
            1.0,
            ("synthetic-regional", "synthetic-global"),
            [regional, global_depth, dict(global_depth)],
        )


def test_unpreferred_duplicate_does_not_override_policy(regional, global_depth) -> None:
    result = resolve_depth(
        "synthetic-field",
        1.0,
        1.0,
        ("synthetic-global",),
        [regional, dict(regional), global_depth],
    )
    assert result.depth_m == 900.0
    assert result.candidate is global_depth


@pytest.mark.parametrize("point", [(-2.0, -2.0), (-2.0, 2.0), (2.0, -2.0), (2.0, 2.0)])
def test_declared_coverage_includes_edges(regional, point) -> None:
    result = resolve_depth(
        "synthetic-field", *point, ("synthetic-regional",), [regional]
    )
    assert result.depth_m == 120.5
    assert result.candidate is regional


@pytest.mark.parametrize(
    "point",
    [(float("nan"), 1.0), (1.0, float("inf")), (181.0, 1.0), (1.0, 91.0), (True, 1.0)],
)
def test_invalid_coordinates_are_rejected(point) -> None:
    with pytest.raises(ValueError, match="coordinates"):
        resolve_depth("synthetic-field", *point, (), [])


@pytest.mark.parametrize("field_id", [None, "", "   "])
def test_missing_field_identity_is_rejected(field_id) -> None:
    with pytest.raises(ValueError, match="field_id"):
        resolve_depth(field_id, 1.0, 1.0, (), [])


@pytest.mark.parametrize(
    "preference", ["synthetic-regional", ("",), (None,), ("same", "same")]
)
def test_invalid_source_policy_is_rejected(preference) -> None:
    with pytest.raises(ValueError, match="source_preference"):
        resolve_depth("synthetic-field", 1.0, 1.0, preference, [])


def test_additional_provenance_is_preserved(regional) -> None:
    regional["citation"] = {"note": "synthetic example only"}
    before = deepcopy(regional)
    result = resolve_depth(
        "synthetic-field", 1.0, 1.0, ("synthetic-regional",), [regional]
    )
    assert result.candidate == before
    assert regional == before
