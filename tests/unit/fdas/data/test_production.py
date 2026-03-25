"""Tests for FDAS production data processing module."""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from worldenergydata.fdas.data.production import (
    ProductionForecaster,
    ProductionProcessingError,
    ProductionProcessor,
    aggregate_monthly_production,
    identify_first_oil_date,
)


# ---------------------------------------------------------------------------
# ProductionProcessingError
# ---------------------------------------------------------------------------

class TestProductionProcessingError:
    def test_is_exception(self):
        err = ProductionProcessingError("test")
        assert isinstance(err, Exception)


# ---------------------------------------------------------------------------
# ProductionProcessor
# ---------------------------------------------------------------------------

def _make_prod_df(**overrides):
    defaults = {
        "API_WELL_NUMBER": ["W1", "W1", "W2"],
        "PROD_DATE": ["2024-01-01", "2024-02-01", "2024-01-01"],
        "OIL_VOLUME": [1000.0, 1200.0, 800.0],
        "WATER_VOLUME": [500.0, 600.0, 400.0],
        "GAS_VOLUME": [5000.0, 6000.0, 4000.0],
    }
    defaults.update(overrides)
    return pd.DataFrame(defaults)


class TestProductionProcessorInit:
    def test_valid_init(self):
        df = _make_prod_df()
        proc = ProductionProcessor(df)
        assert proc.production_df is not None

    def test_missing_columns_raises(self):
        df = pd.DataFrame({"OTHER": [1]})
        with pytest.raises(ProductionProcessingError, match="Missing required columns"):
            ProductionProcessor(df)


class TestAggregateMonthly:
    def test_basic_aggregation(self):
        df = _make_prod_df()
        proc = ProductionProcessor(df)
        result = proc.aggregate_monthly(by="API_WELL_NUMBER")
        assert "MONTHLY_OIL_BBL" in result.columns
        assert "MONTHLY_WATER_BBL" in result.columns
        assert "MONTHLY_GAS_MCF" in result.columns

    def test_two_months_for_w1(self):
        df = _make_prod_df()
        proc = ProductionProcessor(df)
        result = proc.aggregate_monthly(by="API_WELL_NUMBER")
        w1_rows = result[result["API_WELL_NUMBER"] == "W1"]
        assert len(w1_rows) == 2


class TestIdentifyFirstOil:
    def test_basic(self):
        df = _make_prod_df()
        proc = ProductionProcessor(df)
        result = proc.identify_first_oil(by="API_WELL_NUMBER")
        assert "FIRST_OIL_DATE" in result.columns
        assert len(result) == 2  # W1 and W2

    def test_threshold_filters(self):
        df = _make_prod_df(OIL_VOLUME=[5.0, 1200.0, 800.0])
        proc = ProductionProcessor(df)
        result = proc.identify_first_oil(by="API_WELL_NUMBER", threshold_bbl=10.0)
        # W1's first month (5 bbl) is below threshold, so first oil is month 2
        w1 = result[result["API_WELL_NUMBER"] == "W1"]
        assert pd.Timestamp(w1["FIRST_OIL_DATE"].iloc[0]) == pd.Timestamp("2024-02-01")


class TestCalculateCumulativeProduction:
    def test_basic(self):
        df = _make_prod_df()
        proc = ProductionProcessor(df)
        result = proc.calculate_cumulative_production(by="API_WELL_NUMBER")
        assert "CUMULATIVE_OIL_BBL" in result.columns
        assert "WATER_CUT" in result.columns

    def test_cumulative_increases(self):
        df = _make_prod_df()
        proc = ProductionProcessor(df)
        result = proc.calculate_cumulative_production(by="API_WELL_NUMBER")
        w1 = result[result["API_WELL_NUMBER"] == "W1"].sort_values("YEAR_MONTH")
        cumsums = w1["CUMULATIVE_OIL_BBL"].values
        assert cumsums[-1] > cumsums[0]


class TestGenerateProductionSummary:
    def test_basic(self):
        df = _make_prod_df()
        proc = ProductionProcessor(df)
        result = proc.generate_production_summary(by="API_WELL_NUMBER")
        assert "TOTAL_OIL_BBL" in result.columns
        assert "PRODUCTION_MONTHS" in result.columns


class TestCreatePivotTable:
    def test_basic(self):
        df = _make_prod_df()
        proc = ProductionProcessor(df)
        pivot = proc.create_pivot_table(by="API_WELL_NUMBER")
        assert pivot.shape[0] == 2  # 2 wells


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

class TestConvenienceFunctions:
    def test_aggregate_monthly_production(self):
        df = _make_prod_df()
        result = aggregate_monthly_production(df, by="API_WELL_NUMBER")
        assert "MONTHLY_OIL_BBL" in result.columns

    def test_identify_first_oil_date(self):
        df = _make_prod_df()
        result = identify_first_oil_date(df, by="API_WELL_NUMBER")
        assert "FIRST_OIL_DATE" in result.columns


# ---------------------------------------------------------------------------
# ProductionForecaster
# ---------------------------------------------------------------------------

class TestExponentialDecline:
    def test_basic(self):
        df = _make_prod_df()
        forecaster = ProductionForecaster(df)
        forecast = forecaster.exponential_decline(10000, 0.15, 60)
        assert len(forecast) == 60
        assert forecast[0] == pytest.approx(10000, abs=1)
        # Production should decline over time
        assert forecast[-1] < forecast[0]

    def test_zero_decline(self):
        df = _make_prod_df()
        forecaster = ProductionForecaster(df)
        forecast = forecaster.exponential_decline(10000, 0.0, 12)
        assert all(v == pytest.approx(10000) for v in forecast)


class TestHyperbolicDecline:
    def test_exponential_mode(self):
        df = _make_prod_df()
        forecaster = ProductionForecaster(df)
        forecast = forecaster.hyperbolic_decline(10000, 0.15, 0, 60)
        assert len(forecast) == 60
        assert forecast[0] == pytest.approx(10000, abs=1)
        assert forecast[-1] < forecast[0]

    def test_hyperbolic_mode(self):
        df = _make_prod_df()
        forecaster = ProductionForecaster(df)
        forecast = forecaster.hyperbolic_decline(10000, 0.15, 0.5, 60)
        assert len(forecast) == 60
        assert forecast[0] == pytest.approx(10000, abs=1)
        assert forecast[-1] < forecast[0]

    def test_harmonic_mode(self):
        df = _make_prod_df()
        forecaster = ProductionForecaster(df)
        forecast = forecaster.hyperbolic_decline(10000, 0.15, 1.0, 60)
        assert len(forecast) == 60
        # Harmonic decline is slowest
        assert forecast[-1] < forecast[0]
