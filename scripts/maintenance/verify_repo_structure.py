#!/usr/bin/env python3
"""Verify the worldenergydata repository structure contract.

The checker is intentionally conservative for #394 Phase 1: it does not move or
remove files. It classifies tracked/explicit paths against the approved root
contract and requires generated-output roots to carry temporary-exception
metadata before they are tolerated.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
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
class WorktreeStatusEntry:
    """A parsed non-ignored worktree status entry."""

    status: str
    path: str
    old_path: str | None = None


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


class RetirementSafeLoader(yaml.SafeLoader):
    """Read safe YAML while rejecting duplicate keys in every mapping."""


def _unique_retirement_mapping(loader: yaml.SafeLoader, node: yaml.MappingNode) -> dict:
    """Reject overwritten schema values before constructing a mapping."""
    loader.flatten_mapping(node)
    keys: set[object] = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node)
        try:
            if key in keys:
                raise yaml.constructor.ConstructorError(
                    None, None, "duplicate retirement mapping key", key_node.start_mark
                )
            keys.add(key)
        except TypeError as error:
            raise yaml.constructor.ConstructorError(
                None, None, "invalid retirement mapping key", key_node.start_mark
            ) from error
    return loader.construct_mapping(node)


RetirementSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_retirement_mapping
)


def _host_reference(value: str) -> bool:
    """Recognize qualified host or IPv4 syntax rather than version directories."""
    prefix = value.split("/", 1)[0].removesuffix(".")
    return (
        re.fullmatch(r"(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}", prefix) is not None
        or re.fullmatch(r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}", prefix) is not None
    )


def _relative_path_valid(value: object) -> bool:
    """Require an unambiguous relative path without machine-specific syntax."""
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    if any(character in value for character in ("\\", ":", "\x00", "\n", "\r")):
        return False
    return all(part not in ("", ".", "..") for part in value.split("/"))


def _substantive_string(value: object, minimum: int = 1) -> bool:
    """Reject missing, placeholder and insufficient metadata strings."""
    return (
        isinstance(value, str)
        and not _is_placeholder(value)
        and len(value.strip()) >= minimum
    )


def _retirement_disposition_valid(value: object) -> bool:
    """Validate disposition form without accessing a store or running commands."""
    if not isinstance(value, dict):
        return False
    if value.get("kind") == "reproducible":
        return set(value) == {"kind", "command"} and _substantive_string(
            value["command"]
        )
    if value.get("kind") != "cold-store":
        return False
    if set(value) != {"kind", "dataset_path", "digest_list"}:
        return False
    return all(
        _relative_path_valid(value[key]) and _substantive_string(value[key])
        for key in ("dataset_path", "digest_list")
    ) and not _host_reference(value["dataset_path"])


def _retirement_entry_valid(entry: object, contract: RepoStructureContract) -> bool:
    """Validate all required fields and reject unknown schema fields."""
    required = {"path", "sha256", "date", "reason", "disposition", "follow_up"}
    if not isinstance(entry, dict) or set(entry) != required:
        return False
    if not _relative_path_valid(entry["path"]):
        return False
    if root_for(entry["path"]) not in contract.generated_artifact_roots:
        return False
    if not isinstance(entry["sha256"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", entry["sha256"]
    ):
        return False
    entry_date = entry["date"]
    if type(entry_date) is date:
        entry_date = entry_date.isoformat()
    if not isinstance(entry_date, str) or not _DATE_RE.fullmatch(entry_date):
        return False
    try:
        date.fromisoformat(entry_date)
    except ValueError:
        return False
    follow_up_re = _URL_RE.pattern.replace("issues/", "(?:issues|pull)/")
    return (
        _substantive_string(entry["reason"], 30)
        and _retirement_disposition_valid(entry["disposition"])
        and isinstance(entry["follow_up"], str)
        and re.fullmatch(follow_up_re, entry["follow_up"]) is not None
    )


def load_retirements(
    path: Path | str, contract: RepoStructureContract
) -> tuple[dict[str, dict], list[RepoStructureViolation]]:
    """Load valid retirements; malformed entries never grant path exemptions."""
    register_path = Path(path)
    if not register_path.exists():
        return {}, []
    invalid = RepoStructureViolation(
        "invalid-retirement-entry", "config", register_path.as_posix()
    )
    try:
        loader = RetirementSafeLoader(register_path.read_text(encoding="utf-8"))
        try:
            payload = loader.get_single_data()
        finally:
            loader.dispose()
    except (OSError, UnicodeError, ValueError, yaml.YAMLError):
        return {}, [invalid]
    if not isinstance(payload, dict) or set(payload) != {"retirements"}:
        return {}, [invalid]
    if not isinstance(payload["retirements"], list):
        return {}, [invalid]
    entries: dict[str, dict] = {}
    violations: list[RepoStructureViolation] = []
    seen: set[str] = set()
    for entry in payload["retirements"]:
        if not _retirement_entry_valid(entry, contract):
            violations.append(invalid)
            continue
        entry_path = entry["path"]
        if entry_path in seen:
            violations.append(
                RepoStructureViolation(
                    "duplicate-retirement-entry", root_for(entry_path), entry_path
                )
            )
        else:
            entries[entry_path] = entry
            seen.add(entry_path)
    return entries, violations


def validate_retirements(
    retirements: dict[str, dict],
    contract: RepoStructureContract,
    tracked_paths: Iterable[str],
    entries: Iterable[WorktreeStatusEntry],
) -> list[RepoStructureViolation]:
    """Check tracked-path and classification consistency on every default run."""
    if not retirements:
        return []
    leaving = {
        entry.old_path if "R" in entry.status and entry.old_path else entry.path
        for entry in entries
        if "D" in entry.status or "R" in entry.status
    }
    still_tracked = set(tracked_paths) - leaving
    allowed_paths = {
        path
        for metadata in contract.temporary_exceptions.values()
        if isinstance(metadata.get("allowed_paths"), list)
        for path in metadata["allowed_paths"]
        if isinstance(path, str)
    }
    violations: list[RepoStructureViolation] = []
    for path in sorted(retirements):
        if path in still_tracked:
            violations.append(
                RepoStructureViolation(
                    "retirement-entry-for-tracked-path", root_for(path), path
                )
            )
        if path in allowed_paths:
            violations.append(
                RepoStructureViolation(
                    "retired-path-still-allowed", root_for(path), path
                )
            )
    return violations


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
    paths: Iterable[str],
    contract: RepoStructureContract,
    retired_paths: Iterable[str] = (),
) -> list[RepoStructureViolation]:
    """Validate repository-relative paths against the root contract."""

    retired = set(retired_paths)
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
            elif path not in retired and not _path_allowed_by_exception(path, metadata):
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


def _parse_status_path(raw_path: str) -> str:
    """Unquote a porcelain path while tolerating odd shell-like input."""

    try:
        parsed = shlex.split(raw_path)
    except ValueError:
        parsed = []
    return parsed[0] if len(parsed) == 1 else raw_path


def parse_git_status_entries(output: str) -> list[WorktreeStatusEntry]:
    """Parse porcelain-like ``git status --short`` output into status entries.

    Status codes are preserved so Phase-1 policy can reject deletion/relocation
    of generated-looking tracked artifacts instead of treating them like normal
    path classification.
    """

    entries: list[WorktreeStatusEntry] = []
    for raw_line in output.splitlines():
        if not raw_line or raw_line.startswith("## ") or len(raw_line) < 4:
            continue
        status = raw_line[:2]
        path = raw_line[3:]
        old_path: str | None = None
        if " -> " in path:
            old_raw, new_raw = path.rsplit(" -> ", 1)
            old_path = _parse_status_path(old_raw)
            path = new_raw
        path = _parse_status_path(path)
        if path:
            entries.append(
                WorktreeStatusEntry(status=status, path=path, old_path=old_path)
            )
    return entries


def parse_git_status_paths(output: str) -> list[str]:
    """Parse porcelain-like ``git status --short`` output into destination paths."""

    return [entry.path for entry in parse_git_status_entries(output)]


def git_head_digest(repo_root: Path, path: str) -> str | None:
    """Hash committed blob bytes; unreadable HEAD content cannot authorize removal."""
    result = subprocess.run(
        ["git", "cat-file", "blob", f"HEAD:{path}"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return hashlib.sha256(result.stdout).hexdigest() if result.returncode == 0 else None


def validate_worktree_status_entries(
    entries: Iterable[WorktreeStatusEntry],
    contract: RepoStructureContract,
    retirements: dict[str, dict] | None = None,
    repo_root: Path | None = None,
) -> list[RepoStructureViolation]:
    """Validate status-specific Phase-1 constraints for worktree entries."""

    violations: list[RepoStructureViolation] = []
    emitted: set[RepoStructureViolation] = set()

    def add(violation: RepoStructureViolation) -> None:
        if violation not in emitted:
            emitted.add(violation)
            violations.append(violation)

    for entry in entries:
        status = entry.status
        path_root = root_for(entry.path)
        old_root = root_for(entry.old_path) if entry.old_path else ""
        touches_generated_root = (
            path_root in contract.generated_artifact_roots
            or old_root in contract.generated_artifact_roots
        )
        if not touches_generated_root:
            continue
        if "D" in status or "R" in status:
            if entry.old_path and "R" in status:
                violation_path = f"{entry.old_path} -> {entry.path}"
                violation_root = old_root or path_root
            else:
                violation_path = entry.path
                violation_root = path_root or old_root
            leaving_path = (
                entry.old_path if "R" in status and entry.old_path else entry.path
            )
            retirement = (retirements or {}).get(leaving_path)
            if retirement is not None and repo_root is not None:
                digest = git_head_digest(repo_root, leaving_path)
                if digest is not None:
                    if digest != retirement["sha256"]:
                        add(
                            RepoStructureViolation(
                                "retirement-digest-mismatch",
                                violation_root,
                                violation_path,
                            )
                        )
                    continue
            add(
                RepoStructureViolation(
                    "generated-artifact-deletion-or-relocation",
                    violation_root,
                    violation_path,
                )
            )
    return violations


def git_worktree_status_entries(repo_root: Path) -> list[WorktreeStatusEntry]:
    """Return non-ignored working-tree status entries visible to git status."""

    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=repo_root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return parse_git_status_entries(result.stdout)


def git_worktree_paths(repo_root: Path) -> list[str]:
    """Return non-ignored working-tree paths visible to git status."""

    return [entry.path for entry in git_worktree_status_entries(repo_root)]


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
        "--retirements",
        type=Path,
        default=Path("config/generated_retirements.yml"),
        help="Path to the generated retirement register",
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
    retirements, violations = load_retirements(args.retirements, contract)
    if args.paths is not None:
        paths = args.paths
        violations.extend(validate_paths(paths, contract, retirements))
        violations.extend(validate_retirements(retirements, contract, [], []))
    else:
        tracked_paths = git_tracked_paths(repo_root)
        worktree_entries = git_worktree_status_entries(repo_root)
        paths = tracked_paths + [entry.path for entry in worktree_entries]
        violations.extend(validate_paths(paths, contract, retirements))
        violations.extend(
            validate_retirements(retirements, contract, tracked_paths, worktree_entries)
        )
        violations.extend(
            validate_worktree_status_entries(
                worktree_entries, contract, retirements, repo_root
            )
        )
    if violations:
        print(format_violations(violations))
        return 1
    print("Repo structure contract: OK")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
