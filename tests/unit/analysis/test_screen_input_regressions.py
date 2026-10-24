"""Screen-input validity, with a direct pressure/depth hand calculation."""

import math

import pandas as pd
import pytest

from worldenergydata.analysis.underpressured_screen.screen import (
    classify_tiers,
    earliest_per_well,
    estimate_bhp,
)


@pytest.mark.parametrize("column", ["reference_depth_ft", "pressure_psia"])
@pytest.mark.parametrize("bad", [math.inf, -math.inf, math.nan, 0, -1])
@pytest.mark.parametrize("kind", ["BHP_measured", "WHP_shut_in"])
def test_nonfinite_or_nonpositive_input_not_evaluated(column, bad, kind):
    row = {
        "reference_depth_ft": 5000,
        "pressure_psia": 1200,
        "pressure_kind": kind,
        "well_key": "synthetic",
        "test_year": 2020,
    }
    row[column] = bad
    settings = {"gas_sg": 0.65, "z_avg": 0.95, "t_avg_rankine": 520}
    result = estimate_bhp(pd.DataFrame([row]), settings)
    result = classify_tiers(
        result,
        {
            "hydrostatic_normal_min": 0.433,
            "mild_underpressure_min": 0.35,
            "near_vacuum_whp_psia": 50,
        },
    )
    assert math.isnan(result.bhp_gradient_psi_ft.iloc[0])
    assert result.screen_status.iloc[0] == "NOT_EVALUATED"
    assert result.pressure_tier.iloc[0] == "NOT_EVALUATED"
    assert result.screen_status.iloc[0] == "NOT_EVALUATED"
    assert math.isnan(result.bhp_gradient_psi_ft.iloc[0])
    assert not result.near_vacuum.iloc[0]
    assert result.screen_reason.iloc[0]
    assert earliest_per_well(result).empty


def test_normal_pressure_depth_hand_calculation():
    """Pack C06 definition: measured gradient = pressure/depth, in psi/ft.

    Synthetic measured BHP=1200 psia, TVD=5000 ft gives 1200/5000=.24
    psi/ft. No gas correction or model-generated expectation is used.
    """
    obs = pd.DataFrame(
        [
            {
                "reference_depth_ft": 5000,
                "pressure_psia": 1200,
                "pressure_kind": "BHP_measured",
            }
        ]
    )
    result = estimate_bhp(obs, {"gas_sg": 0.65, "z_avg": 0.95, "t_avg_rankine": 520})
    assert result.bhp_gradient_psi_ft.iloc[0] == pytest.approx(0.24)
    assert result.screen_status.iloc[0] == "EVALUATED"


@pytest.mark.parametrize("gradient", [math.inf, -math.inf, math.nan, 0, -1])
def test_direct_classification_refuses_invalid_gradient(gradient):
    frame = pd.DataFrame(
        [
            {
                "bhp_gradient_psi_ft": gradient,
                "pressure_kind": "WHP_shut_in",
                "pressure_psia": 30,
            }
        ]
    )
    result = classify_tiers(
        frame,
        {
            "hydrostatic_normal_min": 0.433,
            "mild_underpressure_min": 0.35,
            "near_vacuum_whp_psia": 50,
        },
    )
    assert result.pressure_tier.iloc[0] == "NOT_EVALUATED"
    assert result.screen_status.iloc[0] == "NOT_EVALUATED"
    assert math.isnan(result.bhp_gradient_psi_ft.iloc[0])
    assert not result.near_vacuum.iloc[0]


def test_overflow_in_bhp_estimate_not_evaluated():
    """A finite depth can still overflow the gas-column exponential."""
    obs = pd.DataFrame(
        [
            {
                "reference_depth_ft": 1e100,
                "pressure_psia": 1200,
                "pressure_kind": "WHP_shut_in",
            }
        ]
    )
    result = estimate_bhp(obs, {"gas_sg": 0.65, "z_avg": 0.95, "t_avg_rankine": 520})
    assert result.screen_status.iloc[0] == "NOT_EVALUATED"
    assert math.isnan(result.bhp_gradient_psi_ft.iloc[0])


@pytest.mark.parametrize("depth_dtype", ["Float64", "Int64"])
@pytest.mark.parametrize("kind", ["BHP_measured", "WHP_shut_in"])
def test_nullable_depth_pipeline_retains_valid_row(depth_dtype, kind):
    observations = pd.DataFrame(
        {
            "reference_depth_ft": pd.array([5000, 5000], dtype=depth_dtype),
            "pressure_psia": [1200, math.nan],
            "pressure_kind": [kind, kind],
            "well_key": ["valid", "invalid"],
            "test_year": [2020, 2020],
        },
        index=[7, 3],
    )
    original = observations.copy(deep=True)
    estimated = estimate_bhp(
        observations, {"gas_sg": 0.65, "z_avg": 0.95, "t_avg_rankine": 520}
    )
    result = classify_tiers(
        estimated,
        {
            "hydrostatic_normal_min": 0.433,
            "mild_underpressure_min": 0.35,
            "near_vacuum_whp_psia": 50,
        },
    )
    assert result.index.tolist() == [7, 3]
    assert result.screen_status.tolist() == ["EVALUATED", "NOT_EVALUATED"]
    assert result.pressure_tier.tolist() == ["severely_underpressured", "NOT_EVALUATED"]
    assert math.isfinite(result.bhp_gradient_psi_ft.loc[7])
    assert pd.isna(result.bhp_gradient_psi_ft.loc[3])
    assert result.screen_reason.loc[3]
    assert result.near_vacuum.tolist() == [False, False]
    assert earliest_per_well(result).well_key.tolist() == ["valid"]
    pd.testing.assert_frame_equal(observations, original)


@pytest.mark.parametrize("gradient_dtype", ["Float64", "Float32"])
def test_direct_nullable_gradients_classify_valid_tiers(gradient_dtype):
    frame = pd.DataFrame(
        {
            "bhp_gradient_psi_ft": pd.array(
                [0.5, 0.4, 0.24, pd.NA, math.inf, -1, 0], dtype=gradient_dtype
            ),
            "pressure_kind": "WHP_shut_in",
            "pressure_psia": 30,
        }
    )
    original = frame.copy(deep=True)
    result = classify_tiers(
        frame,
        {
            "hydrostatic_normal_min": 0.433,
            "mild_underpressure_min": 0.35,
            "near_vacuum_whp_psia": 50,
        },
    )
    expected_tiers = [
        "normal",
        "mildly_underpressured",
        "severely_underpressured",
    ] + ["NOT_EVALUATED"] * 4
    assert result.pressure_tier.tolist() == expected_tiers
    assert result.screen_status.tolist() == ["EVALUATED"] * 3 + ["NOT_EVALUATED"] * 4
    assert result.bhp_gradient_psi_ft.iloc[3:].isna().all()
    assert result.screen_reason.iloc[3:].ne("").all()
    assert result.near_vacuum.tolist() == [True] * 3 + [False] * 4
    pd.testing.assert_frame_equal(frame, original)
