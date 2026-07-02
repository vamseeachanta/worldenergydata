"""Tests for Texas RRC field-opportunity scoring."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from worldenergydata.texas_rrc.opportunities.scoring import (
    SCORING_VERSION,
    build_field_opportunity_rankings,
)
from worldenergydata.texas_rrc.opportunities.sources import FieldOpportunityInputs


def test_builds_ranked_component_scores_and_preserves_caveats() -> None:
    rankings = build_field_opportunity_rankings(_inputs())

    assert SCORING_VERSION == "texas_rrc_field_opportunity_v1"
    assert list(rankings["field_number"]) == ["12345", "77777", "54321"]
    assert list(rankings["opportunity_rank"]) == [1, 2, 3]
    assert rankings.loc[0, "opportunity_score"] > rankings.loc[1, "opportunity_score"]
    assert rankings.loc[1, "opportunity_score"] > rankings.loc[2, "opportunity_score"]
    assert rankings["opportunity_score"].between(0, 100).all()
    assert rankings.loc[0, "production_scale_component_score"] == 100.0
    assert rankings.loc[2, "infrastructure_component_score"] == 0.0
    assert rankings.loc[2, "quality_penalty_score"] > 0
    assert rankings.loc[2, "opportunity_class"] == "low_confidence"
    assert "missing_well_gis" in rankings.loc[2, "source_caveats"]


def test_tied_scores_sort_by_stable_field_identity() -> None:
    frame = _summary_frame().iloc[[0, 0]].copy().reset_index(drop=True)
    frame.loc[0, "field_number"] = "20000"
    frame.loc[0, "field_name"] = "Zulu Field"
    frame.loc[1, "field_number"] = "10000"
    frame.loc[1, "field_name"] = "Alpha Field"

    rankings = build_field_opportunity_rankings(
        FieldOpportunityInputs(
            field_atlas_summary=frame,
            input_paths=(),
            source_gaps=(),
            upstream_manifests=(),
        )
    )

    assert list(rankings["field_number"]) == ["10000", "20000"]


def test_fractional_infrastructure_scores_are_scaled_to_component_percent() -> None:
    rankings = build_field_opportunity_rankings(_inputs())

    alpha = rankings[rankings["field_number"] == "12345"].iloc[0]

    assert alpha["infrastructure_component_score"] == 95.0


def test_fractional_remaining_activity_scores_are_scaled_to_component_percent() -> None:
    frame = _summary_frame().copy()
    frame["remaining_activity_score"] = [0.82, 0.95, 0.04]

    rankings = build_field_opportunity_rankings(
        FieldOpportunityInputs(
            field_atlas_summary=frame,
            input_paths=(),
            source_gaps=(),
            upstream_manifests=(),
        )
    )

    alpha = rankings[rankings["field_number"] == "12345"].iloc[0]

    assert alpha["remaining_activity_component_score"] == 82.0


def test_quality_caveats_do_not_force_low_confidence_when_core_sources_exist() -> None:
    frame = _summary_frame().iloc[[0]].copy()
    frame.loc[0, "source_caveats"] = (
        "lease_level_production|no_per_well_allocation;"
        "rrc_gis_screening_only|field_centroid_pipeline_screening"
    )

    rankings = build_field_opportunity_rankings(
        FieldOpportunityInputs(
            field_atlas_summary=frame,
            input_paths=(),
            source_gaps=(),
            upstream_manifests=(),
        )
    )

    assert rankings.loc[0, "quality_penalty_score"] == 20.0
    assert rankings.loc[0, "opportunity_class"] != "low_confidence"


def _inputs() -> FieldOpportunityInputs:
    return FieldOpportunityInputs(
        field_atlas_summary=_summary_frame(),
        input_paths=(Path("field_atlas_summary.csv"),),
        source_gaps=(),
        upstream_manifests=(),
    )


def _summary_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "district": "08",
                "field_number": "12345",
                "field_name": "Alpha Field",
                "field_slug": "alpha-field",
                "report_path": "fields/08-12345-alpha-field.html",
                "field_page_filename": "08-12345-alpha-field.html",
                "well_count": 10,
                "active_well_count": 7,
                "production_maturity_class": "mature_active",
                "remaining_activity_score": 82.0,
                "cumulative_boe": 10000.0,
                "production_per_well_boe": 1000.0,
                "top_operator_name": "Operator A",
                "top_operator_share": 0.70,
                "infrastructure_access_class": "direct_access",
                "infrastructure_access_score": 0.95,
                "nearest_pipeline_distance_miles": 0.5,
                "nearby_pipeline_count_1mi": 2,
                "nearby_pipeline_count_5mi": 8,
                "nearby_pipeline_count_10mi": 15,
                "source_caveats": "direct_rrc_metrics",
                "quality_flags": "",
            },
            {
                "district": "08",
                "field_number": "77777",
                "field_name": "Gamma Field",
                "field_slug": "gamma-field",
                "report_path": "fields/08-77777-gamma-field.html",
                "field_page_filename": "08-77777-gamma-field.html",
                "well_count": 5,
                "active_well_count": 4,
                "production_maturity_class": "growth",
                "remaining_activity_score": 95.0,
                "cumulative_boe": 2500.0,
                "production_per_well_boe": 500.0,
                "top_operator_name": "Operator C",
                "top_operator_share": 0.40,
                "infrastructure_access_class": "regional_access",
                "infrastructure_access_score": 45.0,
                "nearest_pipeline_distance_miles": 8.0,
                "nearby_pipeline_count_1mi": 0,
                "nearby_pipeline_count_5mi": 0,
                "nearby_pipeline_count_10mi": 1,
                "source_caveats": "rrc_gis_screening_only",
                "quality_flags": "",
            },
            {
                "district": "09",
                "field_number": "54321",
                "field_name": "Beta Field",
                "field_slug": "beta-field",
                "report_path": "fields/09-54321-beta-field.html",
                "field_page_filename": "09-54321-beta-field.html",
                "well_count": 4,
                "active_well_count": 0,
                "production_maturity_class": "late_life",
                "remaining_activity_score": 4.0,
                "cumulative_boe": 300.0,
                "production_per_well_boe": 75.0,
                "top_operator_name": "",
                "top_operator_share": None,
                "infrastructure_access_class": "not_available",
                "infrastructure_access_score": None,
                "nearest_pipeline_distance_miles": None,
                "nearby_pipeline_count_1mi": None,
                "nearby_pipeline_count_5mi": None,
                "nearby_pipeline_count_10mi": None,
                "source_caveats": "missing_well_gis",
                "quality_flags": "missing_lifecycle",
            },
        ]
    )
