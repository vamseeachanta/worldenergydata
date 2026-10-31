"""Source manifest integrity: every shipped row traces to a reviewed public file."""

import json

import pytest

from worldenergydata.india_dgh import load_awarded_blocks, load_source_manifest
from worldenergydata.india_dgh.sources import data_path, verify_file

PUBLIC_HOSTS = ("https://www.dghindia.gov.in/", "https://dghindia.gov.in/", "https://ppac.gov.in/",
                "https://www.ppac.gov.in/", "https://web.archive.org/")


def test_manifest_entries_are_public_and_pinned():
    manifest = load_source_manifest()
    for entry in manifest["files"]:
        assert entry["url"].startswith(PUBLIC_HOSTS), entry["id"]
        assert "ndrdgh" not in entry["url"]  # NDR needs registration; never used
        assert len(entry["sha256"]) == 64 and entry["terms_url"].startswith("https://")


def test_every_block_row_cites_a_manifest_file():
    ids = {e["id"] for e in load_source_manifest()["files"]}
    assert set(load_awarded_blocks().source_id) <= ids


def test_manifest_rejects_entry_without_digest(tmp_path, monkeypatch):
    bad = {"files": [{"id": "x", "publisher": "p", "title": "t", "url": "https://ppac.gov.in/x",
                      "filename": "x", "sha256": "", "retrieved": "2026-10-31", "terms_url": "https://x"}]}
    target = tmp_path / "source_manifest.json"
    target.write_text(json.dumps(bad), encoding="utf-8")
    monkeypatch.setattr("worldenergydata.india_dgh.sources.data_path", lambda name: tmp_path / name)
    with pytest.raises(ValueError, match="SHA-256"):
        load_source_manifest()


def test_verify_file_detects_changed_bytes(tmp_path):
    entry = load_source_manifest()["files"][0]
    changed = tmp_path / entry["filename"]
    changed.write_bytes(b"replaced by publisher")
    with pytest.raises(ValueError, match="does not match"):
        verify_file(changed, entry["id"])


def test_shipped_tables_exist():
    for name in ("awarded_blocks.csv", "basins.csv", "production.csv"):
        assert data_path(name).is_file(), name
