"""Tests for correlation analysis."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.safety_analysis.analysis.correlation import (
    LaggedCrossCorrelation,
    create_incident_counts,
    create_observation_counts,
    crosscorr,
    extract_asset_rates,
)
from worldenergydata.safety_analysis.exceptions import SafetyCorrelationError


class TestCrosscorr:
    def test_zero_lag_perfect_correlation(self):
        x = pd.Series([1, 2, 3, 4, 5], dtype=float)
        y = pd.Series([1, 2, 3, 4, 5], dtype=float)
        result = crosscorr(x, y, lag=0)
        assert abs(result - 1.0) < 1e-10

    def test_zero_lag_negative_correlation(self):
        x = pd.Series([1, 2, 3, 4, 5], dtype=float)
        y = pd.Series([5, 4, 3, 2, 1], dtype=float)
        result = crosscorr(x, y, lag=0)
        assert abs(result + 1.0) < 1e-10

    def test_nonzero_lag(self):
        x = pd.Series([0, 0, 1, 2, 3, 4, 5], dtype=float)
        y = pd.Series([1, 2, 3, 4, 5, 0, 0], dtype=float)
        crosscorr(x, y, lag=0)  # verify no error at lag=0
        result_lag2 = crosscorr(x, y, lag=2)
        # Shifted should be better correlated
        assert not np.isnan(result_lag2)


class TestLaggedCrossCorrelation:
    def test_compute_returns_result(self):
        np.random.seed(42)
        obs = pd.Series(np.random.randn(100))
        inc = pd.Series(np.random.randn(100))
        lcc = LaggedCrossCorrelation(lag_min=-10, lag_max=10, min_observations=30)
        result = lcc.compute(obs, inc, asset_id="RIG-001")
        assert result.asset_id == "RIG-001"
        assert len(result.lag_values) == 21
        assert len(result.correlation_values) == 21

    def test_compute_insufficient_data_raises(self):
        obs = pd.Series([1.0, 2.0, 3.0])
        inc = pd.Series([1.0, 2.0, 3.0])
        lcc = LaggedCrossCorrelation(min_observations=30)
        with pytest.raises(SafetyCorrelationError, match="Insufficient"):
            lcc.compute(obs, inc, asset_id="RIG-001")

    def test_compute_rolling(self):
        np.random.seed(42)
        obs = pd.Series(np.random.randn(100))
        inc = pd.Series(np.random.randn(100))
        lcc = LaggedCrossCorrelation(lag_min=-5, lag_max=5, min_observations=10)
        heatmap = lcc.compute_rolling(obs, inc, window_size=10)
        assert isinstance(heatmap, pd.DataFrame)
        assert len(heatmap.columns) == 11  # lag_min to lag_max


class TestCreateCounts:
    def test_create_observation_counts(self):
        df = pd.DataFrame(
            {
                "observed_at": pd.to_datetime(
                    ["2024-01-01", "2024-01-01", "2024-01-02"]
                ),
                "asset_id": ["RIG-001", "RIG-001", "RIG-002"],
                "description": ["a", "b", "c"],
            }
        )
        result = create_observation_counts(df)
        assert "obs_count" in result.columns
        assert result.loc[result["asset_id"] == "RIG-001", "obs_count"].iloc[0] == 2

    def test_create_incident_counts(self):
        df = pd.DataFrame(
            {
                "occurred_at": pd.to_datetime(
                    ["2024-01-05", "2024-01-05", "2024-01-10"]
                ),
                "asset_id": ["RIG-001", "RIG-001", "RIG-002"],
            }
        )
        result = create_incident_counts(df)
        assert "inc_count" in result.columns

    def test_extract_asset_rates(self):
        counts = pd.DataFrame(
            {
                "asset_id": ["RIG-001", "RIG-001"],
                "inc_count": [1, 2],
            },
            index=pd.to_datetime(["2024-01-01", "2024-01-03"]),
        )
        result = extract_asset_rates(counts, "RIG-001", "2024-01-01", "2024-01-05")
        assert len(result) == 5
        assert result["inc_count"].iloc[1] == 0  # Jan 2 filled with 0
