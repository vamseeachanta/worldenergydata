#!/usr/bin/env python3
"""Advisory reachability inventory using the existing selector without modifying it.

Test discovery mirrors python_files in pyproject.toml, including archived tests.
Reachability means the changed test is covered by a selected target and scope is
not full. This is path coverage, not a claim about pytest collection or execution.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import stat
import subprocess
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


def _linked(path: Path) -> bool:
    if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
        return True
    # MS-FSCC, section 2.1.2.1: only symlink and mount-point tags identify links.
    # https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fscc/c8e77b37-3909-4fe6-a4ea-2b9d423b1ee4
    return path.exists() and getattr(path.lstat(), "st_reparse_tag", 0) in {
        getattr(stat, "IO_REPARSE_TAG_SYMLINK", 0xA000000C),
        getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003),
    }


def _excluded(name: str) -> bool:
    return name in {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
        ".tox",
    } or name.endswith((".egg-info", ".dist-info"))


def _inventory_files(root: Path, base: Path):
    """Prune cache/metadata output and links before walking; keep legitimate build packages."""
    if any(
        _linked(p) or _excluded(p.name)
        for p in (base, *base.parents)
        if p != root and root in p.parents
    ):
        return
    if not base.resolve().is_relative_to(root.resolve()):
        return
    for directory, children, files in os.walk(base, followlinks=False):
        parent = Path(directory)
        children[:] = sorted(
            name
            for name in children
            if not _excluded(name) and not _linked(parent / name)
        )
        for name in sorted(files):
            path = parent / name
            if (
                path.suffix not in {".pyc", ".pyo"}
                and not _linked(path)
                and path.is_file()
            ):
                yield path


def _tracked_files(root: Path) -> set[str] | None:
    """Use the checkout index for source inventory; plain fixture roots have no index."""
    if not (root / ".git").exists():
        return None
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"}
    }
    output = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=root, env=env, encoding="utf-8"
    )
    return set(output.split("\0")) - {""}


def _source_directory(path: Path, root: Path, tracked: set[str] | None) -> bool:
    if not path.is_dir() or _excluded(path.name) or _linked(path):
        return False
    prefix = path.relative_to(root).as_posix() + "/"
    return tracked is None or any(name.startswith(prefix) for name in tracked)


def test_files(root: Path) -> list[str]:
    """Include both pytest filename conventions and package-local test roots."""
    roots = [root / "tests", *sorted((root / "packages").glob("*/tests"))]
    return sorted(
        {
            file.relative_to(root).as_posix()
            for base in roots
            for file in _inventory_files(root, base)
            if file.match("test_*.py") or file.match("*_test.py")
        }
    )


def audit(root: Path) -> dict:
    """Simulate each test-only diff and each member's source-only diffs.

    Source rows retain always-on targets separately from routed targets: selecting
    only an always-on contract must not hide a missing module test home. Every
    tracked source file is probed in Git checkouts, so multi-domain packages are not reduced to an
    arbitrary representative. A directory with no source is NOT_EVALUATED.
    """
    selector = load_selector()
    tracked = _tracked_files(root)
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
        *sorted(
            p
            for p in (root / "packages").glob("*")
            if _source_directory(p, root, tracked)
        ),
        *sorted(
            p
            for p in (root / "src/worldenergydata").glob("*")
            if _source_directory(p, root, tracked)
        ),
    ]
    sources = []
    for group in groups:
        base = group / "src" if group.parent.name == "packages" else group
        namespace = base / "worldenergydata"
        domains = (
            sorted(
                p.name
                for p in namespace.iterdir()
                if _source_directory(p, root, tracked)
            )
            if group.parent.name == "packages" and namespace.is_dir()
            else [group.name]
        )
        paths = sorted(
            p.relative_to(root).as_posix()
            for p in _inventory_files(root, base)
            if tracked is None or p.relative_to(root).as_posix() in tracked
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


def compare_allowlist(result: dict, allowlist: dict[str, str]) -> dict:
    """Report new orphans and removable exceptions without enforcing routing."""
    return {
        "unlisted": unlisted(result, allowlist),
        "reachable": [
            row["path"]
            for row in result["tests"]
            if row["reachable"] and row["path"] in allowlist
        ],
    }


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
    if "allowlist" in result:
        lines.extend(["", "allow-list comparison (report only)"])
        for key, label in (
            ("unlisted", "unlisted orphan"),
            ("reachable", "reachable exception"),
        ):
            paths = result["allowlist"][key]
            lines.append(f"{label} count | {len(paths)}")
            lines.extend(f"{label} | {path}" for path in paths)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO)
    parser.add_argument(
        "--json", type=Path, required=True, help="output JSON inventory"
    )
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=Path(__file__).with_name("selector_reach_allowlist.txt"),
        help="exact-file exceptions to compare (report only)",
    )
    args = parser.parse_args(argv)
    result = audit(args.root)
    result["allowlist"] = compare_allowlist(result, read_allowlist(args.allowlist))
    args.json.write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(table(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
