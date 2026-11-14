"""Append-only revision identity for annual disclosure evidence.

``logical_disclosure_key`` identifies one metric, scope and fiscal year across
revisions, independently of the raw ingest business key. ``version_id`` is
unique across the corpus. Every revision points to an already preserved parent
in the same logical family; original evidence is never updated in place.
Dates describe publication/effectiveness, not the fiscal year being reported.
No date or reason is inferred when the filing does not supply it.
"""

from __future__ import annotations

from datetime import date
from typing import Iterable, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DisclosureRevisionMetadata(BaseModel):
    """Optional companion metadata; absence keeps the legacy ingest contract.

    Originals may lack a publication date. Amendments and restatements require
    both a publication date and a backward pointer. ``revision_reason`` is the
    filing's explanation when known, otherwise absent. Forward links are derived
    from children and are never stored on the original row.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    logical_disclosure_key: str = Field(min_length=1)
    version_id: str = Field(min_length=1)
    revision_classification: Literal["original", "amended", "restated"]
    supersedes_version_id: Optional[str] = None
    publication_date: Optional[date] = None
    effective_date: Optional[date] = None
    revision_reason: Optional[str] = None

    @field_validator(
        "logical_disclosure_key",
        "version_id",
        "supersedes_version_id",
        "revision_reason",
    )
    @classmethod
    def _nonblank(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError(
                "revision identity and reason must be non-blank when supplied"
            )
        return value

    @field_validator("publication_date", "effective_date", mode="before")
    @classmethod
    def _calendar_dates_only(cls, value: object) -> object:
        if isinstance(value, str):
            parsed = date.fromisoformat(value)
            if parsed.isoformat() != value:
                raise ValueError("revision date text must use YYYY-MM-DD")
            return parsed
        if value is not None and type(value) is not date:
            raise ValueError("revision dates must be calendar dates, not epoch numbers")
        return value

    @model_validator(mode="after")
    def _consistent_revision(self) -> DisclosureRevisionMetadata:
        if self.revision_classification == "original":
            if self.supersedes_version_id is not None:
                raise ValueError("original disclosure cannot supersede a version")
        elif self.supersedes_version_id is None or self.publication_date is None:
            raise ValueError("revised disclosure requires parent and publication date")
        if self.supersedes_version_id == self.version_id:
            raise ValueError("a disclosure version cannot supersede itself")
        return self


def disclosure_revision_depths(
    revisions: Iterable[DisclosureRevisionMetadata],
) -> dict[str, int]:
    """Validate complete lineage and return edge distance from each original.

    Input order is immaterial. Missing/cross-family parents, repeated version
    identities, multiple originals and cycles raise ``ValueError``. Competing
    amendments may share a parent; analytics resolves their precedence without
    discarding either from history. Roots have depth zero, not an inferred date.
    """
    versions: dict[str, DisclosureRevisionMetadata] = {}
    originals: set[str] = set()
    for revision in revisions:
        if revision.version_id in versions:
            raise ValueError("duplicate disclosure version_id")
        versions[revision.version_id] = revision
        if revision.revision_classification == "original":
            if revision.logical_disclosure_key in originals:
                raise ValueError(
                    "multiple original versions for one logical disclosure"
                )
            originals.add(revision.logical_disclosure_key)

    for revision in versions.values():
        parent_id = revision.supersedes_version_id
        if parent_id is not None:
            if parent_id not in versions:
                raise ValueError("superseded disclosure version is missing")
            if (
                versions[parent_id].logical_disclosure_key
                != revision.logical_disclosure_key
            ):
                raise ValueError(
                    "superseded disclosure belongs to a different logical key"
                )

    depths: dict[str, int] = {}
    for version_id in versions:
        chain: list[str] = []
        visiting: set[str] = set()
        cursor: Optional[str] = version_id
        while cursor is not None and cursor not in depths:
            if cursor in visiting:
                raise ValueError("disclosure revision lineage contains a cycle")
            visiting.add(cursor)
            chain.append(cursor)
            cursor = versions[cursor].supersedes_version_id
        depth = depths[cursor] if cursor is not None else -1
        for item in reversed(chain):
            depth += 1
            depths[item] = depth
    return depths


__all__ = ["DisclosureRevisionMetadata", "disclosure_revision_depths"]
