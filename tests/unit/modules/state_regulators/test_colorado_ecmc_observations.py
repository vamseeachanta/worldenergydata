"""Tests for Colorado ECMC curated pressure observations (#745)."""

import pandas as pd
import pytest

from worldenergydata.modules.state_regulators.colorado_ecmc.parsers import (
    build_pressure_observations,
    build_quality_stats,
)

SETTINGS = {
    "atmospheric_psi": 14.7,
    "test_type": "ECMC Form 7 monthly production report",
    "gradient_method": "production_wellhead_pressure_over_wells_tvd_screening_only",
    "pressure_priority": ["GasPressureTubing", "GasPressureCasing"],
    "min_test_year": 1999,
    "max_test_year": 2026,
}


def test_build_pressure_observations_maps_gas_pressures_and_adds_atmosphere():
    production = _production_rows(
        [
            {
                "api12": "051233249800",
                "api10": "0512332498",
                "facility_id": "420193",
                "report_year": 2025,
                "report_month": 1,
                "test_date": "2025-01-31",
                "well_name": "WATTENBERG TEST",
                "formation_code": "J SAND",
                "gas_pressure_tubing_psig": 85,
                "gas_pressure_casing_psig": 120,
            }
        ]
    )
    wells = _wells()

    observations = build_pressure_observations(production, wells, SETTINGS)

    assert list(observations["pressure_kind"]) == [
        "WHP_flowing_tubing",
        "WHP_casing",
    ]
    assert list(observations["pressure_psig_reported"]) == [85, 120]
    assert list(observations["pressure_psia"]) == [
        pytest.approx(99.7),
        pytest.approx(134.7),
    ]
    assert set(observations["state"]) == {"CO"}
    assert set(observations["field"]) == {"WATTENBERG"}
    assert set(observations["reference_depth_ft"]) == {7994}
    assert set(observations["reference_depth_source"]) == {"Max_TVD"}


def test_water_pressure_columns_are_counted_but_excluded_from_curated_screen_rows():
    production = _production_rows(
        [
            {
                "api12": "051233249800",
                "api10": "0512332498",
                "facility_id": "420193",
                "report_year": 2025,
                "report_month": 1,
                "test_date": "2025-01-31",
                "water_pressure_tubing_psig": 55,
                "water_pressure_casing_psig": 65,
            }
        ]
    )
    wells = _wells()

    observations = build_pressure_observations(production, wells, SETTINGS)
    quality = build_quality_stats(production, wells, observations, SETTINGS)

    assert observations.empty
    assert quality["water_pressure_candidate_count"] == 2
    assert quality["gas_pressure_candidate_count"] == 0
    assert quality["curated_count"] == 0
    assert quality["source_warnings"] == []


def test_quality_warns_when_configured_sources_have_no_positive_pressure_values():
    production = _production_rows(
        [
            {
                "api12": "051233249800",
                "api10": "0512332498",
                "facility_id": "420193",
                "report_year": 2025,
                "report_month": 1,
                "test_date": "2025-01-31",
            }
        ]
    )
    wells = _wells()

    observations = build_pressure_observations(production, wells, SETTINGS)
    quality = build_quality_stats(production, wells, observations, SETTINGS)

    assert observations.empty
    assert quality["source_warnings"] == [
        "no_positive_pressure_values:GasPressureTubing,GasPressureCasing,"
        "WaterPressureTubing,WaterPressureCasing"
    ]


def test_reference_depth_prefers_tvd_then_md_and_requires_positive_depth():
    production = _production_rows(
        [
            {
                "api12": "051233249800",
                "api10": "0512332498",
                "facility_id": "420193",
                "report_year": 2025,
                "report_month": 1,
                "test_date": "2025-01-31",
                "gas_pressure_tubing_psig": 85,
            },
            {
                "api12": "051233249801",
                "api10": "0512332498",
                "facility_id": "420194",
                "report_year": 2025,
                "report_month": 1,
                "test_date": "2025-01-31",
                "gas_pressure_tubing_psig": 90,
            },
            {
                "api12": "051233249802",
                "api10": "0512332498",
                "facility_id": "420195",
                "report_year": 2025,
                "report_month": 1,
                "test_date": "2025-01-31",
                "gas_pressure_tubing_psig": 95,
            },
        ]
    )
    wells = pd.DataFrame(
        [
            _well("051233249800", "420193", max_tvd_ft=7994, max_md_ft=8150),
            _well("051233249801", "420194", max_tvd_ft=None, max_md_ft=9100),
            _well("051233249802", "420195", max_tvd_ft=None, max_md_ft=None),
        ]
    )

    observations = build_pressure_observations(production, wells, SETTINGS)
    quality = build_quality_stats(production, wells, observations, SETTINGS)

    assert list(observations["well_key"]) == ["051233249800", "051233249801"]
    assert list(observations["reference_depth_ft"]) == [7994, 9100]
    assert list(observations["reference_depth_source"]) == ["Max_TVD", "Max_MD"]
    assert quality["filtered_missing_depth_count"] == 1


