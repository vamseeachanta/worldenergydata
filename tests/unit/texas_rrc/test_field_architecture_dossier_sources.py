"""Tests for Texas RRC field-architecture dossier source loading."""

from __future__ import annotations

import json
from pathlib import Path

from worldenergydata.texas_rrc.dossiers.sources import (
    load_field_architecture_dossier_inputs,
)


def test_loads_rankings_manifest_and_context_sources(tmp_path: Path) -> None:
    root = _write_dossier_source_tree(tmp_path)

    inputs = load_field_architecture_dossier_inputs(root)

    assert inputs.blocking_source_gaps == ()
    assert inputs.informational_source_gaps == (
        "pdq_water_metric_gap",
        "production_metric_gap",
    )
    assert len(inputs.rankings) == 2
    assert inputs.rankings.loc[0, "district"] == "05"
    assert inputs.rankings.loc[0, "field_number"] == "00870500"
    assert len(inputs.field_atlas_summary) == 2
    assert len(inputs.field_development_metrics) == 2
    assert [path.name for path in inputs.upstream_manifests] == [
        "field_atlas_manifest.json"
    ]
    assert sorted(path.name for path in inputs.input_paths) == [
        "field_atlas_manifest.json",
        "field_atlas_summary.csv",
        "field_development_metrics.csv",
        "field_opportunity_rankings.csv",
        "manifest.json",
    ]


def test_records_missing_required_source_gaps(tmp_path: Path) -> None:
    root = _write_dossier_source_tree(tmp_path)
    (
        root
        / "curated"
        / "analysis"
        / "field_opportunities"
        / "field_opportunity_rankings.csv"
    ).unlink()
    (
        root
        / "curated"
        / "field_development"
        / "metrics"
        / "field_development_metrics.csv"
    ).unlink()

    inputs = load_field_architecture_dossier_inputs(root)

    assert inputs.rankings.empty
    assert inputs.field_development_metrics.empty
    assert inputs.blocking_source_gaps == (
        "missing_field_opportunity_rankings",
        "missing_field_development_metrics",
    )


def _write_dossier_source_tree(tmp_path: Path) -> Path:
    root = tmp_path / "texas_rrc"
    opportunity_dir = root / "curated" / "analysis" / "field_opportunities"
    atlas_dir = root / "curated" / "reports" / "field_atlas"
    development_dir = root / "curated" / "field_development" / "metrics"
    for directory in (opportunity_dir, atlas_dir, development_dir):
        directory.mkdir(parents=True)

    (opportunity_dir / "field_opportunity_rankings.csv").write_text(
        "\n".join(
            [
                "opportunity_rank,district,field_number,field_name,"
                "architecture_signal_class,opportunity_score",
                "1,05,00870500,Aguila Vado,high_access_infill_redevelopment,74.79",
                "2,03,84750500,Southern Bay,emerging_growth,74.62",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (opportunity_dir / "manifest.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-02T10:31:17Z",
                "source_gaps": ["pdq_water_metric_gap"],
                "quality": {"source_gaps": ["production_metric_gap"]},
                "upstream_manifests": [
                    str(atlas_dir / "field_atlas_manifest.json"),
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (atlas_dir / "field_atlas_manifest.json").write_text(
        json.dumps({"source_gaps": []}) + "\n",
        encoding="utf-8",
    )
    (atlas_dir / "field_atlas_summary.csv").write_text(
        "\n".join(
            [
                "district,field_number,field_name,report_path,permit_count",
                "05,00870500,Aguila Vado,fields/aguila.html,3",
                "03,84750500,Southern Bay,fields/southern.html,4",
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
                "03,84750500,2019-02,2025-12",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return root
