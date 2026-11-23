"""Tests for Texas RRC field-architecture portfolio output persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.texas_rrc.architecture_portfolio.io import (
    FIELD_ARCHITECTURE_PORTFOLIO_DIR,
    write_field_architecture_portfolio_outputs,
)
from worldenergydata.texas_rrc.architecture_portfolio.quality import (
    FieldArchitecturePortfolioQuality,
)


def test_writes_staged_portfolio_outputs_quality_aliases_and_manifest(
    tmp_path: Path,
) -> None:
    action_queue = pd.DataFrame(
        [
            {
                "portfolio_rank": 1,
                "field_name": "Aguila Vado",
                "architecture_signal_class": "high_access_infill_redevelopment",
                "portfolio_action": "infill_redevelopment_screen",
                "development_theme": "Infill candidate review",
                "source_dossier_href": "../field_architecture_dossiers/fields/aguila.html",
                "dossier_path": "fields/aguila.html",
                "source_caveats": "lease_level_production",
                "quality_flags": "screening_only",
                "portfolio_limitations": "no reserves conclusions",
            }
        ]
    )
    class_summary = pd.DataFrame(
        [
            {
                "architecture_signal_class": "high_access_infill_redevelopment",
                "field_count": 1,
                "portfolio_action": "infill_redevelopment_screen",
            }
        ]
    )
    followup_summary = pd.DataFrame(
        [
            {
                "recommended_followup": "Review infill",
                "portfolio_action": "infill_redevelopment_screen",
                "field_count": 1,
            }
        ]
    )
    quality = FieldArchitecturePortfolioQuality(
        row_count=1,
        blocking_source_gaps=(),
        informational_source_gaps=("pdq_water_gap",),
        portfolio_action_counts={"infill_redevelopment_screen": 1},
        development_theme_counts={"Infill candidate review": 1},
        caveat_counts={"lease_level_production": 1},
        quality_flag_counts={"screening_only": 1},
        limitation_count=1,
    )

    manifest = write_field_architecture_portfolio_outputs(
        action_queue=action_queue,
        class_summary=class_summary,
        followup_summary=followup_summary,
        quality=quality,
        output_root=tmp_path,
        input_paths=[tmp_path / "field_architecture_dossier_index.csv"],
        dossier_input_paths=[tmp_path / "field_atlas_summary.csv"],
        upstream_manifests=[tmp_path / "manifest.json"],
        allow_non_ace_root=True,
        command="worldenergydata texas-rrc build-field-architecture-portfolio",
        code_revision="test-revision",
    )

    output_dir = tmp_path / FIELD_ARCHITECTURE_PORTFOLIO_DIR
    assert manifest.row_count == 1
    assert (output_dir / "field_architecture_action_queue.csv").exists()
    assert (output_dir / "field_architecture_action_queue.parquet").exists()
    assert (output_dir / "field_architecture_class_summary.csv").exists()
    assert (output_dir / "field_architecture_class_summary.parquet").exists()
    assert (output_dir / "field_architecture_followup_summary.csv").exists()
    assert (output_dir / "field_architecture_followup_summary.parquet").exists()
    assert (output_dir / "field_architecture_portfolio.html").exists()
    generic_quality = json.loads((output_dir / "quality.json").read_text())
    component_quality = json.loads(
        (output_dir / "field_architecture_portfolio_quality.json").read_text()
    )
    assert generic_quality == component_quality
    manifest_payload = json.loads((output_dir / "manifest.json").read_text())
    assert manifest_payload["quality_path"] == str(output_dir / "quality.json")
    assert manifest_payload["component_quality_path"] == str(
        output_dir / "field_architecture_portfolio_quality.json"
    )
    assert manifest_payload["html_path"] == str(
        output_dir / "field_architecture_portfolio.html"
    )
    assert manifest_payload["command"] == (
        "worldenergydata texas-rrc build-field-architecture-portfolio"
    )
    assert manifest_payload["dossier_input_paths"] == [
        str(tmp_path / "field_atlas_summary.csv")
    ]
    assert (
        manifest_payload["action_specs"]["high_access_infill_redevelopment"][
            "portfolio_action"
        ]
        == "infill_redevelopment_screen"
    )
    assert (
        manifest_payload["action_specs"]["high_access_infill_redevelopment"][
            "priority_sort"
        ]
        == 30
    )
    assert manifest_payload["limitations"] == ["no reserves conclusions"]


def test_rejects_non_ace_output_root_without_override(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must stay under"):
        write_field_architecture_portfolio_outputs(
            action_queue=pd.DataFrame(),
            class_summary=pd.DataFrame(),
            followup_summary=pd.DataFrame(),
            quality=FieldArchitecturePortfolioQuality(
                row_count=0,
                blocking_source_gaps=(),
                informational_source_gaps=(),
                portfolio_action_counts={},
                development_theme_counts={},
                caveat_counts={},
                quality_flag_counts={},
                limitation_count=0,
            ),
            output_root=tmp_path,
        )
