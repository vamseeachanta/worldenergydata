"""Check all eight metadata contracts against serialized synthetic bundles."""

import ast
import copy
import csv
import hashlib
import importlib.util
import inspect
import io
import json
import re
from types import SimpleNamespace

import catalog_test_support as support
import pytest
import yaml

OFFSHORE = support.ROOT / "data/modules/offshore_assets"
TABLE_NAMES = {
    "entity_registry.csv": "entities",
    "legacy_entity_crosswalk.csv": "crosswalk",
    "legacy_catalog_ledger.csv": "ledger",
    "entity_relationships.csv": "relationships",
    "catalog_links.json": "links",
    "publication_eligibility.json": "eligibility",
    "catalog_match_decisions.json": "match_decisions",
    "integration_manifest.json": "manifest",
}
CSV_NAMES = tuple(n for n in TABLE_NAMES if n.endswith(".csv"))
EMPTY_TABLE = "An empty table is a zero-byte file without a header."
STATUS = "local_draft_public_export_requires_owner_eligibility"


@pytest.fixture(scope="module")
def api():
    return support.api.__wrapped__()


@pytest.fixture(scope="module")
def contract():
    data = yaml.safe_load((OFFSHORE / "schema.yaml").read_text(encoding="utf-8"))
    entries = [d for d in data["datasets"] if "contract_only" in d]
    assert len(entries) == len({d["name"] for d in entries}) == len(TABLE_NAMES)
    return {d["name"]: d for d in entries}


@pytest.fixture(scope="module")
def json_schema():
    return json.loads((OFFSHORE / "catalog_integration_schema.json").read_text())


def column(contract, dataset, name):
    return next(c for c in contract[dataset]["columns"] if c["name"] == name)


def membership_bundle(api, inputs):
    snapshot, legacy, parent = inputs
    path = snapshot / "field_observations.json"
    rows = json.loads(path.read_text())
    rows[0]["development"] = "Synthetic development"
    rows[0]["name"] = "Synthetic field Ω"
    support.write_json(path, rows)
    manifest = json.loads((snapshot / "manifest.json").read_text())
    entry = next(r for r in manifest["files"] if r["path"] == path.name)
    entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    support.write_json(snapshot / "manifest.json", manifest)
    return api.build_integration(snapshot, legacy, parent)


@pytest.fixture(scope="module")
def bundles(api, tmp_path_factory):
    inputs = support.inputs.__wrapped__(tmp_path_factory.mktemp("contract-inputs"))
    draft = membership_bundle(api, inputs)
    decision, reviewed, signed = signed_bundle(api, inputs, draft)
    exported = api.public_export(signed)
    gated, gated_export = gated_bundles(inputs, decision, reviewed)
    snapshot = inputs[0]
    manifest = json.loads((snapshot / "manifest.json").read_text())
    manifest.pop("as_of")
    support.write_json(snapshot / "manifest.json", manifest)
    plain_decision = {
        k: v for k, v in decision.items() if k != "adjudication_source_refs"
    }
    undated = api.build_integration(*inputs, decisions=[plain_decision])
    return draft, signed, exported, undated, gated, gated_export


def signed_bundle(api, inputs, draft):
    candidate = draft["crosswalk"][0]
    decision = {
        k: candidate[k]
        for k in (
            "entity_id",
            "legacy_row_fingerprint",
            "relation_type",
            "candidate_sha256",
        )
    }
    decision.update(
        match_status="pending",
        approved_by=support.reviewed_matrix(draft)[0]["reviewer"],
        approval_ref="synthetic disposition",
        adjudication_source_refs=["s1"],
    )
    reviewed = support.reviewed_matrix(draft)
    reviewed[0].update(
        decision="permission_granted", permission_ref="synthetic permission"
    )
    signed = api.build_integration(*inputs, decisions=[decision], eligibility=reviewed)
    return decision, reviewed, signed


