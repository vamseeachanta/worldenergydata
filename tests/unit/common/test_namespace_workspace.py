# ABOUTME: Guards the uv-workspace + shared-namespace invariants from ADR 0001.
# ABOUTME: Asserts exactly one root __init__.py owner and import-transparency of the carve.

"""Workspace / namespace invariants for the domain-package split (ADR 0001).

Phase 2 PR #1 carved ``worldenergydata.common`` into the
``worldenergydata-core`` uv workspace member while the root ``worldenergydata``
distribution keeps every domain subpackage and the namespace root
(``src/worldenergydata/__init__.py`` with ``pkgutil.extend_path``).

The ADR's top risk is namespace-root misconfiguration: *exactly one* place may
own ``worldenergydata/__init__.py``; every other contributor must be
``__init__``-less / a pure PEP 420 namespace dir. These tests fail loudly if a
future change reintroduces a second root ``__init__.py`` or breaks the
import-transparency of the move.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

# Repo root = three parents up from tests/unit/common/<this file>.
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _root_init_owners() -> list[Path]:
    """Every ``worldenergydata/__init__.py`` directly under a ``src`` tree."""
    return sorted(_REPO_ROOT.glob("**/src/worldenergydata/__init__.py"))


def test_exactly_one_namespace_root_init_owner():
    """Only the root distribution may own ``worldenergydata/__init__.py``."""
    owners = _root_init_owners()
    assert len(owners) == 1, (
        "Exactly one distribution may own worldenergydata/__init__.py "
        f"(ADR 0001 risk). Found: {[str(p.relative_to(_REPO_ROOT)) for p in owners]}"
    )
    # And it must be the root distribution, not a workspace member.
    owner = owners[0]
    assert "packages" not in owner.parts, (
        f"Namespace root __init__.py must live in the root distribution, "
        f"not in a workspace member: {owner.relative_to(_REPO_ROOT)}"
    )


def test_core_member_is_pep420_namespace_dir():
    """The core member ships common/ but NOT a root __init__.py."""
    member_ns = (
        _REPO_ROOT / "packages" / "worldenergydata-core" / "src" / "worldenergydata"
    )
    assert (
        member_ns / "common" / "__init__.py"
    ).is_file(), "worldenergydata-core must ship worldenergydata/common/"
    assert not (member_ns / "__init__.py").exists(), (
        "worldenergydata-core must NOT ship a root worldenergydata/__init__.py "
        "(it is a PEP 420 namespace contributor; the root distribution owns the "
        "namespace root)."
    )


def test_common_resolves_from_core_member():
    """``worldenergydata.common`` must import from the carved-out core member."""
    import worldenergydata.common as common

    common_path = Path(common.__file__).resolve()
    assert "worldenergydata-core" in common_path.parts, (
        f"worldenergydata.common should load from the worldenergydata-core "
        f"member, got: {common_path}"
    )


def test_move_is_import_transparent():
    """Domains + namespace root + legacy redirect all still resolve."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import worldenergydata as wed

        # namespace root machinery preserved
        assert wed.__version__
        assert isinstance(list(wed.__path__), list) and wed.__path__

        # common symbols (from the core member)
        from worldenergydata.common import get_logger  # noqa: F401

        # a domain that heavily uses common still imports from the root dist
        from worldenergydata import bsee

        assert "packages" not in Path(bsee.__file__).resolve().parts

        # legacy worldenergydata.modules.X -> worldenergydata.X redirect intact
        import worldenergydata.modules.bsee as legacy_bsee

        assert legacy_bsee is bsee


def test_two_independent_distributions_present():
    """Both distributions must be installed as independent metadata entries."""
    import importlib.metadata as md

    # Skip gracefully if running from a source tree without installed metadata.
    try:
        root_v = md.version("worldenergydata")
        core_v = md.version("worldenergydata-core")
    except md.PackageNotFoundError:  # pragma: no cover - env-dependent
        pytest.skip("distributions not installed (running from source tree)")
    assert root_v
    assert core_v
