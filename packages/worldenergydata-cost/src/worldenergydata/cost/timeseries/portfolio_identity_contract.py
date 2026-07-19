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
    "c352f8c5a83d951f21af27d1ee24aaf8ed5ebe73d337bf8e188c2688d4aefd4a"
)


@dataclass(frozen=True)
class IdentityContractResult:
    projects: Any
    awards: Any
    requirements: tuple[Any, ...]
    migrations: tuple[IdentityMigration, ...]


def _validate_creation_hashes(projects: Any, awards: Any) -> None:
    project_sources = {row.source_project_key: row for row in projects.sources}
    for identity in projects.identities:
        source = project_sources[identity.source_project_key]
        if identity.created_source_sha256 != source.source_row_sha256:
            raise ValueError("project genesis creation hash mismatch")
    award_sources = {row.source_award_key: row for row in awards.sources}
    for identity in awards.identities:
        source = award_sources[identity.source_award_key]
        if identity.created_source_sha256 != source.source_row_sha256:
            raise ValueError("award genesis creation hash mismatch")


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
    if not migrations:
        ledger_hash = sha256((root / MIGRATION_LEDGER).read_bytes()).hexdigest()
        if ledger_hash != GENESIS_LEDGER_SHA256:
            raise ValueError("identity genesis ledger hash mismatch")
        _validate_creation_hashes(projects, awards)
    active_projects = sum(row.active for row in projects.identities)
    active_awards = sum(row.active for row in awards.identities)
    if (active_projects, active_awards, len(requirements)) != (80, 110, 8):
        raise ValueError("identity genesis counts must remain 80/110/8")
    return IdentityContractResult(projects, awards, requirements, migrations)
