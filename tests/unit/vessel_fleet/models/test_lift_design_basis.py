"""Synthetic schema tests; no engineering dataset or qualified design."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from worldenergydata.vessel_fleet.models.lift_design_basis import (
    LiftDesignBasis,
    blank_template,
    field_requirements,
)


def quantity(value, unit):
    return {
        "value": value,
        "unit": unit,
        "source": "Synthetic input; arithmetic test only",
    }


def complete_basis():
    data = blank_template()
    data["basis_reference"] = "Synthetic schema exercise"
    for section in ("environment", "motion", "string", "pump"):
        for name, requirement in field_requirements()[section].items():
            data[section][name] = quantity(1.0, requirement["unit"])
    data["string"]["inner_diameter_m"]["value"] = 0.5
    data["string"]["outer_diameter_m"]["value"] = 0.6
    data["string"]["length_m"]["value"] = 2.0
    data["pump"]["installation_depth_m"]["value"] = 0.5
    data["auxiliary_lines"] = []
    data["auxiliary_lines_reference"] = "Synthetic bare pipe assumption"
    for case in data["cases"]:
        case["source"] = "Synthetic case definition"
        case["environment_reference"] = "environment"
        case["motion_reference"] = "motion"
        for name, requirement in field_requirements()["case"].items():
            case[name] = quantity(1.0, requirement["unit"])
        for check in case["checks"]:
            check["criterion_reference"] = (
                "Synthetic criterion reference; not acceptance"
            )
    return data


def test_blank_template_is_unfilled_and_not_validated():
    data = blank_template()
    assert data["environment"]["water_depth_m"] is None
    with pytest.raises(ValidationError):
        LiftDesignBasis.model_validate(data)
    data["cases"][0]["checks"].clear()
    assert blank_template()["cases"][0]["checks"]


def test_complete_basis_and_units_metadata():
    basis = LiftDesignBasis.model_validate(complete_basis())
    # Independent geometry: 0.6 m OD - 0.5 m ID = 0.1 m diametral wall.
    assert (
        basis.string.outer_diameter_m.value - basis.string.inner_diameter_m.value
        == pytest.approx(0.1)
    )
    for section in field_requirements().values():
        for requirement in section.values():
            assert requirement["unit"] and requirement["source_requirement"]


@pytest.mark.parametrize("value", [-1, float("inf"), float("nan"), True, "1"])
def test_invalid_quantity_rejected(value):
    data = complete_basis()
    data["environment"]["water_depth_m"]["value"] = value
    with pytest.raises(ValidationError):
        LiftDesignBasis.model_validate(data)


@pytest.mark.parametrize(
    "mutation",
    ["unit", "source", "geometry", "depth", "case", "checks", "criterion", "extra"],
)
def test_invalid_basis_rejected(mutation):
    data = deepcopy(complete_basis())
    if mutation == "unit":
        data["environment"]["water_depth_m"]["unit"] = "ft"
    elif mutation == "source":
        data["pump"]["head_m"]["source"] = " "
    elif mutation == "geometry":
        data["string"]["inner_diameter_m"]["value"] = 0.7
    elif mutation == "depth":
        data["pump"]["installation_depth_m"]["value"] = 2.0
    elif mutation == "case":
        data["cases"] = data["cases"][:1]
    elif mutation == "checks":
        data["cases"][0]["checks"] = []
    elif mutation == "criterion":
        data["cases"][0]["checks"][0]["criterion_reference"] = " "
    elif mutation == "extra":
        data["pump"]["undocumented"] = 1
    with pytest.raises(ValidationError):
        LiftDesignBasis.model_validate(data)


def test_structural_metadata_and_auxiliary_validation():
    requirements = field_requirements(include_structural=True)
    assert requirements["basis"]["cases"]["unit"] == "1"
    assert requirements["quantity"]["source"]["source_requirement"]
    data = complete_basis()
    line = deepcopy(data["string"])
    line.update(function="instrument", attachment_reference="Synthetic attachment")
    data["auxiliary_lines"] = [line]
    LiftDesignBasis.model_validate(data)
    line["inner_diameter_m"]["value"] = 0.8
    with pytest.raises(ValidationError):
        LiftDesignBasis.model_validate(data)


@pytest.mark.parametrize("mutation", ["kind", "duplicate"])
def test_case_coverage_and_unique_names(mutation):
    data = complete_basis()
    if mutation == "kind":
        data["cases"][1]["kind"] = "operating"
    else:
        data["cases"][1]["name"] = "operating"
    with pytest.raises(ValidationError):
        LiftDesignBasis.model_validate(data)


@pytest.mark.parametrize("mutation", ["omitted", "duplicate"])
def test_case_required_check_coverage(mutation):
    data = complete_basis()
    checks = data["cases"][0]["checks"]
    if mutation == "omitted":
        checks.pop()
    else:
        checks.append(dict(checks[0]))
    with pytest.raises(ValidationError):
        LiftDesignBasis.model_validate(data)
