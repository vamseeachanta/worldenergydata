"""Tests for hull dimension estimator."""

from __future__ import annotations

import pandas as pd
import pytest

from worldenergydata.vessel_hull_models.rig_hulls.hull_estimator import (
    HullEstimate,
    estimate_hull,
    populate_estimated_dimensions,
)


class TestEstimateHull:
    def test_drillship_generic(self):
        est = estimate_hull("drillship")
        assert est is not None
        assert est.loa_m == 228.0
        assert est.beam_m == 42.0
        assert est.confidence == "generic"

    def test_semi_sub_generic(self):
        est = estimate_hull("semi_sub")
        assert est is not None
        assert est.loa_m == 104.0
        assert est.beam_m == 78.0

    def test_jackup_generic(self):
        est = estimate_hull("jackup")
        assert est is not None
        assert est.loa_m == 70.0

    def test_barge_generic(self):
        est = estimate_hull("barge")
        assert est is not None
        assert est.loa_m == 90.0

    def test_unknown_type_returns_none(self):
        assert estimate_hull("unknown_type") is None

    def test_none_returns_none(self):
        assert estimate_hull(None) is None

    def test_drillship_shallow_water(self):
        est = estimate_hull("drillship", water_depth_ft=4000.0)
        assert est is not None
        assert est.loa_m == 190.0  # smaller vessel for shallower water
        assert est.confidence == "estimated"

    def test_drillship_deep_water(self):
        est = estimate_hull("drillship", water_depth_ft=10000.0)
        assert est is not None
        assert est.loa_m == 238.0

    def test_semi_sub_shallow(self):
        est = estimate_hull("semi_sub", water_depth_ft=2000.0)
        assert est is not None
        assert est.loa_m == 85.0
        assert est.confidence == "estimated"

    def test_semi_sub_deep(self):
        est = estimate_hull("semi_sub", water_depth_ft=10000.0)
        assert est is not None
        assert est.loa_m == 120.0

    def test_jackup_ignores_water_depth(self):
        est = estimate_hull("jackup", water_depth_ft=500.0)
        assert est is not None
        assert est.loa_m == 70.0  # generic, no depth refinement
        assert est.confidence == "generic"


class TestPopulateEstimatedDimensions:
    def test_fills_missing_dimensions(self):
        df = pd.DataFrame({
            "HULL_FORM_TYPE": ["drillship"],
            "LOA_M": [None],
            "BEAM_M": [None],
            "DRAFT_M": [None],
        })
        result = populate_estimated_dimensions(df)
        assert result["LOA_M"].iloc[0] == 228.0
        assert result["BEAM_M"].iloc[0] == 42.0
        assert result["DRAFT_M"].iloc[0] == 12.0
        assert result["DIMENSION_CONFIDENCE"].iloc[0] == "generic"

    def test_preserves_measured_dimensions(self):
        df = pd.DataFrame({
            "HULL_FORM_TYPE": ["drillship"],
            "LOA_M": [250.0],
            "BEAM_M": [45.0],
            "DRAFT_M": [13.0],
        })
        result = populate_estimated_dimensions(df)
        assert result["LOA_M"].iloc[0] == 250.0
        assert result["DIMENSION_CONFIDENCE"].iloc[0] == "measured"

    def test_uses_water_depth_for_refinement(self):
        df = pd.DataFrame({
            "HULL_FORM_TYPE": ["drillship"],
            "LOA_M": [None],
            "BEAM_M": [None],
            "DRAFT_M": [None],
            "WATER_DEPTH_RATING_FT": [4000.0],
        })
        result = populate_estimated_dimensions(df)
        assert result["LOA_M"].iloc[0] == 190.0  # shallow-water estimate
        assert result["DIMENSION_CONFIDENCE"].iloc[0] == "estimated"

    def test_no_hull_form_no_estimate(self):
        df = pd.DataFrame({
            "HULL_FORM_TYPE": [None],
            "LOA_M": [None],
            "BEAM_M": [None],
            "DRAFT_M": [None],
        })
        result = populate_estimated_dimensions(df)
        assert pd.isna(result["LOA_M"].iloc[0])

    def test_does_not_modify_input(self):
        df = pd.DataFrame({
            "HULL_FORM_TYPE": ["drillship"],
            "LOA_M": [None],
            "BEAM_M": [None],
            "DRAFT_M": [None],
        })
        populate_estimated_dimensions(df)
        assert pd.isna(df["LOA_M"].iloc[0])
