"""Public identity-contract facade for the portfolio cost map."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from worldenergydata.cost.timeseries.portfolio_identity_lifecycle import (
    MIGRATION_LEDGER,
    IdentityMigration,
    validate_identity_migration_ledger,
)

GENESIS_LEDGER_SHA256 = (
    "e8c74604f1e8221851075386e8fe16665de099344c96fd1ac607203b7c18f51b"
)


@dataclass(frozen=True)
class IdentityContractResult:
    projects: Any
    awards: Any
    requirements: tuple[Any, ...]
    migrations: tuple[IdentityMigration, ...]


def _validate_history(
    kind: str,
    opaque_id: str,
    created_hash: str,
    current_locator: str,
    current_source_hash: str,
    current_state: str,
    migrations: tuple[IdentityMigration, ...],
) -> None:
    events = tuple(
        row
        for row in migrations
        if (row.entity_kind, row.opaque_id) == (kind, opaque_id)
    )
    if not events:
        if created_hash != current_source_hash:
            raise ValueError(f"{kind} genesis creation hash mismatch")
        return
    if created_hash != events[0].old_source_row_sha256:
        raise ValueError(f"{kind} creation hash is not immutable")
    locator = events[0].old_locator_json
    source_hash = events[0].old_source_row_sha256
    state = "active"
    for index, event in enumerate(events):
        if (event.old_locator_json, event.old_source_row_sha256) != (
            locator,
            source_hash,
        ):
            raise ValueError("identity migration chain is discontinuous")
        if event.disposition == "correction":
            locator = event.new_locator_json or ""
            source_hash = event.new_source_row_sha256 or ""
        elif event.disposition in ("tombstone", "replacement"):
            state = "tombstoned"
        if state == "tombstoned" and index < len(events) - 1:
            raise ValueError("identity migration follows terminal tombstone")
    if (locator, source_hash, state) != (
        current_locator,
        current_source_hash,
        current_state,
    ):
        raise ValueError("identity terminal migration does not match registry")


def _validate_creation_hashes(
    kind: str,
    result: Any,
    migrations: tuple[IdentityMigration, ...],
) -> None:
    key_name = f"source_{kind}_key"
    id_name = f"{kind}_id"
    source_by_key = {getattr(row, key_name): row for row in result.sources}
    for identity in result.identities:
        source = source_by_key[getattr(identity, key_name)]
        _validate_history(
            kind,
            getattr(identity, id_name),
            identity.created_source_sha256,
            source.locator_json,
            source.source_row_sha256,
            identity.state,
            migrations,
        )


def _validate_requirement_history(
    requirements: tuple[Any, ...], migrations: tuple[IdentityMigration, ...]
) -> None:
    for identity in requirements:
        _validate_history(
            "requirement",
            identity.requirement_id,
            identity.created_locator_sha256,
            identity.locator_json,
            identity.locator_sha256,
            identity.state,
            migrations,
        )


def _validate_requirement_foreign_keys(
    projects: Any,
    requirements: tuple[Any, ...],
) -> None:
    project_by_id = {row.project_id: row for row in projects.identities}
    for requirement in requirements:
        project = project_by_id.get(requirement.project_id)
        if project is None or not project.active:
            raise ValueError("requirement project foreign key is not active")
        if requirement.validation_group_id != project.validation_group_id:
            raise ValueError("requirement validation group must match project")


def validate_identity_contract(root: Path) -> IdentityContractResult:
    """Prove current registry, live-source, pilot, and ledger closure."""

    from worldenergydata.cost.timeseries.portfolio_identity import (
        validate_award_identities,
        validate_project_identities,
        validate_requirement_identities,
    )

    projects = validate_project_identities(root)
    awards = validate_award_identities(root)
    requirements = validate_requirement_identities(root)
    migrations = validate_identity_migration_ledger(root)
    _validate_requirement_foreign_keys(projects, requirements)
    _validate_creation_hashes("project", projects, migrations)
    _validate_creation_hashes("award", awards, migrations)
    _validate_requirement_history(requirements, migrations)
    if not migrations:
        ledger_hash = sha256((root / MIGRATION_LEDGER).read_bytes()).hexdigest()
        if ledger_hash != GENESIS_LEDGER_SHA256:
            raise ValueError("identity genesis ledger hash mismatch")
        active_projects = sum(row.active for row in projects.identities)
        active_awards = sum(row.active for row in awards.identities)
        if (active_projects, active_awards, len(requirements)) != (80, 110, 8):
            raise ValueError("identity genesis counts must remain 80/110/8")
    return IdentityContractResult(projects, awards, requirements, migrations)
