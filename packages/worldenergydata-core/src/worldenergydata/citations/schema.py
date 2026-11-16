"""Citation schema + fail-closed validator.

Fail-closed at calculation time; CitationResolutionError carries code_id.
Uses direct file reads; a remote resolver can follow #2400 without schema changes.

Contract: docs/standards/calc-output-citation.md (workspace-hub).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from numbers import Real
from pathlib import Path
from typing import Optional

_WIKI_PATH_PREFIX = "wikis/"
_FORBIDDEN_SEGMENTS = ("..", "")
_IDENTITY_FIELDS = ("code_id", "publisher", "revision")


class CitationResolutionError(RuntimeError):
    """Raised when a citation cannot be resolved against the live wiki.

    Message always carries code_id so operators can retarget a cited constant
    rather than disabling the citation when a wiki page is moved or archived.
    """

    def __init__(self, *, code_id: str, wiki_path: str, reason: str) -> None:
        self.code_id = code_id
        self.wiki_path = wiki_path
        self.reason = reason
        super().__init__(
            f"CitationResolutionError: code_id={code_id!r} wiki_path={wiki_path!r} reason={reason}"
        )


class CitationValidationError(ValueError):
    """Raised at schema-construction time for structurally invalid citations."""


@dataclass(frozen=True)
class Citation:
    code_id: str
    publisher: str
    revision: str
    section: str
    wiki_path: str
    note: str = ""
    # Routing metadata is retained on the sidecar for downstream consumers.
    source_sibling: str = "generic"
    source_project: Optional[str] = None

    def __post_init__(self) -> None:
        for f in ("code_id", "publisher", "revision", "section", "wiki_path"):
            v = getattr(self, f)
            if not isinstance(v, str) or not v.strip():
                raise CitationValidationError(
                    f"Citation.{f} must be a non-empty string"
                )
        # Source routing fields must be structurally valid.
        if not isinstance(self.source_sibling, str) or not self.source_sibling.strip():
            raise CitationValidationError(
                "Citation.source_sibling must be a non-empty string "
                "('generic' or another source slug)"
            )
        # source_project: optional, but when set must be non-empty string.
        if self.source_project is not None:
            if (
                not isinstance(self.source_project, str)
                or not self.source_project.strip()
            ):
                raise CitationValidationError(
                    "Citation.source_project, when set, must be a non-empty string"
                )
        _validate_wiki_path(self.wiki_path)


@dataclass(frozen=True)
class CitedValue:
    value: float
    citation: Citation
    units: str = ""

    def __post_init__(self) -> None:
        value = self.value
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not math.isfinite(value)
        ):
            raise CitationValidationError(
                f"CitedValue.value must be a finite number: got {value!r}"
            )


def _validate_wiki_path(wiki_path: str) -> None:
    if not wiki_path.startswith(_WIKI_PATH_PREFIX):
        raise CitationValidationError(
            f"wiki_path must be under {_WIKI_PATH_PREFIX!r}: got {wiki_path!r}"
        )
    if any(seg in _FORBIDDEN_SEGMENTS for seg in wiki_path.split("/")):
        raise CitationValidationError(
            f"wiki_path may not contain empty or '..' segments: got {wiki_path!r}"
        )
    if "\\" in wiki_path:
        raise CitationValidationError(
            f"wiki_path must use forward slashes: got {wiki_path!r}"
        )


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict[str, str], set[str]]:
    """Return top-level scalar fields and the names of repeated top-level keys.

    Minimal YAML-frontmatter parser covering the fields this validator needs;
    avoids adding a yaml dependency for the pilot. Only unindented ``key: value``
    lines count, so nested mappings cannot stand in for the page identity.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, set()
    fm: dict[str, str] = {}
    duplicates: set[str] = set()
    for line in m.group(1).splitlines():
        if not line or line[0].isspace() or line.startswith("#") or ":" not in line:
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        value = rest.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        if key in fm:
            duplicates.add(key)
        fm[key] = value
    return fm, duplicates


def _resolution_error(citation: Citation, reason: str) -> CitationResolutionError:
    return CitationResolutionError(
        code_id=citation.code_id, wiki_path=citation.wiki_path, reason=reason
    )


def _contained_page(base: Path, path: Path, citation: Citation) -> Path:
    """Resolve the selected page and require it inside the resolved root."""
    try:
        resolved_base = base.resolve(strict=True)
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise _resolution_error(citation, "page_missing") from error
    if not resolved.is_relative_to(resolved_base):
        raise _resolution_error(citation, "page_outside_root")
    return resolved


def _read_page(path: Path, citation: Citation) -> str:
    """Read the page; failures keep the citation identity, not the local path."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        reason = f"page_unreadable:{type(error).__name__}"
        raise _resolution_error(citation, reason) from error


def _join_with_layout_detection(base: Path, wiki_path: str) -> Path:
    """Join base + wiki_path handling both standalone and workspace-hub layouts.

    Canonical wiki_path form is `wikis/<domain>/...` (no knowledge/ prefix).
    Tries the standalone layout first, then the workspace-hub overlay layout.
    Returns the standalone-form path (for error reporting) when neither hits.
    """
    standalone = base / wiki_path
    if standalone.is_file():
        return standalone
    overlay = base / "knowledge" / wiki_path
    if overlay.is_file():
        return overlay
    return standalone


def validate_citation(
    citation: Citation, *, repo_root: Path | str | None = None
) -> None:
    """Fail-closed resolution check.

    Raises CitationResolutionError if:
    - the cited wiki page does not exist, or resolves outside the wiki root
    - the page cannot be read or decoded as UTF-8
    - the top-level frontmatter lacks or repeats code_id / publisher / revision
    - any of the three fields disagree with the citation

    When repo_root is None, defers to the resolver (LLM_WIKI_PATH precedence chain).
    When repo_root is provided, joins directly but tries both standalone and
    workspace-hub-overlay layouts to find the file. On both routes the selected
    page, after following symlinks, must lie inside the resolved root.

    Does NOT validate the `section` locator — that's a human-readable field.
    """
    if repo_root is None:
        # Defer to resolver for path resolution
        from worldenergydata.citations.resolver import resolve_wiki_base

        try:
            base = resolve_wiki_base()
        except CitationResolutionError as error:
            raise _resolution_error(citation, error.reason) from error
    else:
        base = Path(repo_root)
    path = _join_with_layout_detection(base, citation.wiki_path)
    if not path.is_file():
        raise _resolution_error(citation, "page_missing")
    path = _contained_page(base, path, citation)
    fm, duplicates = _parse_frontmatter(_read_page(path, citation))
    for field_name in _IDENTITY_FIELDS:
        if field_name in duplicates:
            raise _resolution_error(citation, f"frontmatter_duplicate:{field_name}")
    for field_name in _IDENTITY_FIELDS:
        expected = getattr(citation, field_name)
        actual = fm.get(field_name)
        if actual is None:
            raise CitationResolutionError(
                code_id=citation.code_id,
                wiki_path=citation.wiki_path,
                reason=f"frontmatter_missing:{field_name}",
            )
        if actual != expected:
            raise CitationResolutionError(
                code_id=citation.code_id,
                wiki_path=citation.wiki_path,
                reason=f"frontmatter_mismatch:{field_name}:{actual!r}!={expected!r}",
            )
