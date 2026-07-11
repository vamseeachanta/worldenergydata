import json
from scripts.audit.inventory_landman_data_roots import (
    REQUIRED_EVIDENCE,
    scan_inventory,
    write_inventory,
)


def test_schema_and_required_unavailable_rows(tmp_path):
    (tmp_path / "texas" / "data").mkdir(parents=True)
    (tmp_path / "texas" / "data" / "manifest.json").write_text(
        '{"source_url": "https://rrc.texas.gov/data"}', encoding="utf-8"
    )
    document = scan_inventory(tmp_path, observed_at="2026-07-10T00:00:00Z")
    assert set(document) == {
        "schema_version",
        "scan_policy",
        "observed_at",
        "coverage_warnings",
        "rows",
    }
    assert {row["evidence_key"] for row in document["rows"]} >= set(REQUIRED_EVIDENCE)
    assert all("artifact_sha256" in row for row in document["rows"])


def test_quarantine_prevents_child_reads(tmp_path):
    legacy = tmp_path / "legacy" / "data"
    legacy.mkdir(parents=True)
    (legacy / "secret.txt").write_text("client identifier", encoding="utf-8")
    document = scan_inventory(tmp_path, observed_at="2026-07-10T00:00:00Z")
    row = next(
        row for row in document["rows"] if row["root_path"].endswith("legacy/data")
    )
    assert row["quarantined"] is True
    assert row["status"] == "private/legacy"
    assert "client identifier" not in json.dumps(document)


def test_bounded_scan_and_deterministic_report(tmp_path):
    for index in range(5):
        (tmp_path / f"root{index}" / "data").mkdir(parents=True)
    first = scan_inventory(tmp_path, max_entries=2, observed_at="2026-07-10T00:00:00Z")
    second = scan_inventory(tmp_path, max_entries=2, observed_at="2026-07-10T00:00:00Z")
    assert len(first["rows"]) == len(second["rows"])
    assert first == second
    assert any("entry limit" in warning for warning in first["coverage_warnings"])


def test_write_outputs_only_reports(tmp_path):
    output = tmp_path / "out"
    document = scan_inventory(tmp_path / "roots", observed_at="2026-07-10T00:00:00Z")
    json_path, markdown_path = write_inventory(document, output)
    assert json_path.name.endswith(".json")
    assert markdown_path.name.endswith(".md")
    assert sorted(path.suffix for path in output.iterdir()) == [".json", ".md"]


def test_unlisted_root_has_nonempty_evidence_key(tmp_path):
    (tmp_path / "unlisted_source" / "data").mkdir(parents=True)
    document = scan_inventory(tmp_path, observed_at="2026-07-10T00:00:00Z")
    row = next(
        row
        for row in document["rows"]
        if row["root_path"].endswith("unlisted_source/data")
    )
    assert row["evidence_key"] == "unlisted_source"
