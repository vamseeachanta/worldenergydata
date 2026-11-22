"""Literal catalog claims and bounded, read-only dataset path checks (#368)."""

from __future__ import annotations

import os
import re
import stat
from collections import deque
from pathlib import Path, PurePosixPath
from typing import Callable

_CHECKBOX = re.compile(r"^\s*[-*]\s+\[[ xX]\]\s+(.*\S)\s*$")
_CODE = re.compile(r"`[^`\n]*`")
_CLAIM = re.compile(r"catalog entry resolves:\s*`([^`]+)`", re.IGNORECASE)


class CatalogError(ValueError):
    """The selected catalog cannot provide trustworthy lookup evidence."""


def literal_path(token: str) -> str | None:
    """Normalize a literal relative path; reject traversal and command syntax."""
    path = PurePosixPath(token)
    if (
        not token
        or not path.name
        or path.anchor
        or path.drive
        or ".." in path.parts
        or any(c.isspace() or c in "`*?<>|$;:\\\x00" for c in token)
        or token.endswith(("/", "/."))
    ):
        return None
    return path.as_posix()


def parse_catalog_claim(line: str) -> tuple[str, str | None] | None:
    """Return (claim, raw token) for catalog checkboxes, including unsupported ones.

    Terminology inside code spans is not prose. A token is returned only for
    the complete explicit grammar; callers must validate it before lookup.
    Other catalog wording is unsupported and still needs ordinary path checks.
    """
    checkbox = _CHECKBOX.fullmatch(line)
    if checkbox is None or not re.search(r"\bcatalog\b", _CODE.sub(" ", line), re.I):
        return None
    claim = checkbox.group(1).strip()
    match = _CLAIM.fullmatch(claim)
    return claim, match.group(1) if match else None


def _resolution_status(root: Path, relative: str) -> str:
    """Inspect contained components, rejecting link escapes before any external stat.

    Resolve links incrementally: Path.resolve on the complete path could follow
    a second link outside the root. Non-symlink reparse points, including Windows
    junctions, remain unverified. No target contents are opened.
    """
    pending = deque(PurePosixPath(relative).parts)
    current = root
    followed = 0
    try:
        while pending:
            component = pending.popleft()
            if component == "..":
                current = current.parent
                if not current.is_relative_to(root):
                    return "outside_allowed_root"
                continue
            candidate = current / component
            if not candidate.is_relative_to(root):
                return "outside_allowed_root"
            info = candidate.lstat()
            if stat.S_ISLNK(info.st_mode):
                followed += 1
                if followed > 40:
                    return "resolution_error"
                target = candidate.parent / os.readlink(candidate)
                if not target.is_relative_to(root):
                    return "outside_allowed_root"
                pending.extendleft(reversed(target.relative_to(root).parts))
                current = root
            elif (
                getattr(info, "st_file_attributes", 0)
                & stat.FILE_ATTRIBUTE_REPARSE_POINT
            ):
                return "resolution_error"
            else:
                if pending and not stat.S_ISDIR(info.st_mode):
                    return "missing_in_allowed_root"
                current = candidate
        return "present"
    except (FileNotFoundError, NotADirectoryError):
        return "missing_in_allowed_root"
    except (OSError, RuntimeError):
        return "resolution_error"


def load_catalog(path: Path) -> dict[str, list[dict]]:
    """Load dataset paths only; malformed input is never an empty clean catalog."""
    # YAML is needed only for the opt-in catalog check.
    import yaml

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise CatalogError("catalog could not be read as safe YAML") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("modules"), dict):
        raise CatalogError("catalog modules must be a mapping")
    entries: dict[str, list[dict]] = {}
    for module in payload["modules"].values():
        if not isinstance(module, dict) or not isinstance(module.get("datasets"), list):
            raise CatalogError("catalog module datasets must be a list")
        for entry in module["datasets"]:
            if (
                not isinstance(entry, dict)
                or not isinstance(entry.get("path"), str)
                or not entry["path"].strip()
            ):
                raise CatalogError("catalog dataset path must be a nonempty string")
            key = literal_path(entry["path"]) or entry["path"]
            entries.setdefault(key, []).append({**entry, "path": key})
    return entries


def make_catalog_checker(path: Path, repo_root: Path) -> Callable[[str], str]:
    """Select one catalog; inspect claimed dataset targets only within repo_root.

    Duplicate entries with identical metadata are accepted. Conflicting metadata
    for the same normalized path cannot establish an unambiguous catalog claim.
    """
    root = repo_root.resolve()
    path = Path(os.path.abspath(path))
    if not path.is_relative_to(root):
        raise CatalogError("catalog must be inside the allowed root")
    if _resolution_status(root, path.relative_to(root).as_posix()) != "present":
        raise CatalogError("catalog is unavailable inside the allowed root")
    entries = load_catalog(path)

    def check(token: str) -> str:
        relative = literal_path(token)
        if relative is None:
            return "invalid_claim"
        matches = entries.get(relative, [])
        if not matches:
            return "not_catalogued"
        if any(entry != matches[0] for entry in matches[1:]):
            return "conflicting_duplicate"
        return _resolution_status(root, relative)

    return check
