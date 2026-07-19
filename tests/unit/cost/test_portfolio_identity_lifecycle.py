"""Lifecycle tests for stable portfolio identities."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest

from worldenergydata.cost.timeseries.portfolio_identity import (
    AWARD_CROSSWALK,
    AWARD_IDENTITIES,
    AWARD_SOURCE,
    MIGRATION_LEDGER,
    PROJECT_CROSSWALK,
    PROJECT_IDENTITIES,
    PROJECT_SOURCE,
    IdentityMigration,
    IdentityState,
    canonical_json,
    digest_text,
    validate_identity_migration_ledger,
    validate_identity_transition,
    validate_identity_update,
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


def _copy_contract(target: Path) -> Path:
    curated = target / CURATED
    curated.mkdir(parents=True)
    for name in CONTRACT_FILES:
        shutil.copy2(ROOT / CURATED / name, curated / name)
    return target


def _read(path: Path) -> tuple[list[dict[str, str]], tuple[str, ...]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader), tuple(reader.fieldnames or ())


def _write(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _append_migration(root: Path, row: dict[str, str]) -> None:
    path = root / MIGRATION_LEDGER
    rows, fields = _read(path)
    rows.append(row)
    _write(path, fields, rows)


def _reverse_rows(path: Path) -> None:
    rows, fields = _read(path)
    _write(path, fields, list(reversed(rows)))


def _find(rows: list[dict[str, str]], field: str, value: str) -> dict[str, str]:
    return next(row for row in rows if row[field] == value)


def _project_binding(rows: list[dict[str, str]], label: str) -> dict[str, str]:
    return next(
        row for row in rows if json.loads(row["locator_json"])["PROJECT"] == label
    )


def _replace_appomattox(root: Path) -> tuple[str, str]:
    source_rows, source_fields = _read(root / PROJECT_SOURCE)
    source = _find(source_rows, "PROJECT", "Appomattox")
    source["PROJECT"] = "Appomattox successor"
    _write(root / PROJECT_SOURCE, source_fields, source_rows)

    bindings, binding_fields = _read(root / PROJECT_CROSSWALK)
    old_binding = _project_binding(bindings, "Appomattox")
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
    _write(root / PROJECT_CROSSWALK, binding_fields, bindings)

    identities, identity_fields = _read(root / PROJECT_IDENTITIES)
    old = _find(identities, "source_project_key", old_binding["source_project_key"])
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
    _write(root / PROJECT_IDENTITIES, identity_fields, identities)
    migration = _migration(
        "replacement",
        old_binding["locator_json"],
        locator,
        old["project_id"],
        old_binding["source_project_key"],
        new_id,
    )
    _append_migration(root, migration.model_dump(mode="json"))
    return old["project_id"], new_id


def _state(locator: str, *, state: str = "active") -> IdentityState:
    return IdentityState(
        entity_kind="project",
        opaque_id="prj-000001",
        source_key="src-prj-000001",
        locator_json=locator,
        state=state,
        active=state == "active",
        no_reuse=True,
    )


def _migration(
    disposition: str,
    old_locator: str,
    new_locator: str | None = None,
    opaque_id: str = "prj-000001",
    source_key: str = "src-prj-000001",
    replacement_id: str | None = None,
    entity_kind: str = "project",
) -> IdentityMigration:
    return IdentityMigration(
        migration_id=f"mig-{disposition}",
        entity_kind=entity_kind,
        opaque_id=opaque_id,
        source_key=source_key,
        old_locator_json=old_locator,
        old_locator_sha256=digest_text(old_locator),
        new_locator_json=new_locator,
        new_locator_sha256=digest_text(new_locator) if new_locator else None,
        disposition=disposition,
        reason="curated identity lifecycle test",
        provenance="curation_review",
        effective_date="2026-07-19",
        replacement_id=replacement_id,
    )


def test_identity_correction_preserves_source_key_and_opaque_id() -> None:
    old_locator = canonical_json({"PROJECT": "Old label"})
    new_locator = canonical_json({"PROJECT": "Corrected label"})
    before = _state(old_locator)
    corrected = _state(new_locator)
    correction = _migration("correction", old_locator, new_locator)
    assert validate_identity_transition(before, corrected, correction) == corrected

    changed_id = IdentityState(**(corrected.model_dump() | {"opaque_id": "prj-000002"}))
    with pytest.raises(
        ValueError, match="opaque ID and source key must remain reserved"
    ):
        validate_identity_transition(before, changed_id, correction)


def test_identity_tombstone_preserves_history_and_prevents_reuse() -> None:
    locator = canonical_json({"PROJECT": "Corrected label"})
    active = _state(locator)
    tombstoned = _state(locator, state="tombstoned")
    tombstone = _migration("tombstone", locator)
    assert validate_identity_transition(active, tombstoned, tombstone) == tombstoned

    reused = _state(canonical_json({"PROJECT": "Reused label"}))
    with pytest.raises(ValueError, match="tombstoned identity cannot be reused"):
        validate_identity_transition(tombstoned, reused, tombstone)


@pytest.mark.parametrize("disposition", ["split_rejected", "merge_rejected"])
def test_identity_split_and_merge_migrations_fail_closed(disposition: str) -> None:
    locator = canonical_json({"PROJECT": "Big Foot"})
    state = _state(locator)
    rejected = _migration(disposition, locator)
    assert validate_identity_transition(state, state, rejected) == state

    changed = IdentityState(**(state.model_dump() | {"source_key": "src-prj-000002"}))
    with pytest.raises(
        ValueError, match="opaque ID and source key must remain reserved"
    ):
        validate_identity_transition(state, changed, rejected)


def test_checked_in_migration_ledger_is_append_only_and_empty(tmp_path: Path) -> None:
    assert validate_identity_migration_ledger(ROOT) == ()
    target = tmp_path / MIGRATION_LEDGER
    target.parent.mkdir(parents=True)
    target.write_text(
        (ROOT / MIGRATION_LEDGER).read_text(encoding="utf-8").rstrip("\n")
        + ",unreviewed_field\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="identity migration ledger header mismatch"):
        validate_identity_migration_ledger(tmp_path)


def test_csv_correction_preserves_key_id_and_created_hash(tmp_path: Path) -> None:
    before = _copy_contract(tmp_path / "before")
    after = _copy_contract(tmp_path / "after")
    source_rows, source_fields = _read(after / PROJECT_SOURCE)
    source = _find(source_rows, "PROJECT", "Appomattox")
    source["PROJECT"] = "Appomattox corrected"
    _write(after / PROJECT_SOURCE, source_fields, source_rows)

    bindings, binding_fields = _read(after / PROJECT_CROSSWALK)
    binding = _project_binding(bindings, "Appomattox")
    old_locator = binding["locator_json"]
    new_locator = canonical_json({"PROJECT": "Appomattox corrected"})
    binding["locator_json"] = new_locator
    binding["locator_sha256"] = digest_text(new_locator)
    binding["source_row_sha256"] = digest_text(canonical_json(source))
    _write(after / PROJECT_CROSSWALK, binding_fields, bindings)

    identities, identity_fields = _read(after / PROJECT_IDENTITIES)
    identity = _find(identities, "source_project_key", binding["source_project_key"])
    created_hash = identity["created_source_sha256"]
    identity["display_label"] = "Appomattox corrected"
    _write(after / PROJECT_IDENTITIES, identity_fields, identities)
    migration = _migration(
        "correction",
        old_locator,
        new_locator,
        identity["project_id"],
        binding["source_project_key"],
    )
    _append_migration(after, migration.model_dump(mode="json"))

    result = validate_identity_update(before, after)
    assert result.appended_migrations[-1].disposition == "correction"
    corrected = next(
        row
        for row in result.after_projects.identities
        if row.project_id == identity["project_id"]
    )
    assert corrected.created_source_sha256 == created_hash


def test_csv_tombstone_removes_live_row_but_reserves_identity(tmp_path: Path) -> None:
    before = _copy_contract(tmp_path / "before")
    after = _copy_contract(tmp_path / "after")
    source_rows, source_fields = _read(after / PROJECT_SOURCE)
    source_rows = [row for row in source_rows if row["PROJECT"] != "Appomattox"]
    _write(after / PROJECT_SOURCE, source_fields, source_rows)

    bindings, binding_fields = _read(after / PROJECT_CROSSWALK)
    binding = _project_binding(bindings, "Appomattox")
    binding["active"] = "false"
    _write(after / PROJECT_CROSSWALK, binding_fields, bindings)

    identities, identity_fields = _read(after / PROJECT_IDENTITIES)
    identity = _find(identities, "source_project_key", binding["source_project_key"])
    identity.update(state="tombstoned", active="false")
    _write(after / PROJECT_IDENTITIES, identity_fields, identities)
    migration = _migration(
        "tombstone",
        binding["locator_json"],
        opaque_id=identity["project_id"],
        source_key=binding["source_project_key"],
    )
    _append_migration(after, migration.model_dump(mode="json"))

    result = validate_identity_update(before, after)
    reserved = next(
        row
        for row in result.after_projects.identities
        if row.project_id == identity["project_id"]
    )
    assert (reserved.state, reserved.active, reserved.no_reuse) == (
        "tombstoned",
        False,
        True,
    )
    assert len(result.after_projects.live_labels) == 79


def test_csv_award_tombstone_is_replayed_by_public_update_validator(
    tmp_path: Path,
) -> None:
    before = _copy_contract(tmp_path / "before")
    after = _copy_contract(tmp_path / "after")
    source_rows, source_fields = _read(after / AWARD_SOURCE)
    removed = source_rows.pop(0)
    _write(after / AWARD_SOURCE, source_fields, source_rows)

    locator = canonical_json(
        {
            field: removed[field]
            for field in (
                "PROJECT",
                "AWARD_YEAR",
                "CONTRACTOR",
                "ASSET_CLASS",
                "SCOPE_DESC",
            )
        }
    )
    bindings, binding_fields = _read(after / AWARD_CROSSWALK)
    binding = _find(bindings, "locator_json", locator)
    binding["active"] = "false"
    _write(after / AWARD_CROSSWALK, binding_fields, bindings)
    identities, identity_fields = _read(after / AWARD_IDENTITIES)
    identity = _find(identities, "source_award_key", binding["source_award_key"])
    identity.update(state="tombstoned", active="false")
    _write(after / AWARD_IDENTITIES, identity_fields, identities)
    migration = _migration(
        "tombstone",
        locator,
        opaque_id=identity["award_id"],
        source_key=binding["source_award_key"],
        entity_kind="award",
    )
    _append_migration(after, migration.model_dump(mode="json"))

    result = validate_identity_update(before, after)
    reserved = next(
        row
        for row in result.after_awards.identities
        if row.award_id == identity["award_id"]
    )
    assert (reserved.state, reserved.active, reserved.no_reuse) == (
        "tombstoned",
        False,
        True,
    )


def test_csv_replacement_reserves_old_and_activates_distinct_identity(
    tmp_path: Path,
) -> None:
    before = _copy_contract(tmp_path / "before")
    after = _copy_contract(tmp_path / "after")
    old_id, new_id = _replace_appomattox(after)
    result = validate_identity_update(before, after)
    by_id = {row.project_id: row for row in result.after_projects.identities}
    assert (by_id[old_id].state, by_id[old_id].no_reuse) == ("tombstoned", True)
    assert (by_id[new_id].state, by_id[new_id].active) == ("active", True)


def test_source_and_registry_row_reordering_preserves_identity_mapping(
    tmp_path: Path,
) -> None:
    before = _copy_contract(tmp_path / "before")
    after = _copy_contract(tmp_path / "after")
    for path in (PROJECT_SOURCE, PROJECT_CROSSWALK, PROJECT_IDENTITIES):
        _reverse_rows(after / path)
    result = validate_identity_update(before, after)
    before_map = {
        row.source_project_key: row.project_id
        for row in result.before_projects.identities
    }
    after_map = {
        row.source_project_key: row.project_id
        for row in result.after_projects.identities
    }
    assert after_map == before_map


def test_migration_ledger_rejects_prefix_rewrite(tmp_path: Path) -> None:
    before = _copy_contract(tmp_path / "before")
    after = _copy_contract(tmp_path / "after")
    path = after / MIGRATION_LEDGER
    path.write_text(" " + path.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(
        ValueError, match="identity migration ledger is not append-only"
    ):
        validate_identity_update(before, after)
