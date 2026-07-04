"""Tests for capped Colorado ECMC source discovery scout (#749)."""

import hashlib
import json
from pathlib import Path

import yaml

from worldenergydata.modules.state_regulators.colorado_ecmc.source_discovery import (
    build_facility_detail_url,
    fetch_facility_detail,
    load_source_discovery_config,
    run_source_discovery,
    write_source_discovery_manifest,
)


FIXTURE = (
    Path(__file__).parents[3]
    / "fixtures"
    / "colorado_ecmc"
    / "facility_detail_12339345_excerpt.html"
)


def test_source_discovery_config_is_capped_and_direct_source():
    config = load_source_discovery_config("config/colorado_ecmc_source_discovery.yml")

    scout = config["facility_detail"]

    assert config["storage"]["base_dir"] == (
        "/mnt/ace/worldenergydata/data/modules/colorado_ecmc/source_discovery"
    )
    assert scout["base_url"] == (
        "https://ecmc.state.co.us/cogisdb/Facility/FacilityDetail.aspx"
    )
    assert scout["sample_apis"] == ["12339345"]
    assert scout["max_requests"] == 1
    assert scout["request_delay_seconds"] >= 1
    assert scout["max_requests"] <= len(scout["sample_apis"])


def test_build_facility_detail_url_normalizes_api_fragment():
    expected = (
        "https://ecmc.state.co.us/cogisdb/Facility/FacilityDetail.aspx?api=12339345"
    )

    assert build_facility_detail_url("12339345") == expected
    assert build_facility_detail_url("05-123-39345") == expected
    assert build_facility_detail_url("0512339345") == expected
    assert build_facility_detail_url("051233934500") == expected


def test_fetch_facility_detail_writes_html_and_metadata(tmp_path, monkeypatch):
    payload = b"<html>facility detail</html>"

    class FakeResponse:
        headers = {"Last-Modified": "Fri, 03 Jul 2026 12:05:27 GMT", "ETag": "abc"}

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

        def getcode(self):
            return 200

    def fake_urlopen(url, timeout):
        assert url.endswith("?api=12339345")
        assert timeout == 60
        return FakeResponse()

    monkeypatch.setattr(
        "worldenergydata.modules.state_regulators.colorado_ecmc."
        "source_discovery.urlopen",
        fake_urlopen,
    )
    destination = tmp_path / "raw" / "facility_detail" / "12339345.html"

    metadata = fetch_facility_detail(
        "https://ecmc.state.co.us/cogisdb/Facility/FacilityDetail.aspx?api=12339345",
        destination,
    )

    assert destination.read_bytes() == payload
    assert metadata["source_url"].endswith("?api=12339345")
    assert metadata["raw_path"] == str(destination)
    assert metadata["status_code"] == 200
    assert metadata["size_bytes"] == len(payload)
    assert metadata["sha256"] == hashlib.sha256(payload).hexdigest()
    assert metadata["last_modified"] == "Fri, 03 Jul 2026 12:05:27 GMT"
    assert metadata["etag"] == "abc"
    assert metadata["downloaded_at"]


def test_write_source_discovery_manifest_records_parser_counts(tmp_path):
    base_dir = tmp_path / "source_discovery"
    downloads = [
        {
            "api_fragment": "12339345",
            "source_url": (
                "https://ecmc.state.co.us/cogisdb/Facility/"
                "FacilityDetail.aspx?api=12339345"
            ),
            "raw_path": str(base_dir / "raw" / "facility_detail" / "12339345.html"),
            "status_code": 200,
            "size_bytes": 17,
            "sha256": "abc123",
            "last_modified": "Fri, 03 Jul 2026 12:05:27 GMT",
            "etag": "etag-1",
            "downloaded_at": "2026-07-04T08:00:00+00:00",
            "parsed_row_count": 7,
            "candidate_pressure_count": 2,
        }
    ]

    manifest = write_source_discovery_manifest(base_dir, downloads)

    assert manifest["source"] == "colorado_ecmc_facility_detail"
    assert manifest["request_count"] == 1
    assert manifest["parsed_row_count"] == 7
    assert manifest["candidate_pressure_count"] == 2
    assert manifest["downloads"][0]["api_fragment"] == "12339345"
    written = json.loads(
        (base_dir / "raw" / "facility_detail" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert written == manifest


def test_run_source_discovery_writes_raw_parsed_and_report_outputs(
    tmp_path, monkeypatch
):
    config_path = tmp_path / "colorado_ecmc_source_discovery.yml"
    base_dir = tmp_path / "source_discovery"
    config_path.write_text(
        yaml.safe_dump(
            {
                "storage": {"base_dir": str(base_dir)},
                "facility_detail": {
                    "base_url": (
                        "https://ecmc.state.co.us/cogisdb/Facility/"
                        "FacilityDetail.aspx"
                    ),
                    "sample_apis": ["12339345"],
                    "max_requests": 1,
                    "request_delay_seconds": 1,
                    "timeout_seconds": 60,
                },
            }
        ),
        encoding="utf-8",
    )

    def fake_fetch(url, destination, timeout=60):
        destination.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        return {
            "api_fragment": "12339345",
            "source_url": url,
            "raw_path": str(destination),
            "status_code": 200,
            "size_bytes": destination.stat().st_size,
            "sha256": "sha",
            "last_modified": "Fri, 03 Jul 2026 12:05:27 GMT",
            "etag": "etag",
            "downloaded_at": "2026-07-04T08:00:00+00:00",
        }

    monkeypatch.setattr(
        "worldenergydata.modules.state_regulators.colorado_ecmc."
        "source_discovery.fetch_facility_detail",
        fake_fetch,
    )
    monkeypatch.setattr(
        "worldenergydata.modules.state_regulators.colorado_ecmc."
        "source_discovery.sleep",
        lambda _: None,
    )

    result = run_source_discovery(config_path)

    parsed_json = (
        base_dir / "parsed" / "facility_detail_initial_tests.json"
    )
    report_json = (
        base_dir / "reports" / "colorado_ecmc_pressure_source_discovery.json"
    )
    assert result["report"]["request_count"] == 1
    assert result["report"]["parsed_row_count"] == 7
    assert result["report"]["candidate_pressure_count"] == 2
    assert result["report"]["decision"] == "facility_detail_candidate_for_follow_up"
    assert parsed_json.exists()
    assert report_json.exists()
    parsed = json.loads(parsed_json.read_text(encoding="utf-8"))
    assert {row["test_type"] for row in parsed} >= {"CASING_PRESS", "TUBING_PRESS"}
