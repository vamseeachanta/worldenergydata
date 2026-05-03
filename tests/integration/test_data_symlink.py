"""Integration tests for symlink-based data flow.

These tests verify the partial-symlink data architecture introduced by #359:
- Git repo holds smaller modules in-tree (BSEE current, paleowells,
  marine_safety, vessel_hull_models, schemas, catalogs — ~389 MB total)
- /mnt/ace/worldenergydata/data/ holds the bulk relocated subtrees
  (HSE raw 6.7 GB, BSEE bin 2.5 GB, BSEE zip 230 MB)
- scripts/setup-data-link.sh wires the relocated subtrees as PER-PATH
  symlinks INSIDE the repo's data/ tree (NOT a whole-tree symlink — that
  would erase access to the in-tree modules)

Resolution order tested (from data_resolver.py):
1. WED_DATA_ROOT environment variable (explicit override)
2. Repo's data/ directory (which contains per-subtree symlinks for the
   relocated paths and real directories for everything else)
3. DataNotFoundError if neither resolves
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from worldenergydata.common.data_resolver import (
    DataNotFoundError,
    _clear_cache,
    get_data_root,
    get_module_data,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
SETUP_SCRIPT = PROJECT_ROOT / "scripts" / "setup-data-link.sh"
ACE_MOUNT = Path("/mnt/ace/worldenergydata")

# The three relocated subtrees per RELOCATION-LOG.md (2026-03-24).
# Each (repo_path, ace_path) pair: repo_path is where the symlink lives,
# ace_path is what it should point at.
RELOCATED_SUBTREES = [
    (DATA_DIR / "modules" / "bsee" / "bin", ACE_MOUNT / "data" / "modules" / "bsee" / "bin"),
    (DATA_DIR / "modules" / "bsee" / "zip", ACE_MOUNT / "data" / "modules" / "bsee" / "zip"),
    (DATA_DIR / "modules" / "hse" / "raw", ACE_MOUNT / "data" / "modules" / "hse" / "raw"),
]

_ace_mount_exists = ACE_MOUNT.exists()
_all_relocated_links_present = all(p.is_symlink() for p, _ in RELOCATED_SUBTREES)


def _require_symlink_or_skip():
    """Distinguish legitimate skip from deployment drift.

    Skip when /mnt/ace isn't mounted on this host (e.g., CI without the mount).
    FAIL when /mnt/ace IS present but the per-subtree symlinks aren't wired —
    that's the bug pattern from #298/#359/#368: precondition-skipif silently
    masking a broken deployment. /mnt/ace data exists, the catalog claims it's
    reachable, but the symlink wiring was never done.
    """
    if not _ace_mount_exists:
        pytest.skip("/mnt/ace mount not present on this host")
    missing = [str(p) for p, _ in RELOCATED_SUBTREES if not p.is_symlink()]
    if missing:
        pytest.fail(
            f"Drift detected: {ACE_MOUNT} exists but per-subtree symlinks are "
            f"missing at: {missing}. Run scripts/setup-data-link.sh. "
            f"See #359 for context."
        )


@pytest.fixture(autouse=True)
def _clear_resolver_cache():
    """Clear the lru_cache on get_data_root before each test."""
    _clear_cache()
    yield
    _clear_cache()


# ---------------------------------------------------------------------------
# a) Script existence
# ---------------------------------------------------------------------------


def test_setup_data_link_script_exists():
    """Verify setup-data-link.sh is present and executable."""
    assert SETUP_SCRIPT.exists(), f"Missing: {SETUP_SCRIPT}"
    mode = SETUP_SCRIPT.stat().st_mode
    assert mode & stat.S_IXUSR, "setup-data-link.sh is not executable (user)"


# ---------------------------------------------------------------------------
# b) Relocated subtrees resolve through per-path symlinks to /mnt/ace
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_relocated_subtrees_resolve_to_ace():
    """Each per-subtree symlink resolves to its /mnt/ace counterpart."""
    _require_symlink_or_skip()
    for link, expected_target in RELOCATED_SUBTREES:
        assert link.is_symlink(), f"{link} is not a symlink"
        assert link.resolve() == expected_target.resolve(), (
            f"{link} resolves to {link.resolve()} (expected {expected_target})"
        )
        # The resolved path should be a real, populated directory.
        assert link.is_dir(), f"{link} target is not a directory"
        assert any(link.iterdir()), f"{link} target is empty"


@pytest.mark.integration
def test_data_root_is_repo_data_dir():
    """data/ itself is a real directory (NOT a whole-tree symlink) under the partial-symlink topology."""
    root = get_data_root()
    assert root.is_dir()
    assert not DATA_DIR.is_symlink(), (
        "data/ should be a real directory under the partial-symlink topology; "
        "if it's a whole-tree symlink, that's the pre-#359 design that erases "
        "access to in-repo modules. Run scripts/setup-data-link.sh after "
        "removing the whole-tree symlink."
    )


# ---------------------------------------------------------------------------
# c) WED_DATA_ROOT env var override
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_data_resolver_with_env_var_override(monkeypatch, tmp_path):
    """WED_DATA_ROOT overrides both symlink and local data/ directory."""
    monkeypatch.setenv("WED_DATA_ROOT", str(tmp_path))
    root = get_data_root()
    assert root == tmp_path


# ---------------------------------------------------------------------------
# d) BSEE binary subtree is reachable specifically (not just bsee/ overall)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_bsee_bin_accessible_via_symlink():
    """BSEE binary subtree (relocated) is reachable AND non-empty.

    Targets data/modules/bsee/bin/ specifically — checking get_module_data('bsee')
    alone would pass even with NO /mnt/ace mounted because bsee/ has in-repo
    children (current/, paleowells/, schema.yaml, etc.). The point of this
    test is that the RELOCATED subtree is wired correctly.
    """
    _require_symlink_or_skip()
    bin_path = get_module_data("bsee") / "bin"
    assert bin_path.is_symlink(), f"{bin_path} is not a symlink"
    assert bin_path.is_dir(), f"BSEE bin subtree missing: {bin_path}"
    assert any(bin_path.iterdir()), f"BSEE bin subtree is empty: {bin_path}"


# ---------------------------------------------------------------------------
# e) HSE raw subtree is reachable specifically
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_hse_raw_accessible_via_symlink():
    """HSE raw subtree (relocated) is reachable AND non-empty.

    Targets data/modules/hse/raw/ specifically. get_module_data('hse')
    alone has the in-repo hse_incidents.db + schema.yaml siblings, so a
    looser check would pass even when /mnt/ace isn't mounted. The relocated
    subtree is what this test gates on.
    """
    _require_symlink_or_skip()
    raw_path = get_module_data("hse") / "raw"
    assert raw_path.is_symlink(), f"{raw_path} is not a symlink"
    assert raw_path.is_dir(), f"HSE raw subtree missing: {raw_path}"
    assert any(raw_path.iterdir()), f"HSE raw subtree is empty: {raw_path}"


# ---------------------------------------------------------------------------
# f) Graceful degradation — no symlink, no env var
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_graceful_degradation_no_symlink(monkeypatch, tmp_path):
    """Without a symlink or env var, resolver falls back to local data/ dir."""
    # Remove WED_DATA_ROOT if set
    monkeypatch.delenv("WED_DATA_ROOT", raising=False)

    # Create a fake project layout with a plain data/ directory
    fake_project = tmp_path / "project"
    fake_project.mkdir()
    (fake_project / "pyproject.toml").write_text("[project]\nname='test'\n")
    (fake_project / "data").mkdir()

    # Temporarily patch _get_project_root to return our fake project
    import worldenergydata.common.data_resolver as dr

    monkeypatch.setattr(dr, "_get_project_root", lambda: fake_project)

    root = get_data_root()
    assert root == fake_project / "data"


# ---------------------------------------------------------------------------
# g) Broken symlink handling
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_symlink_target_unavailable(monkeypatch, tmp_path):
    """A broken symlink (target missing) raises DataNotFoundError."""
    monkeypatch.delenv("WED_DATA_ROOT", raising=False)

    # Create a fake project with a broken data symlink
    fake_project = tmp_path / "project"
    fake_project.mkdir()
    (fake_project / "pyproject.toml").write_text("[project]\nname='test'\n")

    broken_target = tmp_path / "nonexistent_data_dir"
    (fake_project / "data").symlink_to(broken_target)

    import worldenergydata.common.data_resolver as dr

    monkeypatch.setattr(dr, "_get_project_root", lambda: fake_project)

    with pytest.raises(DataNotFoundError, match="does not exist"):
        get_data_root()
