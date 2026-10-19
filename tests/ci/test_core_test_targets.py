"""Core/auxiliary selection contracts from issue #466 (2026 update).

Expected target sets are enumerated independently from the selector: a shared
change selects each unit domain and cross-cutting suite, retains reporting
contracts, and leaves broad integration/performance runs to main and nightly.
No runtime or speedup threshold is inferred from these routing tests.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ci"))

from select_test_targets import select, to_matrix


@pytest.fixture
def tree(tmp_path):
    """Independent fixture: each listed directory contains a real test file."""
    for target in (
        "tests/unit/core",
        "tests/unit/common",
        "tests/unit/example",
        "tests/contracts",
        "tests/workflows",
        "tests/governance",
        "tests/integration/reporting",
        "tests/integration/modules/example",
        "tests/performance",
        "tests/ci",
    ):
        directory = tmp_path / target
        directory.mkdir(parents=True)
        (directory / "test_sample.py").write_text("def test_sample(): pass\n")
    return tmp_path


def targets(matrix):
    return {
        target for shard in matrix["include"] for target in shard["targets"].split()
    }


def test_shared_change_core_flat_targets(tree):
    result = select(["pyproject.toml"], tree, tier="core")
    assert result == {
        "scope": "full",
        "xdist": [
            "tests/ci",
            "tests/contracts",
            "tests/governance",
            "tests/unit",
            "tests/workflows",
            "tests/integration/reporting",
        ],
        "seq": [],
    }


def test_shared_change_core_matrix_keeps_all_unit_domains_and_smoke(tree):
    matrix = to_matrix(["pyproject.toml"], tree, tier="core")
    assert matrix["scope"] == "full"
    assert targets(matrix) == {
        "tests/unit/core",
        "tests/unit/common",
        "tests/unit/example",
        "tests/contracts",
        "tests/workflows",
        "tests/governance",
        "tests/ci",
        "tests/integration/reporting",
    }
    assert all(shard["mode"] == "xdist" for shard in matrix["include"])


@pytest.mark.parametrize(
    "changed",
    [
        ["README.md"],
        ["src/worldenergydata/example/api.py"],
        ["tests/integration/modules/example/test_api.py"],
        ["tests/performance/test_budget.py"],
    ],
)
def test_scoped_core_excludes_auxiliary_targets_but_keeps_reporting(tree, changed):
    matrix = to_matrix(changed, tree, tier="core")
    expected = {
        "tests/unit/core",
        "tests/unit/common",
        "tests/contracts",
        "tests/workflows",
        "tests/governance",
        "tests/integration/reporting",
    }
    if changed == ["src/worldenergydata/example/api.py"]:
        expected.add("tests/unit/example")
    assert targets(matrix) == expected
    assert select(changed, tree, tier="core")["seq"] == []


def test_full_tier_preserves_auxiliary_targets(tree):
    assert select(["pyproject.toml"], tree, tier="full")["seq"] == [
        "tests/integration",
        "tests/performance",
    ]
    assert targets(to_matrix(["pyproject.toml"], tree, tier="full")) == {
        "tests/unit/core",
        "tests/unit/common",
        "tests/unit/example",
        "tests/contracts",
        "tests/workflows",
        "tests/governance",
        "tests/ci",
        "tests/integration",
        "tests/performance",
    }
    assert to_matrix(["pyproject.toml"], tree) == to_matrix(
        ["pyproject.toml"], tree, tier="full"
    )


def test_core_keeps_root_tests_and_other_parallel_suites(tree):
    """Hand-enumerated extra parallel targets must remain in both tiers."""
    (tree / "tests/test_guard.py").write_text("def test_guard(): pass\n")
    modules = tree / "tests/modules"
    modules.mkdir()
    (modules / "test_legacy_contract.py").write_text("def test_contract(): pass\n")
    for tier in ("core", "full"):
        selected = targets(to_matrix(["pyproject.toml"], tree, tier=tier))
        assert {"tests/test_guard.py", "tests/modules"} <= selected


def test_ci_test_edits_select_their_own_regressions(tree):
    matrix = to_matrix(["tests/ci/test_core_test_targets.py"], tree, tier="core")
    assert matrix["scope"] == "modules"
    assert "tests/ci" in targets(matrix)


def test_unknown_tier_fails_closed(tree):
    with pytest.raises(ValueError, match="tier"):
        select(["README.md"], tree, tier="unknown")
    with pytest.raises(ValueError, match="tier"):
        to_matrix(["README.md"], tree, tier="unknown")


@pytest.mark.parametrize("matrix", [False, True])
@pytest.mark.parametrize("requested_tier", [[], ["--tier", "full"]])
def test_reusable_workflow_adapter_uses_core_tier(tree, matrix, requested_tier):
    command = [
        sys.executable,
        str(REPO_ROOT / "scripts/ci/select_core_test_targets.py"),
        "--root",
        str(tree),
        "--files-from",
        "-",
        *requested_tier,
    ]
    if matrix:
        command.append("--emit-matrix")
    result = subprocess.run(
        command, input="pyproject.toml\n", text=True, capture_output=True, check=True
    )
    output = dict(line.split("=", 1) for line in result.stdout.splitlines())
    assert output["scope"] == "full"
    if matrix:
        selected = targets(json.loads(output["matrix"]))
    else:
        assert output["seq_targets"] == ""
        selected = set(output["xdist_targets"].split())
    assert "tests/integration/reporting" in selected
    assert "tests/integration" not in selected
    assert "tests/performance" not in selected


def test_pr_caller_opts_in_without_changing_auxiliary_commands():
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())
    assert workflow["jobs"]["domain-tests"]["with"]["selector"] == (
        "scripts/ci/select_core_test_targets.py"
    )
    full = workflow["jobs"]["test"]
    assert "github.event_name == 'push'" in full["if"]
    assert "github.event_name == 'schedule'" in full["if"]
    assert "tests/integration tests/performance" in next(
        step["run"]
        for step in full["steps"]
        if step["name"].startswith("Run sequential")
    )
