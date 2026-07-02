"""Tests for the Texas RRC field-opportunity CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

from worldenergydata.cli.commands.texas_rrc import app
from worldenergydata.texas_rrc.opportunities.cli_support import (
    run_build_field_opportunities,
)
from worldenergydata.texas_rrc.opportunities.io import (
    FieldOpportunityOutputManifest,
)


def test_build_field_opportunities_cli_calls_support_layer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[dict[str, object]] = []

    def fake_run_build_field_opportunities(**kwargs):
        calls.append(kwargs)
        return _Result(
            row_count=2,
            source_gaps=(),
            dry_run=False,
            manifest=_manifest(tmp_path),
        )

    monkeypatch.setattr(
        "worldenergydata.texas_rrc.opportunities.cli_support."
        "run_build_field_opportunities",
        fake_run_build_field_opportunities,
    )

    result = CliRunner().invoke(
        app,
        [
            "build-field-opportunities",
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
    assert "Wrote field-opportunity rankings" in result.output


def test_run_build_field_opportunities_dry_run_reports_missing_sources(
    tmp_path: Path,
) -> None:
    result = run_build_field_opportunities(
        root=tmp_path,
        output_root=tmp_path,
        dry_run=True,
        require_sources=False,
        allow_non_ace_output=True,
    )

    assert result.dry_run is True
    assert result.row_count == 0
    assert "missing_field_atlas_summary" in result.source_gaps
    assert result.manifest is None


def test_run_build_field_opportunities_requires_sources(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing_field_atlas_summary"):
        run_build_field_opportunities(
            root=tmp_path,
            output_root=tmp_path,
            dry_run=True,
            require_sources=True,
            allow_non_ace_output=True,
        )


@dataclass(frozen=True)
class _Result:
    row_count: int
    source_gaps: tuple[str, ...]
    dry_run: bool
    manifest: FieldOpportunityOutputManifest | None


def _manifest(tmp_path: Path) -> FieldOpportunityOutputManifest:
    target = tmp_path / "curated" / "analysis" / "field_opportunities"
    return FieldOpportunityOutputManifest(
        generated_at="2026-07-02T00:00:00Z",
        output_root=tmp_path,
        output_dir=target,
        rankings_csv_path=target / "field_opportunity_rankings.csv",
        rankings_parquet_path=target / "field_opportunity_rankings.parquet",
        html_path=target / "field_opportunity_summary.html",
        quality_path=target / "field_opportunity_quality.json",
        manifest_path=target / "manifest.json",
        row_count=2,
        input_paths=(),
        upstream_manifests=(),
        source_gaps=(),
        command=None,
        code_revision="test-rev",
    )
