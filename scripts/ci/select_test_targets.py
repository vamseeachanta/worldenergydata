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

import argparse
import re
import json
import sys
from pathlib import Path

# Always-on cross-cutting set: engine contract, assetutilities contracts, the
# durable-workflow registry. Runs for every PR (so xdist is never empty).
ALWAYS_XDIST = [
    "tests/unit/core",
    "tests/unit/common",
    "tests/contracts",
    "tests/workflows",
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
)

# Exact non-module paths that should run a specific contract suite.
CONTRACT_ROUTES = {
    "config/repo_structure.yml": "tests/repo_structure",
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

# Phase 2 batch 3 (#529): the coupled BSEE cluster ships FIVE subpackages in ONE
# member (packages/worldenergydata-bsee/ contains bsee, lower_tertiary, fdas,
# hse, well_production_dashboard — they share an import cycle and cannot be
# split). For those, the distribution name (bsee) does NOT equal four of the
# five inner subpackage names, so the backreferenced _PACKAGE_MEMBER_RE above
# only routes the bsee/ subtree. This second regex routes EACH inner subpackage
# of the cluster member to its OWN shard (tests/unit/<subpkg>). It is scoped to
# the known cluster member name so it never matches worldenergydata-core (whose
# `common` subpackage must stay full-tree, fail-safe), and captures the inner
# subpackage (group 2) as the routed domain.
_CLUSTER_MEMBER_RE = re.compile(
    r"^packages/worldenergydata-(bsee)/src/worldenergydata/"
    r"(bsee|lower_tertiary|fdas|hse|well_production_dashboard)/"
)


def _is_core(path: str) -> bool:
    return path in CORE_EXACT or path.startswith(CORE_PREFIXES)


def _has_tests(directory: Path) -> bool:
    """True if ``directory`` contains at least one pytest file.

    Keeps non-test support dirs (fixtures/, helpers/, mocks/, _archive/, …)
    out of the domain matrix so they don't become empty shards. Note: a dir
    that *has* test files but is excluded by ``norecursedirs`` still becomes a
    shard — the CI step treats pytest's "no tests collected" (exit 5) as a
    pass, so such shards are harmless.
    """
    for pattern in ("test_*.py", "*_test.py"):
        if next(directory.rglob(pattern), None) is not None:
            return True
    return False


def select(changed: list[str], root: Path) -> dict:
    """Return {scope, xdist, seq} for the given changed files."""
    if any(_is_core(p) for p in changed):
        full = _full_tree(root)
        return {
            "scope": "full",
            "xdist": full,
            "seq": ["tests/integration", "tests/performance"],
        }

    modules: set[str] = set()
    seq_modules: set[str] = set()
    contracts: set[str] = set()
    relevant = False

    for p in changed:
        if p in CONTRACT_ROUTES:
            contracts.add(CONTRACT_ROUTES[p])
            relevant = True
            continue
        if p.startswith(WORKFLOW_PREFIXES):
            relevant = True  # covered by ALWAYS_XDIST tests/workflows
            continue
        m = _MODULE_RE.match(p)
        if m:
            modules.add(m.group(1))
            relevant = True
        pm = _PACKAGE_MEMBER_RE.match(p)
        if pm:
            modules.add(pm.group(1))
            relevant = True
        cm = _CLUSTER_MEMBER_RE.match(p)
        if cm:
            # Route to the INNER subpackage's shard (group 2), not the member
            # distribution name (group 1) — the cluster member ships 5 domains.
            modules.add(cm.group(2))
            relevant = True
        mi = _INTEGRATION_RE.match(p)
        if mi:
            seq_modules.add(mi.group(1))
            relevant = True
        # anything else (reports/, notebooks/, *.md, docs/ non-registry,
        # scripts/ non-ci, examples/ non-workflow) is not test-relevant.

    xdist = list(ALWAYS_XDIST)
    for mod in sorted(modules):
        xdist.append(f"tests/unit/{mod}")
    xdist.extend(sorted(contracts))
    seq = [f"tests/integration/modules/{m}" for m in sorted(seq_modules)]

    # keep only dirs that exist, dedupe, preserve order
    xdist = _existing_unique(xdist, root)
    seq = _existing_unique(seq, root)
    return {"scope": "modules" if relevant else "skip", "xdist": xdist, "seq": seq}


def _existing_unique(targets: list[str], root: Path) -> list[str]:
    seen, out = set(), []
    for t in targets:
        if t not in seen and (root / t).is_dir():
            seen.add(t)
            out.append(t)
    return out


def _full_tree(root: Path) -> list[str]:
    tests = root / "tests"
    out = []
    for child in sorted(tests.iterdir()):
        if child.is_dir() and child.name not in {
            "performance",
            "integration",
            "__pycache__",
        }:
            out.append(f"tests/{child.name}")
        elif (
            child.is_file() and child.name.startswith("test_") and child.suffix == ".py"
        ):
            out.append(f"tests/{child.name}")
    return out


def to_matrix(changed: list[str], root: Path) -> dict:
    """Build a GitHub-Actions matrix of per-domain shards from changed files.

    Each shard is ``{"name", "targets", "mode"}`` where ``mode`` is ``xdist``
    (parallel, ``-n auto``) or ``seq`` (sequential, for integration/perf).

    Unlike :func:`select` (one big target list), this fans the work out so
    every domain runs as its own CI job — faster wall-clock and per-domain
    pass/fail isolation (a red domain no longer blocks green siblings).

    * ``scope=full`` -> one shard per ``tests/unit/<domain>`` plus one per other
      top-level ``tests/<dir>`` plus a ``_root`` shard for top-level test files.
    * ``scope=modules`` -> the always-on shard + one shard per touched module +
      one per routed contract; seq shards per touched integration module.
    * ``scope=skip`` -> just the always-on shard (never empty).
    """
    result = select(changed, root)
    scope = result["scope"]
    shards: list[dict] = []

    if scope == "full":
        unit = root / "tests" / "unit"
        if unit.is_dir():
            for child in sorted(unit.iterdir()):
                if (
                    child.is_dir()
                    and child.name != "__pycache__"
                    and _has_tests(child)
                ):
                    shards.append(
                        {
                            "name": f"unit-{child.name}",
                            "targets": f"tests/unit/{child.name}",
                            "mode": "xdist",
                        }
                    )
        tests = root / "tests"
        root_files: list[str] = []
        for child in sorted(tests.iterdir()):
            if (
                child.is_dir()
                and child.name
                not in {
                    "unit",
                    "performance",
                    "integration",
                    "__pycache__",
                }
                and _has_tests(child)
            ):
                shards.append(
                    {
                        "name": child.name,
                        "targets": f"tests/{child.name}",
                        "mode": "xdist",
                    }
                )
            elif (
                child.is_file()
                and child.name.startswith("test_")
                and child.suffix == ".py"
            ):
                root_files.append(f"tests/{child.name}")
        if root_files:
            shards.append(
                {"name": "_root", "targets": " ".join(root_files), "mode": "xdist"}
            )
        for seq in ("tests/integration", "tests/performance"):
            if (root / seq).is_dir():
                shards.append(
                    {
                        "name": seq.split("/")[-1],
                        "targets": seq,
                        "mode": "seq",
                    }
                )
    else:
        # modules / skip: the always-on shard guarantees a non-empty matrix.
        always = _existing_unique(list(ALWAYS_XDIST), root)
        if always:
            shards.append(
                {"name": "_always", "targets": " ".join(always), "mode": "xdist"}
            )
        for tgt in result["xdist"]:
            if tgt in ALWAYS_XDIST:
                continue  # already in the always-on shard
            name = tgt.replace("tests/unit/", "unit-").replace("tests/", "")
            shards.append({"name": name, "targets": tgt, "mode": "xdist"})
        for tgt in result["seq"]:
            name = tgt.replace("tests/integration/modules/", "seq-")
            shards.append({"name": name, "targets": tgt, "mode": "seq"})

    return {"scope": scope, "include": shards}


def _read_changed(args) -> list[str]:
    if args.files_from == "-":
        text = sys.stdin.read()
    elif args.files_from:
        text = Path(args.files_from).read_text(encoding="utf-8")
    else:
        return list(args.files)
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*", help="changed file paths")
    ap.add_argument(
        "--files-from", help="read changed paths from FILE (or - for stdin)"
    )
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument(
        "--emit-matrix",
        action="store_true",
        help="emit a per-domain GitHub Actions matrix (matrix=<json>) instead "
        "of the flat xdist/seq target lists",
    )
    a = ap.parse_args(argv)
    changed = _read_changed(a)
    if a.emit_matrix:
        matrix = to_matrix(changed, Path(a.root))
        print(f"scope={matrix['scope']}")
        print(f"matrix={json.dumps({'include': matrix['include']})}")
        return 0
    result = select(changed, Path(a.root))
    print(f"scope={result['scope']}")
    print(f"xdist_targets={' '.join(result['xdist'])}")
    print(f"seq_targets={' '.join(result['seq'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
