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
def test_overflowed_failure_pressure_cannot_produce_verdict(workflow, incident, method):
    """Hand check: with D=t, (2t/D)*maximum_float overflows before reduction.

    The maximum finite float is supplied by Python 3's sys.float_info.max.
    This synthetic overflow probe is not an engineering geometry or benchmark.
    """
    incident["pipe_od_mm"] = incident["wall_thickness_mm"]
    incident["smys_mpa"] = sys.float_info.max
    with pytest.raises(ValueError, match="failure_pressure_mpa"):
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
