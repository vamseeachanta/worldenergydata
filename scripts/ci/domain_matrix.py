"""Portable, stdlib-only pytest selector for the shared domain-matrix workflow.

The routing and matrix protocol are extracted from select_test_targets.py
(the implementation introduced for #531). Repository conventions are inputs;
this module neither runs tests nor changes quarantine or aggregate policy.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SelectionRules:
    """Repository routes; regex group 1 is the domain's unit-directory name.

    All paths are repository-relative POSIX paths. The test tree has ``unit``,
    ``integration/modules`` and ``performance`` children, as in the original
    selector. ``tests_root`` permits a different top-level directory name.
    """

    always_xdist: tuple[str, ...]
    core_exact: frozenset[str]
    core_prefixes: tuple[str, ...]
    module_patterns: tuple[str, ...]
    integration_patterns: tuple[str, ...]
    contract_routes: Mapping[str, str]
    workflow_prefixes: tuple[str, ...] = ()
    tests_root: str = "tests"


def _has_tests(directory: Path) -> bool:
    """Keep support directories without pytest files out of the full matrix."""
    for pattern in ("test_*.py", "*_test.py"):
        if next(directory.rglob(pattern), None) is not None:
            return True
    return False


def _existing_unique(targets: list[str], root: Path) -> list[str]:
    seen, out = set(), []
    for target in targets:
        path = root / target
        is_test_file = (
            path.is_file() and path.name.startswith("test_") and path.suffix == ".py"
        )
        if target not in seen and (path.is_dir() or is_test_file):
            seen.add(target)
            out.append(target)
    return out


def _full_tree(root: Path, rules: SelectionRules) -> list[str]:
    tests = root / rules.tests_root
    out = []
    for child in sorted(tests.iterdir()):
        if (
            child.is_dir()
            and child.name not in {"performance", "integration", "__pycache__"}
        ) or (
            child.is_file() and child.name.startswith("test_") and child.suffix == ".py"
        ):
            out.append(f"{rules.tests_root}/{child.name}")
    return out


def select(changed: list[str], root: Path, rules: SelectionRules) -> dict:
    """Return the legacy flat ``scope``, ``xdist`` and ``seq`` target lists."""
    if any(p in rules.core_exact or p.startswith(rules.core_prefixes) for p in changed):
        return {
            "scope": "full",
            "xdist": _full_tree(root, rules),
            "seq": [
                f"{rules.tests_root}/integration",
                f"{rules.tests_root}/performance",
            ],
        }

    modules: set[str] = set()
    seq_modules: set[str] = set()
    contracts: set[str] = set()
    relevant = False
    for path in changed:
        if path in rules.contract_routes:
            contracts.add(rules.contract_routes[path])
            relevant = True
            continue
        if path.startswith(rules.workflow_prefixes):
            relevant = True
            continue
        for pattern in rules.module_patterns:
            match = re.match(pattern, path)
            if match:
                modules.add(match.group(1))
                relevant = True
        for pattern in rules.integration_patterns:
            match = re.match(pattern, path)
            if match:
                seq_modules.add(match.group(1))
                relevant = True

    xdist = list(rules.always_xdist)
    xdist.extend(f"{rules.tests_root}/unit/{mod}" for mod in sorted(modules))
    xdist.extend(sorted(contracts))
    seq = [
        f"{rules.tests_root}/integration/modules/{mod}" for mod in sorted(seq_modules)
    ]
    return {
        "scope": "modules" if relevant else "skip",
        "xdist": _existing_unique(xdist, root),
        "seq": _existing_unique(seq, root),
    }


def to_matrix(changed: list[str], root: Path, rules: SelectionRules) -> dict:
    """Return per-domain shards in the shared workflow's ``include`` protocol.

    Full scope enumerates domains with pytest files, then other test trees,
    root-level tests and sequential suites. Narrow scope preserves always-on
    contracts and routes touched modules. An empty matrix is a configuration
    error rather than an apparent successful gate without any test jobs.
    """
    result = select(changed, root, rules)
    scope = result["scope"]
    shards: list[dict] = []
    tests = rules.tests_root

    if scope == "full":
        unit = root / tests / "unit"
        if unit.is_dir():
            for child in sorted(unit.iterdir()):
                if child.is_dir() and child.name != "__pycache__" and _has_tests(child):
                    shards.append(
                        {
                            "name": f"unit-{child.name}",
                            "targets": f"{tests}/unit/{child.name}",
                            "mode": "xdist",
                        }
                    )
        root_files: list[str] = []
        for child in sorted((root / tests).iterdir()):
            if (
                child.is_dir()
                and child.name
                not in {"unit", "performance", "integration", "__pycache__"}
                and _has_tests(child)
            ):
                shards.append(
                    {
                        "name": child.name,
                        "targets": f"{tests}/{child.name}",
                        "mode": "xdist",
                    }
                )
            elif (
                child.is_file()
                and child.name.startswith("test_")
                and child.suffix == ".py"
            ):
                root_files.append(f"{tests}/{child.name}")
        if root_files:
            shards.append(
                {"name": "_root", "targets": " ".join(root_files), "mode": "xdist"}
            )
        for name in ("integration", "performance"):
            target = f"{tests}/{name}"
            if (root / target).is_dir():
                shards.append({"name": name, "targets": target, "mode": "seq"})
    else:
        always = _existing_unique(list(rules.always_xdist), root)
        if always:
            shards.append(
                {"name": "_always", "targets": " ".join(always), "mode": "xdist"}
            )
        for target in result["xdist"]:
            if target in rules.always_xdist:
                continue
            name = target.replace(f"{tests}/unit/", "unit-").replace(f"{tests}/", "")
            shards.append({"name": name, "targets": target, "mode": "xdist"})
        for target in result["seq"]:
            name = target.replace(f"{tests}/integration/modules/", "seq-")
            shards.append({"name": name, "targets": target, "mode": "seq"})

    if not shards:
        raise ValueError(
            "no test shards selected; configure an existing always-on target"
        )
    return {"scope": scope, "include": shards}


def main(rules: SelectionRules, root: Path, argv: list[str] | None = None) -> int:
    """Emit GitHub Actions outputs without installing repository dependencies."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="changed file paths")
    parser.add_argument(
        "--files-from", help="read changed paths from FILE (or - for stdin)"
    )
    parser.add_argument("--root", default=str(root))
    parser.add_argument("--emit-matrix", action="store_true")
    args = parser.parse_args(argv)
    if args.files_from:
        text = (
            sys.stdin.read()
            if args.files_from == "-"
            else Path(args.files_from).read_text(encoding="utf-8")
        )
        changed = [line.strip() for line in text.splitlines() if line.strip()]
    else:
        changed = args.files
    if args.emit_matrix:
        try:
            matrix = to_matrix(changed, Path(args.root), rules)
        except ValueError as exc:
            parser.error(str(exc))
        print(f"scope={matrix['scope']}")
        print(f"matrix={json.dumps({'include': matrix['include']})}")
    else:
        result = select(changed, Path(args.root), rules)
        print(f"scope={result['scope']}")
        print(f"xdist_targets={' '.join(result['xdist'])}")
        print(f"seq_targets={' '.join(result['seq'])}")
    return 0
