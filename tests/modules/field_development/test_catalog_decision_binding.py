"""Decision records bind changed crosswalk dispositions, without authenticating them."""

import copy
import csv
import io
import json

import catalog_test_support as support
import pytest

api = support.api
inputs = support.inputs


def accepted_bundle(api, inputs, public=False):
    draft = api.build_integration(*inputs)
    candidate = next(
        r for r in draft["crosswalk"] if r["origin_entity_id"] == "ao-dalia"
    )
    decision = dict(
        candidate,
        match_status="accepted",
        approved_by="Vamsee",
        approval_ref="synthetic binding fixture",
        adjudication_source_refs=[],
    )
    bundle = api.build_integration(
        *inputs,
        decisions=[decision],
        eligibility=support.reviewed_matrix(draft) if public else None,
    )
    return api.public_export(bundle) if public else bundle


@pytest.mark.parametrize("public", [False, True])
def test_recorded_decision_roundtrip_preserves_binding(api, inputs, tmp_path, public):
    bundle = accepted_bundle(api, inputs, public)
    out = tmp_path / "bound"
    api.write_bundle(bundle, out)
    restored = api.read_bundle(out, public_only=public)
    assert len(restored["match_decisions"]) == 1
    assert (
        next(r for r in restored["crosswalk"] if r["origin_entity_id"] == "ao-dalia")[
            "match_status"
        ]
        == "accepted"
    )


@pytest.mark.parametrize("public", [False, True])
@pytest.mark.parametrize(
    "defect",
    [
        "missing",
        "duplicate",
        "candidate_sha256",
        "match_status",
        "approval_ref",
        "approved_by",
        "adjudication_source_refs",
        "entity_id",
    ],
)
def test_reader_rejects_rehashed_decision_binding_defects(
    api, inputs, tmp_path, public, defect
):
    out = tmp_path / "tampered"
    api.write_bundle(accepted_bundle(api, inputs, public), out)
    path = out / "catalog_match_decisions.json"
    decisions = json.loads(path.read_text())
    if defect == "missing":
        decisions = []
    elif defect == "duplicate":
        decisions.append(copy.deepcopy(decisions[0]))
    else:
        decisions[0][defect] = {
            "candidate_sha256": "0" * 64,
            "match_status": "rejected",
            "adjudication_source_refs": ["s1"],
        }.get(defect, "tampered")
    support.write_json(path, decisions)
    support.repin(out, path.name)
    manifest_path = out / "integration_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["decision_sha256"] = api.row_fingerprint(decisions)
    support.write_json(manifest_path, manifest)
    with pytest.raises(ValueError, match="decision"):
        api.read_bundle(out, public_only=public)


@pytest.mark.parametrize("status", ["accepted", "rejected", "conflicting"])
def test_reader_rejects_rehashed_disposition_without_decision(
    api, inputs, tmp_path, status
):
    out = tmp_path / "unsigned"
    api.write_bundle(api.build_integration(*inputs), out)
    path = out / "legacy_entity_crosswalk.csv"
    reader = csv.DictReader(io.StringIO(path.read_text()))
    rows = list(reader)
    header = list(reader.fieldnames)
    row = next(r for r in rows if r["origin_entity_id"] == "ao-dalia")
    row.update(match_status=status, approved_by="Vamsee", approval_ref="invented")
    header += [k for k in row if k not in header]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=header)
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(stream.getvalue())
    support.repin(out, path.name)
    with pytest.raises(ValueError, match="decision"):
        api.read_bundle(out)


@pytest.mark.parametrize("scope", ["development", "block"])
def test_signed_nonfield_same_entity_cannot_be_built(api, inputs, scope):
    draft = api.build_integration(*inputs)
    entities = copy.deepcopy(draft["entities"])
    entity = next(e for e in entities if e.get("origin_entity_id") == "ao-cameia")
    entity["entity_type"] = scope
    candidates = api.build_crosswalk(
        entities,
        draft["evidence"]["field_observations"],
        copy.deepcopy(draft["ledger"]),
        [],
    )
    row = next(r for r in candidates if r["origin_entity_id"] == "ao-cameia")
    decision = dict(
        row,
        match_status="accepted",
        approved_by="Vamsee",
        approval_ref="synthetic fixture",
        adjudication_source_refs=["s1"],
    )
    with pytest.raises(ValueError, match="field scope"):
        api.build_crosswalk(
            entities,
            draft["evidence"]["field_observations"],
            copy.deepcopy(draft["ledger"]),
            [decision],
        )


@pytest.mark.parametrize("scope", ["development", "block"])
def test_reader_rejects_signed_nonfield_same_entity(api, inputs, tmp_path, scope):
    out = tmp_path / "scope-tampered"
    api.write_bundle(accepted_bundle(api, inputs), out)
    path = out / "entity_registry.csv"
    reader = csv.DictReader(io.StringIO(path.read_text()))
    rows = list(reader)
    header = reader.fieldnames
    next(r for r in rows if r.get("origin_entity_id") == "ao-dalia")[
        "entity_type"
    ] = scope
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=header)
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(stream.getvalue())
    support.repin(out, path.name)
    manifest_path = out / "integration_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["entity_counts"]["field"] -= 1
    manifest["entity_counts"][scope] = manifest["entity_counts"].get(scope, 0) + 1
    support.write_json(manifest_path, manifest)
    with pytest.raises(ValueError, match="field scope"):
        api.read_bundle(out)


def test_accepted_candidate_payload_cannot_bypass_decision_binding(api, inputs):
    bundle = accepted_bundle(api, inputs)
    row = next(r for r in bundle["crosswalk"] if r["origin_entity_id"] == "ao-dalia")
    row["candidate_payload"]["match_status"] = "accepted"
    row["candidate_sha256"] = api.row_fingerprint(row["candidate_payload"])
    bundle["match_decisions"] = []
    with pytest.raises(ValueError, match="decision"):
        api.validation.validate_crosswalk(
            bundle, {e["entity_id"] for e in bundle["entities"]}, {"s1"}
        )


@pytest.mark.parametrize("status", ["accepted", "rejected"])
def test_reader_rejects_rehashed_candidate_disposition_tamper(
    api, inputs, tmp_path, status
):
    out = tmp_path / "candidate-tampered"
    api.write_bundle(api.build_integration(*inputs), out)
    path = out / "legacy_entity_crosswalk.csv"
    reader = csv.DictReader(io.StringIO(path.read_text()))
    rows, header = list(reader), reader.fieldnames
    row = next(r for r in rows if r["origin_entity_id"] == "ao-dalia")
    candidate = json.loads(row["candidate_payload"])
    candidate["match_status"] = status
    row.update(
        candidate_payload=json.dumps(candidate),
        candidate_sha256=api.row_fingerprint(candidate),
        match_status=status,
        approved_by="Vamsee",
        approval_ref="forged candidate",
    )
    header += [k for k in row if k not in header]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=header)
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(stream.getvalue())
    support.repin(out, path.name)
    with pytest.raises(ValueError, match="decision"):
        api.read_bundle(out)
