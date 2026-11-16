"""Regressions for explicit missing/non-finite assessment inputs.

Source: issue 1295 and the repository's offline workflow CSV. These tests
establish input rejection, not independent qualification of either B31G formula.
"""

import math
import sys
from dataclasses import replace
from io import StringIO
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def workflow():
    from worldenergydata.pipeline_safety.workflow import PipelineSafetyWorkflow

    return PipelineSafetyWorkflow()


@pytest.fixture
def incident():
    """Use the shipped example as regression input, not a pressure benchmark."""
    root = Path(__file__).resolve().parents[3]
    return (
        pd.read_csv(root / "examples/workflows/pipeline-safety-ffs/defects.csv")
        .iloc[0]
        .to_dict()
    )


@pytest.mark.parametrize(
    "field",
    [
        "depth_pct_wall",
        "length_mm",
        "pipe_od_mm",
        "wall_thickness_mm",
        "smys_mpa",
        "maop_mpa",
    ],
)
@pytest.mark.parametrize("method", ["modified_b31g", "b31g"])
def test_blank_csv_numeric_cell_raises(workflow, incident, field, method):
    """A blank cell is missing evidence: no pressure or verdict is established.

    Expected rejection follows issue 1295's explicit fail-closed requirement;
    no computed pressure is used as the expected value.
    """
    incident[field] = ""
    csv = pd.DataFrame([incident]).to_csv(index=False)
    frame = pd.read_csv(StringIO(csv))
    with pytest.raises(ValueError, match=field):
        workflow.generate_report(frame, method=method)


@pytest.mark.parametrize(
    "field",
    [
        "depth_pct_wall",
        "length_mm",
        "pipe_od_mm",
        "wall_thickness_mm",
        "smys_mpa",
        "maop_mpa",
    ],
)
@pytest.mark.parametrize(
    "value",
    [
        None,
        pd.NA,
        pd.NaT,
        "",
        " ",
        "nan",
        "inf",
        "-inf",
        "invalid",
        math.nan,
        math.inf,
        -math.inf,
    ],
)
def test_explicit_invalid_numeric_input_raises(workflow, incident, field, value):
    """Issue 1295 requires missing/non-finite inputs to fail, not use defaults."""
    incident[field] = value
    with pytest.raises(ValueError, match=field):
        workflow.assess(incident)


@pytest.mark.parametrize(
    "field",
    [
        "depth_pct_wall",
        "length_mm",
        "pipe_od_mm",
        "wall_thickness_mm",
        "smys_mpa",
        "maop_mpa",
    ],
)
@pytest.mark.parametrize("value", [None, pd.NA, math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("method", ["modified_b31g", "b31g"])
def test_direct_defect_cannot_bypass_validation(
    workflow, incident, field, value, method
):
    """The issue 1295 rejection criterion also applies without characterization."""
    defect = replace(workflow.characterize(incident), **{field: value})
    with pytest.raises(ValueError, match=field):
        workflow.assess_ffs(defect, method=method)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, 0.0, -1.0])
@pytest.mark.parametrize("method", ["modified_b31g", "b31g"])
def test_invalid_safety_factor_raises(workflow, incident, value, method):
    """Hand calculation: P/0 is undefined and P/(-1) is negative for P > 0.

    Neither is a valid divisor for the existing safe-pressure definition;
    NaN/infinity are excluded by Python 3's math.isfinite definition.
    This establishes no engineering safety-factor magnitude.
    """
    defect = workflow.characterize(incident)
    with pytest.raises(ValueError, match="safety_factor"):
        workflow.assess_ffs(defect, method=method, safety_factor=value)


@pytest.mark.parametrize("method", ["modified_b31g", "b31g"])
def test_non_finite_calculated_pressure_cannot_produce_verdict(
    workflow, incident, method
):
    """Hand check: positive MPa / smallest positive float exceeds float range.

    Python 3 Library Reference, math.ulp defines ulp(0) as the smallest positive
    subnormal float. No engineering coefficient or pressure benchmark is used.
    """
    defect = workflow.characterize(incident)
    with pytest.raises(ValueError, match="safe_pressure_mpa"):
        workflow.assess_ffs(defect, method=method, safety_factor=math.ulp(0.0))


