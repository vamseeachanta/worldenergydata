"""Tests for Texas RRC field-architecture portfolio quality summaries."""

from __future__ import annotations

import pandas as pd

from worldenergydata.texas_rrc.architecture_portfolio.quality import (
    assess_field_architecture_portfolio_quality,
)


def test_assesses_portfolio_quality_counts_and_inherited_gaps() -> None:
    action_queue = pd.DataFrame(
        [
            {
                "portfolio_action": "data_completion_review",
                "development_theme": "Source/data completion before architecture interpretation",
                "source_caveats": "missing_context; lease_level_production",
                "quality_flags": "flag_b",
                "portfolio_limitations": "screening-only; no reserves",
            },
            {
                "portfolio_action": "infill_redevelopment_screen",
                "development_theme": "Infill, recompletion, redevelopment candidate review",
                "source_caveats": "lease_level_production",
                "quality_flags": "flag_a; flag_b",
                "portfolio_limitations": "screening-only; no reserves",
            },
        ]
    )

    quality = assess_field_architecture_portfolio_quality(
        action_queue,
        blocking_source_gaps=("missing_index",),
        informational_source_gaps=("water_bbl", "well_count"),
    )

    assert quality.row_count == 2
    assert quality.blocking_source_gaps == ("missing_index",)
    assert quality.informational_source_gaps == ("water_bbl", "well_count")
    assert quality.portfolio_action_counts == {
        "data_completion_review": 1,
        "infill_redevelopment_screen": 1,
    }
    assert quality.development_theme_counts == {
        "Infill, recompletion, redevelopment candidate review": 1,
        "Source/data completion before architecture interpretation": 1,
    }
    assert quality.caveat_counts == {
        "lease_level_production": 2,
        "missing_context": 1,
    }
    assert quality.quality_flag_counts == {"flag_b": 2, "flag_a": 1}
    assert quality.limitation_count == 2
