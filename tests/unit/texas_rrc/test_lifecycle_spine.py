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

    assert sorted(spine["api14"].tolist()) == [
        "42001000010000",
        "42001000010102",
    ]
    base_row = spine.set_index("api14").loc["42001000010000"]
    assert base_row["api10"] == "4200100001"
    assert base_row["field_number"] == "11111"
    assert base_row["lease_number"] == "22222"
    assert base_row["operator_number"] == "333333"
    assert base_row["permit_number"] == "999001"
    assert base_row["spud_date"] == "2024-02-01"
    assert base_row["completion_date"] is None
    assert base_row["has_wellbore"] is True
    assert base_row["has_permit"] is True
    assert base_row["has_completion"] is False
    assert base_row["source_ids"] == "wellbore_query|drilling_permits"

    completion_row = spine.set_index("api14").loc["42001000010102"]
    assert completion_row["api10"] == "4200100001"
    assert completion_row["sidetrack_code"] == "01"
    assert completion_row["completion_code"] == "02"
    assert completion_row["field_number"] == "11111"
    assert completion_row["lease_number"] == "22222"
    assert completion_row["operator_number"] == "333333"
    assert completion_row["permit_number"] == "999001"
    assert completion_row["spud_date"] == "2024-02-01"
    assert completion_row["completion_date"] == "2024-03-01"
    assert completion_row["has_wellbore"] is True
    assert completion_row["has_permit"] is True
    assert completion_row["has_completion"] is True
    assert (
        completion_row["source_ids"]
        == "wellbore_query|drilling_permits|completion_data"
    )
