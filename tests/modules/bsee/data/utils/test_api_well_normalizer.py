"""Tests for API well number normalizer — TDD-first (WRK-116 Phase 0a)."""

from __future__ import annotations

import pandas as pd

from worldenergydata.bsee.data.utils.api_well_normalizer import (
    normalize_api_column_name,
    normalize_api_well_number,
)


# --- normalize_api_well_number ---


class TestNormalizeApiWellNumber:
    """Covers every format observed across BSEE datasets."""

    def test_float_input_drops_trailing_decimal_zero(self):
        series = pd.Series([177114156300.0])
        result = normalize_api_well_number(series)
        assert result.iloc[0] == "177114156300"

    def test_int_input_converts_to_string(self):
        series = pd.Series([608054000300], dtype="int64")
        result = normalize_api_well_number(series)
        assert result.iloc[0] == "608054000300"

    def test_string_input_unchanged(self):
        series = pd.Series(["177114156300"])
        result = normalize_api_well_number(series)
        assert result.iloc[0] == "177114156300"

    def test_string_with_trailing_dot_zero_stripped(self):
        series = pd.Series(["177114156300.0"])
        result = normalize_api_well_number(series)
        assert result.iloc[0] == "177114156300"

    def test_nan_preserved(self):
        series = pd.Series([float("nan")])
        result = normalize_api_well_number(series)
        assert pd.isna(result.iloc[0])

    def test_none_preserved_as_nan(self):
        series = pd.Series([None])
        result = normalize_api_well_number(series)
        assert pd.isna(result.iloc[0])

    def test_whitespace_stripped(self):
        series = pd.Series([" 177114156300 "])
        result = normalize_api_well_number(series)
        assert result.iloc[0] == "177114156300"

    def test_mixed_types_in_single_series(self):
        series = pd.Series([177114156300.0, 608054000300, "177114156300", None])
        result = normalize_api_well_number(series)
        assert result.iloc[0] == "177114156300"
        assert result.iloc[1] == "608054000300"
        assert result.iloc[2] == "177114156300"
        assert pd.isna(result.iloc[3])

    def test_result_dtype_is_string_like(self):
        series = pd.Series([177114156300.0, 608054000300])
        result = normalize_api_well_number(series)
        assert pd.api.types.is_string_dtype(result)

    def test_empty_series_returns_empty(self):
        series = pd.Series([], dtype="object")
        result = normalize_api_well_number(series)
        assert len(result) == 0


# --- normalize_api_column_name ---


class TestNormalizeApiColumnName:
    """Rename spaced column header found in Paleowells.csv."""

    def test_renames_spaced_column(self):
        df = pd.DataFrame({"API Well Number": [1], "Other": [2]})
        result = normalize_api_column_name(df)
        assert "API_WELL_NUMBER" in result.columns
        assert "API Well Number" not in result.columns

    def test_preserves_other_columns(self):
        df = pd.DataFrame({"API Well Number": [1], "Depth": [500]})
        result = normalize_api_column_name(df)
        assert "Depth" in result.columns

    def test_no_op_when_column_absent(self):
        df = pd.DataFrame({"API_WELL_NUMBER": [1], "Depth": [500]})
        result = normalize_api_column_name(df)
        assert list(result.columns) == ["API_WELL_NUMBER", "Depth"]

    def test_does_not_mutate_original(self):
        df = pd.DataFrame({"API Well Number": [1]})
        _ = normalize_api_column_name(df)
        assert "API Well Number" in df.columns
