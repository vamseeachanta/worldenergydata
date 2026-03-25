"""Tests for API well number normalizer utility functions."""

import pandas as pd
import pytest

from worldenergydata.bsee.data.utils.api_well_normalizer import (
    normalize_api_column_name,
    normalize_api_well_number,
)


class TestNormalizeApiWellNumber:
    def test_float_drops_trailing_zero(self):
        s = pd.Series([1770161234.0])
        result = normalize_api_well_number(s)
        assert result.iloc[0] == "1770161234"

    def test_int_to_str(self):
        s = pd.Series([1770161234])
        result = normalize_api_well_number(s)
        assert result.iloc[0] == "1770161234"

    def test_string_stripped(self):
        s = pd.Series(["  1770161234  "])
        result = normalize_api_well_number(s)
        assert result.iloc[0] == "1770161234"

    def test_nan_preserved(self):
        s = pd.Series([float("nan")])
        result = normalize_api_well_number(s)
        assert pd.isna(result.iloc[0])

    def test_none_preserved(self):
        s = pd.Series([None])
        result = normalize_api_well_number(s)
        assert pd.isna(result.iloc[0])

    def test_mixed_types(self):
        s = pd.Series([1770161234.0, "1770161235", None, float("nan")])
        result = normalize_api_well_number(s)
        assert result.iloc[0] == "1770161234"
        assert result.iloc[1] == "1770161235"
        assert pd.isna(result.iloc[2])
        assert pd.isna(result.iloc[3])

    def test_no_trailing_dot_zero(self):
        s = pd.Series(["12345.0"])
        result = normalize_api_well_number(s)
        assert result.iloc[0] == "12345"

    def test_value_with_decimals_preserved(self):
        s = pd.Series(["12345.5"])
        result = normalize_api_well_number(s)
        assert result.iloc[0] == "12345.5"


class TestNormalizeApiColumnName:
    def test_rename_with_spaces(self):
        df = pd.DataFrame({"API Well Number": [1, 2], "other": [3, 4]})
        result = normalize_api_column_name(df)
        assert "API_WELL_NUMBER" in result.columns
        assert "API Well Number" not in result.columns

    def test_no_rename_needed(self):
        df = pd.DataFrame({"API_WELL_NUMBER": [1, 2]})
        result = normalize_api_column_name(df)
        assert "API_WELL_NUMBER" in result.columns

    def test_original_not_mutated(self):
        df = pd.DataFrame({"API Well Number": [1]})
        normalize_api_column_name(df)
        assert "API Well Number" in df.columns

    def test_other_columns_preserved(self):
        df = pd.DataFrame({"API Well Number": [1], "foo": [2]})
        result = normalize_api_column_name(df)
        assert "foo" in result.columns
