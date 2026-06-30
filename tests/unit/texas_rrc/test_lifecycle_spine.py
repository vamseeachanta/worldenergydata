"""Tests for Texas RRC lifecycle spine assembly."""

import pandas as pd

from worldenergydata.texas_rrc.lifecycle.sources import LifecycleInputFrames
from worldenergydata.texas_rrc.lifecycle.spine import build_lifecycle_spine


def test_build_lifecycle_spine_joins_sources_by_api14():
    inputs = LifecycleInputFrames(
        wellbores=pd.DataFrame(
            [
                {
                    "api_number": "4200100001",
                    "district": "08",
                    "field_number": "11111",
                    "field_name": "SPRABERRY",
                    "lease_number": "22222",
                    "operator_number": "333333",
                    "well_status": "A",
                    "well_type": "O",
                    "total_depth": "12000",
                }
            ]
        ),
        permits=pd.DataFrame(
            [
                {
                    "api_number": "420010000100",
                    "permit_number": "999001",
                    "field_number": "99999",
                    "permit_issued_date": "2024-01-15",
                    "spud_date": "2024-02-01",
                    "latitude": "31.5",
                    "longitude": "-97.2",
                }
            ]
        ),
        completions=pd.DataFrame(
            [
                {
                    "api_number": "42001000010102",
                    "completion_date": "2024-03-01",
                    "form_type": "W-2",
                    "field_number": "88888",
                    "lease_number": "77777",
                    "operator_number": "666666",
                }
            ]
        ),
        source_gaps=(),
    )

    spine = build_lifecycle_spine(inputs)

    assert len(spine) == 1
    row = spine.iloc[0]
    assert row["api14"] == "42001000010000"
    assert row["api10"] == "4200100001"
    assert row["field_number"] == "11111"
    assert row["lease_number"] == "22222"
    assert row["operator_number"] == "333333"
    assert row["permit_number"] == "999001"
    assert row["spud_date"] == "2024-02-01"
    assert row["completion_date"] == "2024-03-01"
    assert row["has_wellbore"] is True
    assert row["has_permit"] is True
    assert row["has_completion"] is True
    assert row["source_ids"] == "wellbore_query|drilling_permits|completion_data"
