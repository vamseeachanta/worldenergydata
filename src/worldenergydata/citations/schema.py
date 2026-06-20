"""Calc-citation-contract schema + fail-closed validator for worldenergydata.

Mirrors the digitalmodel pilot (``src/digitalmodel/citations/schema.py``) per
worldenergydata#361 and the workspace-hub ``calc-citation-contract`` rule.

Contract summary
----------------
Every standards-derived constant or formula used in a calc emits a ``Citation``
recording *which standard / publisher / revision* the number came from. The
citation rides on a sidecar (see ``sidecar.py``) so the primary numeric payload
is never mutated -- preserving downstream-consumer compatibility (#361 AC).

Per workspace-hub #2481 decisions:
- D2: fail-closed at calc time; ``CitationResolutionError`` carries ``code_id``
  so an operator can retarget a cited constant rather than silently disabling
  the citation when a wiki page is moved or archived.
- D3: direct file read for v1; migration to the MCP resolver (#2400) is a later
  change that does not touch this schema.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

_WIKI_PATH_PREFIX = "wikis/"
_FORBIDDEN_SEGMENTS = ("..", "")


class CitationResolutionError(RuntimeError):
    """Raised when a citation cannot be resolved against the live wiki.

    The message always carries ``code_id`` so operators can retarget a cited
    constant (point it at a moved/renamed standards page) rather than disabling
    the citation outright.
    """

    def __init__(self, *, code_id: str, wiki_path: str, reason: str) -> None:
        self.code_id = code_id
        self.wiki_path = wiki_path
        self.reason = reason
        super().__init__(
            f"CitationResolutionError: code_id={code_id!r} "
            f"wiki_path={wiki_path!r} reason={reason}"
        )


class CitationValidationError(ValueError):
    """Raised at schema-construction time for structurally invalid citations."""


@dataclass(frozen=True)
class Citation:
    """Provenance record for a single standards-derived constant or formula.

    Required fields (all non-empty strings):
        code_id    -- canonical standard / source identifier (e.g. "30-cfr-250").
        publisher  -- the issuing body (e.g. "BSEE", "EIA").
        revision   -- revision / edition / as-of marker (e.g. "2024", "2025-10").
        section    -- human-readable locator within the source.
        wiki_path  -- path to the backing wiki page (``wikis/...`` canonical form).

    Optional:
        units      -- units of the cited value (dimensionless constants -> "fraction").
        retrieved  -- retrieval / as-of date (ISO-8601) for time-varying sources
                      such as price decks.
        note       -- free-text derivation note.
    """

    code_id: str
    publisher: str
    revision: str
    section: str
    wiki_path: str
    units: str = ""
    retrieved: str = ""
    note: str = ""

    def __post_init__(self) -> None:
        for f in ("code_id", "publisher", "revision", "section", "wiki_path"):
            v = getattr(self, f)
            if not isinstance(v, str) or not v.strip():
                raise CitationValidationError(
                    f"Citation.{f} must be a non-empty string"
                )
        _validate_wiki_path(self.wiki_path)

    def to_dict(self) -> dict[str, str]:
        """Flat, JSON-serializable representation for sidecar emission."""
        return {
            "code_id": self.code_id,
            "publisher": self.publisher,
            "revision": self.revision,
            "section": self.section,
            "wiki_path": self.wiki_path,
            "units": self.units,
            "retrieved": self.retrieved,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Citation":
        """Reconstruct a Citation from its ``to_dict`` form (sidecar round-trip)."""
        return cls(
            code_id=data["code_id"],
            publisher=data["publisher"],
            revision=data["revision"],
            section=data["section"],
            wiki_path=data["wiki_path"],
            units=data.get("units", ""),
            retrieved=data.get("retrieved", ""),
            note=data.get("note", ""),
        )


@dataclass(frozen=True)
class CitedValue:
    """A numeric value bundled with the citation that justifies it."""

    value: float
    citation: Citation
    units: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "units": self.units,
            "citation": self.citation.to_dict(),
        }


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


def _read_frontmatter(path: Path) -> Mapping[str, Any]:
    text = path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    # Minimal flat-scalar YAML-frontmatter parser; avoids a yaml dependency for
    # the three fields this validator needs (matches the digitalmodel pilot).
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        value = rest.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        fm[key] = value
    return fm


def validate_citation(citation: Citation, *, repo_root: Optional[Path] = None) -> None:
    """Fail-closed resolution check against the backing wiki page.

    Raises ``CitationResolutionError`` if:
      - the cited wiki page does not exist, or
      - its frontmatter lacks ``code_id`` / ``publisher`` / ``revision``, or
      - any of those three fields disagree with the citation.

    When ``repo_root`` is None the resolver's precedence chain is used
    (``LLM_WIKI_PATH`` etc.). When ``repo_root`` is supplied the path is joined
    directly, trying both the standalone (``<root>/wikis/...``) and
    workspace-hub-overlay (``<root>/knowledge/wikis/...``) layouts.

    The ``section`` locator is NOT validated -- it is a human-readable field.
    """
    if repo_root is None:
        from worldenergydata.citations.resolver import resolve_wiki_path

        path = resolve_wiki_path(citation.wiki_path)
    else:
        path = _join_with_layout_detection(Path(repo_root), citation.wiki_path)

    if not path.is_file():
        raise CitationResolutionError(
            code_id=citation.code_id,
            wiki_path=citation.wiki_path,
            reason="page_missing",
        )
    fm = _read_frontmatter(path)
    for field_name in ("code_id", "publisher", "revision"):
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


def _join_with_layout_detection(base: Path, wiki_path: str) -> Path:
    """Join ``base`` + ``wiki_path`` handling standalone and overlay layouts."""
    standalone = base / wiki_path
    if standalone.is_file():
        return standalone
    overlay = base / "knowledge" / wiki_path
    if overlay.is_file():
        return overlay
    return standalone
