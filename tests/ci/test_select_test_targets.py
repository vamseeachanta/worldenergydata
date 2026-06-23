# ABOUTME: Drift guard for the PR-gate test selector (#496).
# ABOUTME: Fails if any tests/unit/<module> stops being selected, or routing regresses.

"""Tests for scripts/ci/select_test_targets.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ci"))

from select_test_targets import (  # noqa: E402
    ALWAYS_XDIST,
    _has_tests,
    select,
    to_matrix,
)


def _unit_modules() -> list[str]:
    base = REPO_ROOT / "tests" / "unit"
    return sorted(
        d.name for d in base.iterdir() if d.is_dir() and d.name != "__pycache__"
    )


def test_core_change_runs_full_tree():
    r = select(["src/worldenergydata/engine.py"], REPO_ROOT)
    assert r["scope"] == "full"
    assert "tests/integration" in r["seq"] and "tests/performance" in r["seq"]


def test_selector_self_change_is_core():
    assert select(["scripts/ci/select_test_targets.py"], REPO_ROOT)["scope"] == "full"


def test_hse_change_is_module_scoped_not_full():
    r = select(["src/worldenergydata/hse/grounding.py"], REPO_ROOT)
    assert r["scope"] == "modules"
    assert "tests/unit/hse" in r["xdist"]
    # the always-on cross-cutting set is always present
    assert all(t in r["xdist"] for t in ALWAYS_XDIST)


def test_carved_domain_member_change_routes_to_its_shard_not_full():
    """A change under a carved uv workspace member
    (packages/worldenergydata-<domain>/src/worldenergydata/<domain>/) is
    module-scoped to that domain's shard, NOT the full tree (ADR 0001 Phase 2,
    #529)."""
    r = select(
        ["packages/worldenergydata-sodir/src/worldenergydata/sodir/api.py"],
        REPO_ROOT,
    )
    assert r["scope"] == "modules"
    assert "tests/unit/sodir" in r["xdist"]
    assert all(t in r["xdist"] for t in ALWAYS_XDIST)


def test_core_member_change_still_runs_full_tree():
    """worldenergydata-core ships worldenergydata/common (name != subpackage),
    so it must NOT match the per-domain member regex and must stay full-tree."""
    r = select(
        ["packages/worldenergydata-core/src/worldenergydata/common/config.py"],
        REPO_ROOT,
    )
    assert r["scope"] == "full"


def test_noncode_only_change_skips_full_tree():
    for path in ("reports/hse/x.html", "notebooks/demo.ipynb", "README.md"):
        r = select([path], REPO_ROOT)
        assert r["scope"] == "skip", path
        # skip still runs the cheap always-on set, never module/full dirs
        assert r["xdist"] == [t for t in ALWAYS_XDIST if (REPO_ROOT / t).is_dir()]


def test_config_repo_structure_routes_to_its_contract():
    r = select(["config/repo_structure.yml"], REPO_ROOT)
    assert r["scope"] == "modules"
    assert "tests/repo_structure" in r["xdist"]


@pytest.mark.parametrize("module", _unit_modules())
def test_every_unit_module_is_selected(module):
    """Drift guard: a change under any tests/unit/<module> must be module-scoped
    and pull in that module's dir (no module silently regresses to full/skip)."""
    r = select([f"tests/unit/{module}/test_smoke.py"], REPO_ROOT)
    assert r["scope"] == "modules"
    assert f"tests/unit/{module}" in r["xdist"]


def test_integration_module_adds_seq_target():
    r = select(["tests/integration/modules/bsee/test_x.py"], REPO_ROOT)
    if (REPO_ROOT / "tests/integration/modules/bsee").is_dir():
        assert "tests/integration/modules/bsee" in r["seq"]


# --- Matrix-emitter (domain fan-out) tests ---


def _names(m: dict) -> set[str]:
    return {s["name"] for s in m["include"]}


def test_matrix_is_never_empty_on_skip():
    """Docs-only change still yields the always-on shard (matrix never empty)."""
    m = to_matrix(["README.md"], REPO_ROOT)
    assert m["scope"] == "skip"
    assert m["include"], "matrix must never be empty (CI matrix would error)"
    assert _names(m) == {"_always"}


def test_matrix_module_scope_one_shard_per_domain():
    m = to_matrix(
        ["src/worldenergydata/hse/x.py", "src/worldenergydata/sodir/y.py"],
        REPO_ROOT,
    )
    assert m["scope"] == "modules"
    names = _names(m)
    assert "_always" in names
    assert "unit-hse" in names and "unit-sodir" in names
    # always-on dirs are not duplicated into their own shards
    assert "unit-core" not in names and "unit-common" not in names


def test_matrix_full_scope_fans_out_every_unit_domain_with_tests():
    """A core change fans out to one shard per tests/unit/<domain> that has
    tests; pure support dirs (no test files) are excluded to avoid empty shards."""
    m = to_matrix(["uv.lock"], REPO_ROOT)
    assert m["scope"] == "full"
    names = _names(m)
    base = REPO_ROOT / "tests" / "unit"
    for module in _unit_modules():
        if _has_tests(base / module):
            assert f"unit-{module}" in names, f"{module} missing from full matrix"
        else:
            assert f"unit-{module}" not in names, f"{module} is an empty shard"


def test_matrix_full_scope_excludes_non_test_support_dirs():
    """Support dirs under tests/ (fixtures/helpers/mocks/...) must not become
    shards when they contain no test files."""
    m = to_matrix(["uv.lock"], REPO_ROOT)
    names = _names(m)
    for support in ("fixtures", "helpers", "mocks"):
        d = REPO_ROOT / "tests" / support
        if d.is_dir() and not _has_tests(d):
            assert support not in names, f"{support} should not be a shard"


def test_matrix_shards_have_required_fields():
    m = to_matrix(["uv.lock"], REPO_ROOT)
    for shard in m["include"]:
        assert set(shard) >= {"name", "targets", "mode"}
        assert shard["mode"] in {"xdist", "seq"}
        assert shard["targets"].strip()


def test_matrix_targets_only_existing_dirs_in_module_scope():
    m = to_matrix(["src/worldenergydata/subsea/x.py"], REPO_ROOT)
    for shard in m["include"]:
        for tgt in shard["targets"].split():
            assert (REPO_ROOT / tgt).exists(), f"{tgt} does not exist"
