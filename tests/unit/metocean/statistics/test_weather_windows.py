"""
ABOUTME: Tests for WeatherWindowAnalysis (operability and weather window analysis).
ABOUTME: Uses synthetic Hs time series — no live API calls.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from worldenergydata.metocean.statistics.weather_windows import (
    OperabilityResult,
    WeatherWindowAnalysis,
)


def _make_hs_series(n_years: int = 5, seed: int = 42) -> pd.Series:
    """Synthetic 3-hourly Hs series (typical hindcast interval)."""
    rng = np.random.default_rng(seed)
    n = n_years * 365 * 8  # 3-hourly
    dates = pd.date_range("2015-01-01", periods=n, freq="3h")
    hs = rng.weibull(1.5, size=n) * 2.0 + 0.1
    return pd.Series(hs, index=dates, name="hs")


class TestOperabilityResult:
    def test_operability_result_fields(self):
        result = OperabilityResult(
            threshold=2.5,
            min_window_hours=12,
            operability_pct=72.5,
            mean_window_hours=18.3,
            total_windows=120,
        )
        assert result.threshold == 2.5
        assert result.min_window_hours == 12
        assert result.operability_pct == pytest.approx(72.5, rel=0.001)
        assert result.total_windows == 120

    def test_operability_pct_valid_range(self):
        result = OperabilityResult(
            threshold=2.5,
            min_window_hours=12,
            operability_pct=72.5,
            mean_window_hours=18.3,
            total_windows=120,
        )
        assert 0 <= result.operability_pct <= 100


class TestWeatherWindowOperability:
    def setup_method(self):
        self.wwa = WeatherWindowAnalysis()
        self.hs = _make_hs_series()

    def test_operability_returns_result(self):
        result = self.wwa.operability(self.hs, threshold=2.5)
        assert isinstance(result, OperabilityResult)

    def test_operability_threshold_stored(self):
        result = self.wwa.operability(self.hs, threshold=2.5)
        assert result.threshold == pytest.approx(2.5, rel=0.001)

    def test_operability_pct_valid_range(self):
        result = self.wwa.operability(self.hs, threshold=2.5)
        assert 0 <= result.operability_pct <= 100

    def test_operability_higher_threshold_means_more_operable(self):
        result_low = self.wwa.operability(self.hs, threshold=1.0)
        result_high = self.wwa.operability(self.hs, threshold=4.0)
        assert result_low.operability_pct <= result_high.operability_pct

    def test_operability_window_hours_stored(self):
        result = self.wwa.operability(self.hs, threshold=2.5, min_window_hours=12)
        assert result.min_window_hours == 12

    def test_operability_mean_window_positive(self):
        result = self.wwa.operability(self.hs, threshold=2.5)
        if result.total_windows > 0:
            assert result.mean_window_hours >= 0


class TestMonthlyOperability:
    def setup_method(self):
        self.wwa = WeatherWindowAnalysis()
        self.hs = _make_hs_series(n_years=3)

    def test_monthly_operability_returns_dataframe(self):
        df = self.wwa.monthly_operability(self.hs, threshold=2.5)
        assert isinstance(df, pd.DataFrame)

    def test_monthly_operability_has_12_months(self):
        df = self.wwa.monthly_operability(self.hs, threshold=2.5)
        # Either 12 rows (months) or 12 columns
        assert df.shape[0] == 12 or df.shape[1] == 12

    def test_monthly_operability_values_valid_range(self):
        df = self.wwa.monthly_operability(self.hs, threshold=2.5)
        numeric = df.select_dtypes(include=[np.number])
        assert (numeric.values >= 0).all()
        assert (numeric.values <= 100).all()

    def test_monthly_operability_higher_threshold_higher_values(self):
        df_low = self.wwa.monthly_operability(self.hs, threshold=1.0)
        df_high = self.wwa.monthly_operability(self.hs, threshold=4.0)
        num_low = df_low.select_dtypes(include=[np.number]).values.mean()
        num_high = df_high.select_dtypes(include=[np.number]).values.mean()
        assert num_low <= num_high


class TestPlotMonthlyHeatmap:
    def setup_method(self):
        self.wwa = WeatherWindowAnalysis()
        self.hs = _make_hs_series(n_years=3)

    def test_heatmap_returns_plotly_figure(self):
        result = self.wwa.operability(self.hs, threshold=2.5)
        df = self.wwa.monthly_operability(self.hs, threshold=2.5)
        fig = self.wwa.plot_monthly_heatmap(df)
        assert isinstance(fig, go.Figure)

    def test_heatmap_has_traces(self):
        df = self.wwa.monthly_operability(self.hs, threshold=2.5)
        fig = self.wwa.plot_monthly_heatmap(df)
        assert len(fig.data) >= 1
