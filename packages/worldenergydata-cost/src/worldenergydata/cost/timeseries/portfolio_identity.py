"""Stable source bindings and identity closure for portfolio cost maps."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable, TypeVar

from pydantic import BaseModel

from worldenergydata.cost.timeseries.portfolio_identity_contract import (  # noqa: F401
    validate_identity_contract,
)
from worldenergydata.cost.timeseries.portfolio_identity_lifecycle import (  # noqa: F401
    MIGRATION_FIELDS,
    MIGRATION_LEDGER,
    IdentityMigration,
    IdentityState,
    digest_text,
    validate_identity_migration_ledger,
    validate_identity_transition,
)
from worldenergydata.cost.timeseries.portfolio_identity_update import (  # noqa: F401
    validate_identity_update,
)
from worldenergydata.cost.timeseries.portfolio_schema import (
    AwardIdentity,
    AwardSourceBinding,
    ProjectIdentity,
    ProjectSourceBinding,
    RequirementIdentity,
)

PROJECT_SOURCE = Path("data/modules/cost/curated/sanctioned_projects.csv")
PROJECT_CROSSWALK = Path(
    "data/modules/cost/curated/portfolio_project_source_crosswalk.v2.csv"
)
PROJECT_IDENTITIES = Path("data/modules/cost/curated/portfolio_project_identity.v2.csv")
AWARD_SOURCE = Path("data/modules/cost/curated/contract_awards.csv")
AWARD_CROSSWALK = Path(
    "data/modules/cost/curated/portfolio_award_source_crosswalk.v2.csv"
)
AWARD_IDENTITIES = Path("data/modules/cost/curated/portfolio_award_identity.v2.csv")
REQUIREMENT_IDENTITIES = Path(
    "data/modules/cost/curated/portfolio_requirement_identity.v2.csv"
)
PROJECT_SOURCE_FIELDS = (
    "source_project_key",
    "locator_json",
    "locator_sha256",
    "source_row_sha256",
    "active",
)
PROJECT_IDENTITY_FIELDS = (
    "project_id",
    "source_project_key",
    "display_label",
    "state",
    "active",
    "aliases_json",
    "validation_group_id",
    "created_source_sha256",
    "migration_note",
    "no_reuse",
)
AWARD_SOURCE_FIELDS = (
    "source_award_key",
    "locator_json",
    "locator_sha256",
    "source_row_sha256",
    "active",
)
AWARD_IDENTITY_FIELDS = (
    "award_id",
    "source_award_key",
    "project_id",
    "display_label",
    "state",
    "active",
    "aliases_json",
    "validation_group_id",
    "created_source_sha256",
    "migration_note",
    "no_reuse",
)
REQUIREMENT_IDENTITY_FIELDS = (
    "requirement_id",
    "source_requirement_key",
    "project_id",
    "work_package_slug",
    "locator_json",
    "locator_sha256",
    "created_locator_sha256",
    "state",
    "active",
    "validation_group_id",
    "no_reuse",
    "migration_note",
)
AWARD_LOCATOR_FIELDS = (
    "PROJECT",
    "AWARD_YEAR",
    "CONTRACTOR",
    "ASSET_CLASS",
    "SCOPE_DESC",
)
ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass(frozen=True)
class ProjectIdentityResult:
    sources: tuple[ProjectSourceBinding, ...]
    identities: tuple[ProjectIdentity, ...]
    live_labels: frozenset[str]


@dataclass(frozen=True)
class AwardIdentityResult:
    sources: tuple[AwardSourceBinding, ...]
    identities: tuple[AwardIdentity, ...]
    source_sha256: str
    projects_without_awards: int


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


BIG_FOOT_AWARD_LOCATORS = {
    "awd-000001": canonical_json(
        {
            "PROJECT": "Big Foot",
            "AWARD_YEAR": "2011",
            "CONTRACTOR": "GE Oil & Gas",
            "ASSET_CLASS": "surf",
            "SCOPE_DESC": "Largest TLP push-up marine riser tensioner systems",
        }
    ),
    "awd-000002": canonical_json(
        {
            "PROJECT": "Big Foot",
            "AWARD_YEAR": "2009",
            "CONTRACTOR": "Enbridge",
            "ASSET_CLASS": "other",
            "SCOPE_DESC": "Oil export pipeline / gathering system",
        }
    ),
}
BIG_FOOT_REQUIREMENTS = {
    "req-000001": "host_tlp",
    "req-000002": "dry_trees",
    "req-000003": "wells",
    "req-000004": "drilling_completion",
    "req-000005": "marine_riser_tensioner",
    "req-000006": "export",
    "req-000007": "installation_hookup",
    "req-000008": "controls",
}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _models(
    path: Path,
    model: type[ModelT],
    fields: tuple[str, ...],
    label: str,
) -> tuple[ModelT, ...]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != fields:
            raise ValueError(f"{label} header mismatch")
        return tuple(model.model_validate(row) for row in reader)


def _unique(values: Iterable[str], message: str) -> None:
    items = list(values)
    if len(items) != len(set(items)):
        raise ValueError(message)


def _live_project_rows(root: Path) -> dict[str, dict[str, str]]:
    rows = _rows(root / PROJECT_SOURCE)
    live = {canonical_json({"PROJECT": row["PROJECT"]}): row for row in rows}
    if len(live) != len(rows):
        raise ValueError("live project locator collision")
    return live


def _validate_project_sources(
    sources: tuple[ProjectSourceBinding, ...], live: dict[str, dict[str, str]]
) -> None:
    _unique((row.source_project_key for row in sources), "duplicate source project key")
    _unique((row.locator_json for row in sources), "duplicate project locator")
    if {row.locator_json for row in sources if row.active} != set(live):
        raise ValueError("project source binding set does not equal live projects")
    for binding in sources:
        if digest_text(binding.locator_json) != binding.locator_sha256:
            raise ValueError("project locator hash mismatch")
        if binding.active and (
            digest_text(canonical_json(live[binding.locator_json]))
            != binding.source_row_sha256
        ):
            raise ValueError("project source row hash mismatch")


def _validate_project_identities(
    identities: tuple[ProjectIdentity, ...], sources: tuple[ProjectSourceBinding, ...]
) -> None:
    source_by_key = {row.source_project_key: row for row in sources}
    _unique((row.project_id for row in identities), "duplicate project ID")
    _unique(
        (row.source_project_key for row in identities), "duplicate project source FK"
    )
    active_sources = {key for key, row in source_by_key.items() if row.active}
    if {row.source_project_key for row in identities if row.active} != active_sources:
        raise ValueError("project identity set does not equal source bindings")
    for identity in identities:
        source = source_by_key[identity.source_project_key]
        label = json.loads(source.locator_json)["PROJECT"]
        if identity.display_label != label:
            raise ValueError("project identity label mismatch")


def validate_project_identities(root: Path) -> ProjectIdentityResult:
    """Prove one stable active identity exists for each live project row."""

    live = _live_project_rows(root)
    sources = _models(
        root / PROJECT_CROSSWALK,
        ProjectSourceBinding,
        PROJECT_SOURCE_FIELDS,
        "project source binding",
    )
    identities = _models(
        root / PROJECT_IDENTITIES,
        ProjectIdentity,
        PROJECT_IDENTITY_FIELDS,
        "project identity",
    )
    _validate_project_sources(sources, live)
    _validate_project_identities(identities, sources)
    big_foot = next(row for row in identities if row.display_label == "Big Foot")
    if (big_foot.project_id, big_foot.source_project_key) != (
        "prj-000001",
        "src-prj-000001",
    ):
        raise ValueError("Big Foot project identity must remain stable")
    return ProjectIdentityResult(
        sources, identities, frozenset(row["PROJECT"] for row in live.values())
    )


def _live_award_rows(root: Path) -> dict[str, dict[str, str]]:
    rows = _rows(root / AWARD_SOURCE)
    live = {
        canonical_json({field: row[field] for field in AWARD_LOCATOR_FIELDS}): row
        for row in rows
    }
    if len(live) != len(rows):
        raise ValueError("live award locator collision")
    return live


def _validate_award_sources(
    sources: tuple[AwardSourceBinding, ...], live: dict[str, dict[str, str]]
) -> None:
    _unique((row.source_award_key for row in sources), "duplicate source award key")
    _unique((row.locator_json for row in sources), "duplicate award locator")
    for binding in sources:
        locator = json.loads(binding.locator_json)
        if set(locator) != set(AWARD_LOCATOR_FIELDS):
            raise ValueError("award locator must contain exact five fields")
        if canonical_json(locator) != binding.locator_json:
            raise ValueError("award locator must use canonical JSON")
    if {row.locator_json for row in sources if row.active} != set(live):
        raise ValueError("award source binding set does not equal live awards")
    for binding in sources:
        if digest_text(binding.locator_json) != binding.locator_sha256:
            raise ValueError("award locator hash mismatch")
        if binding.active and (
            digest_text(canonical_json(live[binding.locator_json]))
            != binding.source_row_sha256
        ):
            raise ValueError("award source row hash mismatch")


def _validate_pilot_awards(
    identities: tuple[AwardIdentity, ...],
    source_by_key: dict[str, AwardSourceBinding],
) -> None:
    identity_by_id = {row.award_id: row for row in identities}
    actual = {
        award_id: source_by_key[identity_by_id[award_id].source_award_key].locator_json
        for award_id in BIG_FOOT_AWARD_LOCATORS
    }
    if actual != BIG_FOOT_AWARD_LOCATORS:
        raise ValueError("Big Foot award identity must remain stable")


def validate_award_identities(root: Path) -> AwardIdentityResult:
    """Prove one stable active identity exists for each live award row."""
    projects = validate_project_identities(root)
    project_by_label = {row.display_label: row for row in projects.identities}
    live = _live_award_rows(root)
    sources = _models(
        root / AWARD_CROSSWALK,
        AwardSourceBinding,
        AWARD_SOURCE_FIELDS,
        "award source binding",
    )
    identities = _models(
        root / AWARD_IDENTITIES,
        AwardIdentity,
        AWARD_IDENTITY_FIELDS,
        "award identity",
    )
    _validate_award_sources(sources, live)
    source_by_key = {row.source_award_key: row for row in sources}
    _unique((row.award_id for row in identities), "duplicate award ID")
    _unique((row.source_award_key for row in identities), "duplicate award source FK")
    active_sources = {key for key, row in source_by_key.items() if row.active}
    if {row.source_award_key for row in identities if row.active} != active_sources:
        raise ValueError("award identity set does not equal source bindings")
    _validate_pilot_awards(identities, source_by_key)
    for identity in identities:
        source = source_by_key[identity.source_award_key]
        locator = json.loads(source.locator_json)
        project = project_by_label[locator["PROJECT"]]
        if identity.project_id != project.project_id:
            raise ValueError("award project identity mismatch")
        if identity.active and not project.active:
            raise ValueError("active award project foreign key must be active")
        expected_label = " / ".join(
            locator[field] for field in ("PROJECT", "AWARD_YEAR", "CONTRACTOR")
        )
        if identity.display_label != expected_label:
            raise ValueError("award identity label mismatch")
        if identity.validation_group_id != project.validation_group_id:
            raise ValueError("award validation group must match project")
    source_sha = sha256((root / AWARD_SOURCE).read_bytes()).hexdigest()
    award_projects = {
        json.loads(row.locator_json)["PROJECT"] for row in sources if row.active
    }
    return AwardIdentityResult(
        sources,
        identities,
        source_sha,
        sum(row.active for row in projects.identities) - len(award_projects),
    )


def validate_requirement_identities(root: Path) -> tuple[RequirementIdentity, ...]:
    """Validate the exact eight v1 Big Foot requirement identities."""

    identities = _models(
        root / REQUIREMENT_IDENTITIES,
        RequirementIdentity,
        REQUIREMENT_IDENTITY_FIELDS,
        "requirement identity",
    )
    _unique((row.requirement_id for row in identities), "duplicate requirement ID")
    _unique(
        (row.source_requirement_key for row in identities),
        "duplicate source requirement key",
    )
    _unique((row.locator_json for row in identities), "duplicate requirement locator")
    for identity in identities:
        locator = json.loads(identity.locator_json)
        expected = {
            "PROJECT_ID": identity.project_id,
            "WORK_PACKAGE_SLUG": identity.work_package_slug,
        }
        if locator != expected or canonical_json(locator) != identity.locator_json:
            raise ValueError("requirement locator mismatch")
        if digest_text(identity.locator_json) != identity.locator_sha256:
            raise ValueError("requirement locator hash mismatch")
    mapping = {row.requirement_id: row for row in identities}
    actual = {
        key: (
            row.source_requirement_key,
            row.project_id,
            row.work_package_slug,
            row.validation_group_id,
        )
        for key, row in mapping.items()
    }
    expected = {
        key: (f"src-req-{key[-6:]}", "prj-000001", slug, "vg-cost-map-pilot-000001")
        for key, slug in BIG_FOOT_REQUIREMENTS.items()
    }
    if {key: actual.get(key) for key in expected} != expected:
        raise ValueError("requirement identity meaning must remain stable")
    return identities