def test_facility_id_fallback_join_fills_wells_metadata_when_api_misses():
    production = _production_rows(
        [
            {
                "api12": "059990000000",
                "api10": "0599900000",
                "facility_id": "420193",
                "report_year": 2025,
                "report_month": 1,
                "test_date": "2025-01-31",
                "gas_pressure_tubing_psig": 85,
            }
        ]
    )
    wells = _wells()

    observations = build_pressure_observations(production, wells, SETTINGS)

    assert len(observations) == 1
    assert observations.loc[0, "field"] == "WATTENBERG"
    assert observations.loc[0, "reference_depth_ft"] == 7994
    assert observations.loc[0, "reference_depth_source"] == "Max_TVD"


def test_earliest_flags_use_report_date_then_pressure_priority():
    production = _production_rows(
        [
            {
                "api12": "051233249800",
                "api10": "0512332498",
                "facility_id": "420193",
                "report_year": 2025,
                "report_month": 2,
                "test_date": "2025-02-28",
                "gas_pressure_tubing_psig": 80,
            },
            {
                "api12": "051233249800",
                "api10": "0512332498",
                "facility_id": "420193",
                "report_year": 2025,
                "report_month": 1,
                "test_date": "2025-01-31",
                "gas_pressure_tubing_psig": 85,
                "gas_pressure_casing_psig": 120,
            },
        ]
    )
    wells = _wells()

    observations = build_pressure_observations(production, wells, SETTINGS)

    assert list(observations["pressure_kind"]) == [
        "WHP_flowing_tubing",
        "WHP_casing",
        "WHP_flowing_tubing",
    ]
    assert list(observations["is_earliest_observation"]) == [True, False, False]
    assert list(observations["screen_observation_priority"]) == [0, 1, 1]


def test_duplicate_annual_and_monthly_pressure_rows_are_dropped():
    production = _production_rows(
        [
            {
                "source_name": "production_2025",
                "doc_num": 42,
                "api12": "051233249800",
                "api10": "0512332498",
                "facility_id": "420193",
                "report_year": 2025,
                "report_month": 1,
                "test_date": "2025-01-31",
                "gas_pressure_tubing_psig": 85,
            },
            {
                "source_name": "production_monthly",
                "doc_num": 42,
                "api12": "051233249800",
                "api10": "0512332498",
                "facility_id": "420193",
                "report_year": 2025,
                "report_month": 1,
                "test_date": "2025-01-31",
                "gas_pressure_tubing_psig": 85,
            },
        ]
    )
    wells = _wells()

    observations = build_pressure_observations(production, wells, SETTINGS)
    quality = build_quality_stats(production, wells, observations, SETTINGS)

    assert len(observations) == 1
    assert quality["dropped_duplicate_pressure_observation_count"] == 1


def _production_rows(rows):
    defaults = {
        "source_name": "production_2025",
        "doc_num": 1,
        "api12": "051233249800",
        "api10": "0512332498",
        "facility_id": "420193",
        "report_year": 2025,
        "report_month": 1,
        "test_date": pd.Timestamp("2025-01-31"),
        "well_name": "WATTENBERG TEST",
        "formation_code": "J SAND",
        "gas_pressure_tubing_psig": None,
        "gas_pressure_casing_psig": None,
        "water_pressure_tubing_psig": None,
        "water_pressure_casing_psig": None,
        "gas_mcf": None,
        "days_produced": None,
    }
    return pd.DataFrame([{**defaults, **row} for row in rows])


def _well(api12, facility_id, max_tvd_ft=7994, max_md_ft=8150):
    return {
        "api12": api12,
        "api10": api12[:10],
        "facility_id": facility_id,
        "field": "WATTENBERG",
        "max_tvd_ft": max_tvd_ft,
        "max_md_ft": max_md_ft,
        "latitude": 40.123,
        "longitude": -104.456,
    }


def _wells():
    return pd.DataFrame([_well("051233249800", "420193")])
