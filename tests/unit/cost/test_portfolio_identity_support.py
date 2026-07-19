"""Shared real-CSV fixtures for portfolio identity lifecycle tests."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from worldenergydata.cost.timeseries.portfolio_identity import (
    MIGRATION_LEDGER,
    PROJECT_CROSSWALK,
    PROJECT_IDENTITIES,
    PROJECT_SOURCE,
    IdentityMigration,
    IdentityState,
    canonical_json,
    digest_text,
)

ROOT = Path(__file__).resolve().parents[3]
CURATED = Path("data/modules/cost/curated")
CONTRACT_FILES = (
    "sanctioned_projects.csv",
    "portfolio_project_source_crosswalk.v2.csv",
    "portfolio_project_identity.v2.csv",
    "contract_awards.csv",
    "portfolio_award_source_crosswalk.v2.csv",
    "portfolio_award_identity.v2.csv",
    "portfolio_requirement_identity.v2.csv",
    "portfolio_identity_migrations.v2.csv",
)


def copy_contract(target: Path) -> Path:
    curated = target / CURATED
    curated.mkdir(parents=True)
    for name in CONTRACT_FILES:
        shutil.copy2(ROOT / CURATED / name, curated / name)
    return target


def read_csv(path: Path) -> tuple[list[dict[str, str]], tuple[str, ...]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader), tuple(reader.fieldnames or ())


def write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def append_migration(root: Path, row: dict[str, str]) -> None:
    path = root / MIGRATION_LEDGER
    rows, fields = read_csv(path)
    rows.append(row)
    write_csv(path, fields, rows)


def reverse_rows(path: Path) -> None:
    rows, fields = read_csv(path)
    write_csv(path, fields, list(reversed(rows)))


def find_row(rows: list[dict[str, str]], field: str, value: str) -> dict[str, str]:
    return next(row for row in rows if row[field] == value)


def project_binding(rows: list[dict[str, str]], label: str) -> dict[str, str]:
    return next(
        row for row in rows if json.loads(row["locator_json"])["PROJECT"] == label
    )


def migration(
    disposition: str,
    old_locator: str,
    new_locator: str | None = None,
    opaque_id: str = "prj-000001",
    source_key: str = "src-prj-000001",
    replacement_id: str | None = None,
    entity_kind: str = "project",
    old_source_hash: str | None = None,
    new_source_hash: str | None = None,
) -> IdentityMigration:
    return IdentityMigration(
        migration_id=f"mig-{disposition}-{opaque_id}",
        entity_kind=entity_kind,
        opaque_id=opaque_id,
        source_key=source_key,
        old_locator_json=old_locator,
        old_locator_sha256=digest_text(old_locator),
        old_source_row_sha256=old_source_hash or digest_text(old_locator),
        new_locator_json=new_locator,
        new_locator_sha256=digest_text(new_locator) if new_locator else None,
        new_source_row_sha256=(
            new_source_hash or digest_text(new_locator) if new_locator else None
        ),
        disposition=disposition,
        reason="curated identity lifecycle test",
        provenance="curation_review",
        effective_date="2026-07-19",
        replacement_id=replacement_id,
    )


def state(locator: str, *, state: str = "active") -> IdentityState:
    return IdentityState(
        entity_kind="project",
        opaque_id="prj-000001",
        source_key="src-prj-000001",
        locator_json=locator,
        state=state,
        active=state == "active",
        no_reuse=True,
    )


def replace_appomattox(root: Path) -> tuple[str, str]:
    source_rows, source_fields = read_csv(root / PROJECT_SOURCE)
    source = find_row(source_rows, "PROJECT", "Appomattox")
    source["PROJECT"] = "Appomattox successor"
    write_csv(root / PROJECT_SOURCE, source_fields, source_rows)
    bindings, binding_fields = read_csv(root / PROJECT_CROSSWALK)
    old_binding = project_binding(bindings, "Appomattox")
    old_binding["active"] = "false"
    locator = canonical_json({"PROJECT": "Appomattox successor"})
    new_key = "src-prj-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    row_hash = digest_text(canonical_json(source))
    bindings.append(
        dict(
            source_project_key=new_key,
            locator_json=locator,
            locator_sha256=digest_text(locator),
            source_row_sha256=row_hash,
            active="true",
        )
    )
    write_csv(root / PROJECT_CROSSWALK, binding_fields, bindings)
    identities, identity_fields = read_csv(root / PROJECT_IDENTITIES)
    old = find_row(identities, "source_project_key", old_binding["source_project_key"])
    old.update(state="tombstoned", active="false")
    new_id = "prj-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    identities.append(
        dict(
            old,
            project_id=new_id,
            source_project_key=new_key,
            display_label="Appomattox successor",
            state="active",
            active="true",
            created_source_sha256=row_hash,
        )
    )
    write_csv(root / PROJECT_IDENTITIES, identity_fields, identities)
    event = migration(
        "replacement",
        old_binding["locator_json"],
        locator,
        old["project_id"],
        old_binding["source_project_key"],
        new_id,
        old_source_hash=old_binding["source_row_sha256"],
        new_source_hash=row_hash,
    )
    append_migration(root, event.model_dump(mode="json"))
    return old["project_id"], new_id
