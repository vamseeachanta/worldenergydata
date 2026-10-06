"""Contract tests for evidence-preserving Angola catalog integration (#1144)."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "catalog_integration", ROOT / "src/worldenergydata/field_development/catalog_integration.py"
)


@pytest.fixture
def api():
    module = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
    return module


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def inputs(tmp_path):
    legacy = tmp_path / "fields.csv"
    legacy.write_text("FIELD_ID,FIELD_NAME,COUNTRY,BLOCK\n1,Cameia,Angola,Block 21\n"
                      "2,Dalia,Angola,17\n2,Dalia,Angola,17\n"
                      "2,Other,Angola,17\n3,Tombua Landana,Angola,Block 14\n",
                      encoding="utf-8")
    parent = tmp_path / "sanctioned.csv"
    parent.write_text("PROJECT,SOURCE_URL\nDalia,https://example.org/dalia\n", encoding="utf-8")
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    common = {"entity_type": "field", "country": "Angola", "development": "Unassigned",
              "current_configuration_verified": False, "source_ref": "s1",
              "source_vintage": "2004", "water_depth_scope": "development envelope"}
    rows = [dict(common, entity_id="ao-cameia", name="Cameia", block="20/11", water_depth_m=1700),
            dict(common, entity_id="ao-dalia", name="Dalia", block="17", water_depth_m={"min": 600, "max": 1200}),
            dict(common, entity_id="ao-tombua", name="Tombua", block="14"),
            dict(common, entity_id="ao-phase", name="Mafumeira Sul", block="0", entity_type="development_phase")]
    tables = {"field_observations": rows,
              "sources": [{"source_ref": "s1", "url": "https://example.org/s1"}],
              "cost_observations": [{"cost_id": "c1", "entity_or_scope": "Dalia", "source_ref": "s1",
                                     "scope_type": "project", "unit": "USD billion", "value": 3.4,
                                     "field_allocation_permitted": False}],
              "milestone_observations": [{"subject": "Dalia", "event_date": "2004-01-01", "precision": "upper_bound_day", "source_ref": "s1", "scope": "field"},
                                         {"subject": "Landana North #1", "event_date": "2029-H1", "precision": "half_year", "source_ref": "s1", "scope": "well"}],
              "inherited_cost_records": [{"project": "Dalia", "source_url": "https://example.org/dalia"}]}
    for name, records in tables.items():
        write_json(snapshot / (name + ".json"), records)
    manifest = {"dataset_id": "angola-field-development-evidence", "as_of": "2026-10-02",
                "files": [{"path": name + ".json", "record_count": len(records),
                           "sha256": hashlib.sha256((snapshot / (name + ".json")).read_bytes()).hexdigest()}
                          for name, records in tables.items()],
                "inherited_cost_input": {"sha256": hashlib.sha256(parent.read_bytes()).hexdigest()}}
    write_json(snapshot / "manifest.json", manifest)
    return snapshot, legacy, parent


def test_draft_reconciles_rows_without_automatic_equivalence(api, inputs):
    bundle = api.build_integration(*inputs)
    assert len([e for e in bundle["entities"] if not e.get("supplemental")]) == 4
    assert len(bundle["ledger"]) == 4
    assert sum(row["multiplicity"] for row in bundle["ledger"]) == 5
    matches = {row["origin_entity_id"]: row for row in bundle["crosswalk"]}
    assert matches["ao-cameia"]["match_status"] == "conflicting"
    assert matches["ao-dalia"]["match_status"] == "pending"
    assert matches["ao-tombua"]["relation_type"] == "constituent_of"
    assert all(row["match_status"] != "accepted" for row in bundle["crosswalk"])


def test_preserves_scopes_bound_dates_and_separate_inherited_costs(api, inputs):
    bundle = api.build_integration(*inputs)
    assert bundle["evidence"]["field_observations"][1]["water_depth_m"] == {"min": 600, "max": 1200}
    assert [row["precision"] for row in bundle["evidence"]["milestone_observations"]] == ["upper_bound_day", "half_year"]
    assert bundle["manifest"]["counts"]["cost_observations"] == 1
    assert bundle["manifest"]["counts"]["inherited_cost_records"] == 1
    inherited = [row for row in bundle["links"]["records"] if row["table"] == "inherited_cost_records"]
    assert inherited[0]["parent_row_fingerprint"]
    well = [row for row in bundle["links"]["records"] if row["subject"] == "Landana North #1"]
    assert well[0]["link_status"] == "candidate"
    cost = [row for row in bundle["links"]["records"] if row["table"] == "cost_observations"]
    assert cost[0]["link_status"] == "candidate"
    cost_entity = next(e for e in bundle["entities"] if e["entity_id"] == cost[0]["entity_id"])
    assert cost_entity["entity_type"] == "development"  # project cost is not a field cost


def test_deterministic_output_and_reader_tamper_detection(api, inputs, tmp_path):
    first = api.build_integration(*inputs)
    second = api.build_integration(*inputs)
    assert first == second
    out = tmp_path / "out"
    api.write_bundle(first, out)
    assert len(api.read_bundle(out)["entities"]) == len(first["entities"])
    registry = out / "entity_registry.csv"
    registry.write_bytes(registry.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="digest"):
        api.read_bundle(out)


def test_source_tamper_fails_before_import(api, inputs):
    (inputs[0] / "sources.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="digest"):
        api.build_integration(*inputs)


def test_missing_decisions_cannot_publish_empty_success(api, inputs):
    bundle = api.build_integration(*inputs)
    assert all(row["decision"] == "unresolved" for row in bundle["eligibility"])
    with pytest.raises(ValueError, match="empty|deferred"):
        api.public_export(bundle)


def test_acceptance_requires_verified_owner_decision(api, inputs):
    bundle = api.build_integration(*inputs)
    decision = dict(bundle["crosswalk"][1], match_status="accepted")
    with pytest.raises(ValueError, match="signoff"):
        api.build_integration(*inputs, decisions=[decision])


def test_eligibility_cascades_source_denial(api, inputs):
    bundle = api.build_integration(*inputs)
    matrix = [dict(row, decision="eligible_factual_derivative", basis="public authored facts",
                   reviewer="Vamsee", approval_ref="owner decision", reviewed_sha256=row["sha256"])
              for row in bundle["eligibility"]]
    next(row for row in matrix if row["table"] == "sources")["decision"] = "prohibited"
    bundle = api.build_integration(*inputs, eligibility=matrix)
    with pytest.raises(ValueError, match="empty|deferred"):
        api.public_export(bundle)


def test_invalid_precision_and_duplicate_source_rejected(api, inputs):
    assert api.record_id("dataset", "table", {"a": 1}) == api.record_id("dataset", "table", {"a": 1})
    assert api.row_fingerprint(["x", ""]) != api.row_fingerprint(["x ", ""])
    with pytest.raises(ValueError, match="precision"):
        api.validate_evidence({"milestone_observations": [{"precision": "exact-ish"}]})


def test_supported_membership_is_source_dated_and_scope_separated(api, inputs):
    snapshot, legacy, parent = inputs
    rows = json.loads((snapshot / "field_observations.json").read_text())
    rows[0]["development"] = "Kaminho"
    write_json(snapshot / "field_observations.json", rows)
    manifest = json.loads((snapshot / "manifest.json").read_text())
    next(r for r in manifest["files"] if r["path"] == "field_observations.json")["sha256"] = hashlib.sha256((snapshot / "field_observations.json").read_bytes()).hexdigest()
    write_json(snapshot / "manifest.json", manifest)
    bundle = api.build_integration(snapshot, legacy, parent)
    relationship = bundle["relationships"][0]
    assert relationship["predicate"] == "part_of"
    assert relationship["source_refs"] == ["s1"]
    assert relationship["effective_date"] is None  # publication year is not effective date
    assert relationship["source_vintage"] == "2004"


def reviewed_matrix(bundle):
    return [dict(row, decision="eligible_factual_derivative", basis="test factual derivative",
                 reviewer="Vamsee", approval_ref="test owner decision", reviewed_sha256=row["sha256"])
            for row in bundle["eligibility"]]


def test_public_export_preserves_scopes_and_parent_nonduplication(api, inputs, tmp_path):
    draft = api.build_integration(*inputs)
    reviewed = api.build_integration(*inputs, eligibility=reviewed_matrix(draft))
    exported = api.public_export(reviewed)
    api.write_bundle(exported, tmp_path / "public")
    reread = api.read_bundle(tmp_path / "public", public_only=True)
    assert reread["manifest"]["counts"]["cost_observations"] == 1
    assert reread["manifest"]["counts"]["inherited_cost_records"] == 1
    assert reread["manifest"]["research_entity_count"] == 4
    assert len(reread["entities"]) == reread["manifest"]["registry_entity_count"]
    assert reread["crosswalk"]


def test_field_rejection_defers_dependent_milestone(api, inputs):
    draft = api.build_integration(*inputs)
    matrix = reviewed_matrix(draft)
    next(r for r in matrix if r["record_id"].endswith("field_observations:ao-dalia"))["decision"] = "prohibited"
    exported = api.public_export(api.build_integration(*inputs, eligibility=matrix))
    assert not any(r["subject"] == "Dalia" and r["table"] == "milestone_observations" for r in exported["links"]["records"])
    assert exported["manifest"]["deferred_counts"]["milestone_observations"] == 1


def test_parent_rejection_defers_inherited_record(api, inputs):
    draft = api.build_integration(*inputs)
    matrix = reviewed_matrix(draft)
    next(r for r in matrix if r["table"] == "parent_reference")["decision"] = "prohibited"
    exported = api.public_export(api.build_integration(*inputs, eligibility=matrix))
    assert not exported["evidence"]["inherited_cost_records"]
    assert exported["manifest"]["deferred_counts"]["inherited_cost_records"] == 1
    assert exported["manifest"]["deferred_counts"]["parent_reference"] == 1
    assert exported["manifest"]["source_counts"]["inherited_cost_records"] == 1


def test_stale_signoff_and_missing_output_pin_rejected(api, inputs, tmp_path):
    draft = api.build_integration(*inputs)
    matrix = reviewed_matrix(draft)
    matrix[0]["reviewed_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="signoff"):
        api.build_integration(*inputs, eligibility=matrix)
    api.write_bundle(draft, tmp_path / "out")
    path = tmp_path / "out/integration_manifest.json"
    manifest = json.loads(path.read_text())
    del manifest["output_hashes"]["sources.json"]
    write_json(path, manifest)
    with pytest.raises(ValueError, match="pin"):
        api.read_bundle(tmp_path / "out")


def repin(out, name):
    path = out / "integration_manifest.json"
    manifest = json.loads(path.read_text())
    manifest["output_hashes"][name] = hashlib.sha256((out / name).read_bytes()).hexdigest()
    write_json(path, manifest)


@pytest.mark.parametrize("kind", ["duplicate_entity", "dangling_crosswalk", "invalid_relation"])
def test_reader_semantics_fail_even_with_rehashed_files(api, inputs, tmp_path, kind):
    bundle = api.build_integration(*inputs)
    if kind == "duplicate_entity":
        bundle["entities"].append(bundle["entities"][0])
    elif kind == "dangling_crosswalk":
        bundle["crosswalk"][0]["entity_id"] = "does-not-exist"
    else:
        bundle["relationships"] = [{"relationship_id": "r", "subject_entity_id": bundle["entities"][0]["entity_id"],
                                   "object_entity_id": bundle["entities"][1]["entity_id"], "predicate": "invented",
                                   "source_refs": ["s1"], "date_precision": "unknown", "status": "supported"}]
    api.write_bundle(bundle, tmp_path / "out")
    with pytest.raises(ValueError):
        api.read_bundle(tmp_path / "out")


def test_reader_decodes_nested_values_and_preserves_empty_tables(api, inputs, tmp_path):
    bundle = api.build_integration(*inputs)
    bundle["crosswalk"] = []
    api.write_bundle(bundle, tmp_path / "out")
    reread = api.read_bundle(tmp_path / "out")
    assert reread["crosswalk"] == []
    assert isinstance(reread["ledger"][0]["attributes"], dict)
    assert isinstance(reread["ledger"][0]["multiplicity"], int)


def test_conflicting_identity_needs_known_adjudication_source(api, inputs):
    bundle = api.build_integration(*inputs)
    candidate = next(r for r in bundle["crosswalk"] if r["origin_entity_id"] == "ao-cameia")
    decision = dict(candidate, match_status="accepted", approved_by="Vamsee", approval_ref="test decision",
                    adjudication_source_refs=["invented-source"])
    with pytest.raises(ValueError, match="source"):
        api.build_integration(*inputs, decisions=[decision])


def test_reader_cannot_promote_unreviewed_draft_by_state_string(api, inputs, tmp_path):
    bundle = api.build_integration(*inputs)
    bundle["manifest"]["state"] = "eligible_derived_export"
    api.write_bundle(bundle, tmp_path / "out")
    with pytest.raises(ValueError, match="eligibility"):
        api.read_bundle(tmp_path / "out", public_only=True)


@pytest.mark.parametrize("defect", ["dataset_id", "input_hashes", "decision_sha256"])
def test_reader_requires_manifest_identity_and_provenance(api, inputs, tmp_path, defect):
    bundle = api.build_integration(*inputs)
    api.write_bundle(bundle, tmp_path / "out")
    path = tmp_path / "out/integration_manifest.json"
    manifest = json.loads(path.read_text())
    if defect == "dataset_id":
        manifest[defect] = "unrelated-dataset"
    elif defect == "input_hashes":
        manifest[defect] = {}
    else:
        manifest[defect] = "not-a-digest"
    write_json(path, manifest)
    with pytest.raises(ValueError):
        api.read_bundle(tmp_path / "out")


@pytest.mark.parametrize("defect", ["missing_link", "link_digest", "legacy_digest", "candidate_digest", "legacy_count"])
def test_reader_rejects_rehashed_semantic_closure_defects(api, inputs, tmp_path, defect):
    bundle = api.build_integration(*inputs)
    if defect == "missing_link":
        bundle["links"]["records"] = [r for r in bundle["links"]["records"] if r["table"] != "cost_observations"]
    elif defect == "link_digest":
        bundle["links"]["records"][0]["sha256"] = "0" * 64
    elif defect == "legacy_digest":
        bundle["ledger"][0]["attributes"]["FIELD_NAME"] = "tampered"
    elif defect == "candidate_digest":
        bundle["crosswalk"][0]["candidate_sha256"] = "0" * 64
    else:
        bundle["manifest"]["legacy_row_count"] += 1
    api.write_bundle(bundle, tmp_path / "out")
    with pytest.raises(ValueError):
        api.read_bundle(tmp_path / "out")


def test_export_recomputes_decision_pins_and_preserves_composite_status(api, inputs):
    draft = api.build_integration(*inputs)
    matrix = reviewed_matrix(draft)
    next(r for r in matrix if r["table"] == "parent_reference")["decision"] = "prohibited"
    exported = api.public_export(api.build_integration(*inputs, eligibility=matrix))
    assert exported["manifest"]["eligibility_sha256"] == api.row_fingerprint(exported["eligibility"])
    assert exported["manifest"]["decision_sha256"] == api.row_fingerprint(exported["match_decisions"])
    composite = next(g for g in exported["ledger"] if g["attributes"]["FIELD_NAME"] == "Tombua Landana")
    assert composite["status"] == "composite"


def test_reader_consumes_each_pinned_artifact_once(api, inputs, tmp_path, monkeypatch):
    api.write_bundle(api.build_integration(*inputs), tmp_path / "out")
    original = Path.open
    reads = {}
    def counted(path, *args, **kwargs):
        if path.parent == tmp_path / "out":
            reads[path.name] = reads.get(path.name, 0) + 1
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", counted)
    api.read_bundle(tmp_path / "out")
    assert set(reads.values()) == {1}


def test_public_export_defers_match_with_unreleased_adjudication_source(api, inputs):
    snapshot, _, _ = inputs
    sources = json.loads((snapshot / "sources.json").read_text())
    sources.append({"source_ref": "s2", "url": "https://example.org/adjudication"})
    write_json(snapshot / "sources.json", sources)
    manifest = json.loads((snapshot / "manifest.json").read_text())
    pin = next(r for r in manifest["files"] if r["path"] == "sources.json")
    pin.update(record_count=2, sha256=hashlib.sha256((snapshot / "sources.json").read_bytes()).hexdigest())
    write_json(snapshot / "manifest.json", manifest)
    draft = api.build_integration(*inputs)
    candidate = next(r for r in draft["crosswalk"] if r["origin_entity_id"] == "ao-cameia")
    decision = dict(candidate, match_status="accepted", approved_by="Vamsee", approval_ref="fixture evidence", adjudication_source_refs=["s2"])
    matrix = reviewed_matrix(draft)
    next(r for r in matrix if r["record_id"].endswith("sources:s2"))["decision"] = "prohibited"
    exported = api.public_export(api.build_integration(*inputs, decisions=[decision], eligibility=matrix))
    assert not any(r["origin_entity_id"] == "ao-cameia" for r in exported["crosswalk"])


def test_reader_rejects_duplicate_manifest_keys(api, inputs, tmp_path):
    api.write_bundle(api.build_integration(*inputs), tmp_path / "out")
    path = tmp_path / "out/integration_manifest.json"
    path.write_text(path.read_text().replace('{', '{"schema_version":2,', 1), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        api.read_bundle(tmp_path / "out")


@pytest.mark.parametrize("status", ["pending", "rejected"])
def test_conflict_disposition_requires_revision_bound_evidence_claim(api, inputs, status):
    bundle = api.build_integration(*inputs)
    candidate = next(r for r in bundle["crosswalk"] if r["origin_entity_id"] == "ao-cameia")
    decision = {k: candidate[k] for k in ("entity_id", "legacy_row_fingerprint", "relation_type")}
    decision["match_status"] = status
    with pytest.raises(ValueError, match="evidence"):
        api.build_integration(*inputs, decisions=[decision])