def gated_bundles(inputs, decision, reviewed):
    path = support.ROOT / "scripts/field_development/integrate_angola_catalog.py"
    spec = importlib.util.spec_from_file_location("catalog_cli", path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    decision_path = inputs[0].parent / "synthetic-decisions.json"
    eligibility_path = inputs[0].parent / "synthetic-eligibility.json"
    support.write_json(decision_path, [decision])
    support.write_json(eligibility_path, reviewed)
    args = SimpleNamespace(
        snapshot=inputs[0],
        legacy=inputs[1],
        parent_costs=inputs[2],
        match_decisions=decision_path,
        eligibility=eligibility_path,
        public_export=False,
    )
    gated = cli.build_from_arguments(args)
    args.public_export = True
    return gated, cli.build_from_arguments(args)


def serialized_rows(api, bundle, name):
    raw = api.storage._serialized_files(bundle)[name]
    if name in CSV_NAMES:
        return api.validation.parsed_csv(raw)
    value = json.loads(raw)
    assert raw == (json.dumps(value, **canonical_options(api)) + "\n").encode("utf-8")
    if name == "catalog_links.json":
        return [value] + value["records"]
    return value if isinstance(value, list) else [value]


def literal_domain(function, field):
    """Read the finite membership domain from the committed semantic validator."""
    tree = ast.parse(inspect.getsource(function))
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and isinstance(node.comparators[0], ast.Set):
            left = ast.unparse(node.left)
            if repr(field) in left:
                return set(ast.literal_eval(node.comparators[0]))
    raise AssertionError((function.__name__, field))


def expected_enums(api, bundles, schema):
    defs, props = schema["$defs"], schema["properties"]
    assert set(defs["entity_type"]["enum"]) == set(api.TYPES)
    assert set(defs["date_precision"]["enum"]) == set(api.PRECISIONS)

    def observed(name, field):
        return {
            row[field]
            for bundle in bundles
            for row in serialized_rows(api, bundle, name)
            if field in row
        }

    values = code_enums(api, observed, props)
    for name in ("legacy_entity_crosswalk.csv", "catalog_match_decisions.json"):
        for field in ("relation_type", "match_status"):
            values[name, field] = set(defs[field]["enum"])
    values["entity_relationships.csv", "predicate"] = set(defs["predicate"]["enum"])
    for field in ("dataset_id", "schema_version", "readiness", "state"):
        prop = props[field]
        values["integration_manifest.json", field] = set(
            prop.get("enum", [prop.get("const")])
        )
    return values


def code_enums(api, observed, props):
    eligibility = api.common.load_peer("catalog_build_eligibility")
    return {
        ("entity_registry.csv", "entity_type"): api.TYPES,
        ("entity_registry.csv", "current_configuration_verified"): {
            str(v)
            for v in observed("entity_registry.csv", "current_configuration_verified")
        },
        ("entity_registry.csv", "readiness"): {props["readiness"]["const"]},
        ("legacy_entity_crosswalk.csv", "schema_version"): observed(
            "legacy_entity_crosswalk.csv", "schema_version"
        ),
        ("legacy_catalog_ledger.csv", "status"): literal_domain(
            api.validation.crosswalk.validate_ledger, "status"
        ),
        ("entity_relationships.csv", "date_precision"): api.PRECISIONS,
        ("entity_relationships.csv", "status"): literal_domain(
            api.validation.validate_relationships, "status"
        ),
        ("catalog_links.json", "link_status"): link_status_domain(api),
        ("catalog_links.json", "table"): set(api.TABLES),
        ("publication_eligibility.json", "decision"): literal_domain(
            eligibility._validate_eligibility_update, "decision"
        ),
    }


def link_status_domain(api):
    module = api.common.load_peer("catalog_build_links")
    tree = ast.parse(inspect.getsource(module))
    values = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "link_status":
            values |= {
                n.value
                for n in ast.walk(node.value)
                if isinstance(n, ast.Constant)
                and isinstance(n.value, str)
                and n.value != "field_observations"
            }
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Subscript)
            and isinstance(t.slice, ast.Constant)
            and t.slice.value == "link_status"
            for t in node.targets
        ):
            values.add(ast.literal_eval(node.value))
    return values


def canonical_options(api):
    tree = ast.parse(inspect.getsource(api.canonical))
    call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call))
    return {k.arg: ast.literal_eval(k.value) for k in call.keywords}


def recompute(value, options):
    return hashlib.sha256(json.dumps(value, **options).encode("utf-8")).hexdigest()


