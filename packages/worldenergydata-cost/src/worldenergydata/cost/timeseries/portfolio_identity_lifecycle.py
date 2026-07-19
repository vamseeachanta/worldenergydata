"""Append-only lifecycle primitives for portfolio identities."""

from __future__ import annotations

import csv
import re
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

MIGRATION_LEDGER = Path(
    "data/modules/cost/curated/portfolio_identity_migrations.v2.csv"
)
MIGRATION_FIELDS = (
    "migration_id",
    "entity_kind",
    "opaque_id",
    "source_key",
    "old_locator_json",
    "old_locator_sha256",
    "new_locator_json",
    "new_locator_sha256",
    "disposition",
    "reason",
    "provenance",
    "effective_date",
    "replacement_id",
)


def digest_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


class IdentityState(BaseModel):
    """Minimal immutable state needed to validate identity transitions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    entity_kind: Literal["project", "award", "requirement"]
    opaque_id: str
    source_key: str
    locator_json: str
    state: Literal["active", "tombstoned"]
    active: bool
    no_reuse: bool

    @model_validator(mode="after")
    def _validate_state(self) -> "IdentityState":
        if self.active != (self.state == "active"):
            raise ValueError("identity state and active flag disagree")
        if not self.no_reuse:
            raise ValueError("identity must retain no-reuse reservation")
        return self


class IdentityMigration(BaseModel):
    """Append-only evidence for one identity binding transition."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    migration_id: str
    entity_kind: Literal["project", "award", "requirement"]
    opaque_id: str
    source_key: str
    old_locator_json: str
    old_locator_sha256: str
    new_locator_json: str | None
    new_locator_sha256: str | None
    disposition: Literal[
        "correction",
        "tombstone",
        "replacement",
        "split_rejected",
        "merge_rejected",
    ]
    reason: str
    provenance: str
    effective_date: date
    replacement_id: str | None

    @field_validator(
        "new_locator_json", "new_locator_sha256", "replacement_id", mode="before"
    )
    @classmethod
    def _empty_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("old_locator_sha256", "new_locator_sha256")
    @classmethod
    def _require_hash(cls, value: str | None) -> str | None:
        if value is not None and re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError("migration locator hash must be lowercase 64-hex")
        return value

    @model_validator(mode="after")
    def _require_evidence(self) -> "IdentityMigration":
        if not self.reason or not self.provenance:
            raise ValueError("migration requires reason and provenance")
        if self.disposition == "correction" and None in (
            self.new_locator_json,
            self.new_locator_sha256,
        ):
            raise ValueError("correction requires a new binding")
        if self.disposition == "tombstone" and any(
            value is not None
            for value in (self.new_locator_json, self.new_locator_sha256)
        ):
            raise ValueError("tombstone cannot create a new binding")
        return self


def _validate_common_transition(
    before: IdentityState,
    after: IdentityState,
    migration: IdentityMigration,
) -> None:
    if before.state == "tombstoned":
        raise ValueError("tombstoned identity cannot be reused")
    if (before.entity_kind, before.opaque_id, before.source_key) != (
        after.entity_kind,
        after.opaque_id,
        after.source_key,
    ):
        raise ValueError("opaque ID and source key must remain reserved")
    if (migration.entity_kind, migration.opaque_id, migration.source_key) != (
        before.entity_kind,
        before.opaque_id,
        before.source_key,
    ):
        raise ValueError("migration identity does not match current binding")
    if migration.old_locator_json != before.locator_json or (
        migration.old_locator_sha256 != digest_text(before.locator_json)
    ):
        raise ValueError("migration old binding does not match current locator")


def validate_identity_transition(
    before: IdentityState,
    after: IdentityState,
    migration: IdentityMigration,
) -> IdentityState:
    """Fail closed unless one curated migration explains the exact transition."""

    _validate_common_transition(before, after, migration)
    if migration.disposition == "correction":
        if after.state != "active" or after.locator_json != migration.new_locator_json:
            raise ValueError("correction terminal binding mismatch")
        if migration.new_locator_sha256 != digest_text(after.locator_json):
            raise ValueError("correction new locator hash mismatch")
        if migration.replacement_id is not None:
            raise ValueError("correction cannot name a replacement")
    elif migration.disposition in ("tombstone", "replacement"):
        if after.state != "tombstoned" or after.locator_json != before.locator_json:
            raise ValueError("tombstone must preserve identity and prevent reuse")
        if migration.disposition == "replacement" and migration.replacement_id in (
            None,
            before.opaque_id,
        ):
            raise ValueError("replacement must name a distinct identity")
        if (
            migration.disposition == "tombstone"
            and migration.replacement_id is not None
        ):
            raise ValueError("tombstone cannot name a replacement")
    elif migration.disposition in ("split_rejected", "merge_rejected"):
        if after != before or any(
            value is not None
            for value in (
                migration.new_locator_json,
                migration.new_locator_sha256,
                migration.replacement_id,
            )
        ):
            raise ValueError("rejected split or merge must preserve current binding")
    return after


def validate_identity_migration_ledger(root: Path) -> tuple[IdentityMigration, ...]:
    """Read the append-only ledger without exposing a rewrite operation."""

    with (root / MIGRATION_LEDGER).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != MIGRATION_FIELDS:
            raise ValueError("identity migration ledger header mismatch")
        migrations = tuple(IdentityMigration.model_validate(row) for row in reader)
    ids = [row.migration_id for row in migrations]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate migration ID")
    return migrations
