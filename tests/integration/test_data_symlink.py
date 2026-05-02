"""Integration tests for symlink-based data flow.

These tests verify the two-tier data architecture:
- Git repo holds small data files (~400 MB in data/modules/)
- /mnt/ace/worldenergydata/data/ holds large files (BSEE bin, HSE raw)
- A symlink connects them via scripts/setup-data-link.sh

Resolution order tested (from data_resolver.py):
1. WED_DATA_ROOT environment variable (explicit override)
2. Symlink at <project_root>/data -> external mount
3. Fallback to <project_root>/data/ directory (development)
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

_is_symlink = DATA_DIR.is_symlink()
_ace_mount_exists = ACE_MOUNT.exists()


def _require_symlink_or_skip():
    """Distinguish legitimate skip from deployment drift.

    Skip when /mnt/ace isn't mounted on this host (e.g., CI without the mount).
    FAIL when /mnt/ace IS present but data/ isn't a symlink — that's the bug
    pattern from #298/#359/#368: precondition-skipif silently masking a broken
    deployment. /mnt/ace data exists, the catalog claims it's reachable, but
    the symlink wiring was never done.
    """
    if not _ace_mount_exists:
        pytest.skip("/mnt/ace mount not present on this host")
    if not _is_symlink:
        pytest.fail(
            f"Drift detected: {ACE_MOUNT} exists but {DATA_DIR} is not a symlink. "
            f"Run scripts/setup-data-link.sh. See #359 for context."
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
# b) DataResolver follows symlink
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_data_resolver_follows_symlink():
    """When data/ is a symlink, DataResolver resolves through it."""
    _require_symlink_or_skip()
    root = get_data_root()
    assert root.is_dir()
    # The resolved path should NOT be the symlink itself
    assert root == DATA_DIR.resolve()


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
# d) BSEE binary accessible via symlink
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_bsee_bin_accessible_via_symlink():
    """BSEE binary data is reachable through the symlink."""
    _require_symlink_or_skip()
    bsee_path = get_module_data("bsee")
    assert bsee_path.is_dir(), f"BSEE module dir missing: {bsee_path}"
    # Sanity: directory should contain files
    children = list(bsee_path.iterdir())
    assert len(children) > 0, "BSEE module dir is empty"


# ---------------------------------------------------------------------------
# e) HSE raw accessible via symlink
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_hse_raw_accessible_via_symlink():
    """HSE OSHA CSVs are reachable through the symlink."""
    _require_symlink_or_skip()
    hse_path = get_module_data("hse")
    assert hse_path.is_dir(), f"HSE module dir missing: {hse_path}"
    children = list(hse_path.iterdir())
    assert len(children) > 0, "HSE module dir is empty"


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
