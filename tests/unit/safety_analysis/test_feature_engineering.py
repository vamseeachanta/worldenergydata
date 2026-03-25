"""Tests for feature engineering."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.safety_analysis.analysis.feature_engineering import (
    FeatureEngineer,
)


@pytest.fixture
def sample_observation_data():
    """Create sample observation count data for 2 assets."""
    np.random.seed(42)
    n = 50
    return pd.DataFrame(
        {
            "asset_id": ["RIG-001"] * n + ["RIG-002"] * n,
            "obs_count": np.random.randint(0, 10, 2 * n).astype(float),
        }
    )


@pytest.fixture
def sample_label_data():
    np.random.seed(42)
    n = 50
    return pd.DataFrame(
        {
            "asset_id": ["RIG-001"] * n + ["RIG-002"] * n,
            "inc_count": np.random.randint(0, 2, 2 * n).astype(float),
        }
    )


class TestFeatureEngineer:
    def test_create_windows(self, sample_observation_data):
        fe = FeatureEngineer(window_size=10, step=1)
        windows, labels = fe.create_windows(sample_observation_data, labels=None)
        assert len(windows) > 0
        assert all(len(w) == 10 for w in windows)
        assert labels is None

    def test_create_windows_with_labels(
        self, sample_observation_data, sample_label_data
    ):
        fe = FeatureEngineer(window_size=10, step=1)
        windows, labels = fe.create_windows(
            sample_observation_data,
            labels=sample_label_data,
        )
        assert len(windows) == len(labels)

    def test_compute_statistical_features(self, sample_observation_data):
        fe = FeatureEngineer(window_size=10, step=5)
        windows, _ = fe.create_windows(sample_observation_data)
        features = fe.compute_statistical_features(windows)
        assert "mean" in features.columns
        assert "std" in features.columns
        assert "skewness" in features.columns
        assert "kurtosis" in features.columns
        assert "energy" in features.columns
        assert "gradient" in features.columns
        assert len(features) == len(windows)

    def test_compute_fft_features(self, sample_observation_data):
        fe = FeatureEngineer(window_size=10, step=5)
        windows, _ = fe.create_windows(sample_observation_data)
        features = fe.compute_fft_features(windows)
        assert "mean_fft" in features.columns
        assert "energy_fft" in features.columns
        assert len(features) == len(windows)

    def test_compute_all_features(self, sample_observation_data):
        fe = FeatureEngineer(window_size=10, step=5)
        windows, _ = fe.create_windows(sample_observation_data)
        features = fe.compute_all_features(windows)
        expected_cols = len(FeatureEngineer.STAT_FEATURE_NAMES) + len(
            FeatureEngineer.FFT_FEATURE_NAMES
        )
        assert len(features.columns) == expected_cols

    def test_create_labels_max(self, sample_observation_data, sample_label_data):
        fe = FeatureEngineer(window_size=10, step=5)
        _, labels = fe.create_windows(sample_observation_data, labels=sample_label_data)
        max_labels = fe.create_labels_max(labels)
        assert len(max_labels) == len(labels)

    def test_create_labels_last(self, sample_observation_data, sample_label_data):
        fe = FeatureEngineer(window_size=10, step=5)
        _, labels = fe.create_windows(sample_observation_data, labels=sample_label_data)
        last_labels = fe.create_labels_last(labels)
        assert len(last_labels) == len(labels)

    def test_feature_values_are_numeric(self, sample_observation_data):
        fe = FeatureEngineer(window_size=10, step=5)
        windows, _ = fe.create_windows(sample_observation_data)
        features = fe.compute_all_features(windows)
        assert features.dtypes.apply(lambda dt: np.issubdtype(dt, np.number)).all()
