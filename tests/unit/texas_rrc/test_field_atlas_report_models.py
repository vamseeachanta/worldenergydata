"""Tests for Texas RRC field-atlas report assembly."""

from __future__ import annotations

import pandas as pd

from worldenergydata.texas_rrc.reports.field_atlas import (
    SUMMARY_COLUMNS,
    build_field_atlas_pages,
    build_field_atlas_summary,
    slugify_field,
)
from worldenergydata.texas_rrc.reports.sources import FieldAtlasReportInputs


def test_builds_summary_and_page_models_from_curated_inputs() -> None:
    pages = build_field_atlas_pages(_inputs())
    summary = build_field_atlas_summary(pages)

    assert len(pages) == 2
    first_page = pages[0]
    assert first_page.district == "08"
    assert first_page.field_number == "12345"
    assert first_page.field_page_filename == "08-12345-alpha-field.html"
    assert first_page.report_path == "fields/08-12345-alpha-field.html"
    assert first_page.summary["infrastructure_access_class"] == "high"
    assert first_page.lease_rows[0]["lease_number"] == "L-1"
    assert first_page.lease_rows[0]["cumulative_boe"] == 1620.0
    assert "direct_rrc_metrics" in first_page.source_caveats
    assert "gis_centroid" in first_page.source_caveats

    assert list(summary.columns) == SUMMARY_COLUMNS
    assert list(summary["field_number"]) == ["12345", "54321"]
    assert summary.loc[0, "report_path"] == "fields/08-12345-alpha-field.html"
    assert summary.loc[0, "cumulative_boe"] == 2025.0
    assert summary.loc[1, "infrastructure_access_class"] == "not_available"
    assert "missing_infrastructure_access" in summary.loc[1, "source_caveats"]


def test_slugify_field_is_stable_for_report_paths() -> None:
    assert slugify_field("  A&B Field / North  ") == "a-b-field-north"
    assert slugify_field("") == "field"


def test_max_fields_limits_after_rank_sorting() -> None:
    pages = build_field_atlas_pages(_inputs(), max_fields=1)

    assert [page.field_number for page in pages] == ["12345"]


def _inputs() -> FieldAtlasReportInputs:
    field_development = pd.DataFrame(
        [
            {
                "district": "08",
                "field_number": "12345",
                "field_name": "Alpha Field",
                "well_count": 10,
                "active_well_count": 7,
                "permit_count": 3,
                "completion_count": 2,
                "production_maturity_class": "late-life",
                "remaining_activity_score": 81.5,
                "rank_cumulative_boe": 1,
                "rank_remaining_activity": 4,
                "rank_well_density_proxy": 7,
                "cumulative_oil_bbl": 1000,
                "cumulative_gas_mcf": 6000,
                "cumulative_condensate_bbl": 25,
                "cumulative_boe": 2025,
                "production_per_well_boe": 202.5,
                "lease_count": 2,
                "operator_count": 2,
                "top_operator_number": "1001",
                "top_operator_name": "Operator A",
                "top_operator_share": 0.75,
                "source_caveats": "direct_rrc_metrics",
                "quality_flags": "",
            },
            {
                "district": "09",
                "field_number": "54321",
                "field_name": "Beta Field",
                "well_count": 4,
                "active_well_count": 0,
                "permit_count": 0,
                "completion_count": 0,
                "production_maturity_class": "inactive",
                "remaining_activity_score": 4.0,
                "rank_cumulative_boe": 2,
                "rank_remaining_activity": 9,
                "rank_well_density_proxy": 6,
                "cumulative_oil_bbl": 200,
                "cumulative_gas_mcf": 600,
                "cumulative_condensate_bbl": 0,
                "cumulative_boe": 300,
                "production_per_well_boe": 75.0,
                "lease_count": 1,
                "operator_count": 1,
                "top_operator_number": "1002",
                "top_operator_name": "Operator B",
                "top_operator_share": 1.0,
                "source_caveats": "",
                "quality_flags": "no_active_wells",
            },
        ]
    )
    infrastructure = pd.DataFrame(
        [
            {
                "district": "08",
                "field_number": "12345",
                "field_name": "Alpha Field",
                "nearest_pipeline_distance_miles": 0.8,
                "nearby_pipeline_count_1mi": 1,
                "nearby_pipeline_count_5mi": 4,
                "nearby_pipeline_count_10mi": 10,
                "nearest_pipeline_identifier": "PL-1",
                "infrastructure_access_score": 92.0,
                "infrastructure_access_class": "high",
                "source_caveats": "gis_centroid",
                "quality_flags": "",
            }
        ]
    )
    production_atlas = pd.DataFrame(
        [
            {
                "aggregation_level": "lease",
                "district": "08",
                "field_number": "12345",
                "field_name": "Alpha Field",
                "lease_number": "L-2",
                "lease_name": "Second Lease",
                "operator_number": "1002",
                "operator_name": "Operator B",
                "cumulative_boe": 405.0,
                "cumulative_oil_bbl": 200.0,
                "cumulative_gas_mcf": 1200.0,
                "cumulative_condensate_bbl": 5.0,
            },
            {
                "aggregation_level": "lease",
                "district": "08",
                "field_number": "12345",
                "field_name": "Alpha Field",
                "lease_number": "L-1",
                "lease_name": "Alpha Lease",
                "operator_number": "1001",
                "operator_name": "Operator A",
                "cumulative_boe": 1620.0,
                "cumulative_oil_bbl": 800.0,
                "cumulative_gas_mcf": 4800.0,
                "cumulative_condensate_bbl": 20.0,
            },
        ]
    )
    return FieldAtlasReportInputs(
        field_development=field_development,
        infrastructure_access=infrastructure,
        production_atlas=production_atlas,
        input_paths=(),
        source_gaps=(),
    )
