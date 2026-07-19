"""Fail-closed manifest validation for the portfolio cost-map contract."""

from __future__ import annotations

import json
import re
import subprocess
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

V1_MANIFEST = Path("data/modules/cost/curated/cost_map_contract_manifest.v1.json")
V1_MANIFEST_SHA256 = "f5dc2fce6c0ee376d577f8dcebb70511c756bd28264744600dc018deab5fcf9e"


def _digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def _safe_relative(value: str) -> Path:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("manifest path must be a safe repository-relative path")
    return Path(*path.parts)


def _git(root: Path, *arguments: str) -> bytes:
    try:
        return subprocess.run(
            ["git", *arguments], cwd=root, check=True, capture_output=True
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("trusted producer history unavailable") from error


def _has_commit(root: Path, commit: str) -> bool:
    try:
        _git(root, "cat-file", "-e", f"{commit}^{{commit}}")
        return True
    except ValueError:
        return False


def _hydrate_main_history(root: Path, commit: str) -> None:
    if _has_commit(root, commit):
        return
    if _git(root, "rev-parse", "--is-shallow-repository").strip() != b"true":
        raise ValueError("producer commit remains unavailable")
    _git(root, "fetch", "--no-tags", "--unshallow", "origin", "main")
    if not _has_commit(root, commit):
        raise ValueError("producer commit remains unavailable")


def _validate_hash_rows(root: Path, rows: list[dict[str, str]]) -> None:
    seen: set[str] = set()
    for row in rows:
        relative = row["path"]
        if relative in seen:
            raise ValueError("manifest paths must be unique within a section")
        seen.add(relative)
        if _digest((root / _safe_relative(relative)).read_bytes()) != row["sha256"]:
            raise ValueError(f"v1 artifact hash mismatch: {relative}")


def _validate_producer(root: Path, manifest: dict[str, Any]) -> None:
    commit = manifest["producer"]["commit"]
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("producer commit must be full 40-hex")
    _hydrate_main_history(root, commit)
    _git(root, "merge-base", "--is-ancestor", commit, "HEAD")
    executable_rows = [row for row in manifest["inputs"] if row["path"].endswith(".py")]
    for row in executable_rows:
        current = (root / _safe_relative(row["path"])).read_bytes()
        if _git(root, "show", f"{commit}:{row['path']}") != current:
            raise ValueError(f"producer executable blob mismatch: {row['path']}")


def validate_v1_contract(root: Path) -> dict[str, Any]:
    """Validate the immutable v1 pack against its external trust root."""

    manifest_bytes = (root / V1_MANIFEST).read_bytes()
    if _digest(manifest_bytes) != V1_MANIFEST_SHA256:
        raise ValueError("v1 manifest trust root mismatch")
    manifest: dict[str, Any] = json.loads(manifest_bytes)
    _validate_hash_rows(root, [manifest["schema"]])
    _validate_hash_rows(root, manifest["inputs"])
    _validate_hash_rows(root, manifest["outputs"])
    _validate_producer(root, manifest)
    return manifest
