"""CLI tests for Texas RRC infrastructure access metrics."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import shapefile
from typer.testing import CliRunner

from worldenergydata.cli.commands.texas_rrc import app


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _zip_shapefile(base: Path, zip_path: Path) -> None:
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        for suffix in (".shp", ".shx", ".dbf"):
            archive.write(base.with_suffix(suffix), base.with_suffix(suffix).name)


def _write_well_zip(root: Path) -> None:
    raw = root / "raw/gis/wells"
    raw.mkdir(parents=True, exist_ok=True)
    base = raw / "well001"
    writer = shapefile.Writer(str(base), shapeType=shapefile.POINT)
    writer.field("API", "C")
    writer.field("CNTY_FIPS", "C")
    writer.point(-102.0, 31.0)
    writer.record("42001000010000", "001")
    writer.close()
    _zip_shapefile(base, raw / "well001.zip")


def _write_pipeline_zip(root: Path) -> None:
    raw = root / "raw/gis/pipelines"
    raw.mkdir(parents=True, exist_ok=True)
    base = raw / "pipeline001"
    writer = shapefile.Writer(str(base), shapeType=shapefile.POLYLINE)
    writer.field("T4PERMIT", "C")
    writer.field("CNTY_FIPS", "C")
    writer.line([[(-102.0, 30.9), (-102.0, 31.1)]])
    writer.record("T4-12345", "001")
    writer.close()
    _zip_shapefile(base, raw / "pipeline001.zip")


def _write_curated_inputs(root: Path) -> None:
    lifecycle_path = (
        root / "curated" / "well_lifecycle" / "spine" / "well_lifecycle_spine.csv"
    )
    lifecycle_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "api14": "42001000010000",
                "api10": "4200100001",
                "district": "08",
                "field_number": "00010001",
                "field_name": "SPRABERRY",
            }
        ]
    ).to_csv(lifecycle_path, index=False)

    metrics_path = (
        root
        / "curated"
        / "field_development"
        / "metrics"
        / "field_development_metrics.parquet"
    )
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "district": "08",
                "field_number": "00010001",
                "field_name": "SPRABERRY",
                "well_count": 1,
            }
        ]
    ).to_parquet(metrics_path, index=False)

    _write_json(
        lifecycle_path.with_name("manifest.json"),
        {"row_count": 1, "input_paths": ["raw/wells/example.zip"]},
    )
    _write_json(
        metrics_path.with_name("manifest.json"),
        {"row_count": 1, "input_paths": ["curated/well_lifecycle/spine/manifest.json"]},
    )


def _write_all_inputs(root: Path) -> None:
    _write_curated_inputs(root)
    _write_well_zip(root)
    _write_pipeline_zip(root)
    _write_json(
        root / "raw/gis/wells/manifest.json",
        {"source_id": "well_gis_layers", "artifacts": []},
    )
    _write_json(
        root / "raw/gis/pipelines/manifest.json",
        {"source_id": "pipeline_gis_layers", "artifacts": []},
    )


def test_build_infrastructure_access_metrics_cli_refuses_missing_sources(tmp_path):
    result = CliRunner().invoke(
        app,
        [
            "build-infrastructure-access-metrics",
            "--root",
            str(tmp_path),
            "--output-root",
            str(tmp_path),
            "--allow-non-ace-output",
            "--require-sources",
        ],
    )

    assert result.exit_code == 1
    assert "missing infrastructure sources" in result.output
    assert "field_development_metrics" in result.output
    assert "well_lifecycle_spine" in result.output
    assert "well_gis_layers" in result.output
    assert "pipeline_gis_layers" in result.output


def test_build_infrastructure_access_metrics_cli_dry_run(tmp_path):
    _write_all_inputs(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "build-infrastructure-access-metrics",
            "--root",
            str(tmp_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Infrastructure access rows" in result.output
    assert "Dry run" in result.output
    assert not (tmp_path / "curated/infrastructure/access").exists()


def test_build_infrastructure_access_metrics_cli_writes_outputs(tmp_path):
    output_root = tmp_path / "out"
    _write_all_inputs(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "build-infrastructure-access-metrics",
            "--root",
            str(tmp_path),
            "--output-root",
            str(output_root),
            "--allow-non-ace-output",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Wrote infrastructure access metrics" in result.output
    assert (
        output_root
        / "curated"
        / "infrastructure"
        / "access"
        / "field_infrastructure_access.csv"
    ).exists()
    manifest = json.loads(
        (
            output_root / "curated" / "infrastructure" / "access" / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["row_count"] == 1
    assert "rrc_gis_screening_only" in manifest["direct_source_caveats"]


def test_build_infrastructure_access_metrics_cli_refreshes_gis_when_requested(
    monkeypatch,
    tmp_path,
):
    import worldenergydata.texas_rrc.raw_refresh as raw_refresh

    _write_curated_inputs(tmp_path)
    refreshed: list[str] = []

    class FakeRefresher:
        def __init__(self, output_root):
            self.output_root = output_root

        def refresh_source(self, source_id, selection=None, rows_per_page=1000):
            refreshed.append(source_id)
            if source_id == "well_gis_layers":
                _write_well_zip(self.output_root)
            if source_id == "pipeline_gis_layers":
                _write_pipeline_zip(self.output_root)
            return object()

    monkeypatch.setattr(raw_refresh, "RawSnapshotRefresher", FakeRefresher)

    result = CliRunner().invoke(
        app,
        [
            "build-infrastructure-access-metrics",
            "--root",
            str(tmp_path),
            "--output-root",
            str(tmp_path / "out"),
            "--allow-non-ace-output",
            "--refresh-gis",
        ],
    )

    assert result.exit_code == 0, result.output
    assert refreshed == ["well_gis_layers", "pipeline_gis_layers"]
