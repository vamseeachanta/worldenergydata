"""Tests for Texas RRC field-architecture dossier CLI support."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

from worldenergydata.cli.commands.texas_rrc import app
from worldenergydata.texas_rrc.dossiers.cli_support import (
    FieldArchitectureDossierBuildResult,
    run_build_field_architecture_dossiers,
)
from worldenergydata.texas_rrc.dossiers.io import (
    FieldArchitectureDossierOutputManifest,
)


def test_build_field_architecture_dossiers_cli_calls_support_layer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_run_build_field_architecture_dossiers(**kwargs):
        calls.append(kwargs)
        return _Result(
            row_count=2,
            blocking_source_gaps=(),
            informational_source_gaps=("pdq_water_gap",),
            dry_run=False,
            manifest=_manifest(tmp_path),
        )

    monkeypatch.setattr(
        "worldenergydata.texas_rrc.dossiers.cli_support."
        "run_build_field_architecture_dossiers",
        fake_run_build_field_architecture_dossiers,
    )

    result = CliRunner().invoke(
        app,
        [
            "build-field-architecture-dossiers",
            "--root",
            str(tmp_path),
            "--output-root",
            str(tmp_path),
            "--allow-non-ace-output",
            "--max-fields",
            "2",
            "--class-coverage-limit",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == [
        {
            "root": tmp_path,
            "output_root": tmp_path,
            "dry_run": False,
            "require_sources": False,
            "allow_non_ace_output": True,
            "max_fields": 2,
            "class_coverage_limit": 1,
        }
    ]
    assert "Wrote field-architecture dossiers" in result.output


def test_run_build_field_architecture_dossiers_dry_run_reports_missing_sources(
    tmp_path: Path,
) -> None:
    result = run_build_field_architecture_dossiers(
        root=tmp_path,
        output_root=tmp_path,
        dry_run=True,
        require_sources=False,
        allow_non_ace_output=True,
    )

    assert isinstance(result, FieldArchitectureDossierBuildResult)
    assert result.dry_run is True
    assert result.row_count == 0
    assert "missing_field_opportunity_rankings" in result.blocking_source_gaps
    assert result.manifest is None


def test_run_build_field_architecture_dossiers_fails_publication_on_invalid_rank(
    tmp_path: Path,
) -> None:
    root = _write_cli_source_tree(tmp_path, opportunity_rank="not-a-number")

    with pytest.raises(ValueError, match="invalid_opportunity_rank"):
        run_build_field_architecture_dossiers(
            root=root,
            output_root=tmp_path / "out",
            allow_non_ace_output=True,
        )


def test_run_build_field_architecture_dossiers_dry_run_reports_invalid_rank(
    tmp_path: Path,
) -> None:
    root = _write_cli_source_tree(tmp_path, opportunity_rank="not-a-number")

    result = run_build_field_architecture_dossiers(
        root=root,
        output_root=tmp_path / "out",
        dry_run=True,
        allow_non_ace_output=True,
    )

    assert result.dry_run is True
    assert result.manifest is None
    assert "invalid_opportunity_rank" in result.blocking_source_gaps


@dataclass(frozen=True)
class _Result:
    row_count: int
    blocking_source_gaps: tuple[str, ...]
    informational_source_gaps: tuple[str, ...]
    dry_run: bool
    manifest: FieldArchitectureDossierOutputManifest | None


def _manifest(tmp_path: Path) -> FieldArchitectureDossierOutputManifest:
    target = tmp_path / "curated" / "analysis" / "field_architecture_dossiers"
    return FieldArchitectureDossierOutputManifest(
        generated_at="2026-07-02T00:00:00Z",
        output_root=tmp_path,
        output_dir=target,
        index_csv_path=target / "field_architecture_dossier_index.csv",
        index_parquet_path=target / "field_architecture_dossier_index.parquet",
        summary_html_path=target / "field_architecture_dossier_summary.html",
        field_dir=target / "fields",
        quality_path=target / "quality.json",
        component_quality_path=target / "field_architecture_dossier_quality.json",
        manifest_path=target / "manifest.json",
        row_count=2,
        input_paths=(),
        upstream_manifests=(),
        blocking_source_gaps=(),
        informational_source_gaps=(),
        selection_policy={"max_fields": 2, "class_coverage_limit": 1},
        limitations=("no reserves conclusions",),
        command=None,
        code_revision="test-rev",
    )


def _write_cli_source_tree(tmp_path: Path, opportunity_rank: str) -> Path:
    root = tmp_path / "texas_rrc"
    opportunity_dir = root / "curated" / "analysis" / "field_opportunities"
    atlas_dir = root / "curated" / "reports" / "field_atlas"
    development_dir = root / "curated" / "field_development" / "metrics"
    for directory in (opportunity_dir, atlas_dir, development_dir):
        directory.mkdir(parents=True)

    (opportunity_dir / "field_opportunity_rankings.csv").write_text(
        "\n".join(
            [
                "opportunity_rank,district,field_number,field_name,architecture_signal_class",
                f"{opportunity_rank},05,00870500,Aguila Vado,high_access_infill_redevelopment",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (opportunity_dir / "manifest.json").write_text(
        '{"source_gaps":[],"upstream_manifests":[]}\n',
        encoding="utf-8",
    )
    (atlas_dir / "field_atlas_summary.csv").write_text(
        "\n".join(
            [
                "district,field_number,field_name,report_path",
                "05,00870500,Aguila Vado,fields/aguila.html",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (development_dir / "field_development_metrics.csv").write_text(
        "\n".join(
            [
                "district,field_number,first_production_month,last_production_month",
                "05,00870500,2020-01,2026-01",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return root
