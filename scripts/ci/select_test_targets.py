#!/usr/bin/env python3
# ABOUTME: Single-source PR-gate test selector — maps changed files -> pytest targets.
# ABOUTME: Auto-discovers modules from the filesystem so new modules never drift (#496).

"""Select pytest targets for the PR gate from a list of changed files.

Replaces the three hand-maintained, drift-prone lists that used to live in
``ci.yml`` (the ``dorny/paths-filter`` filters, the ``unclassified`` negation
list, and the bash ``module_xdist`` map). The module list is now the filesystem:
a module is "mapped" iff ``tests/unit/<module>/`` exists. Adding a module needs
no CI edit — and the drift-guard test (``tests/ci/test_select_test_targets.py``)
fails if any ``tests/unit/<module>`` stops being selected.

Decision tree (first match wins):
  * a **core** path changed (engine, common, base_configs, packaging, conftest,
    the workflow itself, this selector) -> ``scope=full`` (whole tree).
  * otherwise collect the modules touched under ``src/worldenergydata/<m>/`` or
    ``tests/unit/<m>/`` (+ integration under ``tests/integration/modules/<m>/``)
    and any contract routed by an exact path (e.g. ``config/repo_structure.yml``
    -> ``tests/repo_structure``) -> ``scope=modules``.
  * if nothing test-relevant changed (docs / reports / notebooks only)
    -> ``scope=skip`` — still runs the cheap always-on cross-cutting set so the
    required "Test (PR gate)" check passes fast, never the full tree.

The always-on set always runs, so the xdist target list is never empty.

Usage::

    python3 scripts/ci/select_test_targets.py --files-from changed.txt
    git diff --name-only BASE...HEAD | python3 scripts/ci/select_test_targets.py -

Emits ``scope=`` / ``xdist_targets=`` / ``seq_targets=`` lines (GitHub Actions
``$GITHUB_OUTPUT`` format).
"""

from __future__ import annotations

import re
from pathlib import Path

from domain_matrix import SelectionRules, _has_tests
from domain_matrix import main as _main
from domain_matrix import select as _select
from domain_matrix import to_matrix as _to_matrix

__all__ = ["ALWAYS_XDIST", "_has_tests", "main", "select", "to_matrix"]

# Always-on cross-cutting set: engine contract, assetutilities contracts, the
# durable-workflow registry. Runs for every PR (so xdist is never empty).
ALWAYS_XDIST = [
    "tests/unit/core",
    "tests/unit/common",
    "tests/contracts",
    "tests/workflows",
    "tests/governance",
    "tests/integration/reporting",
]

# Changing any of these can affect every module -> run the whole tree.
CORE_EXACT = {
    "src/worldenergydata/engine.py",
    "src/worldenergydata/__main__.py",
    # pyproject.toml is now the SINGLE pytest config (#529): root pytest.ini
    # and tests/pytest.ini were deleted, so a config change here already routes
    # to the full tree via this entry.
    "pyproject.toml",
    "uv.lock",
    "tests/conftest.py",
    ".github/workflows/ci.yml",
}
CORE_PREFIXES = (
    "src/worldenergydata/base_configs/",
    "src/worldenergydata/common/",
    # Shared core carved into the worldenergydata-core workspace member
    # (ADR 0001 Phase 2 PR #1). common/ now lives here; touching it must still
    # fail safe to the full tree. Keep the legacy src/ path above for history.
    "packages/worldenergydata-core/",
    "scripts/ci/",  # the selector itself / its tests -> fail safe to full
    "tests/ci/",
)

# Exact non-module paths that should run a specific contract suite.
CONTRACT_ROUTES = {
    "docs/ci/templates/select_test_targets.py": "tests/ci",
    "config/repo_structure.yml": "tests/repo_structure",
    "scripts/capabilities/build_onepagers.py": "tests/test_capability_onepagers.py",
    "tests/test_capability_onepagers.py": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/benchmark.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/completion.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/economics-anchor.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/economics-big_foot.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/economics-cascade_chinook.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/economics-jack_st_malo.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/economics-julia.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/economics-shenandoah.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/economics-stones.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/fd-bsee-matched.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/fd-playbook.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/fd-portfolio.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/fd-showcase.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/imo.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/mooring.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/ms-exec.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/ms-fatality.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/ms-foundering.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/ms-hatch.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/portfolio.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/sec-economics.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/sec-playbook.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/sec-safety.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/sec-validation.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/sec-wells.html": "tests/test_capability_onepagers.py",
    "reports/capabilities/pdf/well-path.html": "tests/test_capability_onepagers.py",
}

