"""Tests for Texas RRC pressure-observation source discovery."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from worldenergydata.texas_rrc.pressure_observations.sources import (
    load_pressure_observation_inputs,
)


def _packet_line(values: dict[int, str], length: int = 61) -> str:
    columns = [""] * length
    columns[0] = "PACKET"
    for index, value in values.items():
        columns[index] = value
    return "{".join(columns)


def _record_line(record_type: str, values: dict[int, str], length: int = 90) -> str:
    columns = [""] * length
    columns[0] = record_type
    for index, value in values.items():
        columns[index] = value
    return "{".join(columns)


def _write_zip(path: Path, member_name: str, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(member_name, content)


def test_load_pressure_observation_inputs_parses_completion_zip_and_wellbore(
    tmp_path: Path,
) -> None:
    completion_zip = tmp_path / "raw" / "completions" / "06-29-2026.zip"
    _write_zip(
        completion_zip,
        "completion.dat",
        "\n".join(
            [
                _packet_line(
                    {
                        1: "123456",
                        2: "654321",
                        5: "456789",
                        6: "00100001",
                        8: "98765",
                        25: "12345678",
                        27: "08",
                        29: "SPRABERRY",
                    }
                ),
                _record_line(
                    "G-1",
                    {
                        1: "123456",
                        2: "654321",
                        3: "999",
                        4: "03/01/2024",
                        13: "10000",
                        59: "2500",
                    },
                ),
            ]
        ),
    )
    wellbore = tmp_path / "raw" / "wellbore" / "query" / "wellbore.csv"
    wellbore.parent.mkdir(parents=True)
    wellbore.write_text(
        "API_NO,TOTAL_DEPTH\n4200100001,10000\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifests" / "completion_data-20260701T003655Z.json"
    manifest.parent.mkdir()
    manifest.write_text(
        json.dumps(
            {
                "source_id": "completion_data",
                "status": "error",
                "retrieved_at": "2026-07-01T00:36:55Z",
                "raw_path": str(completion_zip.parent),
            }
        ),
        encoding="utf-8",
    )

    inputs = load_pressure_observation_inputs(tmp_path)

    assert inputs.source_gaps == ()
    assert inputs.candidates.iloc[0]["api14"] == "42001000010000"
    assert inputs.wellbore.iloc[0].to_dict() == {
        "api14": "42001000010000",
        "api10": "4200100001",
        "total_depth": "10000",
    }
    assert inputs.parser_quality == {
        "candidate_count": 1,
        "malformed_row_count": 0,
        "unlinked_row_count": 0,
    }
    assert str(completion_zip) in inputs.input_paths
    assert str(wellbore) in inputs.input_paths
    artifacts_by_path = {
        str(artifact["path"]): artifact for artifact in inputs.input_artifacts
    }
    assert set(artifacts_by_path) == {str(completion_zip), str(wellbore)}
    assert artifacts_by_path[str(completion_zip)]["byte_size"] > 0
    assert len(artifacts_by_path[str(completion_zip)]["sha256"]) == 64
    assert artifacts_by_path[str(wellbore)]["byte_size"] > 0
    assert len(artifacts_by_path[str(wellbore)]["sha256"]) == 64
    assert inputs.source_warnings == (
        "raw_manifest_warning:completion_data:error:" "2026-07-01T00:36:55Z",
    )


def test_load_pressure_observation_inputs_reports_missing_sources(
    tmp_path: Path,
) -> None:
    inputs = load_pressure_observation_inputs(tmp_path)

    assert inputs.candidates.empty
    assert inputs.wellbore.empty
    assert inputs.source_gaps == ("completion_data", "wellbore_query")
