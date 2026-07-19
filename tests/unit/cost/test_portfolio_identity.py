"""Contract and identity tests for the portfolio cost-map v2 surface."""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
V1_MANIFEST = Path("data/modules/cost/curated/cost_map_contract_manifest.v1.json")
V1_MANIFEST_SHA256 = "f5dc2fce6c0ee376d577f8dcebb70511c756bd28264744600dc018deab5fcf9e"
IDENTITY_INPUTS = (
    "sanctioned_projects.csv",
    "portfolio_project_source_crosswalk.v2.csv",
    "portfolio_project_identity.v2.csv",
    "contract_awards.csv",
    "portfolio_award_source_crosswalk.v2.csv",
    "portfolio_award_identity.v2.csv",
)


def _copy_identity_inputs(target_root: Path) -> Path:
    curated = target_root / "data/modules/cost/curated"
    curated.mkdir(parents=True)
    for name in IDENTITY_INPUTS:
        shutil.copy2(ROOT / "data/modules/cost/curated" / name, curated / name)
    return curated


def _read_csv(path: Path) -> tuple[list[dict[str, str]], tuple[str, ...]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader), tuple(reader.fieldnames or ())


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_v1_external_trust_root_and_closed_producer(tmp_path: Path) -> None:
    from worldenergydata.cost.timeseries.portfolio_manifest import (
        validate_v1_contract,
    )

    assert sha256((ROOT / V1_MANIFEST).read_bytes()).hexdigest() == V1_MANIFEST_SHA256
    manifest = validate_v1_contract(ROOT)
    assert manifest["producer"]["commit"] == "66ce9d6808492a01f6a7cac60415304bcc6e6ef5"
    assert {
        row["path"] for row in manifest["inputs"] if row["path"].endswith(".py")
    } == {
        "scripts/cost/build_big_foot_cost_map.py",
        "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/cost_map.py",
        "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/cost_map_schema.py",
        "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/evidence_pack.py",
        "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/evidence_pack_render.py",
        "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/project_trace.py",
    }

    payload = json.loads((ROOT / V1_MANIFEST).read_text(encoding="utf-8"))
    payload["inputs"][0]["sha256"] = "0" * 64
    tampered = tmp_path / V1_MANIFEST
    tampered.parent.mkdir(parents=True)
    tampered.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="v1 manifest trust root mismatch"):
        validate_v1_contract(tmp_path)


def test_owner_decision_requires_exact_approval_evidence() -> None:
    from pydantic import ValidationError

    from worldenergydata.cost.timeseries.portfolio_schema import (
        APPROVAL_MARKER_TEXT,
        PortfolioReuseDecision,
        validate_decision_evidence,
        validate_owner_decision,
    )

    decision = validate_owner_decision(ROOT)
    assert decision.taxonomy == "approved"
    assert decision.accounting == "approved"
    assert decision.portfolio_reuse == "approved"
    assert decision.allocation_scenarios == "deferred"
    assert decision.approval.approval_quote == (
        "Approved: #1040 revised plan at 5ba42c1; authorize taxonomy, accounting, "
        "and portfolio reuse; keep allocation scenarios deferred; proceed with PR1 "
        "TDD implementation."
    )
    assert decision.approval.published_plan_sha256 == (
        "9a0eb6dba27bcc58f2b82af991d482b0651a702174a5f4cad0bd93915ec5e5f9"
    )
    assert decision.approval.reviewed_plan_sha256 == (
        "c1d7a43004f1eb18f054fa9bd82642f0141a15b593f7ca0deecd039de1274f91"
    )
    assert decision.approval.approved_at == datetime(
        2026, 7, 19, 11, 54, 1, tzinfo=timezone.utc
    )
    assert decision.approval.issue_comment_url.endswith("#issuecomment-5015609061")

    payload = decision.model_dump(mode="json")
    payload["unreviewed_authority"] = True
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PortfolioReuseDecision.model_validate(payload)

    payload.pop("unreviewed_authority")
    payload["approval"]["published_plan_commit"] = "a" * 64
    with pytest.raises(ValidationError, match="commit must be full 40-hex"):
        PortfolioReuseDecision.model_validate(payload)

    payload = decision.model_dump(mode="json")
    payload["approval"]["approval_quote"] = "Approved: something else"
    with pytest.raises(ValueError, match="approval evidence mismatch: approval_quote"):
        validate_decision_evidence(payload, APPROVAL_MARKER_TEXT)
    with pytest.raises(ValueError, match="approval marker does not exactly match"):
        validate_decision_evidence(
            decision.model_dump(mode="json"), APPROVAL_MARKER_TEXT + "Revoked: true\n"
        )


def test_reviewed_plan_is_authenticated_without_main_ancestry() -> None:
    from worldenergydata.cost.timeseries.portfolio_schema import validate_owner_decision

    decision = validate_owner_decision(ROOT)
    reviewed = decision.approval.reviewed_plan_commit
    published = decision.approval.published_plan_commit
    relationship = subprocess.run(
        ["git", "merge-base", "--is-ancestor", reviewed, published],
        cwd=ROOT,
        check=False,
    )
    assert relationship.returncode == 1


