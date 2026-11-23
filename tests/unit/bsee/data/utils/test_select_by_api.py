"""Dtype-safe API matching (#1113).

``df["API_WELL_NUMBER"] == api`` evaluates to all-False across dtypes without
raising, so the filter returns nothing and the caller reports the well as
having no data. These tests pin every spelling combination that reaches the
comparison in practice.
"""

import pandas as pd
import pytest

from worldenergydata.bsee.data.utils.api_well_normalizer import select_by_api

API_STR = "608124009500"
API_INT = 608124009500
API_FLOAT = 608124009500.0


def _frame(values):
    return pd.DataFrame({"API_WELL_NUMBER": values, "payload": range(len(values))})


class TestCrossDtypeMatching:
    @pytest.mark.parametrize("column_value", [API_STR, API_INT, API_FLOAT])
    @pytest.mark.parametrize("argument", [API_STR, API_INT, API_FLOAT])
    def test_every_spelling_combination_matches(self, column_value, argument):
        # The regression: an int64 column against a string argument silently
        # matched nothing, which downstream reads as "this well has no WAR".
        out = select_by_api(_frame([column_value, 999999999999]), argument)
        assert len(out) == 1
        assert out["payload"].iloc[0] == 0

    def test_float_column_does_not_carry_a_dot_zero_into_the_match(self):
        # Concatenating heterogeneous frames widens the column to float64,
        # which stringifies as "608124009500.0" and matches nothing.
        out = select_by_api(_frame([API_FLOAT]), API_STR)
        assert len(out) == 1

    def test_whitespace_is_ignored_on_both_sides(self):
        out = select_by_api(_frame([f"  {API_STR} "]), f"{API_STR}  ")
        assert len(out) == 1


class TestNonMatches:
    def test_a_genuine_miss_returns_empty(self):
        out = select_by_api(_frame([API_STR]), "111111111111")
        assert out.empty

    def test_missing_api_values_never_match(self):
        out = select_by_api(_frame([None, pd.NA, API_STR]), API_STR)
        assert len(out) == 1

    def test_a_null_argument_matches_nothing_rather_than_everything(self):
        # Normalising None must not collapse into a value that matches the
        # frame's own nulls -- that would return rows for a well nobody asked
        # about.
        out = select_by_api(_frame([None, API_STR]), None)
        assert out.empty


class TestContract:
    def test_absent_column_is_a_clear_error_not_a_silent_empty(self):
        with pytest.raises(KeyError, match="API_WELL_NUMBER"):
            select_by_api(pd.DataFrame({"other": [1]}), API_STR)

    def test_alternate_column_name_is_supported(self):
        df = pd.DataFrame({"BOTM_API": [API_INT], "payload": [0]})
        assert len(select_by_api(df, API_STR, column="BOTM_API")) == 1

    def test_original_frame_is_not_mutated(self):
        df = _frame([API_INT])
        before = df["API_WELL_NUMBER"].dtype
        select_by_api(df, API_STR)
        assert df["API_WELL_NUMBER"].dtype == before
