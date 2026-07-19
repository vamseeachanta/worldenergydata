"""Cross-version validation for append-only portfolio identity updates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from worldenergydata.cost.timeseries.portfolio_identity_lifecycle import (
    MIGRATION_LEDGER,
    IdentityMigration,
    IdentityState,
    digest_text,
    validate_identity_migration_ledger,
    validate_identity_transition,
)


@dataclass(frozen=True)
class IdentityUpdateResult:
    before_projects: Any
    after_projects: Any
    before_awards: Any
    after_awards: Any
    before_requirements: tuple[Any, ...]
    after_requirements: tuple[Any, ...]
    appended_migrations: tuple[IdentityMigration, ...]


StateRecord = tuple[IdentityState, str, str]


def _states(result: Any, kind: str) -> dict[str, StateRecord]:
    key_name = f"source_{kind}_key"
    id_name = f"{kind}_id"
    source_by_key = {getattr(row, key_name): row for row in result.sources}
    states: dict[str, StateRecord] = {}
    for identity in result.identities:
        source_key = getattr(identity, key_name)
        source = source_by_key[source_key]
        opaque_id = getattr(identity, id_name)
        states[opaque_id] = (
            IdentityState(
                entity_kind=kind,
                opaque_id=opaque_id,
                source_key=source_key,
                locator_json=source.locator_json,
                state=identity.state,
                active=identity.active,
                no_reuse=identity.no_reuse,
            ),
            identity.created_source_sha256,
            source.source_row_sha256,
        )
    return states


def _requirement_states(rows: tuple[Any, ...]) -> dict[str, StateRecord]:
    return {
        row.requirement_id: (
            IdentityState(
                entity_kind="requirement",
                opaque_id=row.requirement_id,
                source_key=row.source_requirement_key,
                locator_json=row.locator_json,
                state=row.state,
                active=row.active,
                no_reuse=row.no_reuse,
            ),
            row.created_locator_sha256,
            row.locator_sha256,
        )
        for row in rows
    }


def _validate_existing(
    kind: str,
    before: dict[str, StateRecord],
    after: dict[str, StateRecord],
    events: dict[tuple[str, str], IdentityMigration],
) -> set[tuple[str, str]]:
    consumed: set[tuple[str, str]] = set()
    for opaque_id, (old_state, old_created, old_current) in before.items():
        new_state, new_created, new_current = after[opaque_id]
        if old_created != new_created:
            raise ValueError("identity creation hash must remain immutable")
        event = events.get((kind, opaque_id))
        if old_state != new_state and event is None:
            raise ValueError("active locator change requires correction migration")
        if event is not None:
            if event.old_source_row_sha256 != old_current:
                raise ValueError("migration old source hash mismatch")
            if event.disposition == "correction" and (
                event.new_source_row_sha256 != new_current
            ):
                raise ValueError("migration new source hash mismatch")
            validate_identity_transition(old_state, new_state, event)
            consumed.add((kind, opaque_id))
    return consumed


def _validate_replacements(
    before: dict[str, StateRecord],
    after: dict[str, StateRecord],
    appended: tuple[IdentityMigration, ...],
) -> None:
    added = set(after) - set(before)
    replacements = {
        row.replacement_id: row for row in appended if row.disposition == "replacement"
    }
    replacement_count = sum(row.disposition == "replacement" for row in appended)
    if replacement_count != len(replacements):
        raise ValueError("multiple identities cannot merge into one replacement")
    if added != set(replacements):
        raise ValueError("identities cannot be added without replacement")
    old_keys = {state.source_key for state, _, _ in before.values()}
    for opaque_id in added:
        new_state, new_created, new_current = after[opaque_id]
        event = replacements[opaque_id]
        if new_state.state != "active" or new_state.source_key in old_keys:
            raise ValueError("replacement must allocate a distinct active identity")
        if new_state.locator_json != event.new_locator_json or (
            event.new_locator_sha256 != digest_text(new_state.locator_json)
        ):
            raise ValueError("replacement target binding mismatch")
        if new_created != new_current or event.new_source_row_sha256 != new_current:
            raise ValueError("replacement creation hash mismatch")


def _validate_state_update(
    kind: str,
    before: dict[str, StateRecord],
    after: dict[str, StateRecord],
    appended: tuple[IdentityMigration, ...],
) -> set[tuple[str, str]]:
    if set(before) - set(after):
        raise ValueError("historical identities cannot be deleted")
    relevant = tuple(row for row in appended if row.entity_kind == kind)
    events = {(row.entity_kind, row.opaque_id): row for row in relevant}
    if len(events) != len(relevant):
        raise ValueError("duplicate identity transition")
    consumed = _validate_existing(kind, before, after, events)
    _validate_replacements(before, after, relevant)
    return consumed


def _validate_entity_update(
    kind: str,
    before_result: Any,
    after_result: Any,
    appended: tuple[IdentityMigration, ...],
) -> set[tuple[str, str]]:
    before = _states(before_result, kind)
    after = _states(after_result, kind)
    return _validate_state_update(kind, before, after, appended)


def validate_identity_update(
    before_root: Path, after_root: Path
) -> IdentityUpdateResult:
    """Validate one append-only identity-contract update across real CSV roots."""

    from worldenergydata.cost.timeseries.portfolio_identity import (
        validate_award_identities,
        validate_project_identities,
        validate_requirement_identities,
    )

    before_bytes = (before_root / MIGRATION_LEDGER).read_bytes()
    after_bytes = (after_root / MIGRATION_LEDGER).read_bytes()
    if not after_bytes.startswith(before_bytes):
        raise ValueError("identity migration ledger is not append-only")
    before_ledger = validate_identity_migration_ledger(before_root)
    after_ledger = validate_identity_migration_ledger(after_root)
    appended = after_ledger[len(before_ledger) :]
    before_projects = validate_project_identities(before_root)
    after_projects = validate_project_identities(after_root)
    before_awards = validate_award_identities(before_root)
    after_awards = validate_award_identities(after_root)
    before_requirements = validate_requirement_identities(before_root)
    after_requirements = validate_requirement_identities(after_root)
    consumed = _validate_entity_update(
        "project", before_projects, after_projects, appended
    )
    consumed |= _validate_entity_update("award", before_awards, after_awards, appended)
    consumed |= _validate_state_update(
        "requirement",
        _requirement_states(before_requirements),
        _requirement_states(after_requirements),
        appended,
    )
    if consumed != {(row.entity_kind, row.opaque_id) for row in appended}:
        raise ValueError("migration does not reference a changed identity")
    return IdentityUpdateResult(
        before_projects,
        after_projects,
        before_awards,
        after_awards,
        before_requirements,
        after_requirements,
        appended,
    )
