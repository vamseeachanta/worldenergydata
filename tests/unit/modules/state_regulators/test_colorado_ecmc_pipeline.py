"""Tests for Colorado ECMC source manifesting (#745)."""

import hashlib
import json

import yaml

from worldenergydata.modules.state_regulators.colorado_ecmc.pipeline import (
    configured_sources,
    download_source,
    load_config,
    write_manifest,
)


def test_configured_sources_reads_direct_ecmc_urls():
    config = load_config("config/colorado_ecmc.yml")

    sources = {source["name"]: source for source in configured_sources(config)}

    assert set(sources) == {
        "production_2025",
        "production_monthly",
        "wells_shapefile",
    }
    assert sources["production_2025"]["url"].endswith("/2025_prod_reports.csv")
    assert sources["production_2025"]["raw_path"] == (
        "production/2025_prod_reports.csv"
    )
    assert sources["production_2025"]["source_type"] == "production_csv"
    assert sources["production_2025"]["refresh"] == "annual_static"
    assert "GasPressureTubing" in sources["production_2025"]["required_columns"]
    assert sources["production_monthly"]["url"].endswith("/monthly_prod.csv")
    assert sources["production_monthly"]["refresh"] == "monthly"
    assert sources["wells_shapefile"]["url"].endswith("/WELLS_SHP.ZIP")
    assert sources["wells_shapefile"]["source_type"] == "wells_shapefile"


def test_download_source_writes_bytes_and_response_metadata(tmp_path, monkeypatch):
    payload = b"colorado ecmc production"

    class FakeResponse:
        headers = {"Last-Modified": "Fri, 12 Jun 2026 17:04:34 GMT", "ETag": "abc"}

        def __init__(self):
            self._used = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, size=-1):
            if self._used:
                return b""
            self._used = True
            return payload

    def fake_urlopen(url, timeout):
        assert url == "https://example.test/monthly_prod.csv"
        assert timeout == 120
        return FakeResponse()

    monkeypatch.setattr(
        "worldenergydata.modules.state_regulators.colorado_ecmc.pipeline.urlopen",
        fake_urlopen,
    )
    destination = tmp_path / "raw" / "production" / "monthly_prod.csv"

    metadata = download_source("https://example.test/monthly_prod.csv", destination)

    assert destination.read_bytes() == payload
    assert metadata["url"] == "https://example.test/monthly_prod.csv"
    assert metadata["path"] == str(destination)
    assert metadata["size_bytes"] == len(payload)
    assert metadata["sha256"] == hashlib.sha256(payload).hexdigest()
    assert metadata["last_modified"] == "Fri, 12 Jun 2026 17:04:34 GMT"
    assert metadata["etag"] == "abc"


def test_write_manifest_records_hash_refresh_and_required_columns(tmp_path):
    base_dir = tmp_path / "colorado_ecmc"
    raw_dir = base_dir / "raw"
    production = raw_dir / "production" / "2025_prod_reports.csv"
    wells = raw_dir / "wells" / "WELLS_SHP.ZIP"
    production.parent.mkdir(parents=True)
    wells.parent.mkdir(parents=True)
    production.write_bytes(b"production")
    wells.write_bytes(b"wells")
    config = {
        "storage": {"raw_dir": "raw"},
        "sources": {
            "production_2025": {
                "url": "https://example.test/2025_prod_reports.csv",
                "raw_path": "production/2025_prod_reports.csv",
                "source_type": "production_csv",
                "refresh": "annual_static",
                "required_columns": ["GasPressureTubing"],
            },
            "wells_shapefile": {
                "url": "https://example.test/WELLS_SHP.ZIP",
                "raw_path": "wells/WELLS_SHP.ZIP",
                "source_type": "wells_shapefile",
                "refresh": "daily",
                "required_columns": ["API", "Field_Name"],
            },
        },
    }

    manifest = write_manifest(config, base_dir, downloads=[])

    assert set(manifest) == {"production_2025", "wells_shapefile"}
    assert manifest["production_2025"]["source_url"].endswith("2025_prod_reports.csv")
    assert manifest["production_2025"]["source_type"] == "production_csv"
    assert manifest["production_2025"]["refresh"] == "annual_static"
    assert manifest["production_2025"]["required_columns"] == ["GasPressureTubing"]
    assert manifest["production_2025"]["size_bytes"] == len(b"production")
    assert (
        manifest["production_2025"]["sha256"]
        == hashlib.sha256(b"production").hexdigest()
    )
    written = json.loads((raw_dir / "manifest.json").read_text(encoding="utf-8"))
    assert written == manifest


def test_load_config_reads_yaml(tmp_path):
    config_path = tmp_path / "colorado_ecmc.yml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "storage": {"base_dir": str(tmp_path), "raw_dir": "raw"},
                "sources": {
                    "production_2025": {
                        "url": "https://example.test/2025_prod_reports.csv",
                        "raw_path": "production/2025_prod_reports.csv",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config["sources"]["production_2025"]["raw_path"] == (
        "production/2025_prod_reports.csv"
    )
