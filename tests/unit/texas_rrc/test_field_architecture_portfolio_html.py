"""Tests for Texas RRC field-architecture portfolio HTML rendering."""

from __future__ import annotations

import pandas as pd

from worldenergydata.texas_rrc.architecture_portfolio.html import (
    render_field_architecture_portfolio_html,
)
from worldenergydata.texas_rrc.architecture_portfolio.quality import (
    FieldArchitecturePortfolioQuality,
)


def test_renders_self_contained_portfolio_html_with_safe_links() -> None:
    action_queue = pd.DataFrame(
        [
            {
                "portfolio_rank": 1,
                "field_name": "Aguila <Vado>",
                "district": "05",
                "field_number": "00870500",
                "architecture_signal_class": "high_access_infill_redevelopment",
                "portfolio_action": "infill_redevelopment_screen",
                "followup_priority": "high",
                "opportunity_score": 74.79,
                "recommended_followup": "Review <infill>",
                "source_dossier_href": (
                    "../field_architecture_dossiers/fields/aguila-dossier.html"
                ),
                "dossier_path": "fields/aguila-dossier.html",
                "source_caveats": "lease_level_production",
                "quality_flags": "screening_only",
                "portfolio_limitations": "no reserves conclusions",
            },
            {
                "portfolio_rank": 2,
                "field_name": "Southern Bay",
                "district": "03",
                "field_number": "84750500",
                "architecture_signal_class": "high_access_infill_redevelopment",
                "portfolio_action": "infill_redevelopment_screen",
                "followup_priority": "high",
                "opportunity_score": 50.0,
                "recommended_followup": "Review infill",
                "source_dossier_href": "https://example.invalid/dossier.html",
                "dossier_path": "fields/<unsafe>.html",
                "source_caveats": "source_dossier_link_not_relative_to_output_root",
                "quality_flags": "screening_only",
                "portfolio_limitations": "no reserves conclusions",
            },
        ]
    )
    class_summary = pd.DataFrame(
        [
            {
                "architecture_signal_class": "high_access_infill_redevelopment",
                "field_count": 1,
                "portfolio_action": "infill_redevelopment_screen",
                "development_theme": "Infill review",
                "mean_opportunity_score": 74.79,
                "direct_or_near_access_count": 1,
                "top_caveats": "lease_level_production",
                "top_quality_flags": "screening_only",
            }
        ]
    )
    followup_summary = pd.DataFrame(
        [
            {
                "recommended_followup": "Review <infill>",
                "portfolio_action": "infill_redevelopment_screen",
                "development_theme": "Infill review",
                "field_count": 1,
                "min_opportunity_score": 74.79,
                "max_opportunity_score": 74.79,
            }
        ]
    )
    quality = FieldArchitecturePortfolioQuality(
        row_count=2,
        blocking_source_gaps=("missing_context",),
        informational_source_gaps=("water_bbl",),
        portfolio_action_counts={"infill_redevelopment_screen": 1},
        development_theme_counts={"Infill review": 1},
        caveat_counts={"lease_level_production": 1},
        quality_flag_counts={"screening_only": 1},
        limitation_count=1,
    )

    html = render_field_architecture_portfolio_html(
        action_queue,
        class_summary,
        followup_summary,
        quality,
    )

    assert "Aguila &lt;Vado&gt;" in html
    assert "Review &lt;infill&gt;" in html
    assert "../field_architecture_dossiers/fields/aguila-dossier.html" in html
    assert 'href="https://example.invalid/dossier.html"' not in html
    assert "fields/&lt;unsafe&gt;.html" in html
    assert "missing_context" in html
    assert "water_bbl" in html
    assert "no reserves conclusions" in html
    assert "http://" not in html
    assert "https://" not in html