def fingerprint_inputs(api, bundles):
    draft = bundles[0]
    relation = draft["relationships"][0]
    candidate = draft["crosswalk"][0]["candidate_payload"]
    return {
        "entity_relationships.csv": {
            "relationship": sorted(set(relation) - {"relationship_id"})
        },
        "legacy_entity_crosswalk.csv": {"candidate": sorted(candidate)},
        "legacy_catalog_ledger.csv": {
            "legacy_row": (
                "parsed cell strings in original_header order, without normalization"
            )
        },
        "catalog_links.json": {
            "record": (
                "complete native evidence object; parent digest uses parsed parent "
                "cells in pinned header order"
            )
        },
        "integration_manifest.json": {
            "decision_sha256": "complete ordered match_decisions array",
            "eligibility_sha256": "complete ordered eligibility array",
        },
    }


def check_fingerprints(contract, api, bundles):
    options = canonical_options(api)
    for name, inputs in fingerprint_inputs(api, bundles).items():
        check_recipe(contract[name]["fingerprint"], inputs, options, api)
    vector = contract["entity_relationships.csv"]["fingerprint"]["recomputation"]
    inputs = fingerprint_inputs(api, bundles)
    fields = inputs["entity_relationships.csv"]["relationship"]
    assert sorted(vector["object"]) == fields
    assert vector["sha256"] == recompute(vector["object"], options)
    raw = api.csv_bytes([vector["object"]]).decode()
    csv_row = next(csv.DictReader(io.StringIO(raw)))
    assert recompute(csv_row, options) != vector["sha256"]
    check_live_fingerprints(api, bundles, options)


def check_recipe(spec, inputs, options, api):
    assert spec["inputs"] == inputs
    assert spec["algorithm"] == "SHA-256" and spec["encoding"] == "UTF-8"
    declared = dict(spec["json_options"])
    declared["separators"] = tuple(declared["separators"])
    assert declared == options
    assert spec["native_values"] == (
        "null stays null; lists retain order; objects have sorted names; no CSV conversion"
    )
    vector = spec["recomputation"]
    value = vector["object"] if "object" in vector else vector["value"]
    assert vector["sha256"] == api.row_fingerprint(value) == recompute(value, options)


def check_live_fingerprints(api, bundles, options):
    relation = bundles[0]["relationships"][0]
    native = {k: v for k, v in relation.items() if k != "relationship_id"}
    assert relation["relationship_id"].endswith(recompute(native, options))
    raw = api.storage._serialized_files(bundles[0])["entity_relationships.csv"].decode()
    emitted = next(csv.DictReader(io.StringIO(raw)))
    assert recompute(emitted, options) != recompute(native, options)
    for row in bundles[0]["crosswalk"]:
        assert row["candidate_sha256"] == recompute(row["candidate_payload"], options)
    for bundle in bundles:
        for name, field in (
            ("decision_sha256", "match_decisions"),
            ("eligibility_sha256", "eligibility"),
        ):
            assert bundle["manifest"][name] == recompute(bundle[field], options)
        dataset = bundle["manifest"]["dataset_id"]
        by_id = {r["record_id"]: r for r in bundle["links"]["records"]}
        for table, rows in bundle["evidence"].items():
            for row in rows:
                identifier = api.record_id(dataset, table, row)
                assert by_id[identifier]["sha256"] == recompute(row, options)


def check_types_and_presence(contract, api, bundles, schema):
    for name, entry in contract.items():
        rows = [r for b in bundles for r in serialized_rows(api, b, name)]
        actual = set().union(*(r.keys() for r in rows))
        if name == "catalog_links.json":
            actual = {"records", "parent_references", "table", "link_status"}
            assert all(not c.get("optional", False) for c in entry["columns"])
        if name == "integration_manifest.json":
            actual |= set(schema["properties"])
        columns = entry["columns"]
        assert len(columns) == len({c["name"] for c in columns})
        assert {c["name"] for c in columns} == actual, name
        check_column_types(columns, rows, name)
        if name in CSV_NAMES:
            check_csv_columns(entry, api, bundles, name)
    check_json_presence(contract, api, bundles)
    check_manifest_presence(contract, api, bundles, schema)


def check_column_types(columns, rows, name):
    kinds = {
        str: "string",
        int: "integer",
        bool: "boolean",
        list: "list",
        dict: "dict",
        type(None): "null",
    }
    for col in columns:
        values = [r[col["name"]] for r in rows if col["name"] in r]
        types = {kinds[type(v)] for v in values}
        assert set(col["type"].split("|")) == types, (name, col["name"], types)
        assert col["unit"] == ""
        assert isinstance(col["description"], str) and col["description"]
        for flag in ("optional", "primary_key"):
            if flag in col:
                assert type(col[flag]) is bool


