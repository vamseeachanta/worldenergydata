#!/usr/bin/env python3
"""Explain individual path rules, combined test selection and emitted matrix shards.

Accept name-only lines, tab-separated git --name-status lines, or a JSON list of
{status, paths} records. Rename sources are context only; destinations and deleted
paths determine selection even when they no longer exist. No tests or workflow
jobs are executed.
"""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import os
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


def parse_lines(text: str, *, json_input: bool = False) -> list[dict]:
    if json_input:
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
    """Read the merge-base diff with NUL separation; leave the index untouched."""
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-status",
            "-z",
            "--find-renames",
            "--end-of-options",
            f"{base}...{head}",
            "--",
        ],
        cwd=root,
        text=True,
        encoding="utf-8",
        env={
            k: v
            for k, v in os.environ.items()
            if k not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"}
        },
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


def _rule(selection: dict, *, fast: bool = False) -> str:
    """Describe the selector's actual disposition without duplicating its rules."""
    return {
        "full": "core (fast gate)" if fast else "core",
        "modules": "selector route",
        "skip": "ignored",
    }[selection["scope"]]


def explain(changes: list[dict], root: Path, *, mode: str = "pr") -> dict:
    selector = _selector()
    if mode not in {"pr", "full"}:
        raise ValueError("mode must be pr or full")
    fast = mode == "pr"
    if fast:
        try:
            if not callable(getattr(selector, "select_fast", None)):
                raise TypeError("missing fast selector")
            inspect.signature(selector.to_matrix).bind([], root, fast=True)
        except (TypeError, ValueError):
            raise ValueError(
                "PR mode requires both selector fast APIs; use --mode full with this revision"
            ) from None
    select = selector.select_fast if fast else selector.select
    rows, paths = [], []
    for change in _validate(changes):
        for index, path in enumerate(change["paths"]):
            context_only = change["status"].startswith(("R", "C")) and index == 0
            selection = select([path], root)
            rows.append(
                {
                    "status": change["status"],
                    "path": path,
                    "rule": _rule(
                        selector.select([path], root) if fast else selection, fast=fast
                    ),
                    "selection": selection,
                    "context_only": context_only,
                }
            )
            if not context_only:
                paths.append(path)
    return {
        "mode": mode,
        "paths": rows,
        "selection": select(paths, root),
        "matrix": (
            selector.to_matrix(paths, root, fast=True)
            if fast
            else selector.to_matrix(paths, root)
        ),
    }


def render(result: dict) -> str:
    lines = [f"mode={result['mode']}"]
    for row in result["paths"]:
        path = row["path"]
        if any(c in path for c in "\t\r\n"):
            path = json.dumps(path)
        selected = row["selection"]
        context = " (context only)" if row["context_only"] else ""
        lines.append(f"{row['status']} {path} -> {row['rule']}{context}")
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
    parser.add_argument(
        "--mode",
        choices=("pr", "full"),
        default="pr",
        help="PR fast gate (default) or push/full selection",
    )
    parser.add_argument(
        "--json", action="store_true", help="parse --files-from as a JSON change list"
    )
    args = parser.parse_args(argv)
    if args.json and args.files_from is None:
        parser.error("--json requires --files-from")
    try:
        if args.files_from is not None:
            if args.base or args.head:
                parser.error("choose --files-from or --base with --head")
            text = (
                sys.stdin.read()
                if args.files_from == "-"
                else Path(args.files_from).read_text(encoding="utf-8")
            )
            changes = parse_lines(text, json_input=args.json)
        elif args.base and args.head:
            changes = git_changes(args.root, args.base, args.head)
        else:
            parser.error("provide --files-from or both --base and --head")
        result = explain(changes, args.root, mode=args.mode)
    except subprocess.CalledProcessError as error:
        parser.error(error.stderr.strip() if error.stderr else str(error))
    except OSError as error:
        parser.error(f"input or Git executable unavailable: {error.strerror}")
    except (ValueError, TypeError, UnicodeError) as error:
        parser.error(str(error))
    print(render(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