@pytest.mark.parametrize("method", ["modified_b31g", "b31g"])
def test_nonphysical_geometry_rejected_before_overflow(workflow, incident, method):
    """D=t leaves no pipe bore, so invalid geometry is rejected before pressure.

    The maximum finite float is supplied by Python 3's sys.float_info.max.
    No engineering pressure benchmark is used.
    """
    incident["pipe_od_mm"] = incident["wall_thickness_mm"]
    incident["smys_mpa"] = sys.float_info.max
    with pytest.raises(ValueError, match="wall_thickness_mm"):
        workflow.assess(incident, method=method)


@pytest.mark.parametrize(
    "field",
    [
        "depth_pct_wall",
        "length_mm",
        "pipe_od_mm",
        "wall_thickness_mm",
        "smys_mpa",
        "maop_mpa",
    ],
)
@pytest.mark.parametrize("method", ["modified_b31g", "b31g"])
def test_csv_router_rejects_batch_before_writing_outputs(
    incident, field, method, tmp_path
):
    """Issue 1295: an incomplete second record must not yield a partial report."""
    from worldenergydata.pipeline_safety.pipeline_safety import PipelineSafety

    invalid = dict(incident, **{field: ""})
    pd.DataFrame([incident, invalid]).to_csv(tmp_path / "defects.csv", index=False)
    outputs = tmp_path / "results"
    cfg = {
        "analysis": {"type": "ffs", "method": method},
        "data": {"source": "csv", "file": "defects.csv"},
        "Analysis": {
            "analysis_root_folder": str(tmp_path),
            "result_folder": str(outputs),
        },
    }
    with pytest.raises(ValueError, match=field):
        PipelineSafety().router(cfg)
    assert not list(outputs.glob("*"))
    assert "status" not in cfg["pipeline_safety"]


@pytest.mark.parametrize(
    "field",
    [
        "depth_pct_wall",
        "length_mm",
        "pipe_od_mm",
        "wall_thickness_mm",
        "smys_mpa",
        "maop_mpa",
    ],
)
def test_omitted_numeric_input_raises(workflow, incident, field):
    """Issue 1295: absence carries no measured geometry or operating pressure."""
    incident.pop(field)
    with pytest.raises(ValueError, match=field):
        workflow.assess(incident)


@pytest.mark.parametrize("blank_field", [None, "depth_pct_wall", "maop_mpa"])
def test_reviewer_complete_record_and_blank_cells(workflow, blank_field):
    """Issue 1294 review SF1: complete=repair; blank depth/MAOP must raise.

    Synthetic review inputs, not a published pressure benchmark. The complete
    case uses the historical 0.9*SMYS variant. ORNL (2019) eqs. 2, 10-11
    give z=400**2/(323.85*9.53)>50, M=0.032*z+3.3.
    With area=0.85*0.7=0.595, base=2*9.53/323.85*358.53*0.9,
    Pf=base*0.405/(1-0.595/M)=8.7400 MPa; Pf/1.39=6.2878 MPa.
    Thus safe<6.895<Pf, requiring repair under the pressure-screening policy.
    """
    complete = {
        "depth_pct_wall": 70,
        "length_mm": 400,
        "pipe_od_mm": 323.85,
        "wall_thickness_mm": 9.53,
        "smys_mpa": 358.53,
        "maop_mpa": 6.895,
    }
    if blank_field is None:
        result = workflow.assess(complete)
        assert result.verdict == "repair"
        assert result.failure_pressure_mpa == pytest.approx(8.7400, abs=0.0001)
        assert result.safe_pressure_mpa == pytest.approx(6.2878, abs=0.0001)
    else:
        blank = dict(complete, **{blank_field: ""})
        frame = pd.read_csv(StringIO(pd.DataFrame([blank]).to_csv(index=False)))
        with pytest.raises(ValueError, match=blank_field):
            workflow.generate_report(frame)
