"""Tests for Texas RRC field-atlas report HTML rendering."""

from __future__ import annotations

import pandas as pd

from worldenergydata.texas_rrc.reports.field_atlas import FieldAtlasPage
from worldenergydata.texas_rrc.reports.html import render_field_html, render_index_html


def test_index_html_is_self_contained_and_links_field_pages() -> None:
    page = _page()
    summary = pd.DataFrame([page.summary])

    html = render_index_html(summary, (page,))

    assert html.startswith("<!doctype html>")
    assert "Texas RRC Onshore Field Atlas" in html
    assert "fields/08-12345-alpha-field.html" in html
    assert "Alpha Field" in html
    assert "http://" not in html
    assert "https://" not in html
    assert "<script src=" not in html


def test_index_counts_only_fields_with_infrastructure_rows() -> None:
    page = _page()
    row_without_access = dict(page.summary)
    row_without_access["infrastructure_access_class"] = "not_available"
    summary = pd.DataFrame([page.summary, row_without_access])

    html = render_index_html(summary, (page,))

    assert "Fields With Infrastructure Row" in html
    assert '<div class="value">1</div>' in html


def test_field_html_escapes_content_and_shows_lifecycle_sections() -> None:
    page = _page(field_name="Alpha & Beta <Field>")

    html = render_field_html(page)

    assert "Alpha &amp; Beta &lt;Field&gt;" in html
    assert "Lifecycle" in html
    assert "Production" in html
    assert "Infrastructure" in html
    assert "Lease And Operator Context" in html
    assert "PL-1" in html
    assert "Alpha Lease" in html
    assert "direct_rrc_metrics" in html
    assert "http://" not in html
    assert "https://" not in html


def _page(field_name: str = "Alpha Field") -> FieldAtlasPage:
    summary = {
        "district": "08",
        "field_number": "12345",
        "field_name": field_name,
        "field_slug": "alpha-field",
        "report_path": "fields/08-12345-alpha-field.html",
        "field_page_filename": "08-12345-alpha-field.html",
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
        "infrastructure_access_class": "high",
        "infrastructure_access_score": 92.0,
        "nearest_pipeline_distance_miles": 0.8,
        "nearest_pipeline_identifier": "PL-1",
        "nearby_pipeline_count_1mi": 1,
        "nearby_pipeline_count_5mi": 4,
        "nearby_pipeline_count_10mi": 10,
        "source_caveats": "direct_rrc_metrics; gis_centroid",
        "quality_flags": "",
    }
    return FieldAtlasPage(
        district="08",
        field_number="12345",
        field_name=field_name,
        field_slug="alpha-field",
        field_page_filename="08-12345-alpha-field.html",
        report_path="fields/08-12345-alpha-field.html",
        summary=summary,
        lease_rows=(
            {
                "lease_number": "L-1",
                "lease_name": "Alpha Lease",
                "operator_number": "1001",
                "operator_name": "Operator A",
                "cumulative_boe": 1620.0,
            },
        ),
        source_caveats=("direct_rrc_metrics", "gis_centroid"),
        quality_flags=(),
    )
