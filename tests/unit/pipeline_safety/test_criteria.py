"""Independent hand calculations using ORNL/TM-2019/1192 (May 2019).

Public source: https://www.osti.gov/servlets/purl/1855701, sections 2.1-2.4.
The report identifies the original basis as ASME B31G-1991 (reaffirmed 2004).
All geometries and strengths here are synthetic test inputs, not design limits.
"""

import math

import pytest

from worldenergydata.pipeline_safety.workflow import (
    _failure_pressure_b31g,
    _failure_pressure_modified_b31g,
)


@pytest.mark.parametrize("z", [1.0, 10.0, 20.0, 20.0001, 40.0, 100.0])
def test_original_hand_calculation(z):
    """ORNL eqs. 2, 5, 6, 8: D=200, t=10, SMYS=400, d/t=1/2.

    Base=2*10/200*1.1*400=44 MPa. For z<=20, loss area=1/3,
    so Pf=44*(2/3)/(1-1/(3*sqrt(1+0.8*z))). For z>20,
    rectangular long-flaw reduction=1/2, giving Pf=22 MPa.
    """
    expected = 44 * (2 / 3) / (1 - 1 / (3 * math.sqrt(1 + 0.8 * z))) if z <= 20 else 22
    actual = _failure_pressure_b31g(50, math.sqrt(z * 2000), 200, 10, 400)
    assert actual == pytest.approx(expected)


@pytest.mark.parametrize("z", [10.0, 50.0, 50.0001, 100.0])
def test_modified_variant_hand_calculation(z):
    """ORNL eqs. 2, 10-11 and section 2.1.2 give the shape and M.

    Synthetic D=200,t=10,SMYS=400,d/t=1/2. Historical variant flow=360,
    base=36 MPa, area=0.85/2=0.425, Pf=20.7/(1-0.425/M).
    The 0.9 flow multiplier is the repository pack revision 1, SF2 legacy
    choice, not the report's published modified flow stress (section 2.2.2).
    """
    bulge = math.sqrt(1 + 0.6275 * z - 0.003375 * z * z) if z <= 50 else 0.032 * z + 3.3
    expected = 20.7 / (1 - 0.425 / bulge)
    assert _failure_pressure_modified_b31g(
        50, math.sqrt(z * 2000), 200, 10, 400
    ) == pytest.approx(expected)


@pytest.mark.parametrize("z, ratio", [(40, 1.308), (100, 1.278)])
def test_review_ratios_against_confirmed_original(z, ratio):
    """Confirm SF2 ratios from sourced equations, independent of production M.

    ORNL sections 2.1.1, 2.2.1, 2.4.1: original long Pf=22 MPa for
    synthetic D=200,t=10,SMYS=400,d/t=1/2. The reviewed OLD branch used
    SMYS and modified M, so its pressure=40*(2/3)/(1-1/(3*M)).
    Dividing this by 22 gives 1.308 and 1.278, rounded to three decimals.
    """
    bulge = math.sqrt(1 + 0.6275 * z - 0.003375 * z * z) if z <= 50 else 0.032 * z + 3.3
    reviewed_pressure = 40 * (2 / 3) / (1 - 1 / (3 * bulge))
    assert reviewed_pressure / 22 == pytest.approx(ratio, abs=0.0005)
    assert _failure_pressure_b31g(
        50, math.sqrt(z * 2000), 200, 10, 400
    ) == pytest.approx(22)


@pytest.mark.parametrize("method", ["b31g", "modified_b31g"])
@pytest.mark.parametrize(
    "field, value",
    [
        ("depth_pct_wall", -1),
        ("depth_pct_wall", 80.1),
        ("depth_pct_wall", 100),
        ("length_mm", 0),
        ("length_mm", -1),
        ("pipe_od_mm", 0),
        ("wall_thickness_mm", 0),
        ("wall_thickness_mm", 1000),
        ("smys_mpa", 0),
        ("maop_mpa", 0),
    ],
)
def test_invalid_geometry_has_no_pressure_or_verdict(
    workflow_record, method, field, value
):
    """ORNL sections 2.1.1-2.1.2 restrict depth to 80%; dimensions need a bore.

    Invalid geometry must raise, never return a zero-pressure sentinel.
    """
    from worldenergydata.pipeline_safety.workflow import PipelineSafetyWorkflow

    with pytest.raises(ValueError, match=field):
        PipelineSafetyWorkflow().assess(dict(workflow_record, **{field: value}), method)


@pytest.fixture
def workflow_record():
    return {
        "depth_pct_wall": 50,
        "length_mm": 200,
        "pipe_od_mm": 200,
        "wall_thickness_mm": 10,
        "smys_mpa": 400,
        "maop_mpa": 10,
    }


def test_flow_stress_disclosed_in_report(workflow_record):
    import pandas as pd

    from worldenergydata.pipeline_safety.workflow import PipelineSafetyWorkflow

    report = PipelineSafetyWorkflow().generate_report(pd.DataFrame([workflow_record]))
    assert "0.9 * SMYS" in report.iloc[0]["notes"]
    assert "not published" in report.iloc[0]["notes"]
    assert report.iloc[0]["units"] == "mm, % wall, MPa"
    assert report.iloc[0]["remaining_life_years"] is None
