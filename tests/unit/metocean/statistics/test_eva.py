"""
ABOUTME: Tests for ExtremeValueAnalysis wrapper (metocean-stats EVA).
ABOUTME: Uses synthetic data — no live API calls.
"""

import numpy as np
import pandas as pd
import pytest
import plotly.graph_objects as go

from worldenergydata.metocean.statistics.eva import (
    EVAResult,
    ExtremeValueAnalysis,
)


def _make_hs_series(n_years: int = 10, seed: int = 42) -> pd.Series:
    """Create synthetic hourly Hs time series (Weibull-like distribution)."""
    rng = np.random.default_rng(seed)
    n_hours = n_years * 365 * 24
    dates = pd.date_range("2010-01-01", periods=n_hours, freq="h")
    hs = rng.weibull(1.5, size=n_hours) * 2.0 + 0.1  # ~0.1-8 m range
    return pd.Series(hs, index=dates, name="hs")


class TestEVAResult:
    def test_eva_result_has_required_fields(self):
        result = EVAResult(
            method="POT",
            distribution="Weibull_2P",
            return_levels={50: 7.2, 100: 8.5, 1000: 11.0},
            parameters={"alpha": 1.2, "beta": 0.8},
            threshold=2.5,
        )
        assert result.method == "POT"
        assert result.distribution == "Weibull_2P"
        assert 50 in result.return_levels
        assert result.parameters is not None
        assert result.threshold == 2.5

    def test_eva_result_annual_maxima_no_threshold(self):
        result = EVAResult(
            method="AM",
            distribution="GEV",
            return_levels={100: 10.0},
            parameters={"loc": 5.0, "scale": 1.5, "shape": -0.1},
            threshold=None,
        )
        assert result.threshold is None
        assert result.method == "AM"


class TestExtremeValueAnalysisPOT:
    def setup_method(self):
        self.eva = ExtremeValueAnalysis()
        self.hs = _make_hs_series(n_years=10)

    def test_fit_pot_returns_eva_result(self):
        result = self.eva.fit_pot(self.hs)
        assert isinstance(result, EVAResult)

    def test_fit_pot_method_label(self):
        result = self.eva.fit_pot(self.hs)
        assert result.method == "POT"

    def test_fit_pot_has_return_levels(self):
        result = self.eva.fit_pot(self.hs)
        assert isinstance(result.return_levels, dict)
        assert len(result.return_levels) > 0

    def test_fit_pot_return_levels_monotonic(self):
        result = self.eva.fit_pot(self.hs)
        periods = sorted(result.return_levels.keys())
        values = [result.return_levels[p] for p in periods]
        # Longer return periods must yield higher values
        for i in range(len(values) - 1):
            assert values[i] <= values[i + 1], (
                f"Return levels not monotonic: {result.return_levels}"
            )

    def test_fit_pot_custom_threshold(self):
        result = self.eva.fit_pot(self.hs, threshold=3.0)
        assert result.threshold == pytest.approx(3.0, rel=0.01)

    def test_fit_pot_has_parameters(self):
        result = self.eva.fit_pot(self.hs)
        assert isinstance(result.parameters, dict)
        assert len(result.parameters) >= 2

    def test_fit_pot_positive_return_levels(self):
        result = self.eva.fit_pot(self.hs)
        for period, value in result.return_levels.items():
            assert value > 0, f"Return level for period {period} is non-positive"


class TestExtremeValueAnalysisAnnualMaxima:
    def setup_method(self):
        self.eva = ExtremeValueAnalysis()
        self.hs = _make_hs_series(n_years=15)

    def test_fit_annual_maxima_returns_eva_result(self):
        result = self.eva.fit_annual_maxima(self.hs)
        assert isinstance(result, EVAResult)

    def test_fit_annual_maxima_method_label(self):
        result = self.eva.fit_annual_maxima(self.hs)
        assert result.method == "AM"

    def test_fit_annual_maxima_has_return_levels(self):
        result = self.eva.fit_annual_maxima(self.hs)
        assert len(result.return_levels) > 0

    def test_fit_annual_maxima_return_levels_monotonic(self):
        result = self.eva.fit_annual_maxima(self.hs)
        periods = sorted(result.return_levels.keys())
        values = [result.return_levels[p] for p in periods]
        for i in range(len(values) - 1):
            assert values[i] <= values[i + 1]

    def test_fit_annual_maxima_distribution_label(self):
        result = self.eva.fit_annual_maxima(self.hs)
        assert isinstance(result.distribution, str)
        assert len(result.distribution) > 0


class TestReturnPeriodTable:
    def setup_method(self):
        self.eva = ExtremeValueAnalysis()
        self.hs = _make_hs_series(n_years=10)

    def test_return_period_table_returns_dataframe(self):
        result = self.eva.fit_pot(self.hs)
        df = self.eva.return_period_table(result)
        assert isinstance(df, pd.DataFrame)

    def test_return_period_table_default_periods(self):
        result = self.eva.fit_pot(self.hs)
        df = self.eva.return_period_table(result)
        assert len(df) == 5  # default [1, 10, 50, 100, 1000]

    def test_return_period_table_custom_periods(self):
        result = self.eva.fit_pot(self.hs)
        periods = [10, 25, 50]
        df = self.eva.return_period_table(result, periods=periods)
        assert len(df) == 3

    def test_return_period_table_has_return_period_column(self):
        result = self.eva.fit_pot(self.hs)
        df = self.eva.return_period_table(result)
        assert "return_period" in df.columns or df.index.name == "return_period"

    def test_return_period_table_has_return_value_column(self):
        result = self.eva.fit_pot(self.hs)
        df = self.eva.return_period_table(result)
        # At least one numeric column beyond the period index
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        assert len(numeric_cols) >= 1

    def test_return_period_table_values_positive(self):
        result = self.eva.fit_pot(self.hs)
        df = self.eva.return_period_table(result)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            assert (df[col] > 0).all()


class TestPlotReturnPeriod:
    def setup_method(self):
        self.eva = ExtremeValueAnalysis()
        self.hs = _make_hs_series(n_years=10)

    def test_plot_returns_plotly_figure(self):
        result = self.eva.fit_pot(self.hs)
        fig = self.eva.plot_return_period(result)
        assert isinstance(fig, go.Figure)

    def test_plot_has_traces(self):
        result = self.eva.fit_pot(self.hs)
        fig = self.eva.plot_return_period(result)
        assert len(fig.data) >= 1

    def test_plot_annual_maxima_returns_figure(self):
        result = self.eva.fit_annual_maxima(self.hs)
        fig = self.eva.plot_return_period(result)
        assert isinstance(fig, go.Figure)