def test_project_identity_set_equals_live_projects() -> None:
    from worldenergydata.cost.timeseries.portfolio_identity import (
        validate_project_identities,
    )

    result = validate_project_identities(ROOT)
    assert len(result.sources) == 80
    assert len(result.identities) == 80
    assert {row.display_label for row in result.identities} == result.live_labels
    assert {row.source_project_key for row in result.identities} == {
        row.source_project_key for row in result.sources
    }
    big_foot = next(row for row in result.identities if row.display_label == "Big Foot")
    assert big_foot.project_id == "prj-000001"
    assert big_foot.source_project_key == "src-prj-000001"


def test_identity_contract_closes_genesis_80_110_8() -> None:
    from worldenergydata.cost.timeseries.portfolio_identity import (
        validate_identity_contract,
    )

    contract = validate_identity_contract(ROOT)
    assert len(contract.projects.identities) == 80
    assert len(contract.awards.identities) == 110
    assert len(contract.requirements) == 8
    assert contract.migrations == ()


def test_award_identity_set_equals_live_awards() -> None:
    from worldenergydata.cost.timeseries.portfolio_identity import (
        validate_award_identities,
    )

    result = validate_award_identities(ROOT)
    assert result.source_sha256 == (
        "7a5769b36f87a3d5a4290d165f338ce829d13d00b83cacdc81e8a639b5496dc1"
    )
    assert len(result.sources) == 110
    assert len(result.identities) == 110
    assert len({row.source_award_key for row in result.sources}) == 110
    assert len({row.award_id for row in result.identities}) == 110
    assert {row.source_award_key for row in result.identities} == {
        row.source_award_key for row in result.sources
    }
    assert len({row.project_id for row in result.identities}) == 29
    assert result.projects_without_awards == 51

    pilot = {
        (row.display_label, row.award_id)
        for row in result.identities
        if row.project_id == "prj-000001"
    }
    assert ("Big Foot / 2011 / GE Oil & Gas", "awd-000001") in pilot
    assert ("Big Foot / 2009 / Enbridge", "awd-000002") in pilot
    source_by_key = {row.source_award_key: row for row in result.sources}
    locator_by_id = {
        row.award_id: json.loads(source_by_key[row.source_award_key].locator_json)
        for row in result.identities
    }
    assert locator_by_id["awd-000001"]["CONTRACTOR"] == "GE Oil & Gas"
    assert locator_by_id["awd-000001"]["AWARD_YEAR"] == "2011"
    assert locator_by_id["awd-000002"]["CONTRACTOR"] == "Enbridge"
    assert locator_by_id["awd-000002"]["AWARD_YEAR"] == "2009"


def test_big_foot_award_ids_are_bound_to_exact_source_awards(tmp_path: Path) -> None:
    from worldenergydata.cost.timeseries.portfolio_identity import (
        AWARD_IDENTITIES,
        validate_award_identities,
    )

    _copy_identity_inputs(tmp_path)
    rows, fields = _read_csv(tmp_path / AWARD_IDENTITIES)
    ge = next(row for row in rows if row["award_id"] == "awd-000001")
    enbridge = next(row for row in rows if row["award_id"] == "awd-000002")
    for field in ("source_award_key", "created_source_sha256"):
        ge[field], enbridge[field] = enbridge[field], ge[field]
    _write_csv(tmp_path / AWARD_IDENTITIES, fields, rows)
    with pytest.raises(ValueError, match="Big Foot award identity must remain stable"):
        validate_award_identities(tmp_path)


def test_award_identity_label_and_group_match_project(tmp_path: Path) -> None:
    from worldenergydata.cost.timeseries.portfolio_identity import (
        AWARD_IDENTITIES,
        validate_award_identities,
    )

    _copy_identity_inputs(tmp_path)
    rows, fields = _read_csv(tmp_path / AWARD_IDENTITIES)
    row = next(
        item for item in rows if item["award_id"] not in {"awd-000001", "awd-000002"}
    )
    row["display_label"] = "self-authored false label"
    _write_csv(tmp_path / AWARD_IDENTITIES, fields, rows)
    with pytest.raises(ValueError, match="award identity label mismatch"):
        validate_award_identities(tmp_path)


