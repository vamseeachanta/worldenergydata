"""Append-only annual-disclosure revision identity (issue 344).

Contract source: docs/plans/2026-04-23-issue-344-restatement-version-lineage-for-annual-disclosure-records.md,
Scope Boundaries. Identities are caller-supplied opaque strings, never inferred
from monetary values, citations or lexical version order.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class DisclosureRevision(BaseModel):
    """One immutable statement version; only the backward edge is persisted."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    logical_disclosure_key: str
    version_id: str
    revision_classification: Literal["original", "amended", "restated"]
    supersedes_version_id: str | None = None
    publication_date: date | None = None
    effective_date: date | None = None
    revision_reason: str | None = None

    @field_validator(
        "logical_disclosure_key",
        "version_id",
        "supersedes_version_id",
        "revision_reason",
    )
    @classmethod
    def _nonblank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("revision strings must be non-blank when supplied")
        return value

    @model_validator(mode="after")
    def _check_parent(self) -> DisclosureRevision:
        if self.revision_classification == "original":
            if self.supersedes_version_id is not None:
                raise ValueError("original versions cannot supersede another version")
        elif self.supersedes_version_id is None or self.publication_date is None:
            raise ValueError("revised versions require a parent and publication_date")
        if self.supersedes_version_id == self.version_id:
            raise ValueError("a version cannot supersede itself")
        return self


def revision_lineage_depths(
    records: Iterable[Any], *, business_key: Callable[[Any], tuple]
) -> dict[str, int]:
    """Validate a complete corpus and return root-relative depth per version.

    Exact replays are idempotent. Version IDs are corpus-wide; a logical key
    belongs to one business key and one original. Forks are retained. Missing
    parents, cycles, identity reuse and mixed legacy/versioned keys fail closed.
    """
    by_id = _index_versions(list(records), business_key)
    for row in by_id.values():
        revision = row.revision
        parent_id = revision.supersedes_version_id
        if parent_id is None:
            continue
        if parent_id not in by_id:
            raise ValueError("superseded version is missing from the corpus")
        if (
            by_id[parent_id].revision.logical_disclosure_key
            != revision.logical_disclosure_key
        ):
            raise ValueError("superseded version belongs to another logical disclosure")
    return _lineage_depths(by_id)


def _index_versions(
    rows: list[Any], business_key: Callable[[Any], tuple]
) -> dict[str, Any]:
    """Bind logical and version identities before traversing parent edges."""
    by_id: dict[str, Any] = {}
    logical_keys: dict[str, tuple] = {}
    business_keys: dict[tuple, str] = {}
    roots: dict[str, str] = {}
    legacy_keys = {business_key(row) for row in rows if row.revision is None}
    for row in rows:
        revision = row.revision
        if revision is None:
            continue
        key = business_key(row)
        logical = revision.logical_disclosure_key
        if key in legacy_keys:
            raise ValueError("versioned and unversioned rows share a business key")
        if logical in logical_keys and logical_keys[logical] != key:
            raise ValueError("logical disclosure key crosses business keys")
        if key in business_keys and business_keys[key] != logical:
            raise ValueError("business key has competing logical disclosure keys")
        logical_keys[logical], business_keys[key] = key, logical
        if revision.version_id in by_id and by_id[revision.version_id] != row:
            raise ValueError("version_id is reused for different evidence")
        by_id[revision.version_id] = row
        if revision.supersedes_version_id is None:
            if logical in roots and roots[logical] != revision.version_id:
                raise ValueError("logical disclosure key has multiple originals")
            roots[logical] = revision.version_id

    return by_id


def _lineage_depths(by_id: dict[str, Any]) -> dict[str, int]:
    """Follow parent edges iteratively, including chains beyond recursion limits."""
    depths: dict[str, int] = {}
    for version_id in by_id:
        trail: list[str] = []
        seen: set[str] = set()
        cursor = version_id
        while cursor not in depths:
            if cursor in seen:
                raise ValueError("revision lineage contains a cycle")
            trail.append(cursor)
            seen.add(cursor)
            parent = by_id[cursor].revision.supersedes_version_id
            if parent is None:
                # Root depth zero is the ordering convention in the issue 344 plan.
                depth = -1
                break
            cursor = parent
        else:
            depth = depths[cursor]
        for item in reversed(trail):
            depth += 1
            depths[item] = depth
    return depths
