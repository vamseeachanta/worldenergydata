"""Tests for hull dimension estimator module."""

import pandas as pd
import pytest

from worldenergydata.vessel_hull_models.rig_hulls.hull_estimator import (
    HullEstimate,
    estimate_hull,
    populate_estimated_dimensions,
)

# ---------------------------------------------------------------------------
# HullEstimate dataclass
# ---------------------------------------------------------------------------


class TestHullEstimate:
    def test_defaults(self):
        e = HullEstimate()
        assert e.loa_m is None
        assert e.beam_m is None
        assert e.draft_m is None
        assert e.displacement_tonnes is None
        assert e.confidence == "generic"

    def test_frozen(self):
        e = HullEstimate(loa_m=228.0)
        with pytest.raises(AttributeError):
            e.loa_m = 300.0


# ---------------------------------------------------------------------------
# estimate_hull
# ---------------------------------------------------------------------------


class TestEstimateHull:
    def test_none_returns_none(self):
        assert estimate_hull(None) is None

    def test_empty_returns_none(self):
        assert estimate_hull("") is None

    def test_drillship_generic(self):
        e = estimate_hull("drillship")
        assert e is not None
        assert e.loa_m == 228.0
        assert e.confidence == "generic"

    def test_semi_sub_generic(self):
        e = estimate_hull("semi_sub")
        assert e is not None
        assert e.loa_m == 104.0

    def test_jackup_generic(self):
        e = estimate_hull("jackup")
        assert e is not None
        assert e.loa_m == 70.0

    def test_barge_generic(self):
        e = estimate_hull("barge")
        assert e is not None
        assert e.loa_m == 90.0

    def test_spar_generic(self):
        e = estimate_hull("spar")
        assert e is not None
        assert e.loa_m is None  # spar has no LOA
        assert e.draft_m == 198.0

    def test_unknown_form_returns_none(self):
        assert estimate_hull("catamaran") is None

    def test_case_insensitive(self):
        e = estimate_hull("  DRILLSHIP  ")
        assert e is not None
        assert e.loa_m == 228.0


class TestEstimateHullDepthRefined:
    def test_drillship_shallow(self):
        e = estimate_hull("drillship", water_depth_ft=4000)
        assert e.loa_m == 190.0
        assert e.confidence == "estimated"

    def test_drillship_mid(self):
        e = estimate_hull("drillship", water_depth_ft=6000)
        assert e.loa_m == 228.0
        assert e.confidence == "estimated"

    def test_drillship_deep(self):
        e = estimate_hull("drillship", water_depth_ft=10000)
        assert e.loa_m == 238.0
        assert e.confidence == "estimated"

    def test_drillship_ultra_deep_uses_last_bracket(self):
        e = estimate_hull("drillship", water_depth_ft=15000)
        assert e.loa_m == 238.0

    def test_semi_sub_shallow(self):
        e = estimate_hull("semi_sub", water_depth_ft=2000)
        assert e.loa_m == 85.0
        assert e.confidence == "estimated"

    def test_semi_sub_mid(self):
        e = estimate_hull("semi_sub", water_depth_ft=5000)
        assert e.loa_m == 104.0

    def test_semi_sub_deep(self):
        e = estimate_hull("semi_sub", water_depth_ft=10000)
        assert e.loa_m == 120.0

    def test_semi_sub_ultra_deep_uses_last_bracket(self):
        e = estimate_hull("semi_sub", water_depth_ft=15000)
        assert e.loa_m == 120.0

    def test_jackup_depth_ignored(self):
        # Jackup has no depth refinement, falls through to generic
        e = estimate_hull("jackup", water_depth_ft=300)
        assert e.loa_m == 70.0
        assert e.confidence == "generic"

    def test_zero_depth_uses_generic(self):
        e = estimate_hull("drillship", water_depth_ft=0)
        assert e.confidence == "generic"

    def test_negative_depth_uses_generic(self):
        e = estimate_hull("drillship", water_depth_ft=-100)
        assert e.confidence == "generic"


# ---------------------------------------------------------------------------
# populate_estimated_dimensions
# ---------------------------------------------------------------------------


