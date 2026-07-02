"""Tests for Texas RRC field-architecture dossier HTML rendering."""

from __future__ import annotations

import pandas as pd

from worldenergydata.texas_rrc.dossiers.html import (
    render_field_architecture_dossier_html,
    render_field_architecture_dossier_summary_html,
)
from worldenergydata.texas_rrc.dossiers.models import FieldArchitectureDossierPage
from worldenergydata.texas_rrc.dossiers.quality import FieldArchitectureDossierQuality


def test_renders_self_contained_summary_and_field_html() -> None:
    quality = FieldArchitectureDossierQuality(
        row_count=1,
        blocking_source_gaps=("missing_context",),
        informational_source_gaps=("pdq_water_gap",),
        architecture_class_counts={"high_access_infill_redevelopment": 1},
        selection_reason_counts={"top_ranked": 1},
        caveat_counts={"lease_allocated": 1},
        quality_flag_counts={"screening_only": 1},
        limitation_count=3,
    )
    index = pd.DataFrame(
        [
            {
                "dossier_rank": 1,
                "field_name": "Aguila <Vado>",
                "district": "05",
                "field_number": "00870500",
                "architecture_signal_class": "high_access_infill_redevelopment",
                "opportunity_score": 74.79,
                "dossier_path": "fields/aguila-dossier.html",
                "source_field_atlas_report_path": (
                    "reports/field_atlas/fields/05-00870500-aguila-vado.html"
                ),
            }
        ]
    )
    page = FieldArchitectureDossierPage(
        district="05",
        field_number="00870500",
        field_name="Aguila <Vado>",
        field_slug="aguila-vado",
        dossier_filename="05-00870500-aguila-vado-dossier.html",
        dossier_path="fields/05-00870500-aguila-vado-dossier.html",
        source_field_atlas_report_path=(
            "reports/field_atlas/fields/05-00870500-aguila-vado.html"
        ),
        source_field_atlas_href=(
            "../../../reports/field_atlas/fields/05-00870500-aguila-vado.html"
        ),
        summary={
            "architecture_signal_class": "high_access_infill_redevelopment",
            "opportunity_rank": 1,
            "opportunity_score": 74.79,
            "recommended_followup": "Review <infill>",
            "first_production_month": "2020-01",
            "last_production_month": "2020-03",
            "well_count": 10,
            "infrastructure_access_class": "high_access",
            "top_operator_name": "Operator & Co",
        },
        source_caveats=("lease_allocated",),
        quality_flags=("screening_only",),
        limitations=("no reserves conclusions",),
    )

    summary_html = render_field_architecture_dossier_summary_html(index, quality)
    field_html = render_field_architecture_dossier_html(page)

    assert "Aguila &lt;Vado&gt;" in summary_html
    assert "../../reports/field_atlas/fields/05-00870500-aguila-vado.html" in (
        summary_html
    )
    assert "missing_context" in summary_html
    assert "pdq_water_gap" in summary_html
    assert "http://" not in summary_html
    assert "https://" not in summary_html
    assert "Opportunity" in field_html
    assert "Lifecycle and Production" in field_html
    assert "Infrastructure" in field_html
    assert "Operator and Lease Context" in field_html
    assert "Evidence and Provenance" in field_html
    assert "Limitations" in field_html
    assert "Review &lt;infill&gt;" in field_html
    assert "Operator &amp; Co" in field_html
    assert "../../../reports/field_atlas/fields/05-00870500-aguila-vado.html" in field_html
    assert "http://" not in field_html
    assert "https://" not in field_html


def test_summary_renders_source_path_as_text_when_roots_diverge() -> None:
    quality = FieldArchitectureDossierQuality(
        row_count=1,
        blocking_source_gaps=(),
        informational_source_gaps=(),
        architecture_class_counts={"high_access_infill_redevelopment": 1},
        selection_reason_counts={"top_ranked": 1},
        caveat_counts={"source_link_not_relative_to_output_root": 1},
        quality_flag_counts={},
        limitation_count=1,
    )
    index = pd.DataFrame(
        [
            {
                "dossier_rank": 1,
                "field_name": "Aguila Vado",
                "architecture_signal_class": "high_access_infill_redevelopment",
                "opportunity_score": 74.79,
                "dossier_path": "fields/aguila-dossier.html",
                "source_field_atlas_report_path": "reports/field_atlas/fields/source.html",
                "source_caveats": "source_link_not_relative_to_output_root",
            }
        ]
    )

    summary_html = render_field_architecture_dossier_summary_html(index, quality)

    assert "reports/field_atlas/fields/source.html" in summary_html
    assert "../../reports/field_atlas/fields/source.html" not in summary_html


def test_renders_source_path_as_text_when_no_safe_relative_href() -> None:
    page = FieldArchitectureDossierPage(
        district="05",
        field_number="00870500",
        field_name="Aguila Vado",
        field_slug="aguila-vado",
        dossier_filename="05-00870500-aguila-vado-dossier.html",
        dossier_path="fields/05-00870500-aguila-vado-dossier.html",
        source_field_atlas_report_path="reports/field_atlas/fields/source.html",
        source_field_atlas_href=None,
        summary={},
        source_caveats=("source_link_not_relative_to_output_root",),
        quality_flags=(),
        limitations=("no reserves conclusions",),
    )

    field_html = render_field_architecture_dossier_html(page)

    assert "reports/field_atlas/fields/source.html" in field_html
    assert "<a href=" not in field_html
    assert "source_link_not_relative_to_output_root" in field_html
