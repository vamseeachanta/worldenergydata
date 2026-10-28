"""Reservoir measurement contract using synthetic identity examples.

The example below supplies TVDSS 1250.5 m below mean sea level, absolute pressure
2500.25 psia and temperature -40.5 degF; the expected JSON values are those same
literals, without conversion. Zero is the proposed nonnegative input boundary
described in data_dictionary.md, not a bound specified by issue #761; -0.5 is a
synthetic value just below it. NaN and signed infinities are rejection cases,
not engineering thresholds. No example represents a real reservoir.
"""

import json

import pytest
from pydantic import ValidationError

from worldenergydata.field_development.models import FieldConcept

MEASUREMENTS = (
    "reservoir_depth_tvd_m",
    "reservoir_pressure_psi",
    "reservoir_temperature_f",
)
SYNTHETIC_MEASUREMENTS = {
    "reservoir_depth_tvd_m": 1250.5,
    "reservoir_pressure_psi": 2500.25,
    "reservoir_temperature_f": -40.5,
}


@pytest.mark.parametrize(
    "payload", [{"name": "Synthetic"}, {"name": "Synthetic", "hpht": True}]
)
def test_old_inputs_leave_measurements_unavailable(payload):
    concept = FieldConcept(**payload)
    restored = FieldConcept.model_validate_json(json.dumps(payload))
    assert restored == concept
    for attribute in MEASUREMENTS:
        assert getattr(concept, attribute) is None
        assert concept.model_dump()[attribute] is None


def test_explicit_null_measurements_survive_json_roundtrip():
    values = dict.fromkeys(MEASUREMENTS)
    concept = FieldConcept(name="Synthetic", **values)
    assert FieldConcept.model_validate_json(concept.model_dump_json()) == concept
    assert {key: json.loads(concept.model_dump_json())[key] for key in values} == values


def test_supplied_measurements_survive_json_roundtrip_without_conversion():
    concept = FieldConcept(name="Synthetic", **SYNTHETIC_MEASUREMENTS)
    payload = json.loads(concept.model_dump_json())
    assert {key: payload[key] for key in MEASUREMENTS} == SYNTHETIC_MEASUREMENTS
    restored = FieldConcept.model_validate_json(concept.model_dump_json())
    assert restored == concept
    for attribute, expected in SYNTHETIC_MEASUREMENTS.items():
        assert getattr(restored, attribute) == expected
    assert concept.water_depth_m is None
    assert concept.hpht is None


@pytest.mark.parametrize("attribute", MEASUREMENTS)
def test_zero_is_valid_for_each_measurement(attribute):
    concept = FieldConcept(name="Synthetic", **{attribute: 0.0})
    restored = FieldConcept.model_validate_json(concept.model_dump_json())
    assert getattr(restored, attribute) == 0.0


@pytest.mark.parametrize("attribute", MEASUREMENTS)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("as_json", [False, True])
def test_nonfinite_measurements_are_rejected(attribute, value, as_json):
    payload = {"name": "Synthetic", attribute: value}
    with pytest.raises(ValidationError) as error:
        if as_json:
            # Exercise Pydantic's JSON parser with its accepted nonfinite tokens.
            FieldConcept.model_validate_json(json.dumps(payload))
        else:
            FieldConcept(**payload)
    assert [(item["loc"], item["type"]) for item in error.value.errors()] == [
        ((attribute,), "finite_number")
    ]


@pytest.mark.parametrize("attribute", MEASUREMENTS[:2])
@pytest.mark.parametrize("as_json", [False, True])
def test_negative_depth_and_pressure_are_rejected(attribute, as_json):
    payload = {"name": "Synthetic", attribute: -0.5}
    with pytest.raises(ValidationError) as error:
        if as_json:
            FieldConcept.model_validate_json(json.dumps(payload))
        else:
            FieldConcept(**payload)
    assert [(item["loc"], item["type"]) for item in error.value.errors()] == [
        ((attribute,), "greater_than_equal")
    ]


@pytest.mark.parametrize("hpht", [None, False, True])
def test_measurements_do_not_change_hpht(hpht):
    concept = FieldConcept(name="Synthetic", hpht=hpht, **SYNTHETIC_MEASUREMENTS)
    assert concept.hpht is hpht
    assert FieldConcept.model_validate_json(concept.model_dump_json()).hpht is hpht