class TestPopulateEstimatedDimensions:
    def test_fills_missing_dimensions(self):
        df = pd.DataFrame(
            {
                "HULL_FORM_TYPE": ["drillship"],
                "LOA_M": [None],
                "BEAM_M": [None],
                "DRAFT_M": [None],
            }
        )
        result = populate_estimated_dimensions(df)
        assert result["LOA_M"].iloc[0] == 228.0
        assert result["BEAM_M"].iloc[0] == 42.0
        assert result["DRAFT_M"].iloc[0] == 12.0
        assert result["DIMENSION_CONFIDENCE"].iloc[0] == "generic"

    def test_preserves_measured_dimensions(self):
        df = pd.DataFrame(
            {
                "HULL_FORM_TYPE": ["drillship"],
                "LOA_M": [250.0],
                "BEAM_M": [45.0],
                "DRAFT_M": [13.0],
            }
        )
        result = populate_estimated_dimensions(df)
        assert result["LOA_M"].iloc[0] == 250.0
        assert result["DIMENSION_CONFIDENCE"].iloc[0] == "measured"

    def test_partial_dimensions_not_overwritten(self):
        # Only fills rows where ALL of LOA_M, BEAM_M, DRAFT_M are missing
        df = pd.DataFrame(
            {
                "HULL_FORM_TYPE": ["drillship"],
                "LOA_M": [250.0],
                "BEAM_M": [None],
                "DRAFT_M": [None],
            }
        )
        result = populate_estimated_dimensions(df)
        # Has LOA_M, so not "missing all" — should not be filled
        assert pd.isna(result["BEAM_M"].iloc[0])

    def test_with_water_depth_column(self):
        df = pd.DataFrame(
            {
                "HULL_FORM_TYPE": ["drillship"],
                "LOA_M": [None],
                "BEAM_M": [None],
                "DRAFT_M": [None],
                "WATER_DEPTH_RATING_FT": [4000.0],
            }
        )
        result = populate_estimated_dimensions(df)
        assert result["LOA_M"].iloc[0] == 190.0  # shallow drillship
        assert result["DIMENSION_CONFIDENCE"].iloc[0] == "estimated"

    def test_unknown_hull_form_not_filled(self):
        df = pd.DataFrame(
            {
                "HULL_FORM_TYPE": ["catamaran"],
                "LOA_M": [None],
                "BEAM_M": [None],
                "DRAFT_M": [None],
            }
        )
        result = populate_estimated_dimensions(df)
        assert pd.isna(result["LOA_M"].iloc[0])

    def test_original_not_modified(self):
        df = pd.DataFrame(
            {
                "HULL_FORM_TYPE": ["drillship"],
                "LOA_M": [None],
                "BEAM_M": [None],
                "DRAFT_M": [None],
            }
        )
        populate_estimated_dimensions(df)
        assert pd.isna(df["LOA_M"].iloc[0])

    def test_displacement_filled_when_column_exists(self):
        df = pd.DataFrame(
            {
                "HULL_FORM_TYPE": ["drillship"],
                "LOA_M": [None],
                "BEAM_M": [None],
                "DRAFT_M": [None],
                "DISPLACEMENT_TONNES": [None],
            }
        )
        result = populate_estimated_dimensions(df)
        assert result["DISPLACEMENT_TONNES"].iloc[0] == 96000.0

    def test_sparse_input_missing_dimension_columns_does_not_crash(self):
        """Regression test for #408: vendor-only fusion input lacks LOA_M/BEAM_M/DRAFT_M.

        When ``fuse_and_deduplicate.py`` runs against ONLY vendor-spec-details
        parquet (no BSEE WAR enrichment), the input frame's schema does not
        include the three dimension columns. The function must add them as
        NA-filled columns and still produce estimates from HULL_FORM_TYPE.
        """
        df = pd.DataFrame(
            {
                "VESSEL_NAME": ["Noble BlackHawk", "West Capella"],
                "RIG_TYPE": ["drillship", "drillship"],
                "HULL_FORM_TYPE": ["drillship", "drillship"],
                "WATER_DEPTH_RATING_FT": [12000.0, 10000.0],
            }
        )
        result = populate_estimated_dimensions(df)
        # Columns added by the defensive guard
        assert "LOA_M" in result.columns
        assert "BEAM_M" in result.columns
        assert "DRAFT_M" in result.columns
        # Dimensions estimated for both rows (HULL_FORM_TYPE=drillship)
        assert result["LOA_M"].notna().all()
        assert result["BEAM_M"].notna().all()
        assert result["DRAFT_M"].notna().all()
        # Confidence column populated as estimated/generic, not measured
        assert result["DIMENSION_CONFIDENCE"].notna().all()
        assert "measured" not in result["DIMENSION_CONFIDENCE"].values
