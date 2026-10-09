"""Keep the offshore_assets schema.yaml catalog-extension contract in sync with code."""

import hashlib
import json

import catalog_test_support as support
import pytest
import yaml

api = support.api
inputs = support.inputs
OFFSHORE = support.ROOT / "data/modules/offshore_assets"
CSV_NAMES = (
    "entity_registry.csv",
    "legacy_entity_crosswalk.csv",
    "legacy_catalog_ledger.csv",
    "entity_relationships.csv",
)


@pytest.fixture(scope="module")
def contract():
    data = yaml.safe_load((OFFSHORE / "schema.yaml").read_text(encoding="utf-8"))
    return {d["name"]: d for d in data["datasets"] if d.get("contract_only")}


@pytest.fixture(scope="module")
def json_schema():
    raw = (OFFSHORE / "catalog_integration_schema.json").read_text(encoding="utf-8")
    return json.loads(raw)


def membership_bundle(api, inputs):
    """Draft bundle in which one field belongs to a development (relationship row)."""
    snapshot, legacy, parent = inputs
    path = snapshot / "field_observations.json"
    rows = json.loads(path.read_text())
    rows[0]["development"] = "Kaminho"
    support.write_json(path, rows)
    manifest = json.loads((snapshot / "manifest.json").read_text())
    entry = next(r for r in manifest["files"] if r["path"] == path.name)
    entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    support.write_json(snapshot / "manifest.json", manifest)
    return api.build_integration(snapshot, legacy, parent)


def column(contract, dataset, name):
    return next(c for c in contract[dataset]["columns"] if c["name"] == name)


def test_entries_are_draft_and_unsized(contract):
    assert set(CSV_NAMES) <= set(contract)
    for entry in contract.values():
        assert entry["status"].startswith("local_draft")
        assert "row_count" not in entry and "size_bytes" not in entry


def test_csv_headers_match_writer(api, inputs, contract):
    bundle = membership_bundle(api, inputs)
    files = api.storage._serialized_files(bundle)
    for name in CSV_NAMES:
        header = files[name].decode("utf-8").split("\n", 1)[0].split(",")
        declared = [c["name"] for c in contract[name]["columns"]]
        required = [c["name"] for c in contract[name]["columns"] if not c.get("optional")]
        assert declared == sorted(declared), name
        assert set(required) <= set(header) <= set(declared), name


def test_enums_match_code_and_json_schema(api, contract, json_schema):
    defs = json_schema["$defs"]
    expected = {
        ("entity_registry.csv", "entity_type"): set(api.TYPES),
        ("entity_relationships.csv", "date_precision"): set(api.PRECISIONS),
        ("entity_relationships.csv", "predicate"): set(defs["predicate"]["enum"]),
        ("legacy_entity_crosswalk.csv", "match_status"): set(defs["match_status"]["enum"]),
        ("legacy_entity_crosswalk.csv", "relation_type"): set(defs["relation_type"]["enum"]),
        ("integration_manifest.json", "state"): set(json_schema["properties"]["state"]["enum"]),
    }
    for (dataset, name), values in expected.items():
        assert set(column(contract, dataset, name)["enum"]) == values, (dataset, name)
    assert set(defs["entity_type"]["enum"]) == set(api.TYPES)
    assert set(defs["date_precision"]["enum"]) == set(api.PRECISIONS)
    readiness = column(contract, "entity_registry.csv", "readiness")["enum"]
    assert readiness == [json_schema["properties"]["readiness"]["const"]]


def test_manifest_and_dialect_contract(api, inputs, contract, json_schema):
    manifest = api.build_integration(*inputs)["manifest"]
    declared = {c["name"] for c in contract["integration_manifest.json"]["columns"]}
    assert set(manifest) <= declared
    assert set(json_schema["required"]) <= declared
    dialect = contract["entity_registry.csv"]["csv_dialect"]
    assert "UTF-8 without BOM" in dialect and "LF" in dialect
    assert contract["legacy_catalog_ledger.csv"]["schema_version"] == 1
    assert api.row_fingerprint(["a", "b"]) == api.digest_bytes(b'["a","b"]')
