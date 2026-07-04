"""Tests for Colorado ECMC FacilityDetail/Form 5A ingest runner (#751)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from worldenergydata.modules.state_regulators.colorado_ecmc import (
    facility_detail_pipeline,
)

FIXTURE = (
    Path(__file__).parents[3]
    / "fixtures"
    / "colorado_ecmc"
    / "facility_detail_12339345_excerpt.html"
)
SOURCE_URL = (
    "https://ecmc.state.co.us/cogisdb/Facility/FacilityDetail.aspx?api=12339345"
)


def test_facility_detail_ingest_config_is_capped_and_direct_source():
    config = facility_detail_pipeline.load_config(
        "config/colorado_ecmc_facility_detail_ingest.yml"
    )

    assert config["storage"]["base_dir"].startswith("/mnt/ace/")
    assert config["source_list"]["path"].endswith("raw/wells/WELLS_SHP.ZIP")
    assert config["source_list"]["refresh"] == "daily"
    assert config["facility_detail"]["base_url"].endswith(
        "/cogisdb/Facility/FacilityDetail.aspx"
    )
    assert config["facility_detail"]["request_delay_seconds"] >= 0.25
    assert config["facility_detail"]["stop_on_identity_mismatch"] is True
    assert config["max_requests"] <= 10
    assert config["allow_full_source_list"] is False
    assert config["pressure_observations"]["atmospheric_psi"] == 14.7


def test_parse_facility_detail_pages_preserves_raw_lineage(tmp_path):
    raw_path = tmp_path / "12339345.html"
    raw_path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    fetch_manifest = {
        "fetched": [
            {
                "api_fragment": "12339345",
                "raw_path": str(raw_path),
                "source_url": SOURCE_URL,
                "sha256": "fixture-sha",
            }
        ],
        "failed": [],
        "skipped": [],
    }

    parsed, quality = facility_detail_pipeline.parse_facility_detail_pages(
        fetch_manifest
    )

    assert len(parsed) == 7
    assert parsed["raw_path"].nunique() == 1
    assert parsed["sha256"].unique().tolist() == ["fixture-sha"]
    assert quality["fetched_pages"] == 1
    assert quality["parsed_pages"] == 1
    assert quality["parsed_initial_test_rows"] == 7


def test_run_facility_detail_ingest_writes_source_parsed_curated_report(
    tmp_path, monkeypatch
):
    raw_path = tmp_path / "12339345.html"
    raw_path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    config_path = _write_runner_config(tmp_path)
    wells = pd.DataFrame(
        [
            {
                "API": "12339345",
                "API_County": "123",
                "API_Seq": "39345",
                "API_Label": "05-123-39345",
                "Facil_Id": "436953",
                "Field_Name": "WATTENBERG",
                "Max_MD": 14829,
                "Max_TVD": 7041,
            }
        ]
    )

    monkeypatch.setattr(
        facility_detail_pipeline, "read_raw_wells_source", lambda _: wells
    )
    monkeypatch.setattr(
        facility_detail_pipeline,
        "fetch_facility_detail_pages",
        lambda source_list, config: {
            "fetched": [
                {
                    "api_fragment": "12339345",
                    "raw_path": str(raw_path),
                    "source_url": SOURCE_URL,
                    "sha256": "fixture-sha",
                }
            ],
            "failed": [],
            "skipped": [],
        },
    )

    summary = facility_detail_pipeline.run_facility_detail_ingest(config_path)

    base_dir = tmp_path / "facility_detail_ingest"
    candidates_path = (
        base_dir / "curated" / "pressure" / "well_pressure_observations.parquet"
    )
    report_path = base_dir / "reports" / "colorado_ecmc_form5a_ingest_summary.json"
    assert summary["promotion"]["status"] == "candidate_only"
    assert summary["candidate_quality"]["usable_candidate_rows"] == 2
    assert candidates_path.exists()
    assert (
        json.loads(report_path.read_text(encoding="utf-8"))["promotion"]["status"]
        == "candidate_only"
    )


def _write_runner_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "facility_detail.yml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "storage": {"base_dir": str(tmp_path / "facility_detail_ingest")},
                "source_list": {"path": str(tmp_path / "WELLS_SHP.ZIP")},
                "facility_detail": {
                    "base_url": "https://ecmc.state.co.us/cogisdb/Facility/FacilityDetail.aspx",
                    "timeout_seconds": 30,
                    "request_delay_seconds": 0,
                    "user_agent": "worldenergydata-test/1.0",
                    "stop_on_identity_mismatch": True,
                },
                "max_requests": 1,
                "allow_full_source_list": True,
                "pressure_observations": {"atmospheric_psi": 14.7},
            }
        ),
        encoding="utf-8",
    )
    return config_path