def check_json_presence(contract, api, bundles):
    for field in ("basis", "reviewer"):
        prop = column(contract, "publication_eligibility.json", field)
        assert prop["optional"] is False
    for name in ("publication_eligibility.json", "catalog_match_decisions.json"):
        rows = [r for b in bundles for r in serialized_rows(api, b, name)]
        for col in contract[name]["columns"]:
            missing = any(col["name"] not in r for r in rows)
            assert col.get("optional", False) == missing, (name, col["name"])


def check_csv_columns(entry, api, bundles, name):
    cols = entry["columns"]
    assert [c["name"] for c in cols] == sorted(c["name"] for c in cols)
    optional = set()
    for bundle in bundles:
        rows = bundle[TABLE_NAMES[name]]
        raw = api.storage._serialized_files(bundle)[name]
        header = next(csv.reader(io.StringIO(raw.decode(), newline="")))
        present = set().union(*(row.keys() for row in rows))
        assert header == [c["name"] for c in cols if c["name"] in present]
        optional |= {c["name"] for c in cols} - set.intersection(
            *(set(row) for row in rows)
        )
    assert {c["name"] for c in cols if c.get("optional")} == optional


def check_manifest_presence(contract, api, bundles, schema):
    entry = contract["integration_manifest.json"]
    optional = {"gate_input_sha256", "source_counts", "deferred_counts"}
    retained = {"legacy_row_count", "as_of", "raw_source_hashes", "authority_note"}
    for col in entry["columns"]:
        field = col["name"]
        presence = col["presence"]
        if field in retained:
            assert "draft only" not in col["description"]
        for mode, bundle in (("draft", bundles[0]), ("export", bundles[2])):
            manifest = json.loads(api.storage._serialized_files(bundle)[entry["name"]])
            expected = "present" if field in manifest else "absent"
            if field == "gate_input_sha256":
                expected = "optional"
            assert presence[mode] == expected, field
        assert col.get("optional", False) == (field in optional)
        check_manifest_schema(col, api, bundles, entry, schema)
    required = {c["name"] for c in entry["columns"] if not c.get("optional")}
    assert set(schema["required"]) <= required


def check_manifest_schema(col, api, bundles, entry, schema):
    field = col["name"]
    if field not in schema["properties"]:
        return
    prop = schema["properties"][field]
    if "additionalProperties" in prop or "properties" in prop:
        assert col["value_schema"] == prop
        for bundle in bundles:
            manifest = json.loads(api.storage._serialized_files(bundle)[entry["name"]])
            if field in manifest:
                check_mapping(manifest[field], prop)


def check_mapping(value, schema):
    assert isinstance(value, dict)
    if schema.get("additionalProperties") is False:
        assert set(value) <= set(schema["properties"])
    for field, item in value.items():
        rule = schema.get("properties", {}).get(
            field, schema.get("additionalProperties")
        )
        if rule["type"] == "string":
            assert isinstance(item, str) and re.fullmatch(rule["pattern"], item)
        else:
            assert type(item) is int and item >= rule["minimum"]


def check_dialect(contract, api, bundles):
    probe = [
        {"alpha": 'synthetic, "quote"\nΩ', "beta": ["x", None], "gamma": None},
        {"alpha": "plain", "beta": {}, "gamma": False},
    ]
    expected = (
        b'alpha,beta,gamma\n"synthetic, ""quote""\n'
        + "Ω".encode()
        + b'","[""x"",null]",\nplain,{},False\n'
    )
    assert api.csv_bytes(probe) == expected
    for name in CSV_NAMES:
        entry = contract[name]
        probe_bundle = copy.deepcopy(bundles[0])
        probe_bundle[TABLE_NAMES[name]] = probe
        assert api.storage._serialized_files(probe_bundle)[name] == expected
        assert entry["empty_table"] == EMPTY_TABLE and api.csv_bytes([]) == b""
        assert entry["dialect"] == {
            "encoding": "UTF-8 without BOM",
            "lineterminator": "\n",
            "delimiter": csv.excel.delimiter,
            "quotechar": csv.excel.quotechar,
            "doublequote": csv.excel.doublequote,
            "quoting": "minimal",
        }
        for phrase in (
            "UTF-8 without BOM",
            "LF",
            "comma delimiter",
            "double-quote quotechar",
            "doubled quotes",
            "minimal quoting",
        ):
            assert phrase in entry["csv_dialect"], (name, phrase)


