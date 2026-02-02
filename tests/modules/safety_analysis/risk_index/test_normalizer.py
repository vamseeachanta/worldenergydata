"""Tests for HSE Risk Index normalizer functions."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.modules.safety_analysis.risk_index.normalizer import (
    NormalizationResult,
    normalize_to_scale,
    percentile_rank,
)


class TestPercentileRank:
    """Tests for percentile_rank function."""

    def test_basic_ranking(self):
        values = pd.Series([10, 20, 30, 40, 50])
        result = percentile_rank(values)
        assert isinstance(result, pd.Series)
        assert len(result) == 5
        # Smallest value gets lowest percentile, largest gets highest
        assert result.iloc[0] < result.iloc[-1]

    def test_returns_values_between_0_and_1(self):
        values = pd.Series([5, 15, 25, 35, 45, 55])
        result = percentile_rank(values)
        assert (result >= 0.0).all()
        assert (result <= 1.0).all()

    def test_monotonically_increasing_for_sorted_input(self):
        values = pd.Series([1, 2, 3, 4, 5])
        result = percentile_rank(values)
        for i in range(len(result) - 1):
            assert result.iloc[i] < result.iloc[i + 1]

    def test_tied_values_get_same_rank(self):
        values = pd.Series([10, 20, 20, 30])
        result = percentile_rank(values)
        assert result.iloc[1] == result.iloc[2]

    def test_all_same_values(self):
        """All identical values should get the same percentile rank."""
        values = pd.Series([5, 5, 5, 5, 5])
        result = percentile_rank(values)
        # All should have the same rank
        assert result.nunique() == 1

    def test_single_value(self):
        values = pd.Series([42])
        result = percentile_rank(values)
        assert len(result) == 1

    def test_empty_series(self):
        values = pd.Series([], dtype=float)
        result = percentile_rank(values)
        assert len(result) == 0

    def test_with_zeros(self):
        values = pd.Series([0, 0, 10, 20])
        result = percentile_rank(values)
        assert len(result) == 4
        # Zeros are tied, so they share a rank
        assert result.iloc[0] == result.iloc[1]
        # Non-zero values rank higher
        assert result.iloc[2] > result.iloc[0]

    def test_nan_handling(self):
        """NaN values should remain NaN in the output."""
        values = pd.Series([10, np.nan, 30, 40])
        result = percentile_rank(values)
        assert len(result) == 4
        assert pd.isna(result.iloc[1])
        assert not pd.isna(result.iloc[0])

    def test_preserves_index(self):
        values = pd.Series([30, 10, 20], index=["a", "b", "c"])
        result = percentile_rank(values)
        assert list(result.index) == ["a", "b", "c"]

    def test_unsorted_input(self):
        values = pd.Series([50, 10, 40, 20, 30])
        result = percentile_rank(values)
        # 10 should have lowest rank, 50 highest
        assert result.iloc[1] < result.iloc[0]  # 10 < 50
        assert result.iloc[0] == result.max()  # 50 is the max


class TestNormalizeToScale:
    """Tests for normalize_to_scale function."""

    def test_known_answer_default_scale(self):
        """[10, 20, 30, 40, 50] should map to roughly [2, 4, 6, 8, 10]."""
        values = pd.Series([10, 20, 30, 40, 50])
        result = normalize_to_scale(values)
        assert isinstance(result, pd.Series)
        assert len(result) == 5
        # Check approximate mapping (allow integer bucketing variation)
        assert result.iloc[0] == 2
        assert result.iloc[1] == 4
        assert result.iloc[2] == 6
        assert result.iloc[3] == 8
        assert result.iloc[4] == 10

    def test_output_within_scale(self):
        values = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        result = normalize_to_scale(values, low=1, high=10)
        assert (result >= 1).all()
        assert (result <= 10).all()

    def test_custom_scale(self):
        values = pd.Series([10, 20, 30, 40, 50])
        result = normalize_to_scale(values, low=0, high=100)
        assert (result >= 0).all()
        assert (result <= 100).all()

    def test_returns_integers(self):
        """Scale values should be integers."""
        values = pd.Series([10, 20, 30, 40, 50])
        result = normalize_to_scale(values)
        for val in result:
            if not pd.isna(val):
                assert float(val) == int(val)

    def test_all_same_values_get_middle_score(self):
        """All identical values should map to the middle of the scale."""
        values = pd.Series([5, 5, 5, 5, 5])
        result = normalize_to_scale(values, low=1, high=10)
        # All same values get the same score
        assert result.nunique() == 1
        # Middle score for 1-10 scale
        mid = (1 + 10) / 2
        assert all(abs(val - mid) <= 1 for val in result)

    def test_single_value(self):
        values = pd.Series([42])
        result = normalize_to_scale(values)
        assert len(result) == 1

    def test_empty_series(self):
        values = pd.Series([], dtype=float)
        result = normalize_to_scale(values)
        assert len(result) == 0

    def test_nan_handling(self):
        """NaN values should remain NaN in the output."""
        values = pd.Series([10, np.nan, 30, 40])
        result = normalize_to_scale(values)
        assert pd.isna(result.iloc[1])
        assert not pd.isna(result.iloc[0])

    def test_preserves_order(self):
        """Higher input values should get higher or equal scale scores."""
        values = pd.Series([5, 15, 25, 35, 45])
        result = normalize_to_scale(values)
        for i in range(len(result) - 1):
            assert result.iloc[i] <= result.iloc[i + 1]

    def test_preserves_index(self):
        values = pd.Series([30, 10, 20], index=["a", "b", "c"])
        result = normalize_to_scale(values)
        assert list(result.index) == ["a", "b", "c"]


class TestNormalizationResult:
    """Tests for NormalizationResult dataclass."""

    def test_create(self):
        original = pd.Series([10, 20, 30])
        pct = pd.Series([0.2, 0.5, 1.0])
        scaled = pd.Series([2, 5, 10])
        nr = NormalizationResult(
            original=original,
            percentile_ranks=pct,
            scaled=scaled,
            metadata={"method": "percentile"},
        )
        assert len(nr.original) == 3
        assert len(nr.percentile_ranks) == 3
        assert len(nr.scaled) == 3
        assert nr.metadata["method"] == "percentile"

    def test_frozen(self):
        """NormalizationResult should be immutable (frozen dataclass)."""
        original = pd.Series([10, 20, 30])
        pct = pd.Series([0.2, 0.5, 1.0])
        scaled = pd.Series([2, 5, 10])
        nr = NormalizationResult(
            original=original,
            percentile_ranks=pct,
            scaled=scaled,
            metadata={"method": "percentile"},
        )
        with pytest.raises(AttributeError):
            nr.metadata = {"changed": True}

    def test_empty_metadata(self):
        original = pd.Series([10])
        pct = pd.Series([1.0])
        scaled = pd.Series([10])
        nr = NormalizationResult(
            original=original,
            percentile_ranks=pct,
            scaled=scaled,
            metadata={},
        )
        assert nr.metadata == {}
