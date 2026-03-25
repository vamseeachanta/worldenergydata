"""Tests for BseeDeclineAdapter — BSEE production → decline curve bridge."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.bsee.analysis.forecasting.bsee_decline_adapter import (
    BseeDeclineAdapter,
    ProductionTimeSeries,
    _pick_col,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def adapter():
    return BseeDeclineAdapter(min_points=3, shut_in_threshold_days=5)


@pytest.fixture
def sample_production_df():
    """Realistic BSEE production DataFrame with monthly data."""
    dates = list(range(202001, 202013))  # Jan–Dec 2020
    return pd.DataFrame({
        "PRODUCTION_DATE": dates * 2,
        "FIELD_NAME_CODE": ["FIELD_A"] * 12 + ["FIELD_B"] * 12,
        "LEASE_NUMBER": ["OCS-G-30409"] * 12 + ["OCS-G-36543"] * 12,
        "MON_O_PROD_VOL": np.random.default_rng(42).uniform(
            10000, 100000, 24
        ).tolist(),
        "MON_G_PROD_VOL": np.random.default_rng(43).uniform(
            50000, 500000, 24
        ).tolist(),
        "MON_WTR_PROD_VOL": np.random.default_rng(44).uniform(
            1000, 10000, 24
        ).tolist(),
        "DAYS_ON_PROD": [28, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31] * 2,
    })


@pytest.fixture
def declining_production_df():
    """Production data with clear exponential decline for model fitting."""
    qi = 50000
    D = 0.05  # 5% decline per period
    n = 20
    rng = np.random.default_rng(99)
    rates = [qi * np.exp(-D * t) + rng.normal(0, 500) for t in range(n)]
    return pd.DataFrame({
        "PRODUCTION_DATE": list(range(200001, 200001 + n)),
        "FIELD_NAME_CODE": ["DECLINE_FIELD"] * n,
        "MON_O_PROD_VOL": rates,
        "DAYS_ON_PROD": [30] * n,
    })


# ---------------------------------------------------------------------------
# _pick_col tests
# ---------------------------------------------------------------------------

class TestPickCol:
    def test_finds_first_match(self):
        df = pd.DataFrame({"A": [1], "B": [2], "C": [3]})
        assert _pick_col(df, ["X", "B", "C"]) == "B"

    def test_returns_none_when_no_match(self):
        df = pd.DataFrame({"A": [1]})
        assert _pick_col(df, ["X", "Y"]) is None

    def test_returns_first_candidate_present(self):
        df = pd.DataFrame({"MON_O_PROD_VOL": [1], "OIL_STB": [2]})
        assert _pick_col(df, ["MON_O_PROD_VOL", "OIL_STB"]) == "MON_O_PROD_VOL"


# ---------------------------------------------------------------------------
# BseeDeclineAdapter.extract_field_production tests
# ---------------------------------------------------------------------------

class TestExtractFieldProduction:
    def test_extracts_oil_for_field(self, adapter, sample_production_df):
        ts = adapter.extract_field_production(
            sample_production_df, "FIELD_A", product="oil"
        )
        assert isinstance(ts, ProductionTimeSeries)
        assert ts.product_type == "oil"
        assert ts.field_name == "FIELD_A"
        assert ts.n_after_filter > 0
        assert len(ts.rates) == len(ts.time_indices)

    def test_extracts_gas(self, adapter, sample_production_df):
        ts = adapter.extract_field_production(
            sample_production_df, "FIELD_B", product="gas"
        )
        assert ts.product_type == "gas"
        assert ts.n_after_filter > 0

    def test_unknown_field_raises(self, adapter, sample_production_df):
        with pytest.raises(ValueError, match="No data found"):
            adapter.extract_field_production(
                sample_production_df, "NONEXISTENT"
            )

    def test_no_field_column_raises(self, adapter):
        df = pd.DataFrame({"some_col": [1, 2], "MON_O_PROD_VOL": [100, 200]})
        with pytest.raises(ValueError, match="No field column"):
            adapter.extract_field_production(df, "X")

    def test_daily_rate_conversion(self, adapter, sample_production_df):
        ts = adapter.extract_field_production(
            sample_production_df, "FIELD_A", product="oil"
        )
        # Rate should be volume / days, so less than max volume
        max_vol = sample_production_df.loc[
            sample_production_df["FIELD_NAME_CODE"] == "FIELD_A",
            "MON_O_PROD_VOL",
        ].max()
        assert ts.rates.max() < max_vol  # daily rate < monthly volume


class TestExtractLeaseProduction:
    def test_extracts_by_lease(self, adapter, sample_production_df):
        ts = adapter.extract_lease_production(
            sample_production_df, "OCS-G-30409", product="oil"
        )
        assert ts.field_name == "OCS-G-30409"
        assert ts.n_after_filter > 0

    def test_unknown_lease_raises(self, adapter, sample_production_df):
        with pytest.raises(ValueError, match="No data found"):
            adapter.extract_lease_production(
                sample_production_df, "FAKE-LEASE"
            )


class TestShutInExclusion:
    def test_excludes_shut_in_periods(self, adapter):
        df = pd.DataFrame({
            "PRODUCTION_DATE": [202001, 202002, 202003, 202004, 202005],
            "FIELD_NAME_CODE": ["F"] * 5,
            "MON_O_PROD_VOL": [100000, 500, 80000, 70000, 60000],
            "DAYS_ON_PROD": [30, 2, 31, 30, 31],  # period 2 is shut-in
        })
        ts = adapter.extract_field_production(df, "F", product="oil")
        assert ts.shut_in_periods == 1
        assert ts.n_after_filter == 4  # 5 - 1 shut-in

    def test_insufficient_data_after_filter(self, adapter):
        df = pd.DataFrame({
            "PRODUCTION_DATE": [202001, 202002],
            "FIELD_NAME_CODE": ["F"] * 2,
            "MON_O_PROD_VOL": [100, 200],
            "DAYS_ON_PROD": [1, 1],  # both shut-in (< 5 days)
        })
        with pytest.raises(ValueError, match="Insufficient data"):
            adapter.extract_field_production(df, "F")


class TestExtractFromDataframe:
    def test_direct_dataframe_extraction(self, adapter, sample_production_df):
        subset = sample_production_df[
            sample_production_df["FIELD_NAME_CODE"] == "FIELD_A"
        ].copy()
        ts = adapter.extract_from_dataframe(subset, product="oil", label="test")
        assert ts.field_name == "test"
        assert ts.n_after_filter > 0


class TestLoadProductionBinary:
    def test_nonexistent_file(self, adapter, tmp_path):
        result = adapter.load_production_binary(tmp_path / "missing.bin")
        assert result is None

    def test_lfs_stub_detection(self, adapter, tmp_path):
        stub = tmp_path / "stub.bin"
        stub.write_bytes(b"version https://git-lfs.github.com/spec/v1\n")
        result = adapter.load_production_binary(stub)
        assert result is None

    def test_real_pickle_file(self, adapter, tmp_path):
        df = pd.DataFrame({"A": [1, 2, 3]})
        path = tmp_path / "real.bin"
        df.to_pickle(path)
        result = adapter.load_production_binary(path)
        assert result is not None
        assert len(result) == 3


class TestProductionTimeSeries:
    def test_dataclass_fields(self, adapter, declining_production_df):
        ts = adapter.extract_field_production(
            declining_production_df, "DECLINE_FIELD"
        )
        assert hasattr(ts, "time_indices")
        assert hasattr(ts, "rates")
        assert hasattr(ts, "dates")
        assert hasattr(ts, "product_type")
        assert hasattr(ts, "field_name")
        assert hasattr(ts, "unit")
        assert hasattr(ts, "n_original")
        assert hasattr(ts, "n_after_filter")
        assert hasattr(ts, "shut_in_periods")
        assert ts.n_original == 20