PRIMARY_FIELDS = {
    "entity_registry.csv": ["entity_id"],
    "legacy_entity_crosswalk.csv": [
        "entity_id",
        "legacy_row_fingerprint",
        "relation_type",
    ],
    "legacy_catalog_ledger.csv": ["legacy_row_fingerprint"],
    "entity_relationships.csv": ["relationship_id"],
    "publication_eligibility.json": ["record_id"],
}
FOREIGN_FIELDS = {
    (name, field): target
    for name, field, target in (
        (
            "entity_registry.csv",
            "evidence_record_id",
            "catalog_links.json:records.record_id",
        ),
        (
            "entity_registry.csv",
            "source_ref",
            "sources.json:source_ref",
        ),
        (
            "legacy_entity_crosswalk.csv",
            "entity_id",
            "entity_registry.csv:entity_id",
        ),
        (
            "legacy_entity_crosswalk.csv",
            "legacy_row_fingerprint",
            "legacy_catalog_ledger.csv:legacy_row_fingerprint",
        ),
        (
            "legacy_entity_crosswalk.csv",
            "evidence_refs",
            "sources.json:source_ref",
        ),
        (
            "legacy_entity_crosswalk.csv",
            "adjudication_source_refs",
            "sources.json:source_ref",
        ),
        (
            "entity_relationships.csv",
            "dependencies",
            "catalog_links.json:records.record_id",
        ),
        (
            "entity_relationships.csv",
            "object_entity_id",
            "entity_registry.csv:entity_id",
        ),
        (
            "entity_relationships.csv",
            "subject_entity_id",
            "entity_registry.csv:entity_id",
        ),
        (
            "entity_relationships.csv",
            "source_refs",
            "sources.json:source_ref",
        ),
        (
            "publication_eligibility.json",
            "record_id",
            [
                "catalog_links.json:records.record_id",
                "catalog_links.json:parent_references.record_id",
            ],
        ),
    )
}


def check_keys(contract, api, bundles):
    for name, entry in contract.items():
        fields = [c["name"] for c in entry["columns"] if c.get("primary_key")]
        assert fields == PRIMARY_FIELDS.get(name, [])
        for col in entry["columns"]:
            expected = FOREIGN_FIELDS.get((name, col["name"]))
            assert col.get("foreign_key") == expected, (name, col["name"])
    check_runtime_keys(api, bundles)


def check_runtime_keys(api, bundles):
    for bundle in bundles:
        api.validation.validate_bundle(bundle)
        for name, fields in PRIMARY_FIELDS.items():
            rows = bundle[TABLE_NAMES[name]]
            assert len({tuple(r[f] for f in fields) for r in rows}) == len(rows)
        for (name, field), target in FOREIGN_FIELDS.items():
            targets = target if isinstance(target, list) else [target]
            ids = set()
            for spec in targets:
                artifact, path = spec.split(":")
                if artifact == "sources.json":
                    target_rows = bundle["evidence"]["sources"]
                elif artifact == "catalog_links.json":
                    part, path = path.split(".")
                    target_rows = bundle["links"][part]
                else:
                    target_rows = bundle[TABLE_NAMES[artifact]]
                ids |= {r[path] for r in target_rows}
            for row in bundle[TABLE_NAMES[name]]:
                value = row.get(field, [])
                assert set(value if isinstance(value, list) else [value]) <= ids


def check_contract(contract, api, bundles, schema):
    assert set(contract) == set(TABLE_NAMES)
    for name, entry in contract.items():
        assert entry["name"] == name and entry["path"] == "<output-dir>/" + name
        assert entry["format"] == name.rsplit(".", 1)[1]
        assert entry["contract_only"] is True and entry["status"] == STATUS
        assert "row_count" not in entry and "size_bytes" not in entry
        if name in CSV_NAMES + ("catalog_links.json",):
            assert type(entry["schema_version"]) is int
            assert entry["schema_version"] == bundles[0]["manifest"]["schema_version"]
        else:
            assert "schema_version" not in entry
    expected = expected_enums(api, bundles, schema)
    actual = {
        (n, c["name"]): c["enum"]
        for n, d in contract.items()
        for c in d["columns"]
        if "enum" in c
    }
    assert set(actual) == set(expected)
    for field, values in expected.items():
        declared = {(type(v), v) for v in actual[field]}
        assert len(actual[field]) == len(declared)
        assert declared == {(type(v), v) for v in values}, field
    check_types_and_presence(contract, api, bundles, schema)
    check_keys(contract, api, bundles)
    check_dialect(contract, api, bundles)
    check_fingerprints(contract, api, bundles)


