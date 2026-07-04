"""Tests for Texas RRC field-opportunity source loading."""

from __future__ import annotations

import json
from pathlib import Path

from worldenergydata.texas_rrc.opportunities.sources import (
    load_field_opportunity_inputs,
)


def test_loads_field_atlas_summary_and_upstream_manifests(tmp_path: Path) -> None:
    root = _write_opportunity_source_tree(tmp_path)

    inputs = load_field_opportunity_inputs(root)

    assert inputs.source_gaps == ()
    assert len(inputs.field_atlas_summary) == 2
    assert inputs.field_atlas_summary.loc[0, "field_number"] == "12345"
    assert sorted(path.name for path in inputs.input_paths) == [
        "field_atlas_summary.csv",
        "manifest.json",
        "manifest.json",
        "manifest.json",
        "manifest.json",
    ]
    assert len(inputs.upstream_manifests) == 4


def test_records_missing_field_atlas_summary_gap(tmp_path: Path) -> None:
    root = _write_opportunity_source_tree(tmp_path)
    (root / "curated" / "reports" / "field_atlas" / "field_atlas_summary.csv").unlink()

    inputs = load_field_opportunity_inputs(root)

    assert inputs.field_atlas_summary.empty
    assert inputs.source_gaps == ("missing_field_atlas_summary",)


def test_records_unreadable_manifest_gap(tmp_path: Path) -> None:
    root = _write_opportunity_source_tree(tmp_path)
    manifest = root / "curated" / "reports" / "field_atlas" / "manifest.json"
    manifest.write_text("{not-json", encoding="utf-8")

    inputs = load_field_opportunity_inputs(root)

    assert "unreadable_manifest" in inputs.source_gaps


def _write_opportunity_source_tree(tmp_path: Path) -> Path:
    root = tmp_path / "texas_rrc"
    report_dir = root / "curated" / "reports" / "field_atlas"
    field_dir = root / "curated" / "field_development" / "metrics"
    infra_dir = root / "curated" / "infrastructure" / "access"
    production_dir = root / "curated" / "production" / "field_atlas"
    for directory in (report_dir, field_dir, infra_dir, production_dir):
        directory.mkdir(parents=True)
    (report_dir / "field_atlas_summary.csv").write_text(
        "\n".join(
            [
                "district,field_number,field_name,field_slug,report_path,"
                "field_page_filename,well_count,active_well_count,"
                "production_maturity_class,remaining_activity_score,"
                "cumulative_boe,production_per_well_boe,top_operator_name,"
                "top_operator_share,infrastructure_access_class,"
                "infrastructure_access_score,nearest_pipeline_distance_miles,"
                "nearby_pipeline_count_1mi,nearby_pipeline_count_5mi,"
                "nearby_pipeline_count_10mi,source_caveats,quality_flags",
                "08,12345,Alpha Field,alpha-field,fields/alpha.html,"
                "alpha.html,10,7,mature_active,81.5,2025,202.5,Operator A,"
                "0.75,direct_access,92,0.8,1,4,10,direct_rrc_metrics,",
                "09,54321,Beta Field,beta-field,fields/beta.html,beta.html,"
                "4,0,late_life,4.0,300,75,Operator B,1.0,not_available,"
                ",,,,,missing_well_gis,no_active_wells",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    for directory in (report_dir, field_dir, infra_dir, production_dir):
        (directory / "manifest.json").write_text(
            json.dumps({"row_count": 1, "source_gaps": []}) + "\n",
            encoding="utf-8",
        )
    return root
