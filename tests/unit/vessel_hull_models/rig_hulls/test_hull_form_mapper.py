"""Tests for hull form mapper module."""

import pandas as pd
import pytest

from worldenergydata.vessel_hull_models.rig_hulls.hull_form_mapper import (
    map_hull_form,
    populate_hull_forms,
    refresh_hull_library_refs,
    _make_hull_library_ref,
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

    def test_submersible_maps_to_semi_sub(self):
        assert map_hull_form("submersible") == "semi_sub"

    def test_tender_assisted_maps_to_semi_sub(self):
        assert map_hull_form("tender_assisted") == "semi_sub"

    def test_lift_boat_maps_to_jackup(self):
        assert map_hull_form("lift_boat") == "jackup"

    def test_none_returns_none(self):
        assert map_hull_form(None) is None

    def test_empty_string_returns_none(self):
        assert map_hull_form("") is None

    def test_nan_string_returns_none(self):
        assert map_hull_form("nan") is None

    def test_platform_rig_returns_none(self):
        assert map_hull_form("platform_rig") is None

    def test_land_rig_returns_none(self):
        assert map_hull_form("land_rig") is None

    def test_unknown_returns_none(self):
        assert map_hull_form("unknown") is None

    def test_unmapped_type_returns_none(self):
        assert map_hull_form("some_new_type") is None

    def test_case_insensitive(self):
        assert map_hull_form("DRILLSHIP") == "drillship"


class TestMakeHullLibraryRef:
    def test_with_loa(self):
        row = pd.Series({"HULL_FORM_TYPE": "drillship", "LOA_M": 228})
        assert _make_hull_library_ref(row) == "drillship_230m"

    def test_without_loa(self):
        row = pd.Series({"HULL_FORM_TYPE": "semi_sub", "LOA_M": None})
        assert _make_hull_library_ref(row) == "semi_sub_generic"

    def test_zero_loa(self):
        row = pd.Series({"HULL_FORM_TYPE": "jackup", "LOA_M": 0})
        assert _make_hull_library_ref(row) == "jackup_generic"

    def test_nan_hull_form(self):
        row = pd.Series({"HULL_FORM_TYPE": "nan", "LOA_M": 100})
        assert _make_hull_library_ref(row) is None

    def test_none_hull_form(self):
        row = pd.Series({"HULL_FORM_TYPE": None, "LOA_M": 100})
        assert _make_hull_library_ref(row) is None

    def test_rounding(self):
        row = pd.Series({"HULL_FORM_TYPE": "drillship", "LOA_M": 234})
        assert _make_hull_library_ref(row) == "drillship_230m"
        row2 = pd.Series({"HULL_FORM_TYPE": "drillship", "LOA_M": 236})
        assert _make_hull_library_ref(row2) == "drillship_240m"


class TestPopulateHullForms:
    def test_populates_missing(self):
        df = pd.DataFrame({
            "RIG_TYPE": ["drillship", "semi_submersible"],
            "HULL_FORM_TYPE": [None, None],
        })
        result = populate_hull_forms(df)
        assert result["HULL_FORM_TYPE"].iloc[0] == "drillship"
        assert result["HULL_FORM_TYPE"].iloc[1] == "semi_sub"

    def test_preserves_existing(self):
        df = pd.DataFrame({
            "RIG_TYPE": ["drillship"],
            "HULL_FORM_TYPE": ["custom_form"],
        })
        result = populate_hull_forms(df)
        assert result["HULL_FORM_TYPE"].iloc[0] == "custom_form"

    def test_no_rig_type_column(self):
        df = pd.DataFrame({"OTHER": ["A"]})
        result = populate_hull_forms(df)
        assert "HULL_FORM_TYPE" in result.columns

    def test_creates_hull_form_column(self):
        df = pd.DataFrame({"RIG_TYPE": ["drillship"]})
        result = populate_hull_forms(df)
        assert "HULL_FORM_TYPE" in result.columns

    def test_original_not_modified(self):
        df = pd.DataFrame({
            "RIG_TYPE": ["drillship"],
            "HULL_FORM_TYPE": [None],
        })
        original_val = df["HULL_FORM_TYPE"].iloc[0]
        populate_hull_forms(df)
        assert df["HULL_FORM_TYPE"].iloc[0] is original_val


class TestRefreshHullLibraryRefs:
    def test_adds_generic_ref(self):
        df = pd.DataFrame({
            "HULL_FORM_TYPE": ["drillship"],
            "LOA_M": [None],
            "HULL_LIBRARY_REF": [None],
        })
        result = refresh_hull_library_refs(df)
        assert result["HULL_LIBRARY_REF"].iloc[0] == "drillship_generic"

    def test_updates_stale_generic(self):
        df = pd.DataFrame({
            "HULL_FORM_TYPE": ["drillship"],
            "LOA_M": [228.0],
            "HULL_LIBRARY_REF": ["drillship_generic"],
        })
        result = refresh_hull_library_refs(df)
        assert result["HULL_LIBRARY_REF"].iloc[0] == "drillship_230m"

    def test_preserves_custom_ref(self):
        df = pd.DataFrame({
            "HULL_FORM_TYPE": ["drillship"],
            "LOA_M": [228.0],
            "HULL_LIBRARY_REF": ["custom_ref_from_rao"],
        })
        result = refresh_hull_library_refs(df)
        assert result["HULL_LIBRARY_REF"].iloc[0] == "custom_ref_from_rao"

    def test_no_hull_library_ref_column(self):
        df = pd.DataFrame({
            "HULL_FORM_TYPE": ["semi_sub"],
            "LOA_M": [100.0],
        })
        result = refresh_hull_library_refs(df)
        assert "HULL_LIBRARY_REF" in result.columns
