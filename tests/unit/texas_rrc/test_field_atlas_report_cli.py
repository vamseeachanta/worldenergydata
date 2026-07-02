"""Tests for the Texas RRC field-atlas report CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

from worldenergydata.cli.commands.texas_rrc import app
from worldenergydata.texas_rrc.reports.cli_support import (
    run_publish_field_atlas_reports,
)
from worldenergydata.texas_rrc.reports.io import FieldAtlasReportOutputManifest


def test_publish_field_atlas_reports_cli_calls_support_layer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[dict[str, object]] = []

    def fake_run_publish_field_atlas_reports(**kwargs):
        calls.append(kwargs)
        return _Result(
            row_count=2,
            page_count=2,
            source_gaps=(),
            dry_run=False,
            manifest=_manifest(tmp_path),
        )

    monkeypatch.setattr(
        "worldenergydata.texas_rrc.reports.cli_support."
        "run_publish_field_atlas_reports",
        fake_run_publish_field_atlas_reports,
    )

    result = CliRunner().invoke(
        app,
        [
            "publish-field-atlas-reports",
            "--root",
            str(tmp_path),
            "--output-root",
            str(tmp_path),
            "--allow-non-ace-output",
            "--max-fields",
            "2",
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
        }
    ]
    assert "Wrote field-atlas reports" in result.output


def test_run_publish_field_atlas_reports_dry_run_reports_missing_sources(
    tmp_path: Path,
) -> None:
    result = run_publish_field_atlas_reports(
        root=tmp_path,
        output_root=tmp_path,
        dry_run=True,
        require_sources=False,
        allow_non_ace_output=True,
    )

    assert result.dry_run is True
    assert result.row_count == 0
    assert result.page_count == 0
    assert "missing_field_development_metrics" in result.source_gaps
    assert result.manifest is None


def test_run_publish_field_atlas_reports_requires_sources(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing_field_development_metrics"):
        run_publish_field_atlas_reports(
            root=tmp_path,
            output_root=tmp_path,
            dry_run=True,
            require_sources=True,
            allow_non_ace_output=True,
        )


@dataclass(frozen=True)
class _Result:
    row_count: int
    page_count: int
    source_gaps: tuple[str, ...]
    dry_run: bool
    manifest: FieldAtlasReportOutputManifest | None


def _manifest(tmp_path: Path) -> FieldAtlasReportOutputManifest:
    target = tmp_path / "curated" / "reports" / "field_atlas"
    return FieldAtlasReportOutputManifest(
        generated_at="2026-07-02T00:00:00Z",
        output_root=tmp_path,
        output_dir=target,
        index_path=target / "index.html",
        summary_csv_path=target / "field_atlas_summary.csv",
        summary_parquet_path=target / "field_atlas_summary.parquet",
        quality_path=target / "field_atlas_report_quality.json",
        manifest_path=target / "manifest.json",
        row_count=2,
        page_count=2,
        input_paths=(),
        source_gaps=(),
        command=None,
        code_revision="test-rev",
    )
