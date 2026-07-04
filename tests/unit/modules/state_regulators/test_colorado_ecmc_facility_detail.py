"""Tests for Colorado ECMC FacilityDetail/Form 5A source discovery (#749)."""

from pathlib import Path

import pandas as pd

from worldenergydata.modules.state_regulators.colorado_ecmc.facility_detail import (
    classify_facility_detail_pressures,
    parse_facility_detail_html,
)


FIXTURE = (
    Path(__file__).parents[3]
    / "fixtures"
    / "colorado_ecmc"
    / "facility_detail_12339345_excerpt.html"
)
SOURCE_URL = (
    "https://ecmc.state.co.us/cogisdb/Facility/FacilityDetail.aspx?api=12339345"
)


def test_parse_facility_detail_html_extracts_initial_test_rows():
    rows = parse_facility_detail_html(
        FIXTURE.read_text(encoding="utf-8"), source_url=SOURCE_URL
    )

    assert set(rows["test_type"]) == {
        "BBLS_H2O",
        "BBLS_OIL",
        "BTU_GAS",
        "CALC_MCF_GAS",
        "CASING_PRESS",
        "MCF_GAS",
        "TUBING_PRESS",
    }
    casing = rows.set_index("test_type").loc["CASING_PRESS"]
    tubing = rows.set_index("test_type").loc["TUBING_PRESS"]

    assert casing["api10"] == "0512339345"
    assert casing["api_fragment"] == "12339345"
    assert casing["facility_id"] == "436953"
    assert casing["field"] == "WATTENBERG"
    assert casing["formation_code"] == "NBRR"
    assert casing["formation"] == "NIOBRARA"
    assert casing["interval_top_ft"] == 7397
    assert casing["interval_bottom_ft"] == 14700
    assert casing["measured_td_ft"] == 14829
    assert casing["vertical_td_ft"] == 7041
    assert casing["first_production_date"] == pd.Timestamp("2017-05-16")
    assert casing["test_date"] == pd.Timestamp("2017-05-19")
    assert casing["test_method"] == "Flowing"
    assert casing["hours_tested"] == 24
    assert casing["gas_type"] == "WET"
    assert casing["measure_value"] == 1700
    assert casing["source_section"] == "initial_test_data"
    assert casing["source_url"] == SOURCE_URL
    assert tubing["measure_value"] == 1300


def test_classify_facility_detail_pressures_keeps_only_initial_test_candidates():
    raw = pd.DataFrame(
        [
            {
                "source_section": "initial_test_data",
                "test_type": "CASING_PRESS",
                "measure_value": 1700,
            },
            {
                "source_section": "initial_test_data",
                "test_type": "TUBING_PRESS",
                "measure_value": 1300,
            },
            {
                "source_section": "formation_treatment",
                "test_type": "MAX_TREATMENT_PRESS",
                "measure_value": 8871,
            },
            {
                "source_section": "mit_form_21",
                "test_type": "CASING_PRESS",
                "measure_value": 500,
            },
            {
                "source_section": "initial_test_data",
                "test_type": "MCF_GAS",
                "measure_value": 418,
            },
        ]
    )

    classified = classify_facility_detail_pressures(raw)
    by_key = classified.set_index(["source_section", "test_type"])

    casing = by_key.loc[("initial_test_data", "CASING_PRESS")]
    tubing = by_key.loc[("initial_test_data", "TUBING_PRESS")]
    treatment = by_key.loc[("formation_treatment", "MAX_TREATMENT_PRESS")]
    mit = by_key.loc[("mit_form_21", "CASING_PRESS")]
    gas_rate = by_key.loc[("initial_test_data", "MCF_GAS")]

    assert casing["pressure_role"] == "candidate_pressure_observation"
    assert casing["pressure_kind"] == "WHP_casing_initial_test"
    assert casing["underpressured_screen_eligible"] is False
    assert tubing["pressure_kind"] == "WHP_flowing_tubing_initial_test"
    assert treatment["pressure_role"] == "excluded_engineering_pressure"
    assert treatment["exclude_reason"] == "formation_treatment_pressure"
    assert mit["pressure_role"] == "excluded_integrity_pressure"
    assert mit["exclude_reason"] == "mechanical_integrity_pressure"
    assert gas_rate["pressure_role"] == "test_rate_or_property"
