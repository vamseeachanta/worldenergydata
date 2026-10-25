"""Audit expectations follow issue #1262 and the checked-in source sidecar.

No engineering values are exercised. The worked-example count is independent:
the issue lists eight filenames; each sidecar record lacks an edition and a
publication locator, so eight records need a decision and zero are verified.
Synthetic complete citations below test metadata transitions, not a publication.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data/modules/metocean"
SCRIPT = ROOT / "scripts/maintenance/audit_metocean_table_sources.py"


@pytest.fixture
def audit():
    spec = importlib.util.spec_from_file_location("table_source_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def inputs(tmp_path):
    for name in ("table_sources.json", "_metadata.json", "schema.yaml"):
        (tmp_path / name).write_bytes((DATA / name).read_bytes())
    return tmp_path


def update_json(inputs, name, mutate):
    path = inputs / name
    content = json.loads(path.read_text(encoding="utf-8"))
    mutate(content)
    path.write_text(json.dumps(content), encoding="utf-8", newline="\n")


def test_current_worked_example(audit):
    report = audit.audit_sources(DATA)
    assert report["table_count"] == 8  # Issue #1262 filename inventory.
    assert report["verified_citation_count"] == 0
    assert len(report["maintainer_decisions"]) == 8
    assert report["status"] == "NOT_EVALUATED"
    assert [row["name"] for row in report["maintainer_decisions"]] == sorted(
        json.loads((DATA / "table_sources.json").read_text(encoding="utf-8"))["tables"]
    )
    for row in report["maintainer_decisions"]:
        assert row["missing_fields"] == ["edition", "table_or_clause"]
        assert row["verification_status"] == "NOT_EVALUATED"
        assert row["required_evidence"]
        assert row["evidence"]


@pytest.mark.parametrize("catalogue", ["_metadata.json", "schema.yaml"])
@pytest.mark.parametrize("defect", ["missing", "duplicate", "wrong_pointer"])
def test_catalogue_drift_fails(audit, inputs, catalogue, defect):
    path = inputs / catalogue
    content = yaml.safe_load(path.read_text(encoding="utf-8"))
    entries = content["datasets" if catalogue.endswith("yaml") else "external_datasets"]
    if defect == "missing":
        entries.pop()
    elif defect == "duplicate":
        entries.append(entries[0].copy())
    else:
        entries[0]["source_record"] = "table_sources.json#/tables/unknown.csv"
    path.write_text(yaml.safe_dump(content), encoding="utf-8", newline="\n")
    # JSON remains JSON even though the schema fixture is serialized as YAML.
    if catalogue.endswith("json"):
        path.write_text(json.dumps(content), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="inventory|duplicate|source_record"):
        audit.audit_sources(inputs)


@pytest.mark.parametrize(
    "field,value",
    [
        ("edition", " "),
        ("table_or_clause", []),
        ("source_document", None),
        ("reason", ""),
        ("required_evidence", ""),
        ("evidence", []),
        ("evidence", [{}]),
        ("decision_status", "resolved"),
        ("verification_status", "VERIFIED"),
        ("verification_status", "unknown"),
    ],
)
def test_inconsistent_records_fail(audit, inputs, field, value):
    def mutate(content):
        next(iter(content["tables"].values()))[field] = value

    update_json(inputs, "table_sources.json", mutate)
    with pytest.raises(ValueError):
        audit.audit_sources(inputs)


@pytest.mark.parametrize("separator", ["/", "\\"], ids=["posix", "windows"])
@pytest.mark.parametrize(
    "form",
    ["rooted", "drive_relative", "drive_rooted", "network", "parent", "nested_parent"],
)
def test_non_repository_evidence_paths_fail(audit, inputs, separator, form):
    path = separator.join(("docs", "evidence.md"))
    if form == "rooted":
        path = separator + path
    elif form == "drive_relative":
        path = "Z:" + path
    elif form == "drive_rooted":
        path = "Z:" + separator + path
    elif form == "network":
        path = separator * 2 + separator.join(("synthetic", "share", path))
    elif form == "parent":
        path = ".." + separator + path
    else:
        path = separator.join(("docs", "..", "..", "evidence.md"))

    def mutate(content):
        for record in content["tables"].values():
            record["evidence"].append({**record["evidence"][0], "path": path})

    update_json(inputs, "table_sources.json", mutate)
    with pytest.raises(ValueError, match="repository-relative path"):
        audit.audit_sources(inputs)


@pytest.mark.parametrize(
    "path",
    ["docs\\evidence.md", "docs//evidence.md", "./evidence.md", "docs/./evidence.md"],
)
def test_noncanonical_evidence_paths_fail(audit, inputs, path):
    def mutate(content):
        next(iter(content["tables"].values()))["evidence"][0]["path"] = path

    update_json(inputs, "table_sources.json", mutate)
    with pytest.raises(ValueError, match="repository-relative path"):
        audit.audit_sources(inputs)


@pytest.mark.parametrize(
    "path", ["evidence.md", "docs/evidence.md", "docs/évidence.md"]
)
def test_forward_slash_relative_evidence_paths_pass(audit, inputs, path):
    def mutate(content):
        for record in content["tables"].values():
            record["evidence"][0]["path"] = path

    update_json(inputs, "table_sources.json", mutate)
    report = audit.audit_sources(inputs)
    assert all(
        row["evidence"][0]["path"] == path for row in report["maintainer_decisions"]
    )


def test_complete_metadata_does_not_override_pending_verification(audit, inputs):
    def mutate(content):
        for record in content["tables"].values():
            record["edition"] = "synthetic edition"
            record["table_or_clause"] = "synthetic table"

    update_json(inputs, "table_sources.json", mutate)
    report = audit.audit_sources(inputs)
    assert report["verified_citation_count"] == 0
    assert all(not row["missing_fields"] for row in report["maintainer_decisions"])


def test_explicit_complete_verification_clears_the_queue(audit, inputs):
    def mutate(content):
        for record in content["tables"].values():
            record.update(
                source_document="Synthetic metadata fixture, not a standard",
                edition="synthetic edition",
                table_or_clause="synthetic table",
                attribution_status="publication_citation",
                verification_status="VERIFIED",
                decision_status="resolved",
            )
            record["evidence"][0]["scope"] = "Synthetic confirmation fixture only"

    update_json(inputs, "table_sources.json", mutate)
    report = audit.audit_sources(inputs)
    assert report["verified_citation_count"] == report["table_count"]
    assert report["maintainer_decisions"] == []
    assert report["status"] == "CITATIONS_RECORDED"


def test_record_cannot_override_computed_report_fields(audit, inputs):
    def mutate(content):
        for record in content["tables"].values():
            record.update(name="synthetic_override.csv", missing_fields=[])

    update_json(inputs, "table_sources.json", mutate)
    report = audit.audit_sources(inputs)
    assert all(
        row["name"] != "synthetic_override.csv"
        for row in report["maintainer_decisions"]
    )
    assert all(
        row["missing_fields"] == ["edition", "table_or_clause"]
        for row in report["maintainer_decisions"]
    )


@pytest.mark.parametrize(
    "name", ["table_sources.json", "_metadata.json", "schema.yaml"]
)
def test_duplicate_mapping_keys_are_not_silently_overwritten(audit, inputs, name):
    path = inputs / name
    content = path.read_text(encoding="utf-8")
    if name.endswith("json"):
        content = (
            '{"tables": {},' + content[1:]
            if name == "table_sources.json"
            else '{"external_datasets": [],' + content[1:]
        )
    else:
        content = "datasets: []\n" + content
    path.write_text(content, encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="duplicate"):
        audit.audit_sources(inputs)


@pytest.mark.parametrize("strict,expected", [(False, 0), (True, 1)])
def test_cli_reports_unresolved_citations(inputs, strict, expected):
    command = [sys.executable, str(SCRIPT), "--data-dir", str(inputs)]
    if strict:
        command.append("--require-citations")
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", check=False
    )
    assert result.returncode == expected
    assert json.loads(result.stdout)["status"] == "NOT_EVALUATED"
    assert result.stderr == ""


def test_cli_invalid_input_has_no_payload_or_path_disclosure(inputs):
    (inputs / "table_sources.json").write_text(
        "SYNTHETIC_INVALID_JSON", encoding="utf-8", newline="\n"
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--data-dir", str(inputs)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "INVALID"
    assert "SYNTHETIC_INVALID_JSON" not in result.stdout + result.stderr
    assert str(inputs) not in result.stdout + result.stderr


def test_yaml_object_tags_are_refused(audit, inputs):
    """A duplicate-aware loader must retain SafeLoader's tag restrictions."""
    (inputs / "schema.yaml").write_text(
        "!!python/tuple [SYNTHETIC_TAG]\n", encoding="utf-8", newline="\n"
    )
    with pytest.raises(yaml.constructor.ConstructorError):
        audit.audit_sources(inputs)


def test_documented_example_matches_report(audit):
    report = audit.audit_sources(DATA)
    readme = (DATA / "README.md").read_text(encoding="utf-8")
    assert "audit_metocean_table_sources.py" in readme
    for field in ("table_count", "verified_citation_count"):
        assert f'"{field}": {report[field]}' in readme
    assert "--require-citations" in readme
