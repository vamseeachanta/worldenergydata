"""Hostile lifecycle cases found by the second T3 identity review."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.cost.test_portfolio_identity_support import (
    append_migration,
    copy_contract,
    find_row,
    migration,
    project_binding,
    read_csv,
    replace_appomattox,
    write_csv,
)
from worldenergydata.cost.timeseries.portfolio_identity import (
    MIGRATION_LEDGER,
    PROJECT_CROSSWALK,
    PROJECT_IDENTITIES,
    PROJECT_SOURCE,
    REQUIREMENT_IDENTITIES,
    canonical_json,
    digest_text,
    validate_identity_contract,
    validate_identity_update,
)


def _tombstone_project(root: Path, label: str) -> tuple[dict[str, str], dict[str, str]]:
    rows, fields = read_csv(root / PROJECT_SOURCE)
    rows = [row for row in rows if row["PROJECT"] != label]
    write_csv(root / PROJECT_SOURCE, fields, rows)
    bindings, binding_fields = read_csv(root / PROJECT_CROSSWALK)
    binding = project_binding(bindings, label)
    binding["active"] = "false"
    write_csv(root / PROJECT_CROSSWALK, binding_fields, bindings)
    identities, identity_fields = read_csv(root / PROJECT_IDENTITIES)
    identity = find_row(identities, "source_project_key", binding["source_project_key"])
    identity.update(state="tombstoned", active="false")
    write_csv(root / PROJECT_IDENTITIES, identity_fields, identities)
    return binding, identity


def _append_second_replacement(root: Path, replacement_id: str) -> None:
    binding, identity = _tombstone_project(root, "Atlantis (Phase 1)")
    bindings, _ = read_csv(root / PROJECT_CROSSWALK)
    new_binding = find_row(
        bindings, "source_project_key", "src-prj-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    )
    event = migration(
        "replacement",
        binding["locator_json"],
        new_binding["locator_json"],
        identity["project_id"],
        binding["source_project_key"],
        replacement_id,
        old_source_hash=binding["source_row_sha256"],
        new_source_hash=new_binding["source_row_sha256"],
    )
    append_migration(root, event.model_dump(mode="json"))


def _append_unmigrated_successor(
    root: Path,
) -> tuple[dict[str, str], dict[str, str]]:
    rows, fields = read_csv(root / PROJECT_SOURCE)
    row = dict(rows[0], PROJECT="Unmigrated successor")
    rows.append(row)
    write_csv(root / PROJECT_SOURCE, fields, rows)
    locator = canonical_json({"PROJECT": row["PROJECT"]})
    row_hash = digest_text(canonical_json(row))
    bindings, binding_fields = read_csv(root / PROJECT_CROSSWALK)
    new_binding = {
        "source_project_key": "src-prj-cccccccccccccccccccccccccccccccc",
        "locator_json": locator,
        "locator_sha256": digest_text(locator),
        "source_row_sha256": row_hash,
        "active": "true",
    }
    bindings.append(new_binding)
    write_csv(root / PROJECT_CROSSWALK, binding_fields, bindings)
    identities, identity_fields = read_csv(root / PROJECT_IDENTITIES)
    new_identity = dict(
        identities[0],
        project_id="prj-cccccccccccccccccccccccccccccccc",
        source_project_key="src-prj-cccccccccccccccccccccccccccccccc",
        display_label=row["PROJECT"],
        created_source_sha256=row_hash,
    )
    identities.append(new_identity)
    write_csv(root / PROJECT_IDENTITIES, identity_fields, identities)
    return new_binding, new_identity


def _requirement_event(
    root: Path, disposition: str, *, tombstone: bool = False
) -> None:
    rows, fields = read_csv(root / REQUIREMENT_IDENTITIES)
    row = rows[0]
    if tombstone:
        row.update(state="tombstoned", active="false")
        write_csv(root / REQUIREMENT_IDENTITIES, fields, rows)
    event = migration(
        disposition,
        row["locator_json"],
        opaque_id=row["requirement_id"],
        source_key=row["source_requirement_key"],
        entity_kind="requirement",
        old_source_hash=row["created_locator_sha256"],
    )
    append_migration(root, event.model_dump(mode="json"))


def test_real_csv_rejects_two_old_identities_merging_into_one(tmp_path: Path) -> None:
    before = copy_contract(tmp_path / "before")
    after = copy_contract(tmp_path / "after")
    _, replacement_id = replace_appomattox(after)
    _append_second_replacement(after, replacement_id)
    with pytest.raises(ValueError, match="cannot merge into one replacement"):
        validate_identity_update(before, after)


def test_real_csv_rejects_one_old_identity_splitting_into_two(tmp_path: Path) -> None:
    before = copy_contract(tmp_path / "before")
    after = copy_contract(tmp_path / "after")
    old_id, _ = replace_appomattox(after)
    new_binding, new_identity = _append_unmigrated_successor(after)
    bindings, _ = read_csv(after / PROJECT_CROSSWALK)
    old_binding = project_binding(bindings, "Appomattox")
    event = migration(
        "replacement",
        old_binding["locator_json"],
        new_binding["locator_json"],
        old_id,
        old_binding["source_project_key"],
        new_identity["project_id"],
        old_source_hash=old_binding["source_row_sha256"],
        new_source_hash=new_binding["source_row_sha256"],
    ).model_copy(update={"migration_id": "mig-replacement-split-target"})
    append_migration(after, event.model_dump(mode="json"))
    with pytest.raises(ValueError, match="duplicate identity transition"):
        validate_identity_update(before, after)


def test_replacement_rejects_fabricated_creation_hash(tmp_path: Path) -> None:
    before = copy_contract(tmp_path / "before")
    after = copy_contract(tmp_path / "after")
    _, replacement_id = replace_appomattox(after)
    rows, fields = read_csv(after / PROJECT_IDENTITIES)
    find_row(rows, "project_id", replacement_id)["created_source_sha256"] = "0" * 64
    write_csv(after / PROJECT_IDENTITIES, fields, rows)
    with pytest.raises(ValueError, match="replacement creation hash mismatch"):
        validate_identity_update(before, after)


def test_active_award_cannot_reference_tombstoned_project(tmp_path: Path) -> None:
    before = copy_contract(tmp_path / "before")
    after = copy_contract(tmp_path / "after")
    binding, identity = _tombstone_project(after, "Liza Phase 1")
    event = migration(
        "tombstone",
        binding["locator_json"],
        opaque_id=identity["project_id"],
        source_key=binding["source_project_key"],
        old_source_hash=binding["source_row_sha256"],
    )
    append_migration(after, event.model_dump(mode="json"))
    with pytest.raises(ValueError, match="award project foreign key must be active"):
        validate_identity_update(before, after)


@pytest.mark.parametrize("disposition", ["tombstone", "split_rejected"])
def test_requirement_lifecycle_is_consumed_by_public_update(
    tmp_path: Path, disposition: str
) -> None:
    before = copy_contract(tmp_path / "before")
    after = copy_contract(tmp_path / "after")
    _requirement_event(after, disposition, tombstone=disposition == "tombstone")
    result = validate_identity_update(before, after)
    assert result.appended_migrations[-1].entity_kind == "requirement"
    validate_identity_contract(after)


def test_creation_provenance_remains_enforced_after_a_migration(
    tmp_path: Path,
) -> None:
    before = copy_contract(tmp_path / "before")
    after = copy_contract(tmp_path / "after")
    _requirement_event(after, "split_rejected")
    validate_identity_update(before, after)
    rows, fields = read_csv(after / PROJECT_IDENTITIES)
    row = find_row(rows, "display_label", "Appomattox")
    row["created_source_sha256"] = "0" * 64
    write_csv(after / PROJECT_IDENTITIES, fields, rows)
    with pytest.raises(ValueError, match="project genesis creation hash mismatch"):
        validate_identity_contract(after)


def test_migration_source_hashes_are_required() -> None:
    header = (
        (Path(__file__).resolve().parents[3] / MIGRATION_LEDGER)
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    assert "old_source_row_sha256" in header
    assert "new_source_row_sha256" in header
