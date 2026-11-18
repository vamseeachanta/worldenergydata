"""Offline exact-byte registry evidence for newly curated lease extracts."""

import hashlib
import json
import runpy
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[4]
REGISTRY = """fields:
- canonical_id: synthetic_alpha
  display_name: Synthetic café
  aliases: [Synthetic Alpha]
  play: Lower Tertiary
  bsee: {leases: [G00001]}
  surfaces: {lifecycle_poster: true}
- canonical_id: synthetic_hidden
  display_name: Synthetic Hidden
  play: Lower Tertiary
  bsee: {leases: [G00002]}
  surfaces: {lifecycle_poster: false}
- canonical_id: synthetic_other
  display_name: Synthetic Other
  play: Other
  bsee: {leases: [G00003]}
  surfaces: {lifecycle_poster: true}
"""


@pytest.fixture
def script():
    loaded = runpy.run_path(str(ROOT / "scripts/bsee/fetch_leases.py"))
    return loaded["main"].__globals__


@pytest.fixture
def prepared(tmp_path, script, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    (output / "source_manifest.json").write_text("{}\n", encoding="utf-8")
    registry = tmp_path / "private-input" / "registry.yml"
    registry.parent.mkdir()
    registry.write_bytes(REGISTRY.encode("utf-8"))
    tables = {
        "lease": [
            {
                "Lease Number": "G00001",
                "Area Code": "AB",
                "Block Number": "1",
                "Lease Status Code": "PROD",
                "Lease Effective Date": "2000-01-01",
                "Bid System Code": "A",
                "Lease Expiration Date": None,
                "Lease Expected Expiration Date": "2010-01-01",
                "Current Area": 1.0,
                "System Measure Flag": "A",
            }
        ],
        "owner": [],
        "operator": [],
        "company": [],
    }
    monkeypatch.setitem(script, "saved_tables", lambda *args: tables)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "fetch_leases.py",
            "--from-saved",
            "--raw-dir",
            str(tmp_path / "raw"),
            "--output-dir",
            str(output),
            "--registry",
            str(registry),
        ],
    )
    return registry, output, tables


