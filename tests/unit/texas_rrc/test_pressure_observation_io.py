"""Tests for Texas RRC pressure-observation output persistence."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd
import pytest

from worldenergydata.texas_rrc.pressure_observations.io import (
    load_pressure_observations,
    write_pressure_observation_outputs,
)


def test_write_pressure_observation_outputs_persists_tables_quality_and_manifest(
    tmp_path,
) -> None:
    observations = pd.DataFrame(
        [
            {
                "api14": "42001000010000",
                "api10": "4200100001",
                "pressure_kind": "BHP_measured",
                "pressure_psia": 2500.0,
            }
        ]
    )
    candidates = pd.DataFrame(
        [
            {
                "api14": "42001000010000",
                "api10": "4200100001",
                "source_record_type": "G-1",
                "source_pressure_field": "BOTTOM_HOLE_PRESS",
                "pressure_raw_psi": 2500.0,
            }
        ]
    )
    coverage_by_district_decade = pd.DataFrame(
        [
            {
                "district": "08",
                "test_decade": "2020s",
                "pressure_observation_well_count": 1,
                "pressure_observation_count": 1,
            }
        ]
    )
    coverage_by_field_decade = pd.DataFrame(
        [
            {
                "district": "08",
                "field_no": "12345678",
                "field_name": "SPRABERRY",
                "test_decade": "2020s",
                "pressure_observation_well_count": 1,
                "pressure_observation_count": 1,
            }
        ]
    )

    manifest = write_pressure_observation_outputs(
        observations,
        candidates,
        coverage_by_district_decade,
        coverage_by_field_decade,
        quality={"w2_pressure_candidates_not_curated": 0},
        output_root=tmp_path,
        generated_at=datetime(2026, 7, 3, 12, 0, tzinfo=timezone.utc),
        input_paths=["raw/completions/06-29-2026.zip"],
        input_artifacts=[
            {
                "path": "raw/completions/06-29-2026.zip",
                "byte_size": 123,
                "sha256": "a" * 64,
            }
        ],
        source_gaps=(),
        source_warnings=("raw_manifest_warning:completion_data:error:2026-07-01",),
        allow_non_ace_root=True,
        command="worldenergydata texas-rrc build-pressure-observations",
        code_revision="abc123",
    )

    assert manifest.row_count == 1
    assert manifest.candidate_count == 1
    assert manifest.observations_csv_path.exists()
    assert manifest.observations_parquet_path.exists()
    assert manifest.candidates_csv_path.exists()
    assert manifest.candidates_parquet_path.exists()
    assert manifest.coverage_by_district_decade_csv_path.exists()
    assert manifest.coverage_by_district_decade_parquet_path.exists()
    assert manifest.coverage_by_field_decade_csv_path.exists()
    assert manifest.coverage_by_field_decade_parquet_path.exists()
    assert manifest.quality_path.exists()
    assert manifest.manifest_path.exists()
    assert (
        load_pressure_observations(manifest.observations_csv_path).loc[0, "api14"]
        == "42001000010000"
    )

    quality_payload = json.loads(manifest.quality_path.read_text(encoding="utf-8"))
    assert quality_payload["row_count"] == 1
    assert quality_payload["candidate_count"] == 1
    assert quality_payload["source_warnings"] == [
        "raw_manifest_warning:completion_data:error:2026-07-01"
    ]
    assert quality_payload["w2_pressure_candidates_not_curated"] == 0

    manifest_payload = json.loads(manifest.manifest_path.read_text(encoding="utf-8"))
    assert manifest_payload["generated_at"] == "2026-07-03T12:00:00Z"
    assert manifest_payload["observations_csv_path"] == str(
        manifest.observations_csv_path
    )
    assert manifest_payload["candidates_csv_path"] == str(manifest.candidates_csv_path)
    assert manifest_payload["coverage_by_district_decade_csv_path"] == str(
        manifest.coverage_by_district_decade_csv_path
    )
    assert manifest_payload["coverage_by_field_decade_csv_path"] == str(
        manifest.coverage_by_field_decade_csv_path
    )
    assert manifest_payload["input_artifacts"][0]["sha256"] == "a" * 64
    assert manifest_payload["command"] == (
        "worldenergydata texas-rrc build-pressure-observations"
    )
    assert manifest_payload["code_revision"] == "abc123"
    assert not list(tmp_path.rglob(".staging-*"))


def test_write_pressure_observation_outputs_rejects_non_ace_root_without_override(
    tmp_path,
) -> None:
    with pytest.raises(ValueError, match="/mnt/ace"):
        write_pressure_observation_outputs(
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            quality={},
            output_root=tmp_path,
        )
