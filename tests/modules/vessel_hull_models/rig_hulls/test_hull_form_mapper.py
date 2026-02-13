"""Tests for hull form mapper."""

from __future__ import annotations

import pandas as pd
import pytest

from worldenergydata.vessel_hull_models.rig_hulls.hull_form_mapper import (
    map_hull_form,
    populate_hull_forms,
)


class TestMapHullForm:
    def test_drillship(self):
        assert map_hull_form("drillship") == "drillship"

    def test_semi_submersible(self):
        assert map_hull_form("semi_submersible") == "semi_sub"

    def test_jack_up(self):
        assert map_hull_form("jack_up") == "jackup"

    def test_inland_barge(self):
        assert map_hull_form("inland_barge") == "barge"

    def test_submersible(self):
        assert map_hull_form("submersible") == "semi_sub"

    def test_tender_assisted(self):
        assert map_hull_form("tender_assisted") == "semi_sub"

    def test_lift_boat(self):
        assert map_hull_form("lift_boat") == "jackup"

    def test_platform_rig_none(self):
        assert map_hull_form("platform_rig") is None

    def test_land_rig_none(self):
        assert map_hull_form("land_rig") is None

    def test_unknown_none(self):
        assert map_hull_form("unknown") is None

    def test_none_input(self):
        assert map_hull_form(None) is None

    def test_empty_string(self):
        assert map_hull_form("") is None

    def test_nan_string(self):
        assert map_hull_form("nan") is None

    def test_case_insensitive(self):
        assert map_hull_form("DRILLSHIP") == "drillship"
        assert map_hull_form("Semi_Submersible") == "semi_sub"


class TestPopulateHullForms:
    def test_fills_missing_hull_forms(self):
        df = pd.DataFrame({
            "RIG_TYPE": ["drillship", "semi_submersible", "jack_up"],
            "HULL_FORM_TYPE": [None, None, None],
        })
        result = populate_hull_forms(df)
        assert result["HULL_FORM_TYPE"].tolist() == ["drillship", "semi_sub", "jackup"]

    def test_preserves_existing_hull_forms(self):
        df = pd.DataFrame({
            "RIG_TYPE": ["drillship", "semi_submersible"],
            "HULL_FORM_TYPE": ["drillship", "semi_sub"],
        })
        result = populate_hull_forms(df)
        assert result["HULL_FORM_TYPE"].tolist() == ["drillship", "semi_sub"]

    def test_mixed_existing_and_missing(self):
        df = pd.DataFrame({
            "RIG_TYPE": ["drillship", "jack_up", "semi_submersible"],
            "HULL_FORM_TYPE": ["drillship", None, None],
        })
        result = populate_hull_forms(df)
        assert result["HULL_FORM_TYPE"].tolist() == ["drillship", "jackup", "semi_sub"]

    def test_non_vessel_types_remain_none(self):
        df = pd.DataFrame({
            "RIG_TYPE": ["platform_rig", "land_rig", "wireline_unit"],
            "HULL_FORM_TYPE": [None, None, None],
        })
        result = populate_hull_forms(df)
        assert result["HULL_FORM_TYPE"].isna().all()

    def test_creates_column_if_missing(self):
        df = pd.DataFrame({"RIG_TYPE": ["drillship"]})
        result = populate_hull_forms(df)
        assert "HULL_FORM_TYPE" in result.columns
        assert result["HULL_FORM_TYPE"].iloc[0] == "drillship"

    def test_no_rig_type_column_warns(self):
        df = pd.DataFrame({"VESSEL_NAME": ["TEST RIG"]})
        result = populate_hull_forms(df)
        assert "HULL_FORM_TYPE" in result.columns

    def test_does_not_modify_input(self):
        df = pd.DataFrame({
            "RIG_TYPE": ["drillship"],
            "HULL_FORM_TYPE": [None],
        })
        populate_hull_forms(df)
        assert df["HULL_FORM_TYPE"].iloc[0] is None


class TestHullLibraryRef:
    def test_ref_with_dimensions(self):
        df = pd.DataFrame({
            "RIG_TYPE": ["drillship"],
            "HULL_FORM_TYPE": [None],
            "LOA_M": [238.0],
        })
        result = populate_hull_forms(df)
        assert result["HULL_LIBRARY_REF"].iloc[0] == "drillship_240m"

    def test_ref_rounds_to_nearest_10(self):
        df = pd.DataFrame({
            "RIG_TYPE": ["semi_submersible"],
            "HULL_FORM_TYPE": [None],
            "LOA_M": [104.0],
        })
        result = populate_hull_forms(df)
        assert result["HULL_LIBRARY_REF"].iloc[0] == "semi_sub_100m"

    def test_ref_without_dimensions(self):
        df = pd.DataFrame({
            "RIG_TYPE": ["jack_up"],
            "HULL_FORM_TYPE": [None],
            "LOA_M": [None],
        })
        result = populate_hull_forms(df)
        assert result["HULL_LIBRARY_REF"].iloc[0] == "jackup_generic"

    def test_ref_non_vessel_is_none(self):
        df = pd.DataFrame({
            "RIG_TYPE": ["platform_rig"],
            "HULL_FORM_TYPE": [None],
            "LOA_M": [None],
        })
        result = populate_hull_forms(df)
        assert pd.isna(result["HULL_LIBRARY_REF"].iloc[0])

    def test_ref_preserves_existing(self):
        df = pd.DataFrame({
            "RIG_TYPE": ["drillship"],
            "HULL_FORM_TYPE": ["drillship"],
            "LOA_M": [238.0],
            "HULL_LIBRARY_REF": ["custom_ref"],
        })
        result = populate_hull_forms(df)
        assert result["HULL_LIBRARY_REF"].iloc[0] == "custom_ref"
