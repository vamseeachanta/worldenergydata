"""Tests for Texas RRC pressure-observation quality summaries."""

from __future__ import annotations

import pandas as pd

from worldenergydata.texas_rrc.pressure_observations.quality import (
    build_pressure_coverage,
)


def test_coverage_groups_wells_by_district_and_decade_and_field() -> None:
    observations = pd.DataFrame(
        [
            {
                "api14": "42001000010000",
                "district": "08",
                "field_no": "12345678",
                "field_name": "SPRABERRY",
                "test_date": "2024-03-01",
            },
            {
                "api14": "42001000010000",
                "district": "08",
                "field_no": "12345678",
                "field_name": "SPRABERRY",
                "test_date": "2025-03-01",
            },
            {
                "api14": "42001000020000",
                "district": "7C",
                "field_no": "87654321",
                "field_name": "WOLFBONE",
                "test_year": 2018,
            },
        ]
    )

    coverage = build_pressure_coverage(observations)

    district_2020 = coverage.by_district_decade[
        coverage.by_district_decade["district"].eq("08")
    ].iloc[0]
    assert district_2020.to_dict() == {
        "district": "08",
        "test_decade": "2020s",
        "pressure_observation_well_count": 1,
        "pressure_observation_count": 2,
    }

    field_2010 = coverage.by_field_decade[
        coverage.by_field_decade["field_no"].eq("87654321")
    ].iloc[0]
    assert field_2010.to_dict() == {
        "district": "7C",
        "field_no": "87654321",
        "field_name": "WOLFBONE",
        "test_decade": "2010s",
        "pressure_observation_well_count": 1,
        "pressure_observation_count": 1,
    }
