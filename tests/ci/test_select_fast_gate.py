# ABOUTME: PR fast gate (28 Oct 2026): core paths no longer fan out the whole tree on PRs.
# ABOUTME: Push and dispatch keep the full fan-out; quarantine parsing matches the conftest.

"""Tests for the fast-gate mode of scripts/ci/select_test_targets.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SELECTOR = REPO_ROOT / "scripts" / "ci" / "select_test_targets.py"
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ci"))

from select_test_targets import (  # noqa: E402
    ALWAYS_XDIST,
    is_fast_gate,
    select,
    select_fast,
    to_matrix,
)


@pytest.mark.parametrize(
    "path", ["pyproject.toml", "uv.lock", "tests/conftest.py", "src/worldenergydata/engine.py"]
)
def test_core_change_on_pr_runs_always_on_set_not_full_tree(path):
    assert select([path], REPO_ROOT)["scope"] == "full"
    r = select_fast([path], REPO_ROOT)
    assert r["scope"] == "modules"
    assert r["xdist"] == [t for t in ALWAYS_XDIST if (REPO_ROOT / t).exists()]
    assert r["seq"] == []


@pytest.mark.parametrize(
    "path", ["scripts/ci/select_test_targets.py", ".github/workflows/ci.yml"]
)
def test_ci_tooling_change_on_pr_runs_ci_contract_suite(path):
    r = select_fast([path], REPO_ROOT)
    assert r["scope"] == "modules"
    assert "tests/ci" in r["xdist"]
    m = to_matrix([path], REPO_ROOT, fast=True)
    assert [s["name"] for s in m["include"]] == ["_always", "ci"]


def test_core_plus_module_change_keeps_the_module_shard():
    m = to_matrix(
        ["pyproject.toml", "src/worldenergydata/hse/grounding.py"], REPO_ROOT, fast=True
    )
    assert m["scope"] == "modules"
    assert [s["name"] for s in m["include"]] == ["_always", "unit-hse"]


def test_non_core_selection_is_identical_in_both_modes():
    for paths in (
        ["src/worldenergydata/hse/grounding.py"],
        ["README.md"],
        ["config/repo_structure.yml"],
        ["tests/integration/modules/bsee/test_x.py"],
    ):
        assert select_fast(paths, REPO_ROOT) == select(paths, REPO_ROOT)


def test_full_fan_out_is_kept_outside_pull_requests():
    m = to_matrix(["uv.lock"], REPO_ROOT)
    assert m["scope"] == "full"
    assert len(m["include"]) > 10


@pytest.mark.parametrize(
    "event,expected",
    [("pull_request", True), ("push", False), ("workflow_dispatch", False), (None, False)],
)
def test_fast_gate_follows_the_event(event, expected):
    environ = {} if event is None else {"GITHUB_EVENT_NAME": event}
    assert is_fast_gate(environ) is expected


@pytest.mark.parametrize("event,scope", [("pull_request", "modules"), ("push", "full")])
def test_cli_emits_fast_matrix_for_pull_requests(tmp_path, event, scope):
    changed = tmp_path / "changed.txt"
    changed.write_text("uv.lock\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SELECTOR), "--emit-matrix", "--files-from", str(changed)],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "GITHUB_EVENT_NAME": event},
    )
    lines = dict(line.split("=", 1) for line in result.stdout.splitlines())
    assert lines["scope"] == scope
    assert json.loads(lines["matrix"])["include"]


def test_quarantine_file_parses_with_reasons_and_deselects():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "wed_tests_conftest", REPO_ROOT / "tests" / "conftest.py"
    )
    conftest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(conftest)
    entries = conftest._load_quarantine()
    assert entries, "scripts/ci/quarantine.txt parsed to nothing"
    for node_id, (reason, _deselect) in entries.items():
        assert node_id.startswith("tests/") and "::" in node_id, node_id
        assert reason.startswith("quarantined: ") and len(reason) > 13, node_id
    deselected = [node for node, (_r, d) in entries.items() if d]
    assert deselected == [
        "tests/unit/safety_analysis/geohazard/test_usgs.py"
        "::test_transport_caps_timeout_pause_and_headers"
    ]
    # Both historical spellings collapse to one canonical entry.
    assert conftest._canonical_node_id("unit/cli/x.py::t") == "tests/unit/cli/x.py::t"
