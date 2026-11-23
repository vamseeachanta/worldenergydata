"""Tests for Texas RRC field-atlas report source loading."""

from __future__ import annotations

import json
from pathlib import Path

from worldenergydata.texas_rrc.reports.sources import load_field_atlas_report_inputs


def test_loads_direct_curated_sources(tmp_path: Path) -> None:
    root = _write_report_source_tree(tmp_path)

    inputs = load_field_atlas_report_inputs(root)

    assert inputs.source_gaps == ()
    assert len(inputs.field_development) == 1
    assert len(inputs.infrastructure_access) == 1
    assert len(inputs.production_atlas) == 2
    assert inputs.field_development.loc[0, "field_number"] == "12345"
    assert inputs.infrastructure_access.loc[0, "nearest_pipeline_identifier"] == "PL-1"
    assert sorted(path.name for path in inputs.input_paths) == [
        "field_development_metrics.csv",
        "field_infrastructure_access.csv",
        "manifest.json",
        "manifest.json",
        "manifest.json",
        "production_field_atlas.csv",
    ]


def test_records_missing_source_gaps(tmp_path: Path) -> None:
    root = _write_report_source_tree(tmp_path)
    (
        root / "curated" / "production" / "field_atlas" / "production_field_atlas.csv"
    ).unlink()

    inputs = load_field_atlas_report_inputs(root)

    assert inputs.production_atlas.empty
    assert inputs.source_gaps == ("missing_production_field_atlas",)


def _write_report_source_tree(tmp_path: Path) -> Path:
    root = tmp_path / "texas_rrc"
    field_dir = root / "curated" / "field_development" / "metrics"
    infra_dir = root / "curated" / "infrastructure" / "access"
    production_dir = root / "curated" / "production" / "field_atlas"
    field_dir.mkdir(parents=True)
    infra_dir.mkdir(parents=True)
    production_dir.mkdir(parents=True)
    (field_dir / "field_development_metrics.csv").write_text(
        "\n".join(
            [
                "district,field_number,field_name,well_count,active_well_count,"
                "permit_count,completion_count,production_maturity_class,"
                "remaining_activity_score,rank_cumulative_boe,"
                "rank_remaining_activity,rank_well_density_proxy,"
                "cumulative_oil_bbl,cumulative_gas_mcf,cumulative_condensate_bbl,"
                "cumulative_boe,production_per_well_boe,lease_count,operator_count,"
                "top_operator_number,top_operator_name,top_operator_share,"
                "source_caveats,quality_flags",
                "08,12345,Alpha Field,10,7,3,2,late-life,81.5,1,4,7,"
                "1000,6000,25,2025,202.5,2,2,1001,Operator A,0.75,"
                "direct_rrc_metrics,",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (infra_dir / "field_infrastructure_access.csv").write_text(
        "\n".join(
            [
                "district,field_number,field_name,nearest_pipeline_distance_miles,"
                "nearby_pipeline_count_1mi,nearby_pipeline_count_5mi,"
                "nearby_pipeline_count_10mi,nearest_pipeline_identifier,"
                "infrastructure_access_score,infrastructure_access_class,"
                "source_caveats,quality_flags",
                "08,12345,Alpha Field,0.8,1,4,10,PL-1,92.0,high,gis_centroid,",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (production_dir / "production_field_atlas.csv").write_text(
        "\n".join(
            [
                "aggregation_level,district,field_number,field_name,lease_number,"
                "lease_name,operator_number,operator_name,cumulative_oil_bbl,"
                "cumulative_gas_mcf,cumulative_condensate_bbl,cumulative_boe,"
                "first_production_month,last_production_month,still_producing,"
                "lease_count,operator_count,top_operator_number,top_operator_name,"
                "top_operator_boe,top_operator_share",
                "field,08,12345,Alpha Field,,,,,1000,6000,25,2025,2010-01,"
                "2026-05,true,2,2,1001,Operator A,1518.75,0.75",
                "lease,08,12345,Alpha Field,L-1,Alpha Lease,1001,Operator A,800,"
                "4800,20,1620,2010-01,2026-05,true,,,,,",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    for directory in (field_dir, infra_dir, production_dir):
        (directory / "manifest.json").write_text(
            json.dumps({"row_count": 1, "source_gaps": []}) + "\n",
            encoding="utf-8",
        )
    return root
