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
    "pyproject.toml",
    "uv.lock",
    "tests/conftest.py",
    "tests/pytest.ini",
    ".github/workflows/ci.yml",
}
CORE_PREFIXES = (
    "src/worldenergydata/base_configs/",
    "src/worldenergydata/common/",
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


def _is_core(path: str) -> bool:
    return path in CORE_EXACT or path.startswith(CORE_PREFIXES)


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
    a = ap.parse_args(argv)
    result = select(_read_changed(a), Path(a.root))
    print(f"scope={result['scope']}")
    print(f"xdist_targets={' '.join(result['xdist'])}")
    print(f"seq_targets={' '.join(result['seq'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
