"""CLI tests for Texas RRC field-development metrics."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from worldenergydata.cli.commands.texas_rrc import app


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


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
                "lease_number": "02001",
                "operator_number": "300001",
                "well_status": "PRODUCING",
                "completion_date": "2020-01-01",
            }
        ]
    ).to_csv(lifecycle_path, index=False)

    production_path = (
        root
        / "curated"
        / "production"
        / "field_atlas"
        / "production_field_atlas.parquet"
    )
    production_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "aggregation_level": "field",
                "district": "08",
                "field_number": "00010001",
                "field_name": "SPRABERRY",
                "first_production_month": "2020-02",
                "last_production_month": "2025-01",
                "still_producing": True,
                "production_span_months": 60,
                "cumulative_boe": 1000.0,
                "lease_count": 1,
                "operator_count": 1,
            }
        ]
    ).to_parquet(production_path, index=False)

    _write_json(
        lifecycle_path.with_name("well_lifecycle_quality.json"),
        {"row_count": 1, "source_gaps": []},
    )
    _write_json(
        production_path.with_name("production_field_atlas_quality.json"),
        {"row_count": 1, "metric_gaps": []},
    )


def test_build_field_development_metrics_cli_dry_run(tmp_path):
    _write_curated_inputs(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "build-field-development-metrics",
            "--root",
            str(tmp_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Field-development rows" in result.output
    assert "Dry run" in result.output
    assert not (tmp_path / "curated/field_development").exists()


def test_build_field_development_metrics_cli_refuses_missing_sources(tmp_path):
    result = CliRunner().invoke(
        app,
        [
            "build-field-development-metrics",
            "--root",
            str(tmp_path),
            "--output-root",
            str(tmp_path),
            "--allow-non-ace-output",
            "--require-sources",
        ],
    )

    assert result.exit_code == 1
    assert "missing field-development sources" in result.output
    assert "well_lifecycle_spine" in result.output
    assert not (tmp_path / "curated/field_development").exists()


def test_build_field_development_metrics_cli_writes_with_non_ace_override(tmp_path):
    output_root = tmp_path / "out"
    _write_curated_inputs(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "build-field-development-metrics",
            "--root",
            str(tmp_path),
            "--output-root",
            str(output_root),
            "--allow-non-ace-output",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Wrote field-development metrics" in result.output
    assert (
        output_root
        / "curated"
        / "field_development"
        / "metrics"
        / "field_development_metrics.csv"
    ).exists()
    manifest = json.loads(
        (
            output_root / "curated" / "field_development" / "metrics" / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["row_count"] == 1
    assert manifest["input_paths"]
