"""Tests for data freshness scorecard generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "audit"))

from data_freshness_scorecard import build_scorecard, main


def _write_project(root: Path, scheduler_status: str = "success") -> None:
    (root / "data" / "modules" / "bsee").mkdir(parents=True)
    (root / "data" / "modules" / "bsee" / "_metadata.json").write_text(
        json.dumps(
            {
                "last_refresh": "2026-06-01",
                "record_count": 12,
                "file_count": 2,
                "total_size_bytes": 100,
            }
        )
    )
    (root / "data" / "modules" / "bsee" / "manifest.json").write_text(
        json.dumps(
            {
                "last_success_ts": "2026-06-07T00:00:00+00:00",
                "refresh_interval_days": 7,
                "records_updated": 12,
                "status": scheduler_status,
            }
        )
    )
    (root / "module-manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "modules": [
                    {
                        "id": "bsee",
                        "catalog_status": "sample",
                        "in_scheduler": True,
                        "public_cli": True,
                    },
                    {
                        "id": "texas_rrc",
                        "catalog_status": "runtime_fetched",
                        "in_scheduler": False,
                        "public_cli": True,
                    },
                ]
            }
        )
    )
    (root / "data" / "catalog.yaml").write_text(
        yaml.safe_dump(
            {
                "modules": {
                    "bsee": {
                        "datasets": [
                            {"name": "a", "row_count": 5},
                            {"name": "b", "row_count": 7},
                        ]
                    }
                }
            }
        )
    )


def test_build_scorecard_combines_manifest_catalog_and_metadata(tmp_path: Path):
    _write_project(tmp_path)

    scorecard = build_scorecard(tmp_path, report_date="2026-06-08")

    bsee = scorecard["modules"]["bsee"]
    assert bsee["catalog_status"] == "sample"
    assert bsee["dataset_count"] == 2
    assert bsee["record_count"] == 12
    assert bsee["scheduler_last_success_ts"] == "2026-06-07T00:00:00+00:00"
    assert bsee["freshness_status"] == "fresh"

    texas = scorecard["modules"]["texas_rrc"]
    assert texas["dataset_count"] == 0
    assert texas["freshness_status"] == "missing"


def test_build_scorecard_rejects_non_success_scheduler_manifest(tmp_path: Path):
    _write_project(tmp_path, scheduler_status="failure")

    scorecard = build_scorecard(tmp_path, report_date="2026-06-08")

    assert scorecard["modules"]["bsee"]["freshness_status"] == "stale"


def test_main_writes_json_and_markdown_outputs(tmp_path: Path):
    _write_project(tmp_path)
    report_path = tmp_path / "docs" / "reports" / "scorecard.md"
    json_path = tmp_path / "data" / "freshness-scorecard.json"

    rc = main(
        [
            "--project-root",
            str(tmp_path),
            "--date",
            "2026-06-08",
            "--report-output",
            str(report_path),
            "--json-output",
            str(json_path),
        ]
    )

    assert rc == 0
    assert json_path.exists()
    assert report_path.exists()
    assert "| bsee | sample | fresh | 2 | 12 |" in report_path.read_text()
