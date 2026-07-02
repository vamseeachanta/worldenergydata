"""Tests for Texas RRC field-architecture dossier models."""

from __future__ import annotations

import pandas as pd

from worldenergydata.texas_rrc.dossiers.models import (
    DOSSIER_INDEX_COLUMNS,
    build_field_architecture_dossier_index,
    build_field_architecture_dossier_pages,
)


def test_builds_dossier_page_and_index_with_context() -> None:
    selected = pd.DataFrame(
        [
            {
                "dossier_rank": 1,
                "district": "05",
                "field_number": "00870500",
                "field_name": "Aguila Vado",
                "opportunity_rank": 1,
                "opportunity_score": 74.79,
                "opportunity_class": "high",
                "architecture_signal_class": "high_access_infill_redevelopment",
                "architecture_signal_reason": "pipeline proximity and active wells",
                "recommended_followup": "Review infill redevelopment architecture",
                "selection_reason": "top_ranked",
                "dossier_focus": "infill_redevelopment_review",
                "source_caveats": "lease_allocated_production",
                "quality_flags": "screening_only",
            }
        ]
    )
    atlas = pd.DataFrame(
        [
            {
                "district": "05",
                "field_number": "00870500",
                "field_slug": "aguila-vado",
                "report_path": "fields/05-00870500-aguila-vado.html",
                "permit_count": 3,
                "completion_count": 2,
                "lease_count": 5,
                "operator_count": 2,
                "source_caveats": "field_atlas_caveat",
                "quality_flags": "field_atlas_flag",
            }
        ]
    )
    development = pd.DataFrame(
        [
            {
                "district": "05",
                "field_number": "00870500",
                "first_production_month": "2020-01",
                "last_production_month": "2020-03",
                "still_producing": True,
                "well_count": 10,
                "active_well_count": 7,
                "cumulative_boe": 1000.0,
                "production_per_well_boe": 100.0,
            }
        ]
    )

    pages = build_field_architecture_dossier_pages(selected, atlas, development)
    index = build_field_architecture_dossier_index(pages)

    assert len(pages) == 1
    page = pages[0]
    assert page.field_slug == "aguila-vado"
    assert page.dossier_filename == "05-00870500-aguila-vado-dossier.html"
    assert page.source_caveats[:2] == (
        "lease_allocated_production",
        "field_atlas_caveat",
    )
    assert "missing_field_atlas_context" not in page.source_caveats
    assert "missing_field_development_context" not in page.source_caveats
    assert page.quality_flags == ("screening_only", "field_atlas_flag")
    assert "no reserves conclusions" in page.limitations
    assert index.columns.tolist() == DOSSIER_INDEX_COLUMNS
    assert index.loc[0, "source_field_atlas_report_path"] == (
        "reports/field_atlas/fields/05-00870500-aguila-vado.html"
    )
    assert index.loc[0, "production_span_months"] == 3
    assert index.loc[0, "well_count"] == 10


def test_splits_pipe_delimited_caveats_and_marks_missing_context() -> None:
    selected = pd.DataFrame(
        [
            {
                "dossier_rank": 1,
                "district": "05",
                "field_number": "00870500",
                "field_name": "Aguila Vado",
                "opportunity_rank": 1,
                "architecture_signal_class": "high_access_infill_redevelopment",
                "selection_reason": "top_ranked",
                "dossier_focus": "infill_redevelopment_review",
                "source_caveats": (
                    "lease_level_production|no_per_well_allocation;"
                    "rrc_gis_screening_only|dominant_county_pipeline_filter"
                ),
                "quality_flags": "screening_only|missing_well_gis",
            }
        ]
    )

    pages = build_field_architecture_dossier_pages(
        selected,
        pd.DataFrame(),
        pd.DataFrame(),
    )
    index = build_field_architecture_dossier_index(pages)

    assert pages[0].source_caveats == (
        "lease_level_production",
        "no_per_well_allocation",
        "rrc_gis_screening_only",
        "dominant_county_pipeline_filter",
        "missing_field_atlas_context",
        "missing_field_development_context",
    )
    assert pages[0].quality_flags == ("screening_only", "missing_well_gis")
    assert "missing_field_atlas_context" in index.loc[0, "source_caveats"]
    assert "missing_field_development_context" in index.loc[0, "source_caveats"]


def test_marks_missing_stable_columns_as_visible_caveats() -> None:
    selected = pd.DataFrame(
        [
            {
                "dossier_rank": 1,
                "district": "05",
                "field_number": "00870500",
                "field_name": "Aguila Vado",
                "opportunity_rank": 1,
                "architecture_signal_class": "high_access_infill_redevelopment",
                "selection_reason": "top_ranked",
                "dossier_focus": "infill_redevelopment_review",
            }
        ]
    )
    atlas = pd.DataFrame(
        [
            {
                "district": "05",
                "field_number": "00870500",
                "field_slug": "aguila-vado",
                "report_path": "fields/aguila.html",
            }
        ]
    )
    development = pd.DataFrame(
        [{"district": "05", "field_number": "00870500"}]
    )

    pages = build_field_architecture_dossier_pages(selected, atlas, development)

    assert "missing_column:permit_count" in pages[0].source_caveats
    assert "missing_column:first_production_month" in pages[0].source_caveats
    assert "missing_column:cumulative_boe" in pages[0].source_caveats


def test_marks_source_link_when_output_root_is_not_source_root() -> None:
    selected = pd.DataFrame(
        [
            {
                "dossier_rank": 1,
                "district": "05",
                "field_number": "00870500",
                "field_name": "Aguila Vado",
                "opportunity_rank": 1,
                "architecture_signal_class": "high_access_infill_redevelopment",
                "selection_reason": "top_ranked",
                "dossier_focus": "infill_redevelopment_review",
            }
        ]
    )
    atlas = pd.DataFrame(
        [
            {
                "district": "05",
                "field_number": "00870500",
                "field_slug": "aguila-vado",
                "report_path": "fields/aguila.html",
            }
        ]
    )

    pages = build_field_architecture_dossier_pages(
        selected,
        atlas,
        pd.DataFrame(),
        source_links_are_relative=False,
    )

    assert pages[0].source_field_atlas_report_path == (
        "reports/field_atlas/fields/aguila.html"
    )
    assert pages[0].source_field_atlas_href is None
    assert "source_link_not_relative_to_output_root" in pages[0].source_caveats
