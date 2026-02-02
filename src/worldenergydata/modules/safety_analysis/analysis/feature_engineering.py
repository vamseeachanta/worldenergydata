"""
Feature Engineering for Safety Time Series

Compute 30+ statistical and FFT features from windowed time series
for downstream ML classification tasks.

Ported from ENIGMA sshe_lib_feature_engineering.py.
"""

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import find_peaks


class FeatureEngineer:
    """
    Compute statistical and FFT features from windowed time series.

    Creates sliding windows over observation/incident time series and
    extracts features for ML classification. Features include:
    - Statistical: mean, std, median, IQR, skewness, kurtosis
    - Temporal: gradient, argmax, argmin
    - Frequency: FFT-based features (mean, std, peaks, energy)
    - Signal: peaks, energy

    Args:
        window_size: Number of time steps per window.
        step: Step size for sliding the window.
    """

    STAT_FEATURE_NAMES = [
        "mean",
        "std",
        "aad",
        "min",
        "max",
        "max_min_diff",
        "median",
        "mad",
        "IQR",
        "mean_pos_count",
        "skewness",
        "peaks",
        "kurtosis",
        "energy",
        "gradient",
        "argmax",
        "argmin",
        "arg_diff",
    ]

    FFT_FEATURE_NAMES = [
        "mean_fft",
        "std_fft",
        "mean_aad_fft",
        "min_fft",
        "max_fft",
        "diff_fft",
        "median_fft",
        "median_aad_fft",
        "IQR_fft",
        "pos_count_fft",
        "peaks_fft",
        "skewness_fft",
        "kurtosis_fft",
        "energy_fft",
    ]

    def __init__(self, window_size: int = 10, step: int = 1) -> None:
        self.window_size = window_size
        self.step = step

    def create_windows(
        self,
        values: pd.DataFrame,
        labels: Optional[pd.DataFrame] = None,
        value_column: str = "obs_count",
        label_column: str = "inc_count",
        asset_id_column: str = "asset_id",
    ) -> Tuple[List[np.ndarray], Optional[List[np.ndarray]]]:
        """
        Create sliding windows over the data, optionally with labels.

        Args:
            values: DataFrame with observation counts per asset.
            labels: Optional DataFrame with incident labels per asset.
            value_column: Column name for observation values.
            label_column: Column name for label values.
            asset_id_column: Column name for asset grouping.

        Returns:
            Tuple of (windowed_values, windowed_labels or None).
        """
        windowed_values = []
        windowed_labels = [] if labels is not None else None

        for asset in values[asset_id_column].unique():
            asset_values = values[values[asset_id_column] == asset][value_column].values

            if labels is not None:
                asset_labels = labels[labels[asset_id_column] == asset][
                    label_column
                ].values
            else:
                asset_labels = None

            for i in range(0, len(asset_values) - self.window_size, self.step):
                window = asset_values[i : i + self.window_size]
                windowed_values.append(window)

                if asset_labels is not None and windowed_labels is not None:
                    label_window = asset_labels[i : i + self.window_size]
                    windowed_labels.append(label_window)

        return windowed_values, windowed_labels

    def compute_statistical_features(
        self, windowed_values: List[np.ndarray]
    ) -> pd.DataFrame:
        """
        Compute statistical features from windowed time series.

        Returns DataFrame with one row per window and columns for each feature.
        """
        series = pd.Series(windowed_values, dtype=object)
        features = pd.DataFrame()

        features["mean"] = series.apply(lambda x: x.mean())
        features["std"] = series.apply(lambda x: x.std())
        features["aad"] = series.apply(lambda x: np.mean(np.absolute(x - np.mean(x))))
        features["min"] = series.apply(lambda x: x.min())
        features["max"] = series.apply(lambda x: x.max())
        features["max_min_diff"] = features["max"] - features["min"]
        features["median"] = series.apply(lambda x: np.median(x))
        features["mad"] = series.apply(
            lambda x: np.median(np.absolute(x - np.median(x)))
        )
        features["IQR"] = series.apply(
            lambda x: np.percentile(x, 75) - np.percentile(x, 25)
        )
        features["mean_pos_count"] = series.apply(lambda x: np.sum(x > np.mean(x)))
        features["skewness"] = series.apply(lambda x: stats.skew(x))
        features["peaks"] = series.apply(lambda x: len(find_peaks(x)[0]))
        features["kurtosis"] = series.apply(lambda x: stats.kurtosis(x))
        features["energy"] = series.apply(lambda x: np.sum((x**2) / self.window_size))
        features["gradient"] = series.apply(lambda x: (x[-1] - x[0]) / self.window_size)
        features["argmax"] = series.apply(lambda x: np.argmax(x))
        features["argmin"] = series.apply(lambda x: np.argmin(x))
        features["arg_diff"] = abs(features["argmax"] - features["argmin"])

        return features

    def compute_fft_features(self, windowed_values: List[np.ndarray]) -> pd.DataFrame:
        """Compute FFT-based features from windowed time series."""
        series = pd.Series(windowed_values, dtype=object)
        fft_series = series.apply(lambda x: np.abs(np.fft.fft(x))[1:])

        features = pd.DataFrame()
        features["mean_fft"] = fft_series.apply(lambda x: np.mean(x))
        features["std_fft"] = fft_series.apply(lambda x: np.std(x))
        features["mean_aad_fft"] = fft_series.apply(
            lambda x: np.mean(np.absolute(x - np.mean(x)))
        )
        features["min_fft"] = fft_series.apply(lambda x: np.min(x))
        features["max_fft"] = fft_series.apply(lambda x: np.max(x))
        features["diff_fft"] = features["max_fft"] - features["min_fft"]
        features["median_fft"] = fft_series.apply(lambda x: np.median(x))
        features["median_aad_fft"] = fft_series.apply(
            lambda x: np.median(np.absolute(x - np.median(x)))
        )
        features["IQR_fft"] = fft_series.apply(
            lambda x: np.percentile(x, 75) - np.percentile(x, 25)
        )
        features["pos_count_fft"] = fft_series.apply(lambda x: np.sum(x > np.mean(x)))
        features["peaks_fft"] = fft_series.apply(lambda x: len(find_peaks(x)[0]))
        features["skewness_fft"] = fft_series.apply(lambda x: stats.skew(x))
        features["kurtosis_fft"] = fft_series.apply(lambda x: stats.kurtosis(x))
        features["energy_fft"] = fft_series.apply(
            lambda x: np.sum((x**2) / self.window_size)
        )

        return features

    def compute_all_features(self, windowed_values: List[np.ndarray]) -> pd.DataFrame:
        """Compute all statistical and FFT features."""
        stat_features = self.compute_statistical_features(windowed_values)
        fft_features = self.compute_fft_features(windowed_values)
        return pd.concat([stat_features, fft_features], axis=1)

    def create_labels_max(self, windowed_labels: List[np.ndarray]) -> pd.Series:
        """Create labels using the max value in each window."""
        return pd.Series(windowed_labels, dtype=object).apply(lambda x: np.max(x))

    def create_labels_last(self, windowed_labels: List[np.ndarray]) -> pd.Series:
        """Create labels using the last value in each window."""
        return pd.Series(windowed_labels, dtype=object).apply(lambda x: x[-1])
