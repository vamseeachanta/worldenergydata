"""Synthetic contract examples; declarations do not establish source rights."""

import pytest
import yaml

from worldenergydata.common.run_manifest import RunManifest


@pytest.fixture
def record():
    return {
        "schema_version": 1,
        "run_id": "example-run",
        "attempt_id": "attempt-1",
        "created_at": "2026-11-16T12:00:00Z",
        "code_ref": "example-code-revision",
        "scope": "bsee-well-operations",
        "catalog_ref": {
            "catalog_id": "data-catalog",
            "catalog_version": "1.1.0",
            "generated_at": "2026-11-15T12:00:00Z",
            "content_sha256": "a" * 64,
            "unavailable_reason": None,
        },
        "probe_set": ["metadata-summary"],
        "datasets": [
            {
                "dataset_id": "example-source",
                "dataset_version": "example-version",
                "state": "real",
                "domain": "bsee",
                "source_authority": "BSEE",
                "source_url": "https://www.data.bsee.gov/",
                "license": "public-domain",
                "source_class": "public-federal-bsee",
                "retrieved_at": "2026-11-15T12:00:00Z",
                "data_as_of": "2026-11-14",
                "content_sha256": "b" * 64,
                "derivation_path": ["example-source-version"],
                "freshness_criteria": "example-reviewed-criterion-v1",
                "unavailable_reason": None,
            }
        ],
        "outputs": [
            {
                "path": "outputs/summary.json",
                "content_sha256": "c" * 64,
                "unavailable_reason": None,
            }
        ],
        "limitations": ["Synthetic metadata; no source inspection is performed."],
        "rerun_of_attempt_id": None,
        "supersedes_run_id": None,
    }


def test_round_trip(record):
    manifest = RunManifest.from_dict(record)
    assert manifest.to_dict() == record
    assert RunManifest.from_yaml(manifest.to_yaml()) == manifest
    assert manifest.to_yaml() == manifest.to_yaml()
    assert manifest.readiness() == "declared-eligible"


@pytest.mark.parametrize(
    "state",
    ["real", "empty", "stale", "missing_module_dir", "external_only", "lfs_stub"],
)
def test_states(record, state):
    record["datasets"][0]["state"] = state
    manifest = RunManifest.from_dict(record)
    assert RunManifest.from_yaml(manifest.to_yaml()).to_dict() == record
    assert manifest.readiness() == (
        "declared-eligible" if state == "real" else "blocked"
    )


@pytest.mark.parametrize(
    "key",
    [
        "dataset_version",
        "domain",
        "source_authority",
        "source_url",
        "license",
        "source_class",
        "retrieved_at",
        "data_as_of",
        "content_sha256",
        "derivation_path",
        "freshness_criteria",
    ],
)
def test_unavailable_evidence(record, key):
    record["datasets"][0][key] = None
    with pytest.raises(ValueError):
        RunManifest.from_dict(record)
    record["datasets"][0]["unavailable_reason"] = "Evidence not supplied."
    manifest = RunManifest.from_dict(record)
    assert RunManifest.from_yaml(manifest.to_yaml()) == manifest
    assert manifest.readiness() == "blocked"


@pytest.mark.parametrize(
    "key,value",
    [
        ("source_class", "unknown"),
        ("license", "unknown"),
        ("domain", "fdas"),
        ("source_authority", "unknown"),
        ("source_url", "https://example.org/"),
    ],
)
def test_ambiguous_evidence_is_blocked(record, key, value):
    record["datasets"][0][key] = value
    assert RunManifest.from_dict(record).readiness() == "blocked"


@pytest.mark.parametrize(
    "section,key,value",
    [
        (None, "schema_version", 2),
        (None, "schema_version", True),
        (None, "created_at", "2026-11-16"),
        (None, "probe_set", "probe"),
        (None, "outputs", []),
        (None, "datasets", []),
        (None, "surprise", True),
        ("catalog_ref", "generated_at", "2026-11-30T12:00:00Z"),
        ("catalog_ref", "content_sha256", "not-a-hash"),
        ("datasets", "state", "unknown"),
        ("datasets", "dataset_version", ""),
        ("datasets", "retrieved_at", "2026-02-30T12:00:00Z"),
        ("datasets", "retrieved_at", "2026-11-15T12:00:00"),
        ("datasets", "data_as_of", "2026-11-17"),
        ("datasets", "content_sha256", "B" * 64),
        ("datasets", "source_url", "file:relative"),
        ("datasets", "derivation_path", "not-a-sequence"),
        ("datasets", "surprise", True),
        ("outputs", "surprise", True),
        ("outputs", "path", "../escape"),
        ("outputs", "path", "C:\\escape"),
        ("outputs", "path", "/absolute"),
        ("outputs", "path", "a/./b"),
    ],
)
def test_invalid_records(record, section, key, value):
    target = record if section is None else record[section]
    if isinstance(target, list):
        target = target[0]
    target[key] = value
    with pytest.raises(ValueError):
        RunManifest.from_dict(record)


def test_duplicate_datasets_and_lineage(record):
    record["datasets"] *= 2
    with pytest.raises(ValueError):
        RunManifest.from_dict(record)
    record["datasets"] = record["datasets"][:1]
    record["rerun_of_attempt_id"] = "attempt-1"
    with pytest.raises(ValueError):
        RunManifest.from_dict(record)
    record["rerun_of_attempt_id"] = "attempt-0"
    record["supersedes_run_id"] = "earlier-run"
    assert RunManifest.from_dict(record).to_dict() == record


@pytest.mark.parametrize(
    "section,key", [("catalog_ref", "content_sha256"), ("outputs", "content_sha256")]
)
def test_other_missing_evidence(record, section, key):
    target = record[section][0] if section == "outputs" else record[section]
    target[key] = None
    target["unavailable_reason"] = "Evidence pending."
    assert RunManifest.from_dict(record).readiness() == "blocked"


def test_yaml_duplicate_keys(record):
    text = RunManifest.from_dict(record).to_yaml() + "schema_version: 1\n"
    with pytest.raises(ValueError):
        RunManifest.from_yaml(text)


def test_derivation_requires_opaque_references(record):
    record["datasets"][0]["derivation_path"] = ["relative/private-reference"]
    with pytest.raises(ValueError):
        RunManifest.from_dict(record)


def test_yaml_rejects_object_construction():
    with pytest.raises(yaml.constructor.ConstructorError):
        RunManifest.from_yaml("!!python/object:builtins.object {}")
