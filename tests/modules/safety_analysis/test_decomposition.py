"""Tests for seasonal decomposition."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.safety_analysis.analysis.decomposition import (
    _HAS_STATSMODELS,
    decompose_signal,
    remove_trend_and_seasonality,
)

pytestmark = pytest.mark.skipif(
    not _HAS_STATSMODELS, reason="statsmodels not installed"
)


@pytest.fixture
def seasonal_signal():
    """Create a signal with trend + seasonality."""
    np.random.seed(42)
    n = 104  # 2 years of weekly data
    t = np.arange(n)
    trend = 0.1 * t
    seasonal = 5 * np.sin(2 * np.pi * t / 52)
    noise = np.random.normal(0, 0.5, n)
    signal = trend + seasonal + noise
    return pd.DataFrame(
        {
            "datetime": pd.date_range("2022-01-01", periods=n, freq="W"),
            "value": signal,
        }
    )


class TestDecomposeSignal:
    def test_returns_decomposition(self, seasonal_signal):
        result = decompose_signal(seasonal_signal, "value", period=52)
        assert hasattr(result, "trend")
        assert hasattr(result, "seasonal")
        assert hasattr(result, "resid")
        assert hasattr(result, "observed")


class TestRemoveTrendAndSeasonality:
    def test_returns_residuals(self, seasonal_signal):
        result = remove_trend_and_seasonality(seasonal_signal, periods=[52])
        assert "value" in result.columns
        assert "datetime" in result.columns
        # Residuals should be smaller than original
        orig_std = seasonal_signal["value"].std()
        resid_std = result["value"].dropna().std()
        assert resid_std < orig_std