@pytest.mark.parametrize("ending", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_cli_records_exact_snapshot_and_literal_rows(script, prepared, ending):
    registry, output, _ = prepared
    content = REGISTRY.replace("\n", ending).encode("utf-8")
    registry.write_bytes(content)
    script["main"]()
    manifest_text = (output / "extract_manifest.json").read_text()
    manifest = json.loads(manifest_text)
    assert manifest["registry_input"] == {
        "role": "registry",
        "status": "verified",
        "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content),
    }
    assert manifest["target_leases"] == manifest["registry_resolved"] == 1
    assert manifest["unresolved"] == manifest["source_missing"] == []
    assert json.loads((output / "registry.json").read_text()) == [
        {"lease_num": "G00001", "field_id": "synthetic_alpha", "reason": None}
    ]
    assert json.loads((output / "leases.json").read_text()) == [
        {
            "lease_num": "G00001",
            "area_block": "AB001",
            "status": "PROD",
            "effective_date": "2000-01-01",
            "approval_date": [],
            "operator": [],
            "gwi_pct": [],
            "royalty_system": "A",
        }
    ]
    assert str(registry) not in manifest_text
    assert "private-input" not in manifest_text
    for record in manifest["artifacts"]:
        content = (output / record["file"]).read_bytes()
        assert record["size_bytes"] == len(content)
        assert record["sha256"] == hashlib.sha256(content).hexdigest()


def test_cli_writes_manifest_with_windows_text_newlines(script, prepared, monkeypatch):
    _, output, _ = prepared
    open_path = Path.open

    def windows_text_open(path, mode="r", *args, **kwargs):
        if "w" in mode and "b" not in mode and kwargs.get("newline") is None:
            kwargs["newline"] = "\r\n"
        return open_path(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", windows_text_open)
    script["main"]()
    manifest = json.loads((output / "extract_manifest.json").read_text())
    panel = (output / "panel_values.html").read_bytes()
    assert b"\n" in panel
    assert b"\r" not in panel
    record = next(
        item for item in manifest["artifacts"] if item["file"] == "panel_values.html"
    )
    assert record["size_bytes"] == len(panel)
    assert record["sha256"] == hashlib.sha256(panel).hexdigest()


def test_panel_readback_rejects_changed_bytes(script, tmp_path, monkeypatch):
    read_bytes = Path.read_bytes

    def changed_panel_bytes(path):
        content = read_bytes(path)
        return content + b"changed" if path.name == "panel_values.html" else content

    monkeypatch.setattr(Path, "read_bytes", changed_panel_bytes)
    with pytest.raises(OSError, match="Panel HTML readback mismatch"):
        script["save_panel_html"](tmp_path, [])


def test_line_endings_change_evidence_without_changing_registry(script, tmp_path):
    path = tmp_path / "registry.yml"
    path.write_bytes(REGISTRY.encode("utf-8"))
    lf_registry, lf = script["load_registry_snapshot"](path)
    path.write_bytes(REGISTRY.replace("\n", "\r\n").encode("utf-8"))
    crlf_registry, crlf = script["load_registry_snapshot"](path)
    assert lf_registry == crlf_registry
    assert lf["sha256"] != crlf["sha256"]
    assert lf["size_bytes"] != crlf["size_bytes"]


def test_cli_uses_one_capture_despite_path_replacement(script, prepared, monkeypatch):
    registry, output, _ = prepared
    content = registry.read_bytes()
    parse = script["load_fields_text"]
    original_read = Path.read_bytes
    reads = []

    def read_once(path):
        if path == registry:
            reads.append(path)
        return original_read(path)

    def replace_then_parse(text):
        registry.write_bytes(b"fields: []\n")
        return parse(text)

    monkeypatch.setattr(Path, "read_bytes", read_once)
    monkeypatch.setitem(script, "load_fields_text", replace_then_parse)
    script["main"]()
    manifest = json.loads((output / "extract_manifest.json").read_text())
    assert reads == [registry]
    assert registry.read_text() == "fields: []\n"
    assert manifest["registry_input"]["sha256"] == hashlib.sha256(content).hexdigest()
    assert manifest["registry_input"]["size_bytes"] == len(content)
    assert manifest["target_leases"] == manifest["registry_resolved"] == 1
    assert json.loads((output / "registry.json").read_text()) == [
        {"lease_num": "G00001", "field_id": "synthetic_alpha", "reason": None}
    ]


@pytest.mark.parametrize(
    "content, error",
    [
        (b"fields: [\xff]\n", UnicodeDecodeError),
        (b"fields: [", yaml.YAMLError),
        (
            REGISTRY.replace("synthetic_hidden", "synthetic_alpha").encode("utf-8"),
            ValueError,
        ),
    ],
    ids=["invalid-utf8", "invalid-yaml", "collision"],
)
def test_cli_rejects_invalid_registry_without_extract(script, prepared, content, error):
    registry, output, _ = prepared
    registry.write_bytes(content)
    with pytest.raises(error):
        script["main"]()
    assert not (output / "extract_manifest.json").exists()
    assert not (output / "leases.json").exists()


def test_legacy_save_extract_marks_registry_evidence_unavailable(script, prepared):
    _, output, tables = prepared
    schema_path, _ = script["prepare_schema"](output)
    result = script["curate"](tables, ["G00001"])
    result["registry"] = []
    script["save_extract"](output, schema_path, tables, ["G00001"], result)
    manifest = json.loads((output / "extract_manifest.json").read_text())
    assert manifest["registry_input"] == {
        "role": "registry",
        "status": "unavailable",
        "reason": "Registry snapshot provenance was not supplied",
    }
