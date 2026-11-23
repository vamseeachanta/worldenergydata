"""Tests for Texas RRC infrastructure access quality and persistence."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone

import pandas as pd
import pytest


def _metrics() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "district": "08",
                "field_number": "00010001",
                "field_name": "SPRABERRY",
                "field_well_count_with_location": 2,
                "nearest_pipeline_distance_miles": 0.2,
                "infrastructure_access_class": "direct_access",
                "source_caveats": "rrc_gis_screening_only",
            },
            {
                "district": "09",
                "field_number": "00030001",
                "field_name": "NO GIS FIELD",
                "field_well_count_with_location": 0,
                "nearest_pipeline_distance_miles": pd.NA,
                "infrastructure_access_class": "isolated_or_unknown",
                "source_caveats": "missing_well_gis|missing_pipeline_gis",
            },
        ]
    )


def test_assess_infrastructure_quality_counts_classes_and_missing_geometry():
    from worldenergydata.texas_rrc.infrastructure.quality import (
        assess_infrastructure_access_quality,
    )

    quality = assess_infrastructure_access_quality(
        _metrics(),
        source_gaps=("pipeline_gis_layers",),
        malformed_source_files=("bad_pipeline.zip",),
    )

    assert quality.row_count == 2
    assert quality.source_gaps == ("pipeline_gis_layers",)
    assert quality.access_class_counts == {
        "direct_access": 1,
        "isolated_or_unknown": 1,
    }
    assert quality.missing_well_gis_count == 1
    assert quality.missing_pipeline_source_count == 1
    assert quality.malformed_source_file_count == 1
    assert quality.nearest_pipeline_distance_min_miles == 0.2
    assert quality.nearest_pipeline_distance_max_miles == 0.2


def test_write_infrastructure_access_outputs_rejects_non_ace_root_by_default(tmp_path):
    from worldenergydata.texas_rrc.infrastructure.io import (
        write_infrastructure_access_outputs,
    )
    from worldenergydata.texas_rrc.infrastructure.quality import (
        assess_infrastructure_access_quality,
    )

    with pytest.raises(ValueError, match="/mnt/ace"):
        write_infrastructure_access_outputs(
            _metrics(),
            assess_infrastructure_access_quality(_metrics()),
            output_root=tmp_path,
        )


def test_write_infrastructure_access_outputs_persists_quality_and_manifest(tmp_path):
    from worldenergydata.texas_rrc.infrastructure.io import (
        load_infrastructure_access_metrics,
        write_infrastructure_access_outputs,
    )
    from worldenergydata.texas_rrc.infrastructure.quality import (
        SCORING_THRESHOLDS_MILES,
        assess_infrastructure_access_quality,
    )

    quality = assess_infrastructure_access_quality(
        _metrics(),
        source_gaps=("well_gis_layers",),
        malformed_source_files=("bad_well.zip",),
    )
    input_paths = [
        tmp_path / "raw/gis/wells/manifest.json",
        tmp_path / "raw/gis/pipelines/manifest.json",
        tmp_path / "curated/field_development/metrics/manifest.json",
    ]

    manifest = write_infrastructure_access_outputs(
        _metrics(),
        quality,
        output_root=tmp_path,
        generated_at=datetime(2026, 7, 1, 4, 0, tzinfo=timezone.utc),
        input_paths=input_paths,
        allow_non_ace_root=True,
        command="worldenergydata texas-rrc build-infrastructure-access-metrics",
        code_revision="abc123",
    )

    assert manifest.csv_path.exists()
    assert manifest.parquet_path.exists()
    assert manifest.quality_path.exists()
    assert manifest.manifest_path.exists()

    reloaded = load_infrastructure_access_metrics(manifest.csv_path)
    assert reloaded.iloc[0]["field_number"] == "00010001"
    assert load_infrastructure_access_metrics(manifest.parquet_path).shape[0] == 2

    quality_payload = json.loads(manifest.quality_path.read_text(encoding="utf-8"))
    assert quality_payload["source_gaps"] == ["well_gis_layers"]
    assert quality_payload["malformed_source_file_count"] == 1

    manifest_payload = json.loads(manifest.manifest_path.read_text(encoding="utf-8"))
    assert manifest_payload["generated_at"] == "2026-07-01T04:00:00Z"
    assert manifest_payload["row_count"] == 2
    assert manifest_payload["input_paths"] == [str(path) for path in input_paths]
    assert manifest_payload["scoring_thresholds_miles"] == SCORING_THRESHOLDS_MILES
    assert manifest_payload["code_revision"] == "abc123"
    assert manifest_payload["quality"]["access_class_counts"]["direct_access"] == 1


def test_git_revision_returns_head_when_status_times_out(monkeypatch):
    import worldenergydata.texas_rrc.infrastructure.io as infrastructure_io

    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        if args == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(args, 0, stdout="abc123\n", stderr="")
        raise subprocess.TimeoutExpired(args, timeout=kwargs.get("timeout"))

    monkeypatch.setattr(infrastructure_io.subprocess, "run", fake_run)

    assert infrastructure_io._git_revision() == "abc123"
    assert calls[1][0] == ["git", "status", "--porcelain", "--untracked-files=no"]
    assert all(call[1]["timeout"] == 5 for call in calls)
