"""Tests for Texas RRC field-opportunity HTML rendering."""

from __future__ import annotations

import pandas as pd

from worldenergydata.texas_rrc.opportunities.html import (
    render_field_opportunity_summary_html,
)
from worldenergydata.texas_rrc.opportunities.quality import (
    assess_field_opportunity_quality,
)


def test_html_is_self_contained_and_links_field_reports() -> None:
    rankings = _rankings()
    quality = assess_field_opportunity_quality(rankings, source_gaps=())

    html = render_field_opportunity_summary_html(rankings, quality)

    assert html.startswith("<!doctype html>")
    assert "Texas RRC Field Opportunity Ranking" in html
    assert "Alpha &amp; Beta Field" in html
    assert "fields/08-12345-alpha-field.html" in html
    assert "high_access_infill_redevelopment" in html
    assert "screening heuristic" in html
    assert "http://" not in html
    assert "https://" not in html
    assert "<script src=" not in html


def _rankings() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "opportunity_rank": 1,
                "district": "08",
                "field_number": "12345",
                "field_name": "Alpha & Beta Field",
                "report_path": "fields/08-12345-alpha-field.html",
                "opportunity_score": 91.2,
                "opportunity_class": "high_priority",
                "architecture_signal_class": "high_access_infill_redevelopment",
                "recommended_followup": "Review infill redevelopment candidates.",
                "cumulative_boe": 10000,
                "remaining_activity_score": 82.0,
                "infrastructure_access_class": "direct_access",
                "key_drivers": "high production scale",
                "source_caveats": "direct_rrc_metrics",
                "quality_flags": "",
            }
        ]
    )
