"""Tests for Texas RRC field-architecture portfolio models."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from worldenergydata.texas_rrc.architecture_portfolio.models import (
    build_field_architecture_action_queue,
    summarize_architecture_classes,
    summarize_followup_recommendations,
)


def test_builds_action_queue_with_priority_and_unknown_class_caveat() -> None:
    dossier_index = pd.DataFrame(
        [
            {
                "district": "05",
                "field_number": "00870500",
                "field_name": "Aguila Vado",
                "field_slug": "aguila-vado",
                "architecture_signal_class": "high_access_infill_redevelopment",
                "opportunity_rank": 1,
                "opportunity_score": 74.79,
                "source_caveats": "lease_level_production",
                "quality_flags": "",
            },
            {
                "district": "03",
                "field_number": "84750500",
                "field_name": "Southern Bay",
                "field_slug": "southern-bay",
                "architecture_signal_class": "low_data_confidence",
                "opportunity_rank": 9,
                "opportunity_score": 12.5,
                "source_caveats": "",
                "quality_flags": "",
            },
            {
                "district": "02",
                "field_number": "27135750",
                "field_name": "Eagleville",
                "field_slug": "eagleville",
                "architecture_signal_class": "not_in_contract",
                "opportunity_rank": 2,
                "opportunity_score": 60.0,
                "source_caveats": "existing_caveat",
                "quality_flags": "",
            },
        ]
    )

    queue = build_field_architecture_action_queue(dossier_index)

    assert queue["field_name"].tolist() == ["Eagleville", "Southern Bay", "Aguila Vado"]
    assert queue["portfolio_rank"].tolist() == [1, 2, 3]
    assert queue["portfolio_action"].tolist() == [
        "data_completion_review",
        "data_completion_review",
        "infill_redevelopment_screen",
    ]
    assert queue["followup_priority"].tolist() == [
        "source_data_first",
        "source_data_first",
        "high",
    ]
    assert queue["review_sequence"].tolist() == [1, 2, 1]
    assert "unknown_architecture_signal_class" in queue.loc[0, "source_caveats"]
    assert queue.loc[2, "development_theme"] == (
        "Infill, recompletion, redevelopment candidate review"
    )


def test_summarizes_architecture_classes_and_followups() -> None:
    queue = build_field_architecture_action_queue(
        pd.DataFrame(
            [
                {
                    "district": "05",
                    "field_number": "00870500",
                    "field_name": "Aguila Vado",
                    "architecture_signal_class": "high_access_infill_redevelopment",
                    "opportunity_rank": 1,
                    "opportunity_score": 70.0,
                    "recommended_followup": "Review infill",
                    "cumulative_boe": 10.0,
                    "active_well_count": 2,
                    "permit_count": 1,
                    "completion_count": 3,
                    "infrastructure_access_class": "direct_access",
                    "source_caveats": "beta; alpha",
                    "quality_flags": "flag_b",
                },
                {
                    "district": "03",
                    "field_number": "84750500",
                    "field_name": "Southern Bay",
                    "architecture_signal_class": "high_access_infill_redevelopment",
                    "opportunity_rank": 2,
                    "opportunity_score": 50.0,
                    "recommended_followup": "Review infill",
                    "cumulative_boe": 20.0,
                    "active_well_count": 4,
                    "permit_count": 2,
                    "completion_count": 1,
                    "infrastructure_access_class": "regional_access",
                    "source_caveats": "alpha",
                    "quality_flags": "flag_a; flag_b",
                },
            ]
        )
    )

    class_summary = summarize_architecture_classes(queue)
    followup_summary = summarize_followup_recommendations(queue)

    assert class_summary.loc[0, "architecture_signal_class"] == (
        "high_access_infill_redevelopment"
    )
    assert class_summary.loc[0, "field_count"] == 2
    assert class_summary.loc[0, "mean_opportunity_score"] == 60.0
    assert class_summary.loc[0, "median_opportunity_score"] == 60.0
    assert class_summary.loc[0, "total_cumulative_boe"] == 30.0
    assert class_summary.loc[0, "total_active_well_count"] == 6
    assert class_summary.loc[0, "total_permit_count"] == 3
    assert class_summary.loc[0, "total_completion_count"] == 4
    assert class_summary.loc[0, "direct_or_near_access_count"] == 1
    assert class_summary.loc[0, "top_caveats"] == "alpha; beta"
    assert class_summary.loc[0, "top_quality_flags"] == "flag_b; flag_a"

    assert followup_summary.loc[0, "recommended_followup"] == "Review infill"
    assert followup_summary.loc[0, "field_count"] == 2
    assert followup_summary.loc[0, "min_opportunity_score"] == 50.0
    assert followup_summary.loc[0, "max_opportunity_score"] == 70.0


def test_action_queue_builds_safe_dossier_href_and_rejects_unsafe_paths(
    tmp_path: Path,
) -> None:
    root = tmp_path / "texas_rrc"
    input_dossier_dir = root / "curated" / "analysis" / "field_architecture_dossiers"
    fields_dir = input_dossier_dir / "fields"
    fields_dir.mkdir(parents=True)
    (fields_dir / "aguila-dossier.html").write_text("<html></html>\n", encoding="utf-8")

    queue = build_field_architecture_action_queue(
        pd.DataFrame(
            [
                {
                    "district": "05",
                    "field_number": "00870500",
                    "field_name": "Aguila Vado",
                    "architecture_signal_class": "high_access_infill_redevelopment",
                    "opportunity_rank": 1,
                    "dossier_path": "fields/aguila-dossier.html",
                    "source_caveats": "",
                },
                {
                    "district": "03",
                    "field_number": "84750500",
                    "field_name": "Southern Bay",
                    "architecture_signal_class": "high_access_infill_redevelopment",
                    "opportunity_rank": 2,
                    "dossier_path": "fields/southern-dossier.html\x00",
                    "source_caveats": "",
                },
            ]
        ),
        input_dossier_dir=input_dossier_dir,
        output_root=root,
    )

    assert queue.loc[0, "source_dossier_href"] == (
        "../field_architecture_dossiers/fields/aguila-dossier.html"
    )
    assert queue.loc[1, "source_dossier_href"] == ""
    assert (
        "source_dossier_link_not_relative_to_output_root"
        in queue.loc[
            1,
            "source_caveats",
        ]
    )