def test_contract_matches_writer(contract, api, bundles, json_schema):
    check_contract(contract, api, bundles, json_schema)


def test_nullable_draft_values(contract, api, bundles, json_schema):
    assert bundles[0]["eligibility"][0]["basis"] is None
    assert bundles[0]["eligibility"][0]["reviewer"] is None
    assert bundles[3]["manifest"]["as_of"] is None
    check_types_and_presence(contract, api, bundles, json_schema)


def test_eligibility_union_and_uniqueness(contract, api, bundles):
    bundle = bundles[0]
    ids = column(contract, "publication_eligibility.json", "record_id")["foreign_key"]
    assert len(ids) == 2
    for part in ("records", "parent_references"):
        row = bundle["links"][part][0]
        matrix = api.eligibility_matrix(
            bundle["links"],
            [{"record_id": row["record_id"], "decision": "prohibited"}],
        )
        decision = next(r for r in matrix if r["record_id"] == row["record_id"])
        assert decision["decision"] == "prohibited"
    with pytest.raises(ValueError, match="unknown or duplicate"):
        api.eligibility_matrix(bundle["links"], [{"record_id": "synthetic-unknown"}])
    row = {"record_id": bundle["links"]["records"][0]["record_id"]}
    with pytest.raises(ValueError, match="unknown or duplicate"):
        api.eligibility_matrix(bundle["links"], [row, row])


def test_manifest_presence_by_mode(contract, api, bundles, json_schema):
    check_manifest_presence(contract, api, bundles, json_schema)


@pytest.mark.parametrize("name", CSV_NAMES)
def test_empty_table_contract(contract, api, bundles, name):
    empty = copy.deepcopy(bundles[0])
    empty[TABLE_NAMES[name]] = []
    assert api.storage._serialized_files(empty)[name] == b""
    assert contract[name]["empty_table"] == EMPTY_TABLE


def test_fingerprint_native_vector(contract, api, bundles):
    check_fingerprints(contract, api, bundles)


TARGETED_MUTATIONS = (
    "required_header",
    "optional_header",
    "country_type",
    "entity_enum",
    "eligibility_enum",
    "eligibility_fk",
    "registry_pk",
    "delimiter",
    "line_ending",
    "ledger_fingerprint",
    "missing_links",
    "gated_status",
)
EXTRA_MUTATIONS = (
    "basis_null",
    "reviewer_null",
    "as_of_null",
    "single_target",
    "draft_only",
    "empty_table",
    "json_options",
    "quotechar",
    "missing_eligibility",
    "missing_decisions",
    "column_order",
    "duplicate_column",
    "manifest_mapping",
    "missing_manifest",
    "missing_version",
    "links_optional",
    "boolean_version",
    "float_version",
)
ENUM_FIELDS = (
    ("entity_registry.csv", "current_configuration_verified"),
    ("entity_registry.csv", "entity_type"),
    ("entity_registry.csv", "readiness"),
    ("legacy_entity_crosswalk.csv", "match_status"),
    ("legacy_entity_crosswalk.csv", "relation_type"),
    ("legacy_entity_crosswalk.csv", "schema_version"),
    ("legacy_catalog_ledger.csv", "status"),
    ("entity_relationships.csv", "date_precision"),
    ("entity_relationships.csv", "predicate"),
    ("entity_relationships.csv", "status"),
    ("catalog_links.json", "link_status"),
    ("catalog_links.json", "table"),
    ("publication_eligibility.json", "decision"),
    ("catalog_match_decisions.json", "relation_type"),
    ("catalog_match_decisions.json", "match_status"),
    ("integration_manifest.json", "dataset_id"),
    ("integration_manifest.json", "schema_version"),
    ("integration_manifest.json", "state"),
    ("integration_manifest.json", "readiness"),
)


