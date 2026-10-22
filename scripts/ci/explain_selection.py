#!/usr/bin/env python3
"""Explain individual path rules, combined test selection and emitted matrix shards.

Accept name-only lines, tab-separated git --name-status lines, or a JSON list of
{status, paths} records. Renames include both endpoints; deletions keep the old
path even if it no longer exists. No tests or workflow jobs are executed.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STATUS = re.compile(r"(?:[AMDTUXB]|[RC]\d+)")


def _validate(changes: list[dict]) -> list[dict]:
    if not isinstance(changes, list):
        raise TypeError("changes must be a JSON list")
    for change in changes:
        if not isinstance(change, dict):
            raise TypeError("change must contain status and paths")
        status, paths = change.get("status"), change.get("paths")
        if not isinstance(status, str) or not STATUS.fullmatch(status):
            raise ValueError("invalid change status")
        if (
            not isinstance(paths, list)
            or not paths
            or not all(isinstance(p, str) and p for p in paths)
        ):
            raise ValueError("change paths must be nonempty strings")
        # Git diff name-status protocol: rename/copy has two paths, others one.
        expected = 2 if status.startswith(("R", "C")) else 1
        if len(paths) != expected:
            raise ValueError("wrong path count for change status")
    return changes


def parse_lines(text: str) -> list[dict]:
    if text.lstrip().startswith("["):
        return _validate(json.loads(text))
    changes = []
    for line in text.splitlines():
        if not line:
            continue
        fields = line.split("\t")
        if len(fields) == 1:
            changes.append({"status": "M", "paths": fields})
        else:
            changes.append({"status": fields[0], "paths": fields[1:]})
    return _validate(changes)


def git_changes(root: Path, base: str, head: str) -> list[dict]:
    """Read a two-tip diff with NUL separation; never modify the worktree or index."""
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-status",
            "-z",
            "--find-renames",
            "--end-of-options",
            base,
            head,
            "--",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    tokens = result.stdout.split("\0")
    if tokens[-1] == "":
        tokens.pop()
    changes = []
    while tokens:
        status = tokens.pop(0)
        count = 2 if status.startswith(("R", "C")) else 1
        paths, tokens = tokens[:count], tokens[count:]
        changes.append({"status": status, "paths": paths})
    return _validate(changes)


def _selector():
    spec = importlib.util.spec_from_file_location(
        "explain_selector", Path(__file__).with_name("select_test_targets.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rule(path: str, selector) -> str:
    """Label the existing selector's first matching rule; do not reimplement selection."""
    if selector._is_core(path):
        return "core"
    if path in selector.CONTRACT_ROUTES or path.startswith(selector.WORKFLOW_PREFIXES):
        return "contract route"
    if selector._MODULE_RE.match(path) or selector._INTEGRATION_RE.match(path):
        return "module"
    if selector._PACKAGE_MEMBER_RE.match(path) or selector._CLUSTER_MEMBER_RE.match(
        path
    ):
        return "package"
    return "ignored"


def explain(changes: list[dict], root: Path) -> dict:
    selector = _selector()
    rows, paths = [], []
    for change in _validate(changes):
        for path in change["paths"]:
            rows.append(
                {
                    "status": change["status"],
                    "path": path,
                    "rule": _rule(path, selector),
                    "selection": selector.select([path], root),
                }
            )
            paths.append(path)
    return {
        "paths": rows,
        "selection": selector.select(paths, root),
        "matrix": selector.to_matrix(paths, root),
    }


def render(result: dict) -> str:
    lines = []
    for row in result["paths"]:
        path = row["path"]
        if any(c in path for c in "\t\r\n"):
            path = json.dumps(path)
        selected = row["selection"]
        lines.append(f"{row['status']} {path} -> {row['rule']}")
        lines.append(
            f"  scope={selected['scope']}; targets={' '.join(selected['xdist'] + selected['seq'])}"
        )
    selected = result["selection"]
    lines.extend(
        [
            f"scope={selected['scope']}",
            f"xdist={' '.join(selected['xdist'])}",
            f"seq={' '.join(selected['seq'])}",
            "shards:",
        ]
    )
    for shard in result["matrix"]["include"]:
        lines.append(f"  {shard['name']} [{shard['mode']}]: {shard['targets']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO)
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--files-from", help="FILE or - for stdin")
    args = parser.parse_args(argv)
    if args.files_from is not None:
        if args.base or args.head:
            parser.error("choose --files-from or --base with --head")
        text = (
            sys.stdin.read()
            if args.files_from == "-"
            else Path(args.files_from).read_text(encoding="utf-8")
        )
        changes = parse_lines(text)
    elif args.base and args.head:
        changes = git_changes(args.root, args.base, args.head)
    else:
        parser.error("provide --files-from or both --base and --head")
    print(render(explain(changes, args.root)), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
