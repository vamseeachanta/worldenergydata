#!/usr/bin/env python3
"""Advisory reachability inventory using the existing selector without modifying it.

Test discovery follows python_files in pyproject.toml, including archived tests.
Reachability means the changed test is covered by a selected target and scope is
not full. This is path coverage, not a claim about pytest collection or execution.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[2]


def load_selector():
    """Import by path, independently of application dependencies and sys.path."""
    path = Path(__file__).with_name("select_test_targets.py")
    spec = importlib.util.spec_from_file_location("reach_selector", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def contains(path: str, targets: list[str]) -> bool:
    """Directory membership uses path components, never a string prefix."""
    item = PurePosixPath(path)
    return any(
        item == PurePosixPath(t) or PurePosixPath(t) in item.parents for t in targets
    )


def test_files(root: Path) -> list[str]:
    """Include both pytest filename conventions and package-local test roots."""
    roots = [root / "tests", *sorted((root / "packages").glob("*/tests"))]
    return sorted(
        {
            file.relative_to(root).as_posix()
            for base in roots
            for pattern in ("test_*.py", "*_test.py")
            for file in base.rglob(pattern)
            if file.is_file()
        }
    )


def audit(root: Path) -> dict:
    """Simulate each test-only diff and each member's source-only diffs.

    Source rows retain always-on targets separately from routed targets: selecting
    only an always-on contract must not hide a missing module test home. Every
    actual source file is probed, so multi-domain packages are not reduced to an
    arbitrary representative. A directory with no source is NOT_EVALUATED.
    """
    selector = load_selector()
    tests = []
    for path in test_files(root):
        result = selector.select([path], root)
        targets = result["xdist"] + result["seq"]
        tests.append(
            {
                "path": path,
                "scope": result["scope"],
                "targets": targets,
                "reachable": result["scope"] != "full" and contains(path, targets),
            }
        )
    groups = [
        *sorted(p for p in (root / "packages").glob("*") if p.is_dir()),
        *sorted(p for p in (root / "src/worldenergydata").glob("*") if p.is_dir()),
    ]
    sources = []
    for group in groups:
        base = group / "src" if group.parent.name == "packages" else group
        namespace = base / "worldenergydata"
        domains = (
            sorted(p.name for p in namespace.iterdir() if p.is_dir())
            if group.parent.name == "packages" and namespace.is_dir()
            else [group.name]
        )
        paths = sorted(
            p.relative_to(root).as_posix() for p in base.rglob("*") if p.is_file()
        )
        selections = [selector.select([path], root) for path in paths]
        targets = sorted({t for s in selections for t in s["xdist"] + s["seq"]})
        sources.append(
            {
                "path": group.relative_to(root).as_posix(),
                "probes": paths,
                "scopes": sorted({s["scope"] for s in selections}),
                "targets": targets,
                "routed_targets": sorted(set(targets) - set(selector.ALWAYS_XDIST)),
                "any_targets": bool(targets),
                "unit_homes": [
                    f"tests/unit/{d}"
                    for d in domains
                    if (root / "tests/unit" / d).is_dir()
                ],
                "status": "EVALUATED" if paths else "NOT_EVALUATED",
            }
        )
    return {"tests": tests, "sources": sources}


def read_allowlist(path: Path) -> dict[str, str]:
    """Require exact test file paths and a nonempty reason; directories cannot drift."""
    entries = {}
    for number, raw in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        name, marker, reason = raw.partition("#")
        name, reason = name.strip(), reason.strip()
        item = PurePosixPath(name)
        if (
            not marker
            or not reason.startswith("reason: ")
            or not reason.removeprefix("reason: ").strip()
            or item.is_absolute()
            or ".." in item.parts
            or any(c in name for c in "*?[]")
            or item.as_posix() != name
            or item.suffix != ".py"
            or not (item.name.startswith("test_") or item.name.endswith("_test.py"))
            or name in entries
        ):
            raise ValueError(f"invalid allow-list entry at line {number}")
        entries[name] = reason
    return entries


def unlisted(result: dict, allowlist: dict[str, str]) -> list[str]:
    return [
        r["path"]
        for r in result["tests"]
        if not r["reachable"] and r["path"] not in allowlist
    ]


def table(result: dict) -> str:
    lines = ["path | reach | scope | targets"]
    for row in result["tests"]:
        state = "reachable" if row["reachable"] else "orphan"
        lines.append(
            f"{row['path']} | {state} | {row['scope']} | {', '.join(row['targets'])}"
        )
    lines.extend(["", "source | status | any targets | scopes | routed targets"])
    for row in result["sources"]:
        lines.append(
            f"{row['path']} | {row['status']} | {row['any_targets']} | "
            f"{', '.join(row['scopes'])} | {', '.join(row['routed_targets'])}"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO)
    parser.add_argument(
        "--json", type=Path, required=True, help="output JSON inventory"
    )
    args = parser.parse_args(argv)
    result = audit(args.root)
    args.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(table(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
