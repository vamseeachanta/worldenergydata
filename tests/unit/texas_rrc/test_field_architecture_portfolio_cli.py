"""Tests for Texas RRC field-architecture portfolio CLI support."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from worldenergydata.cli.commands.texas_rrc import app
from worldenergydata.texas_rrc.architecture_portfolio.cli_support import (
    FieldArchitecturePortfolioBuildResult,
    run_build_field_architecture_portfolio,
)
from worldenergydata.texas_rrc.architecture_portfolio.io import (
    FieldArchitecturePortfolioOutputManifest,
)


def test_build_field_architecture_portfolio_cli_calls_support_layer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_run_build_field_architecture_portfolio(**kwargs):
        calls.append(kwargs)
        return _Result(
            row_count=2,
            blocking_source_gaps=(),
            informational_source_gaps=("pdq_water_gap",),
            dry_run=False,
            manifest=_manifest(tmp_path),
        )

    monkeypatch.setattr(
        "worldenergydata.texas_rrc.architecture_portfolio.cli_support."
        "run_build_field_architecture_portfolio",
        fake_run_build_field_architecture_portfolio,
    )

    result = CliRunner().invoke(
        app,
        [
            "build-field-architecture-portfolio",
            "--root",
            str(tmp_path),
            "--output-root",
            str(tmp_path),
            "--allow-non-ace-output",
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
        }
    ]
    assert "Wrote field-architecture portfolio" in result.output


def test_run_build_field_architecture_portfolio_dry_run_reports_missing_sources(
    tmp_path: Path,
) -> None:
    result = run_build_field_architecture_portfolio(
        root=tmp_path,
        output_root=tmp_path,
        dry_run=True,
        require_sources=False,
        allow_non_ace_output=True,
    )

    assert isinstance(result, FieldArchitecturePortfolioBuildResult)
    assert result.dry_run is True
    assert result.row_count == 0
    assert "missing_field_architecture_dossier_index" in result.blocking_source_gaps
    assert result.manifest is None


def test_run_build_field_architecture_portfolio_publishes_from_dossier_sources(
    tmp_path: Path,
) -> None:
    root = _write_portfolio_source_tree(tmp_path)

    result = run_build_field_architecture_portfolio(
        root=root,
        output_root=root,
        allow_non_ace_output=True,
    )

    assert result.dry_run is False
    assert result.manifest is not None
    assert result.manifest.row_count == 1
    output_dir = root / "curated" / "analysis" / "field_architecture_portfolio"
    action_queue = pd.read_csv(output_dir / "field_architecture_action_queue.csv")
    assert action_queue.loc[0, "source_dossier_href"] == (
        "../field_architecture_dossiers/fields/aguila.html"
    )
    assert (output_dir / "field_architecture_portfolio.html").is_file()


def test_run_build_field_architecture_portfolio_reports_invalid_rank_as_informational(
    tmp_path: Path,
) -> None:
    root = _write_portfolio_source_tree(tmp_path, opportunity_rank="not-a-number")

    result = run_build_field_architecture_portfolio(
        root=root,
        output_root=root,
        dry_run=True,
        require_sources=True,
        allow_non_ace_output=True,
    )

    assert result.blocking_source_gaps == ()
    assert "invalid_opportunity_rank" in result.informational_source_gaps
    assert result.row_count == 1


@dataclass(frozen=True)
class _Result:
    row_count: int
    blocking_source_gaps: tuple[str, ...]
    informational_source_gaps: tuple[str, ...]
    dry_run: bool
    manifest: FieldArchitecturePortfolioOutputManifest | None


def _manifest(tmp_path: Path) -> FieldArchitecturePortfolioOutputManifest:
    target = tmp_path / "curated" / "analysis" / "field_architecture_portfolio"
    return FieldArchitecturePortfolioOutputManifest(
        generated_at="2026-07-02T00:00:00Z",
        output_root=tmp_path,
        output_dir=target,
        action_queue_csv_path=target / "field_architecture_action_queue.csv",
        action_queue_parquet_path=target / "field_architecture_action_queue.parquet",
        class_summary_csv_path=target / "field_architecture_class_summary.csv",
        class_summary_parquet_path=target / "field_architecture_class_summary.parquet",
        followup_summary_csv_path=target / "field_architecture_followup_summary.csv",
        followup_summary_parquet_path=target
        / "field_architecture_followup_summary.parquet",
        html_path=target / "field_architecture_portfolio.html",
        quality_path=target / "quality.json",
        component_quality_path=target / "field_architecture_portfolio_quality.json",
        manifest_path=target / "manifest.json",
        row_count=2,
        class_summary_row_count=1,
        followup_summary_row_count=1,
        input_paths=(),
        dossier_input_paths=(),
        upstream_manifests=(),
        blocking_source_gaps=(),
        informational_source_gaps=(),
        limitations=("no reserves conclusions",),
        action_specs={},
        command=None,
        code_revision="test-rev",
    )


def _write_portfolio_source_tree(
    tmp_path: Path,
    opportunity_rank: int | str = 1,
) -> Path:
    root = tmp_path / "texas_rrc"
    dossier_dir = root / "curated" / "analysis" / "field_architecture_dossiers"
    fields_dir = dossier_dir / "fields"
    fields_dir.mkdir(parents=True)
    (fields_dir / "aguila.html").write_text("<html></html>\n", encoding="utf-8")
    pd.DataFrame(
        [
            {
                "district": "05",
                "field_number": "00870500",
                "field_name": "Aguila Vado",
                "field_slug": "aguila-vado",
                "architecture_signal_class": "high_access_infill_redevelopment",
                "opportunity_rank": opportunity_rank,
                "opportunity_score": 74.79,
                "recommended_followup": "Review infill",
                "dossier_focus": "High access infill candidate",
                "dossier_path": "fields/aguila.html",
                "source_caveats": "lease_level_production",
                "quality_flags": "screening_only",
            }
        ]
    ).to_csv(dossier_dir / "field_architecture_dossier_index.csv", index=False)
    (dossier_dir / "manifest.json").write_text(
        '{"input_paths":["curated/reports/field_atlas/manifest.json"],'
        '"blocking_source_gaps":[],"informational_source_gaps":["pdq_water_gap"]}\n',
        encoding="utf-8",
    )
    (dossier_dir / "quality.json").write_text(
        '{"blocking_source_gaps":[],"informational_source_gaps":["pdq_water_gap"]}\n',
        encoding="utf-8",
    )
    return root
