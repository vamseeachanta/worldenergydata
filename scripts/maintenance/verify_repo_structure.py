#!/usr/bin/env python3
"""Verify the worldenergydata repository structure contract.

The checker is intentionally conservative for #394 Phase 1: it does not move or
remove files. It classifies tracked/explicit paths against the approved root
contract and requires generated-output roots to carry temporary-exception
metadata before they are tolerated.
"""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import yaml

_PLACEHOLDER_VALUES = {"", "todo", "tbd", "none", "n/a", "placeholder"}
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_URL_RE = re.compile(r"^https://github\.com/vamseeachanta/worldenergydata/issues/\d+")


@dataclass(frozen=True)
class RepoStructureViolation:
    """A deterministic structure-contract violation."""

    code: str
    root: str
    path: str


@dataclass(frozen=True)
class RepoStructureContract:
    """Parsed repo-structure contract."""

    allowed_roots: frozenset[str]
    ignored_roots: frozenset[str]
    generated_artifact_roots: frozenset[str]
    temporary_exceptions: dict[str, dict[str, object]]


def _as_set(payload: dict, key: str) -> frozenset[str]:
    value = payload.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be a list of strings")
    return frozenset(value)


def load_contract(path: Path | str) -> RepoStructureContract:
    """Load and validate the YAML structure contract."""

    contract_path = Path(path)
    payload = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"{contract_path} must contain a YAML mapping")

    exceptions = payload.get("temporary_exceptions", {})
    if not isinstance(exceptions, dict):
        raise ValueError("temporary_exceptions must be a mapping")

    normalized_exceptions: dict[str, dict[str, object]] = {}
    for root, metadata in exceptions.items():
        if not isinstance(root, str) or not isinstance(metadata, dict):
            raise ValueError(
                "temporary_exceptions entries must map roots to metadata mappings"
            )
        normalized_exceptions[root] = dict(metadata)

    return RepoStructureContract(
        allowed_roots=_as_set(payload, "allowed_roots"),
        ignored_roots=_as_set(payload, "ignored_roots"),
        generated_artifact_roots=_as_set(payload, "generated_artifact_roots"),
        temporary_exceptions=normalized_exceptions,
    )


def root_for(path: str) -> str:
    """Return the root entry for a repository-relative path.

    Preserve leading-dot root names (for example, ``.github`` and ``.claude``)
    while tolerating an explicit ``./`` prefix from CLI input.
    """

    normalized = path.strip()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        return ""
    return normalized.split("/", 1)[0]


def _is_placeholder(value: str) -> bool:
    return value.strip().lower() in _PLACEHOLDER_VALUES


def _metadata_value(metadata: dict[str, object], key: str) -> str:
    value = metadata.get(key, "")
    return "" if value is None else str(value)


def _exception_metadata_valid(metadata: dict[str, object]) -> bool:
    required = ("category", "owner", "review_date", "follow_up", "justification")
    if any(
        key not in metadata or _is_placeholder(_metadata_value(metadata, key))
        for key in required
    ):
        return False
    if not _DATE_RE.match(_metadata_value(metadata, "review_date").strip()):
        return False
    if not _URL_RE.match(_metadata_value(metadata, "follow_up").strip()):
        return False
    if len(_metadata_value(metadata, "justification").strip()) < 30:
        return False
    allowed_paths = metadata.get("allowed_paths")
    if not isinstance(allowed_paths, list) or not all(
        isinstance(item, str) and item for item in allowed_paths
    ):
        return False
    return True


def _path_allowed_by_exception(path: str, metadata: dict[str, object]) -> bool:
    allowed_paths = metadata.get("allowed_paths")
    if not isinstance(allowed_paths, list):
        return False
    return path in set(allowed_paths)


def validate_paths(
    paths: Iterable[str], contract: RepoStructureContract
) -> list[RepoStructureViolation]:
    """Validate repository-relative paths against the root contract."""

    violations: list[RepoStructureViolation] = []
    emitted: set[RepoStructureViolation] = set()

    def add(violation: RepoStructureViolation) -> None:
        if violation not in emitted:
            emitted.add(violation)
            violations.append(violation)

    for path in sorted({p for p in paths if p and not p.endswith("/")}):
        root = root_for(path)
        if not root or root in contract.ignored_roots:
            continue

        if root in contract.generated_artifact_roots:
            metadata = contract.temporary_exceptions.get(root)
            if metadata is None:
                add(
                    RepoStructureViolation(
                        "generated-root-missing-exception", root, path
                    )
                )
            elif not _exception_metadata_valid(metadata):
                add(RepoStructureViolation("invalid-exception-metadata", root, root))
            elif not _path_allowed_by_exception(path, metadata):
                add(RepoStructureViolation("generated-path-not-classified", root, path))
            continue

        if root in contract.allowed_roots:
            continue

        add(RepoStructureViolation("unknown-root", root, path))

    return violations


def git_tracked_paths(repo_root: Path) -> list[str]:
    """Return git-tracked paths for the current checkout."""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return [line for line in result.stdout.splitlines() if line]


def parse_git_status_paths(output: str) -> list[str]:
    """Parse porcelain-like ``git status --short`` output into paths.

    This deliberately includes untracked, modified, deleted, and renamed paths
    that are visible in the working tree without reading ignored cache/output
    directories. For renames, validate the destination path because that is the
    root shape that would be committed.
    """

    paths: list[str] = []
    for raw_line in output.splitlines():
        if not raw_line or raw_line.startswith("## ") or len(raw_line) < 4:
            continue
        path = raw_line[3:]
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[1]
        if path:
            try:
                parsed = shlex.split(path)
            except ValueError:
                parsed = []
            paths.append(parsed[0] if len(parsed) == 1 else path)
    return paths


def git_worktree_paths(repo_root: Path) -> list[str]:
    """Return non-ignored working-tree paths visible to git status."""

    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=repo_root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return parse_git_status_paths(result.stdout)


def repository_paths(repo_root: Path) -> list[str]:
    """Return tracked plus non-ignored working-tree paths for contract checks."""

    return git_tracked_paths(repo_root) + git_worktree_paths(repo_root)


def format_violations(violations: Sequence[RepoStructureViolation]) -> str:
    """Render violations for humans and CI logs."""

    lines = ["Repo structure contract violations:"]
    for violation in violations:
        lines.append(f"- {violation.code}: root={violation.root} path={violation.path}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/repo_structure.yml"),
        help="Path to repo_structure.yml (default: config/repo_structure.yml)",
    )
    parser.add_argument(
        "--path",
        action="append",
        dest="paths",
        help="Explicit repo-relative path to validate. Repeatable; defaults to git ls-files.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = Path.cwd()
    contract = load_contract(args.config)
    paths = args.paths if args.paths is not None else repository_paths(repo_root)
    violations = validate_paths(paths, contract)
    if violations:
        print(format_violations(violations))
        return 1
    print("Repo structure contract: OK")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
