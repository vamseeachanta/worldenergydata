"""Tests for Oklahoma OCC source manifesting (#740)."""

import hashlib
import json
from pathlib import Path

import yaml

from worldenergydata.modules.state_regulators.oklahoma_occ.pipeline import (
    download_source,
    load_config,
    write_manifest,
)


def test_load_config_reads_yaml(tmp_path):
    config_path = tmp_path / "oklahoma_occ.yml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "storage": {
                    "base_dir": str(tmp_path / "oklahoma_occ"),
                    "raw_dir": "raw",
                },
                "sources": {
                    "completion_dictionary": {
                        "url": "https://example.test/dictionary.xlsx",
                        "raw_path": "dictionary.xlsx",
                        "refresh": "occasional",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config["storage"]["raw_dir"] == "raw"
    assert config["sources"]["completion_dictionary"]["raw_path"] == "dictionary.xlsx"


def test_download_source_writes_bytes_and_response_metadata(tmp_path, monkeypatch):
    payload = b"oklahoma completion dictionary"

    class FakeResponse:
        headers = {"Last-Modified": "Tue, 26 Aug 2025 15:33:40 GMT", "ETag": "abc"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, size=-1):
            if self._used:
                return b""
            self._used = True
            return payload

        def __init__(self):
            self._used = False

    def fake_urlopen(url, timeout):
        assert url == "https://example.test/dictionary.xlsx"
        assert timeout == 120
        return FakeResponse()

    monkeypatch.setattr(
        "worldenergydata.modules.state_regulators.oklahoma_occ.pipeline.urlopen",
        fake_urlopen,
    )
    destination = tmp_path / "raw" / "dictionary.xlsx"

    metadata = download_source("https://example.test/dictionary.xlsx", destination)

    assert destination.read_bytes() == payload
    assert metadata["url"] == "https://example.test/dictionary.xlsx"
    assert metadata["path"] == str(destination)
    assert metadata["size_bytes"] == len(payload)
    assert metadata["sha256"] == hashlib.sha256(payload).hexdigest()
    assert metadata["last_modified"] == "Tue, 26 Aug 2025 15:33:40 GMT"
    assert metadata["etag"] == "abc"


def test_write_manifest_records_source_hashes_and_refresh(tmp_path):
    base_dir = tmp_path / "oklahoma_occ"
    raw_dir = base_dir / "raw"
    raw_dir.mkdir(parents=True)
    workbook = raw_dir / "completions.xlsx"
    dictionary = raw_dir / "dictionary.xlsx"
    workbook.write_bytes(b"workbook")
    dictionary.write_bytes(b"dictionary")
    config = {
        "storage": {"raw_dir": "raw"},
        "sources": {
            "completion_workbook": {
                "url": "https://example.test/completions.xlsx",
                "raw_path": "completions.xlsx",
                "refresh": "daily",
            },
            "completion_dictionary": {
                "url": "https://example.test/dictionary.xlsx",
                "raw_path": "dictionary.xlsx",
                "refresh": "occasional",
            },
        },
    }

    manifest = write_manifest(config, base_dir, downloads=[])

    assert set(manifest) == {"completion_workbook", "completion_dictionary"}
    assert manifest["completion_workbook"]["source_url"] == (
        "https://example.test/completions.xlsx"
    )
    assert manifest["completion_workbook"]["size_bytes"] == len(b"workbook")
    assert manifest["completion_workbook"]["sha256"] == hashlib.sha256(
        b"workbook"
    ).hexdigest()
    assert manifest["completion_workbook"]["refresh"] == "daily"
    assert "manifest_written_at" in manifest["completion_workbook"]
    written = json.loads((raw_dir / "manifest.json").read_text(encoding="utf-8"))
    assert written == manifest
