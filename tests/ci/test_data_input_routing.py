"""Data-only edits must select the tests that own the tracked inputs."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ci"))

from select_test_targets import (  # noqa: E402
    ALWAYS_XDIST,
    select,
    select_fast,
    to_matrix,
)

WITHHELD_CONTRACT = "tests/modules/field_development/test_withheld_data.py"
MODES = ("select", "select_fast", "matrix", "matrix_fast")
INPUT_ROUTES = [
    pytest.param(
        "data/modules/cost/curated/sanctioned_projects.csv",
        ("tests/unit/cost",),
        id="cost-curated",
    ),
    pytest.param(
        "data/modules/cost/staging/europe-2016-2026.csv",
        ("tests/unit/cost",),
        id="cost-staging",
    ),
    pytest.param(
        "data/modules/facility_specs/curated/mooring_facility_matrix.csv",
        (WITHHELD_CONTRACT,),
        id="facility-metadata-and-availability",
    ),
    pytest.param(
        "data/modules/frontier_basins/curated/frontier_discoveries.csv",
        ("tests/unit/canada",),
        id="frontier-discoveries",
    ),
    pytest.param(
        "data/modules/offshore_assets/curated/lt_reserves_discovery.csv",
        ("tests/unit/field_development", WITHHELD_CONTRACT),
        id="offshore-assets",
    ),
    pytest.param(
        "data/modules/subsea/curated/rigid_jumper_specs.csv",
        ("tests/unit/subsea", "tests/unit/curated"),
        id="subsea",
    ),
    pytest.param(
        "packages/worldenergydata-lng_terminals/src/worldenergydata/"
        "lng_terminals/_data/curated/terminals_seed.csv",
        ("tests/unit/lng_terminals",),
        id="package-lng",
    ),
    pytest.param(
        "packages/worldenergydata-vessel_fleet/src/worldenergydata/"
        "vessel_fleet/_data/curated/construction_evidence.json",
        ("tests/unit/vessel_fleet",),
        id="package-vessel-fleet",
    ),
]


def _selection(changed, mode):
    if mode in ("select", "select_fast"):
        chooser = select_fast if mode == "select_fast" else select
        return chooser(changed, REPO_ROOT)
    matrix = to_matrix(changed, REPO_ROOT, fast=mode == "matrix_fast")
    shards = matrix["include"]
    assert len({shard["name"] for shard in shards}) == len(shards)
    assert all(shard["mode"] == "xdist" for shard in shards)
    return {
        "scope": matrix["scope"],
        "xdist": [target for shard in shards for target in shard["targets"].split()],
        "seq": [],
    }


def _assert_targets(result, expected, scope="modules"):
    assert result["scope"] == scope
    assert result["seq"] == []
    targets = result["xdist"]
    assert set(targets) == set(ALWAYS_XDIST) | set(expected)
    assert len(targets) == len(set(targets))
    assert all((REPO_ROOT / target).exists() for target in targets)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("input_path,expected", INPUT_ROUTES)
def test_tracked_data_only_edit_selects_owning_tests(input_path, expected, mode):
    assert (REPO_ROOT / input_path).is_file()
    _assert_targets(_selection([input_path], mode), expected)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("data_first", [False, True])
@pytest.mark.parametrize("edit_kind", ["source", "test"])
@pytest.mark.parametrize(
    "input_path,source_path,test_path,owner,contracts",
    [
        pytest.param(
            "data/modules/subsea/curated/rigid_jumper_specs.csv",
            "packages/worldenergydata-subsea/src/worldenergydata/subsea/"
            "models/rigid_jumper.py",
            "tests/unit/subsea/test_manifold_suppliers.py",
            "tests/unit/subsea",
            ("tests/unit/curated",),
            id="subsea",
        ),
        pytest.param(
            "data/modules/frontier_basins/curated/frontier_discoveries.csv",
            "packages/worldenergydata-canada/src/worldenergydata/canada/"
            "emerging_basins/discoveries.py",
            "tests/unit/canada/emerging_basins/test_frontier_discoveries.py",
            "tests/unit/canada",
            (),
            id="canada",
        ),
        pytest.param(
            "data/modules/offshore_assets/curated/lt_reserves_discovery.csv",
            "src/worldenergydata/field_development/subseaiq.py",
            "tests/unit/field_development/test_lt_reserves_discovery.py",
            "tests/unit/field_development",
            (WITHHELD_CONTRACT,),
            id="field-development",
        ),
    ],
)
def test_data_contracts_preserve_source_and_test_owner(
    input_path, source_path, test_path, owner, contracts, edit_kind, data_first, mode
):
    code_path = source_path if edit_kind == "source" else test_path
    assert (REPO_ROOT / code_path).is_file()
    _assert_targets(_selection([code_path], mode), (owner,))
    changed = [input_path, code_path] if data_first else [code_path, input_path]
    _assert_targets(_selection(changed, mode), (owner, *contracts))


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "domain", ["cost", "facility_specs", "frontier_basins", "offshore_assets", "subsea"]
)
@pytest.mark.parametrize("suffix", [".csv", "_archive/curated/example.csv"])
def test_data_prefix_routes_require_directory_boundary(domain, suffix, mode):
    # Synthetic strings only: these near-prefix paths are not repository inputs.
    changed = [f"data/modules/{domain}{suffix}"]
    _assert_targets(_selection(changed, mode), (), scope="skip")


@pytest.mark.parametrize("mode", MODES)
def test_combined_data_edits_select_union_without_duplicate_shards(mode):
    changed = [case.values[0] for case in INPUT_ROUTES]
    _assert_targets(
        _selection(changed, mode),
        (
            "tests/unit/cost",
            WITHHELD_CONTRACT,
            "tests/unit/canada",
            "tests/unit/field_development",
            "tests/unit/subsea",
            "tests/unit/curated",
            "tests/unit/lng_terminals",
            "tests/unit/vessel_fleet",
        ),
    )
