# ABOUTME: Drift guard for the PR-gate test selector (#496).
# ABOUTME: Fails if any tests/unit/<module> stops being selected, or routing regresses.

"""Tests for scripts/ci/select_test_targets.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ci"))

from select_test_targets import ALWAYS_XDIST, select  # noqa: E402


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
