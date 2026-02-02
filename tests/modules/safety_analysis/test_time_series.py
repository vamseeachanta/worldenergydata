"""Tests for time series analysis."""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from worldenergydata.modules.safety_analysis.analysis.time_series import (
    TimeSeriesBuilder,
    calculate_gradient,
    calculate_moving_average,
    calculate_multiple_moving_averages,
)


@pytest.fixture
def sample_signal():
    """Create a sample signal DataFrame."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    return pd.DataFrame(
        {
            "asset_id": ["RIG-001"] * 50 + ["RIG-002"] * 50,
            "datetime": list(dates[:50]) + list(dates[25:75]),
            "value": np.random.randint(0, 10, 100),
        }
    )


@pytest.fixture
def builder():
    return TimeSeriesBuilder(frequency="W-SUN")


class TestTimeSeriesBuilder:
    def test_approximate_asset_activity_periods(self, builder, sample_signal):
        periods = builder.approximate_asset_activity_periods([sample_signal])
        assert len(periods) == 2
        assert "start_date" in periods.columns
        assert "end_date" in periods.columns

    def test_activity_periods_with_date_clipping(self, builder, sample_signal):
        min_date = datetime(2024, 1, 15)
        max_date = datetime(2024, 3, 1)
        periods = builder.approximate_asset_activity_periods(
            [sample_signal], min_date=min_date, max_date=max_date
        )
        assert all(periods["start_date"] >= pd.Timestamp(min_date))
        assert all(periods["end_date"] <= pd.Timestamp(max_date))

    def test_collect_all_asset_ids(self, builder, sample_signal):
        ids = builder.collect_all_asset_ids([sample_signal])
        assert "RIG-001" in ids
        assert "RIG-002" in ids
        assert len(ids) == 2

    def test_create_binned_time_series(self, builder, sample_signal):
        ids = builder.collect_all_asset_ids([sample_signal])
        result = builder.create_binned_time_series(
            sample_signal,
            ids,
            datetime(2024, 1, 1),
            datetime(2024, 4, 1),
        )
        assert "datetime" in result.columns
        assert "total" in result.columns
        assert "RIG-001" in result.columns

    def test_normalize_by_active_assets(self, builder, sample_signal):
        ids = builder.collect_all_asset_ids([sample_signal])
        ts = builder.create_binned_time_series(
            sample_signal,
            ids,
            datetime(2024, 1, 1),
            datetime(2024, 4, 1),
        )
        periods = builder.approximate_asset_activity_periods([sample_signal])
        normalized = builder.normalize_by_active_assets(ts, periods)
        assert "active_assets" in normalized.columns
        assert "per_asset" in normalized.columns


class TestGradient:
    def test_calculate_gradient(self):
        ts = pd.DataFrame(
            {
                "datetime": pd.date_range("2024-01-01", periods=5, freq="W"),
                "total": [1.0, 3.0, 2.0, 5.0, 4.0],
            }
        )
        grad = calculate_gradient(ts)
        assert grad["total"].iloc[0] == 0.0
        assert grad["total"].iloc[1] == 2.0
        assert "datetime" in grad.columns


class TestMovingAverage:
    def test_basic_moving_average(self):
        ts = pd.DataFrame(
            {
                "datetime": pd.date_range("2024-01-01", periods=10, freq="D"),
                "value": range(10),
            }
        )
        result = calculate_moving_average(ts, window_size=3)
        assert "datetime" in result.columns
        assert pd.isna(result["value"].iloc[0])
        assert result["value"].iloc[2] == 1.0

    def test_multiple_moving_averages(self):
        ts = pd.DataFrame(
            {
                "datetime": pd.date_range("2024-01-01", periods=10, freq="D"),
                "value": range(10),
            }
        )
        results = calculate_multiple_moving_averages(ts, 2, 4, step=1)
        assert 2 in results
        assert 3 in results
        assert 4 in results
