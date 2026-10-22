"""Application-matrix contracts, independent of hydraulic default assumptions."""

import pytest

from worldenergydata.well_bore_design.decision_framework import (
    APPLICATION_MATRIX,
    BoreTypeDecision,
)
from worldenergydata.well_bore_design.hydraulics import WellBoreHydraulics
from worldenergydata.well_bore_design.schemas import BoreType


@pytest.mark.parametrize(
    "well,depth,window,flow",
    [
        ("exploration", 10000, 0.8, 500),
        ("exploration", 3000, 1, 12000),
        ("exploration", 3000, 2, 20000),
        ("production", 8000, 2, 6000),
    ],
)
def test_selection_respects_all_matrix_envelopes(well, depth, window, flow):
    """Synthetic cases exercise stored matrix bounds, not design acceptance."""
    rec = BoreTypeDecision().recommend(well, depth, window, flow)
    row = APPLICATION_MATRIX[rec.recommended.value]
    inside = (
        well in row["well_types"]
        and row["depth_range_m"][0] <= depth <= row["depth_range_m"][1]
        and row["flow_range_bopd"][0] <= flow <= row["flow_range_bopd"][1]
    )
    assert inside or any("envelope" in c.lower() for c in rec.caveats)


def test_case_and_completion_separators_normalized():
    rec = BoreTypeDecision().recommend(
        " Exploration ", 3000, 0.8, 500, completion_type="Gravel Pack"
    )
    reference = BoreTypeDecision().recommend(
        "exploration", 3000, 0.8, 500, completion_type="gravel_pack"
    )
    assert rec == reference


@pytest.mark.parametrize("category", ["well_type", "completion_type"])
def test_unknown_category_has_explicit_caveat(category):
    args = {
        "well_type": "exploration",
        "total_depth_m": 3000,
        "pressure_window_ppg": 0.8,
        "target_flow_rate_bopd": 500,
        "completion_type": "simple",
    }
    args[category] = "unrecognised"
    rec = BoreTypeDecision().recommend(**args)
    assert any(category in c and "Unknown" in c for c in rec.caveats)
    assert rec.evaluation_status == "NOT_EVALUATED"


def test_missing_rheology_or_geometry_is_required():
    decision = BoreTypeDecision()
    with pytest.raises(TypeError):
        decision.pressure_window_check(BoreType.STANDARD, 10, 14, 9, 500, 8000)
    with pytest.raises(TypeError):
        WellBoreHydraulics().compare_bore_types(500, 10, 8000)
    with pytest.raises(TypeError):
        decision.pressure_window_check(
            BoreType.STANDARD,
            10,
            14,
            9,
            500,
            8000,
            plastic_viscosity_cp=20,
            yield_point_lbf_100ft2=15,
        )


def test_empty_geometries_refused():
    with pytest.raises(ValueError, match="geometry"):
        WellBoreHydraulics().compare_bore_types(500, 10, 8000, 20, 15, {})