def test_moho_locator_collision_is_resolved_by_curated_keys(tmp_path: Path) -> None:
    from worldenergydata.cost.timeseries.portfolio_identity import (
        AWARD_CROSSWALK,
        validate_award_identities,
    )

    result = validate_award_identities(ROOT)
    moho = [
        row
        for row in result.sources
        if json.loads(row.locator_json)["PROJECT"] == "Moho Nord (incl. Phase 1bis)"
        and json.loads(row.locator_json)["AWARD_YEAR"] == "2013"
        and json.loads(row.locator_json)["CONTRACTOR"] == "Hyundai Heavy Industries"
    ]
    assert len(moho) == 2
    assert len({row.source_award_key for row in moho}) == 2
    assert len({row.locator_sha256 for row in moho}) == 2
    assert {json.loads(row.locator_json)["SCOPE_DESC"] for row in moho} == {
        "EPC Likouf FPU (62,000 t, 100 kbopd)",
        "EPC integrated TLP (14,600 t hull + topsides), Congo's first TLP",
    }

    _copy_identity_inputs(tmp_path)
    rows, fields = _read_csv(tmp_path / AWARD_CROSSWALK)
    target = next(
        row for row in rows if row["source_award_key"] == moho[0].source_award_key
    )
    locator = json.loads(target["locator_json"])
    locator.pop("SCOPE_DESC")
    target["locator_json"] = json.dumps(
        locator, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    target["locator_sha256"] = sha256(target["locator_json"].encode()).hexdigest()
    _write_csv(tmp_path / AWARD_CROSSWALK, fields, rows)
    with pytest.raises(
        ValueError, match="award locator must contain exact five fields"
    ):
        validate_award_identities(tmp_path)


def test_duplicate_complete_moho_locator_fails_closed(tmp_path: Path) -> None:
    from worldenergydata.cost.timeseries.portfolio_identity import (
        AWARD_CROSSWALK,
        validate_award_identities,
    )

    _copy_identity_inputs(tmp_path)
    rows, fields = _read_csv(tmp_path / AWARD_CROSSWALK)
    moho = [
        row
        for row in rows
        if json.loads(row["locator_json"])["PROJECT"] == "Moho Nord (incl. Phase 1bis)"
        and json.loads(row["locator_json"])["CONTRACTOR"] == "Hyundai Heavy Industries"
    ]
    moho[1]["locator_json"] = moho[0]["locator_json"]
    moho[1]["locator_sha256"] = moho[0]["locator_sha256"]
    _write_csv(tmp_path / AWARD_CROSSWALK, fields, rows)
    with pytest.raises(ValueError, match="duplicate award locator"):
        validate_award_identities(tmp_path)


def test_requirement_registry_seeds_exact_v1_big_foot_ids() -> None:
    from worldenergydata.cost.timeseries.portfolio_identity import (
        validate_requirement_identities,
    )

    identities = validate_requirement_identities(ROOT)
    assert {row.requirement_id for row in identities} == {
        f"req-{number:06d}" for number in range(1, 9)
    }
    assert {row.source_requirement_key for row in identities} == {
        f"src-req-{number:06d}" for number in range(1, 9)
    }
    assert {row.project_id for row in identities} == {"prj-000001"}
    assert {row.requirement_id: row.work_package_slug for row in identities} == {
        "req-000001": "host_tlp",
        "req-000002": "dry_trees",
        "req-000003": "wells",
        "req-000004": "drilling_completion",
        "req-000005": "marine_riser_tensioner",
        "req-000006": "export",
        "req-000007": "installation_hookup",
        "req-000008": "controls",
    }


def test_requirement_ids_are_bound_to_exact_v1_meanings(tmp_path: Path) -> None:
    from worldenergydata.cost.timeseries.portfolio_identity import (
        REQUIREMENT_IDENTITIES,
        validate_requirement_identities,
    )

    curated = _copy_identity_inputs(tmp_path)
    source = ROOT / REQUIREMENT_IDENTITIES
    shutil.copy2(source, curated / source.name)
    rows, fields = _read_csv(tmp_path / REQUIREMENT_IDENTITIES)
    host = next(row for row in rows if row["requirement_id"] == "req-000001")
    trees = next(row for row in rows if row["requirement_id"] == "req-000002")
    swapped = (
        "source_requirement_key",
        "work_package_slug",
        "locator_json",
        "locator_sha256",
    )
    for field in swapped:
        host[field], trees[field] = trees[field], host[field]
    _write_csv(tmp_path / REQUIREMENT_IDENTITIES, fields, rows)
    with pytest.raises(
        ValueError, match="requirement identity meaning must remain stable"
    ):
        validate_requirement_identities(tmp_path)


def test_identity_csv_headers_are_exactly_enforced(tmp_path: Path) -> None:
    from worldenergydata.cost.timeseries.portfolio_identity import (
        AWARD_IDENTITIES,
        validate_award_identities,
    )

    _copy_identity_inputs(tmp_path)
    path = tmp_path / AWARD_IDENTITIES
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[0] += ",unreviewed_field"
    lines[1] += ",value"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="award identity header mismatch"):
        validate_award_identities(tmp_path)


def test_identity_hashes_require_lowercase_hex() -> None:
    from pydantic import ValidationError

    from worldenergydata.cost.timeseries.portfolio_schema import ProjectSourceBinding

    with pytest.raises(ValidationError, match="SHA-256 must be lowercase 64-hex"):
        ProjectSourceBinding.model_validate(
            {
                "source_project_key": "src-prj-000001",
                "locator_json": '{"PROJECT":"Big Foot"}',
                "locator_sha256": "A" * 64,
                "source_row_sha256": "0" * 64,
                "active": True,
            }
        )
