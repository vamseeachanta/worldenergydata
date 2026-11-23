"""Tests for Texas RRC pressure-observation CLI support."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

from worldenergydata.cli.commands.texas_rrc import app
from worldenergydata.texas_rrc.pressure_observations.cli_support import (
    PressureObservationBuildResult,
    run_build_pressure_observations,
)
from worldenergydata.texas_rrc.pressure_observations.io import (
    PressureObservationOutputManifest,
)


def test_build_pressure_observations_cli_calls_support_layer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_run_build_pressure_observations(**kwargs):
        calls.append(kwargs)
        return _Result(
            row_count=1,
            candidate_count=3,
            source_gaps=(),
            source_warnings=("raw_manifest_warning:completion_data:error:2026-07-01",),
            dry_run=False,
            manifest=_manifest(tmp_path),
        )

    monkeypatch.setattr(
        "worldenergydata.texas_rrc.pressure_observations.cli_support."
        "run_build_pressure_observations",
        fake_run_build_pressure_observations,
    )

    result = CliRunner().invoke(
        app,
        [
            "build-pressure-observations",
            "--raw-root",
            str(tmp_path),
            "--output-root",
            str(tmp_path),
            "--allow-non-ace-output",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == [
        {
            "raw_root": tmp_path,
            "output_root": tmp_path,
            "dry_run": False,
            "require_sources": False,
            "allow_non_ace_output": True,
        }
    ]
    assert "Wrote pressure observations" in result.output
    assert "raw_manifest_warning:completion_data:error:2026-07-01" in result.output


def test_run_build_pressure_observations_dry_run_reports_missing_sources(
    tmp_path: Path,
) -> None:
    result = run_build_pressure_observations(
        raw_root=tmp_path,
        output_root=tmp_path,
        dry_run=True,
        require_sources=False,
        allow_non_ace_output=True,
    )

    assert isinstance(result, PressureObservationBuildResult)
    assert result.dry_run is True
    assert result.row_count == 0
    assert result.candidate_count == 0
    assert result.source_gaps == ("completion_data", "wellbore_query")
    assert result.manifest is None


def test_run_build_pressure_observations_writes_coverage_outputs(
    tmp_path: Path,
) -> None:
    _write_pressure_raw_fixture(tmp_path)

    result = run_build_pressure_observations(
        raw_root=tmp_path,
        output_root=tmp_path,
        allow_non_ace_output=True,
    )

    assert result.row_count == 1
    assert result.candidate_count == 1
    assert result.manifest is not None
    assert result.manifest.coverage_by_district_decade_csv_path.exists()
    assert result.manifest.coverage_by_field_decade_csv_path.exists()
    quality = json.loads(result.manifest.quality_path.read_text(encoding="utf-8"))
    assert quality["pressure_kind_counts"] == {"BHP_measured": 1}
    assert quality["pressure_unit_basis_counts"] == {"source_psi_unspecified": 1}


def test_run_build_pressure_observations_requires_sources(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="completion_data"):
        run_build_pressure_observations(
            raw_root=tmp_path,
            output_root=tmp_path,
            dry_run=True,
            require_sources=True,
            allow_non_ace_output=True,
        )


@dataclass(frozen=True)
class _Result:
    row_count: int
    candidate_count: int
    source_gaps: tuple[str, ...]
    source_warnings: tuple[str, ...]
    dry_run: bool
    manifest: PressureObservationOutputManifest | None


def _manifest(tmp_path: Path) -> PressureObservationOutputManifest:
    curated = tmp_path / "curated" / "pressure" / "well_pressure_observations"
    normalized = tmp_path / "normalized" / "pressure"
    return PressureObservationOutputManifest(
        generated_at="2026-07-03T12:00:00Z",
        output_root=tmp_path,
        observations_csv_path=curated / "texas_rrc_well_pressure_observations.csv",
        observations_parquet_path=curated
        / "texas_rrc_well_pressure_observations.parquet",
        candidates_csv_path=normalized / "texas_rrc_pressure_candidates.csv",
        candidates_parquet_path=normalized / "texas_rrc_pressure_candidates.parquet",
        coverage_by_district_decade_csv_path=curated
        / "coverage_by_district_decade.csv",
        coverage_by_district_decade_parquet_path=curated
        / "coverage_by_district_decade.parquet",
        coverage_by_field_decade_csv_path=curated / "coverage_by_field_decade.csv",
        coverage_by_field_decade_parquet_path=curated
        / "coverage_by_field_decade.parquet",
        quality_path=curated / "texas_rrc_pressure_observation_quality.json",
        manifest_path=curated / "manifest.json",
        row_count=1,
        candidate_count=3,
        input_paths=(),
        input_artifacts=(),
        source_gaps=(),
        source_warnings=("raw_manifest_warning:completion_data:error:2026-07-01",),
        command=None,
        code_revision="test-rev",
    )


def _write_pressure_raw_fixture(root: Path) -> None:
    completion_zip = root / "raw" / "completions" / "06-29-2026.zip"
    completion_zip.parent.mkdir(parents=True)
    with zipfile.ZipFile(completion_zip, "w") as archive:
        archive.writestr(
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
                            59: "2500",
                        },
                    ),
                    _record_line(
                        "G-1 Production Interval Data",
                        {
                            1: "123456",
                            2: "654321",
                            3: "999",
                            4: "1",
                            5: "1000",
                            6: "1200",
                        },
                        length=10,
                    ),
                ]
            ),
        )
    wellbore = root / "raw" / "wellbore" / "query" / "wellbore.csv"
    wellbore.parent.mkdir(parents=True)
    wellbore.write_text("API_NO,TOTAL_DEPTH\n4200100001,1200\n", encoding="utf-8")


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
