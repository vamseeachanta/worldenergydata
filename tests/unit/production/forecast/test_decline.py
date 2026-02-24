"""
ABOUTME: Tests for ArpsDeclineCurve (exponential / hyperbolic / harmonic).
ABOUTME: Uses synthetic data with known parameters — no external data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from worldenergydata.production.forecast.decline import ArpsDeclineCurve, ForecastResult


def _make_synthetic(
    model: str,
    qi: float,
    Di: float,
    b: float,
    n: int = 60,
    noise: float = 0.02,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic Arps decline curve data with Gaussian noise.

    Parameters are recoverable to ±5% by the fitter at noise=0.02.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(1, n + 1, dtype=float)

    if model == "exponential":
        rate = qi * np.exp(-Di * t)
    elif model == "hyperbolic":
        rate = qi * (1.0 + b * Di * t) ** (-1.0 / b)
    elif model == "harmonic":
        rate = qi / (1.0 + Di * t)
    else:
        raise ValueError(f"Unknown model: {model}")

    noise_arr = rng.normal(0.0, noise * rate)
    rate = np.maximum(rate + noise_arr, 1.0)  # keep positive

    return pd.DataFrame({"month": t.astype(int), "rate_bbl": rate})


class TestArpsDeclineCurveFit:
    def setup_method(self):
        self.fitter = ArpsDeclineCurve()

    def test_fit_hyperbolic_recovers_qi(self):
        df = _make_synthetic("hyperbolic", qi=5000.0, Di=0.08, b=1.2)
        result = self.fitter.fit(df, model="hyperbolic")
        assert abs(result.qi - 5000.0) / 5000.0 < 0.05

    def test_fit_exponential_recovers_qi(self):
        df = _make_synthetic("exponential", qi=4000.0, Di=0.10, b=0.0)
        result = self.fitter.fit(df, model="exponential")
        assert abs(result.qi - 4000.0) / 4000.0 < 0.05

    def test_fit_harmonic_recovers_qi(self):
        df = _make_synthetic("harmonic", qi=3000.0, Di=0.06, b=1.0)
        result = self.fitter.fit(df, model="harmonic")
        assert abs(result.qi - 3000.0) / 3000.0 < 0.05

    def test_fit_returns_forecast_result(self):
        df = _make_synthetic("hyperbolic", qi=5000.0, Di=0.08, b=1.2)
        result = self.fitter.fit(df, model="hyperbolic")
        assert isinstance(result, ForecastResult)

    def test_r_squared_above_threshold(self):
        df = _make_synthetic("hyperbolic", qi=5000.0, Di=0.08, b=1.2, noise=0.01)
        result = self.fitter.fit(df, model="hyperbolic")
        assert result.r_squared > 0.90

    def test_eur_positive_finite(self):
        df = _make_synthetic("hyperbolic", qi=5000.0, Di=0.08, b=1.2)
        result = self.fitter.fit(df, model="hyperbolic")
        assert result.eur_bbl > 0
        assert np.isfinite(result.eur_bbl)

    def test_forecast_df_columns(self):
        df = _make_synthetic("hyperbolic", qi=5000.0, Di=0.08, b=1.2)
        result = self.fitter.fit(df, model="hyperbolic")
        expected_cols = {"month", "rate_bbl", "cumulative_bbl"}
        assert expected_cols.issubset(set(result.forecast_df.columns))

    def test_forecast_monotonic_decline(self):
        df = _make_synthetic("hyperbolic", qi=5000.0, Di=0.08, b=1.2)
        result = self.fitter.fit(df, model="hyperbolic")
        rates = result.forecast_df["rate_bbl"].values
        assert (rates[1:] <= rates[:-1]).all()

    def test_plot_returns_figure(self):
        df = _make_synthetic("hyperbolic", qi=5000.0, Di=0.08, b=1.2)
        result = self.fitter.fit(df, model="hyperbolic")
        fig = self.fitter.plot(df, result)
        assert isinstance(fig, go.Figure)

    def test_invalid_model_raises(self):
        df = _make_synthetic("hyperbolic", qi=5000.0, Di=0.08, b=1.2)
        with pytest.raises(ValueError, match="model"):
            self.fitter.fit(df, model="invalid")

    def test_empty_input_raises(self):
        df = pd.DataFrame({"month": pd.Series([], dtype=int), "rate_bbl": pd.Series([], dtype=float)})
        with pytest.raises(ValueError, match="empty"):
            self.fitter.fit(df, model="hyperbolic")

    def test_forecast_length(self):
        df = _make_synthetic("hyperbolic", qi=5000.0, Di=0.08, b=1.2)
        result = self.fitter.fit(df, model="hyperbolic", months=60)
        assert len(result.forecast_df) == 60
