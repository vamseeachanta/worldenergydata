"""Tests for Texas RRC field-architecture dossier quality metadata."""

from __future__ import annotations

import pandas as pd

from worldenergydata.texas_rrc.dossiers.quality import (
    assess_field_architecture_dossier_quality,
)


def test_counts_pipe_delimited_caveats_without_splitting_limitation_prose() -> None:
    index = pd.DataFrame(
        [
            {
                "architecture_signal_class": "high_access_infill_redevelopment",
                "selection_reason": "top_ranked",
                "source_caveats": (
                    "lease_level_production|no_per_well_allocation;"
                    "rrc_gis_screening_only|dominant_county_pipeline_filter"
                ),
                "quality_flags": "screening_only|missing_well_gis",
                "dossier_limitations": (
                    "no economics, tariff, pipeline capacity, right-of-way, "
                    "route, or facility-design conclusions"
                ),
            }
        ]
    )

    quality = assess_field_architecture_dossier_quality(index)

    assert quality.caveat_counts == {
        "lease_level_production": 1,
        "no_per_well_allocation": 1,
        "rrc_gis_screening_only": 1,
        "dominant_county_pipeline_filter": 1,
    }
    assert quality.quality_flag_counts == {
        "screening_only": 1,
        "missing_well_gis": 1,
    }
    assert quality.limitation_count == 1