COLUMN_MUTATIONS = {
    "required_header": ("entity_registry.csv", "country", "name", "aaa_wrong_country"),
    "country_type": ("entity_registry.csv", "country", "type", "integer"),
    "entity_enum": ("entity_registry.csv", "entity_type", "enum", ["wrong"]),
    "registry_pk": ("entity_registry.csv", "entity_id", "primary_key", False),
    "eligibility_enum": ("publication_eligibility.json", "decision", "enum", ["wrong"]),
    "eligibility_fk": (
        "publication_eligibility.json",
        "record_id",
        "foreign_key",
        "wrong:field",
    ),
    "single_target": (
        "publication_eligibility.json",
        "record_id",
        "foreign_key",
        "catalog_links.json:records.record_id",
    ),
    "basis_null": ("publication_eligibility.json", "basis", "type", "string"),
    "reviewer_null": ("publication_eligibility.json", "reviewer", "type", "string"),
    "as_of_null": ("integration_manifest.json", "as_of", "type", "string"),
}
ENTRY_REMOVALS = {
    "missing_links": "catalog_links.json",
    "missing_eligibility": "publication_eligibility.json",
    "missing_decisions": "catalog_match_decisions.json",
    "missing_manifest": "integration_manifest.json",
}
DIALECT_MUTATIONS = {
    "delimiter": ("comma delimiter", "semicolon delimiter"),
    "line_ending": ("LF", "CR"),
    "quotechar": ("double-quote quotechar", "single-quote quotechar"),
}


def mutate(contract, mutation):
    registry = contract["entity_registry.csv"]
    if isinstance(mutation, tuple):
        c = column(contract, *mutation)
        c["enum"] = c["enum"] + ["synthetic-wrong"]
    elif mutation in COLUMN_MUTATIONS:
        name, field, attr, value = COLUMN_MUTATIONS[mutation]
        column(contract, name, field)[attr] = copy.deepcopy(value)
    elif mutation in ENTRY_REMOVALS:
        contract.pop(ENTRY_REMOVALS[mutation])
    elif mutation in DIALECT_MUTATIONS:
        before, after = DIALECT_MUTATIONS[mutation]
        registry["csv_dialect"] = registry["csv_dialect"].replace(before, after)
    else:
        mutate_remaining(contract, registry, mutation)


def mutate_remaining(contract, registry, mutation):
    if mutation == "optional_header":
        registry["columns"].append(
            {"name": "zzz_unemitted", "type": "string", "optional": True}
        )
    elif mutation == "ledger_fingerprint":
        contract["legacy_catalog_ledger.csv"]["fingerprint"] = "different serialization"
    elif mutation == "gated_status":
        registry["status"] = "local_draft_wrong"
    elif mutation == "draft_only":
        prop = column(contract, "integration_manifest.json", "authority_note")
        prop["presence"]["export"] = "absent"
        prop["description"] += "; draft only"
    elif mutation == "empty_table":
        registry.pop("empty_table")
    elif mutation == "json_options":
        recipe = contract["entity_relationships.csv"]["fingerprint"]
        recipe["json_options"]["ensure_ascii"] = True
    elif mutation == "column_order":
        registry["columns"].reverse()
    elif mutation == "duplicate_column":
        registry["columns"].append(copy.deepcopy(registry["columns"][0]))
    elif mutation == "manifest_mapping":
        prop = column(contract, "integration_manifest.json", "counts")
        prop["value_schema"]["additionalProperties"]["minimum"] = -1
    elif mutation == "missing_version":
        registry.pop("schema_version")
    elif mutation == "links_optional":
        column(contract, "catalog_links.json", "records")["optional"] = True
    elif mutation in {"boolean_version", "float_version"}:
        registry["schema_version"] = True if mutation == "boolean_version" else 1.0
    else:
        raise AssertionError(mutation)


@pytest.mark.parametrize(
    "mutation",
    TARGETED_MUTATIONS + EXTRA_MUTATIONS + ENUM_FIELDS,
    ids=list(TARGETED_MUTATIONS + EXTRA_MUTATIONS)
    + [n + ":" + c for n, c in ENUM_FIELDS],
)
def test_contract_mutations_are_caught(contract, api, bundles, json_schema, mutation):
    check_contract(contract, api, bundles, json_schema)
    changed = copy.deepcopy(contract)
    mutate(changed, mutation)
    with pytest.raises((AssertionError, KeyError, TypeError, StopIteration)):
        check_contract(changed, api, bundles, json_schema)
