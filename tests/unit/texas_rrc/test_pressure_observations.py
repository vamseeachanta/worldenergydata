"""Tests for building curated Texas RRC pressure observations."""

from __future__ import annotations

import pandas as pd

from worldenergydata.texas_rrc.pressure_observations.observations import (
    build_pressure_observations,
)


def _candidate(**overrides) -> dict[str, object]:
    row: dict[str, object] = {
        "api14": "42001000010000",
        "api10": "4200100001",
        "district": "08",
        "field_no": "12345678",
        "field_name": "SPRABERRY",
        "test_date": "2024-03-01",
        "test_year": 2024,
        "source_record_type": "G-1",
        "source_pressure_field": "BOTTOM_HOLE_PRESS",
        "pressure_raw_psi": 2500.0,
        "source_row_id": "fixture:1:BOTTOM_HOLE_PRESS",
        "source_file": "fixture.dat",
        "source_tracking_no": "123456",
        "source_packet_id": "654321",
        "source_form_id": "999",
        "source_row_no": "",
    }
    row.update(overrides)
    return row


def test_g1_bottom_hole_pressure_builds_reported_bhp_row():
    result = build_pressure_observations(pd.DataFrame([_candidate()]))

    row = result.observations.iloc[0].to_dict()
    assert row["pressure_kind"] == "BHP_measured"
    assert row["pressure_method"] == "source_reported_bottom_hole_pressure"
    assert row["pressure_psia"] == 2500.0
    assert row["pressure_unit_basis"] == "source_psi_unspecified"
    assert row["usable_for_virgin_pressure_proxy"] is False


def test_shut_in_surface_pressure_psig_converts_to_psia_with_limitation():
    result = build_pressure_observations(
        pd.DataFrame(
            [
                _candidate(
                    source_record_type="G-1 Field Data",
                    source_pressure_field="WELLHEAD_PRESS",
                    source_row_no="SHUT-IN",
                    pressure_raw_psi=100.0,
                    production_interval_from_ft=1000,
                    production_interval_to_ft=1200,
                )
            ]
        )
    )

    row = result.observations.iloc[0].to_dict()
    assert row["pressure_kind"] == "WHP_shut_in"
    assert row["pressure_psia"] == 114.7
    assert row["atmospheric_pressure_psi"] == 14.7
    assert row["pressure_unit_basis"] == "psig_assumed"
    assert "screening" in row["limitations"]


def test_g1_field_wellhead_pressure_without_shut_in_row_is_not_curated():
    result = build_pressure_observations(
        pd.DataFrame(
            [
                _candidate(
                    source_record_type="G-1 Field Data",
                    source_pressure_field="WELLHEAD_PRESS",
                    source_row_no="FLOWING",
                    pressure_raw_psi=100.0,
                    production_interval_from_ft=1000,
                    production_interval_to_ft=1200,
                )
            ]
        )
    )

    assert result.observations.empty
    assert result.quality["uncurated_pressure_candidates"] == 1


def test_g1_field_wellhead_pressure_with_blank_row_no_is_not_curated():
    result = build_pressure_observations(
        pd.DataFrame(
            [
                _candidate(
                    source_record_type="G-1 Field Data",
                    source_pressure_field="WELLHEAD_PRESS",
                    source_row_no="",
                    pressure_raw_psi=100.0,
                    production_interval_from_ft=1000,
                    production_interval_to_ft=1200,
                )
            ]
        )
    )

    assert result.observations.empty
    assert result.quality["uncurated_pressure_candidates"] == 1


def test_candidate_missing_api14_is_not_curated():
    result = build_pressure_observations(
        pd.DataFrame(
            [
                _candidate(
                    api14="",
                    api10="",
                    production_interval_from_ft=1000,
                    production_interval_to_ft=1200,
                )
            ]
        )
    )

    assert result.observations.empty
    assert result.quality["missing_api"] == 1


def test_w2_pressure_candidates_are_not_misclassified_as_bhp():
    result = build_pressure_observations(
        pd.DataFrame(
            [
                _candidate(
                    source_record_type="W-2",
                    source_pressure_field="CALC_CASING_PRESS",
                    pressure_raw_psi=500.0,
                )
            ]
        )
    )

    assert result.observations.empty
    assert result.quality["w2_pressure_candidates_not_curated"] == 1


def test_gradient_prefers_producing_interval_midpoint():
    result = build_pressure_observations(
        pd.DataFrame(
            [
                _candidate(
                    production_interval_from_ft=1000,
                    production_interval_to_ft=1200,
                )
            ]
        )
    )

    row = result.observations.iloc[0].to_dict()
    assert row["reference_depth_ft"] == 1100.0
    assert row["reference_depth_method"] == "production_interval_midpoint"
    assert row["gradient_psi_ft"] == 2500.0 / 1100.0
    assert row["gradient_method"] == "reported_bhp_over_reference_depth"


def test_gradient_suppressed_for_ambiguous_depth_join():
    wellbore = pd.DataFrame(
        [
            {"api14": "42001000010000", "total_depth": 9000},
            {"api14": "42001000010000", "total_depth": 9100},
        ]
    )

    result = build_pressure_observations(pd.DataFrame([_candidate()]), wellbore)

    row = result.observations.iloc[0].to_dict()
    assert pd.isna(row["reference_depth_ft"])
    assert pd.isna(row["gradient_psi_ft"])
    assert "ambiguous_depth_reference" in row["quality_flags"]


def test_earliest_usable_observation_is_virgin_proxy():
    result = build_pressure_observations(
        pd.DataFrame(
            [
                _candidate(
                    test_date="2024-03-01",
                    test_year=2024,
                    production_interval_from_ft=1000,
                    production_interval_to_ft=1200,
                ),
                _candidate(
                    test_date="2025-03-01",
                    test_year=2025,
                    source_row_id="fixture:2:BOTTOM_HOLE_PRESS",
                    production_interval_from_ft=1000,
                    production_interval_to_ft=1200,
                ),
            ]
        )
    )

    observations = result.observations.sort_values("test_date")
    assert observations.iloc[0]["is_earliest_observation_for_well"] is True
    assert observations.iloc[0]["virgin_pressure_proxy_method"] == (
        "earliest_reported_bhp"
    )
    assert observations.iloc[1]["is_earliest_observation_for_well"] is False
