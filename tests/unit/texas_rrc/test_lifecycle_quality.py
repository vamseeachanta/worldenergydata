"""Tests for Texas RRC lifecycle spine quality checks."""

import pandas as pd

from worldenergydata.texas_rrc.lifecycle.quality import assess_lifecycle_quality


def test_assess_lifecycle_quality_counts_core_gap_classes():
    spine = pd.DataFrame(
        [
            {
                "api14": "42001000010000",
                "field_number": "",
                "lease_number": None,
                "operator_number": "",
                "latitude": "40.0",
                "longitude": "-97.2",
                "permit_issued_date": "2024-02-15",
                "spud_date": "2024-02-01",
                "completion_date": "2024-04-01",
                "plug_date": "2024-03-01",
                "has_wellbore": False,
                "has_permit": True,
                "has_completion": True,
                "quality_flags": "",
            },
            {
                "api14": "42001000010000",
                "field_number": "11111",
                "lease_number": "22222",
                "operator_number": "333333",
                "latitude": "31.5",
                "longitude": "-97.2",
                "permit_issued_date": "2024-01-15",
                "spud_date": "2024-02-01",
                "completion_date": "",
                "plug_date": "",
                "has_wellbore": True,
                "has_permit": False,
                "has_completion": False,
                "quality_flags": "",
            },
        ]
    )

    report = assess_lifecycle_quality(spine, source_gaps=("directional_surveys",))

    assert report.row_count == 2
    assert report.duplicate_api14 == 1
    assert report.missing_field_id == 1
    assert report.missing_lease_id == 1
    assert report.missing_operator_id == 1
    assert report.invalid_coordinates == 1
    assert report.impossible_dates == 1
    assert report.permit_without_wellbore == 1
    assert report.completion_without_wellbore == 1
    assert report.wellbore_without_completion == 1
    assert report.source_gaps == ("directional_surveys",)
    assert "missing_field_id" in spine.loc[0, "quality_flags"]
    assert "wellbore_without_completion" in spine.loc[1, "quality_flags"]