# Paths that exercise the durable-workflow registry (covered by tests/workflows,
# already in ALWAYS_XDIST) but should still count as "test-relevant".
WORKFLOW_PREFIXES = (
    "docs/registry/",
    "examples/workflows/",
    "tests/workflows/",
)

_MODULE_RE = re.compile(r"^(?:src/worldenergydata|tests/unit)/([^/]+)/")
_INTEGRATION_RE = re.compile(r"^tests/integration/modules/([^/]+)/")
# Domains carved into uv workspace members (ADR 0001 Phase 2, #529) live under
# packages/worldenergydata-<domain>/src/worldenergydata/<domain>/. A change
# there must route to that domain's own shard (tests/unit/<domain>), NOT to the
# full tree — so this maps the member path to the domain name, mirroring
# _MODULE_RE for the in-root layout. The backreference \1 requires the member
# distribution name to equal the inner namespace subpackage; this holds for the
# domain members (worldenergydata-sodir -> worldenergydata/sodir/...) but NOT
# for worldenergydata-core (ships worldenergydata/common/), which therefore does
# not match here and stays in CORE_PREFIXES -> full tree (fail safe).
_PACKAGE_MEMBER_RE = re.compile(
    r"^packages/worldenergydata-([^/]+)/src/worldenergydata/\1/"
)

# Phase 2 batch 3 (#529): the coupled BSEE cluster ships FOUR subpackages in ONE
# member (packages/worldenergydata-bsee/ contains bsee, lower_tertiary, hse,
# well_production_dashboard — they share an import cycle and cannot be split).
# For those, the distribution name (bsee) does NOT equal three of the four inner
# subpackage names, so the backreferenced _PACKAGE_MEMBER_RE above only routes
# the bsee/ subtree. This second regex routes EACH inner subpackage of the
# cluster member to its OWN shard (tests/unit/<subpkg>). It is scoped to the
# known cluster member name so it never matches worldenergydata-core (whose
# `common` subpackage must stay full-tree, fail-safe), and captures the inner
# subpackage (group 1) as the routed domain.
#
# fdas is NO LONGER here: it was carved to its own member
# (packages/worldenergydata-fdas/, #714) where distribution name == subpackage
# name (fdas), so _PACKAGE_MEMBER_RE routes it automatically — no cluster entry.
_CLUSTER_MEMBER_RE = re.compile(
    r"^packages/worldenergydata-bsee/src/worldenergydata/"
    r"(bsee|lower_tertiary|hse|well_production_dashboard)/"
)


# Repository conventions remain here; the shared engine can be copied unchanged
# alongside another repository's adapter (docs/ci/domain-matrix.md).
RULES = SelectionRules(
    always_xdist=tuple(ALWAYS_XDIST),
    core_exact=frozenset(CORE_EXACT),
    core_prefixes=CORE_PREFIXES,
    module_patterns=(
        _MODULE_RE.pattern,
        _PACKAGE_MEMBER_RE.pattern,
        _CLUSTER_MEMBER_RE.pattern,
    ),
    integration_patterns=(_INTEGRATION_RE.pattern,),
    contract_routes=CONTRACT_ROUTES,
    workflow_prefixes=WORKFLOW_PREFIXES,
)


def select(changed: list[str], root: Path) -> dict:
    """Select flat pytest targets with this repository's routes."""
    return _select(changed, root, RULES)


def to_matrix(changed: list[str], root: Path) -> dict:
    """Select domain shards with this repository's routes."""
    return _to_matrix(changed, root, RULES)


def main(argv: list[str] | None = None) -> int:
    return _main(RULES, Path(__file__).resolve().parents[2], argv)


if __name__ == "__main__":
    raise SystemExit(main())
