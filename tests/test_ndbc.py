# ABOUTME: Tests for NDBC buoy data ingestion and wave scatter matrix (WRK-316).
# ABOUTME: Verifies NDBCClient facade, parse_stdmet_line, build_scatter_matrix,
# ABOUTME: filter_by_season, fit_weibull_hs, wave_rose, and parse_stdmet_file.
"""Tests for NDBC buoy data ingestion."""

import pathlib

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from worldenergydata.metocean.ndbc import (
    NDBCClient,
    build_scatter_matrix,
    filter_by_season,
    fit_weibull_hs,
    parse_stdmet_file,
    parse_stdmet_line,
    wave_rose,
)

# Sample NDBC data file for file-based tests
_SAMPLE_DATA_FILE = (
    pathlib.Path(__file__).parent / "test_data" / "ndbc" / "42001h2023.txt"
)


# ---------------------------------------------------------------------------
# NDBCClient initialisation
# ---------------------------------------------------------------------------

def test_ndbc_client_init():
    client = NDBCClient()
    assert client.base_url == "https://www.ndbc.noaa.gov"


def test_ndbc_client_has_get_station_list():
    """NDBCClient exposes get_station_list method."""
    client = NDBCClient()
    assert callable(getattr(client, "get_station_list", None))


def test_ndbc_client_has_get_stdmet():
    """NDBCClient exposes get_stdmet method."""
    client = NDBCClient()
    assert callable(getattr(client, "get_stdmet", None))


def test_ndbc_client_has_get_historical():
    """NDBCClient exposes get_historical method."""
    client = NDBCClient()
    assert callable(getattr(client, "get_historical", None))


# ---------------------------------------------------------------------------
# build_scatter_matrix
# ---------------------------------------------------------------------------

def test_build_scatter_matrix_empty():
    """Empty records return a zero-filled matrix."""
    matrix = build_scatter_matrix(
        [],
        hs_bins=[0, 1, 2, 3, 4, 5],
        tp_bins=[0, 4, 8, 12, 16, 20],
    )
    assert matrix.shape == (5, 5)
    assert matrix.sum() == 0


def test_build_scatter_matrix_returns_ndarray():
    """build_scatter_matrix returns a numpy ndarray."""
    matrix = build_scatter_matrix(
        [],
        hs_bins=[0, 1, 2, 3, 4, 5],
        tp_bins=[0, 4, 8, 12, 16, 20],
    )
    assert isinstance(matrix, np.ndarray)


def test_scatter_matrix_normalization():
    """Scatter matrix entries sum to 1.0 when normalized."""
    data = [{"hs": 1.5, "tp": 8.0}, {"hs": 2.5, "tp": 10.0}]
    matrix = build_scatter_matrix(data, normalize=True)
    assert abs(matrix.sum() - 1.0) < 1e-6


def test_scatter_matrix_counts_without_normalization():
    """Without normalization scatter matrix holds integer counts."""
    data = [
        {"hs": 0.5, "tp": 5.0},
        {"hs": 0.5, "tp": 5.0},
        {"hs": 1.5, "tp": 9.0},
    ]
    matrix = build_scatter_matrix(data, normalize=False)
    assert matrix.sum() == 3


def test_scatter_matrix_default_bins():
    """build_scatter_matrix works with default bins."""
    data = [{"hs": 1.0, "tp": 7.0}]
    matrix = build_scatter_matrix(data)
    assert matrix.ndim == 2
    assert matrix.sum() >= 1


def test_scatter_matrix_records_outside_bins_ignored():
    """Records outside the bin range are silently ignored."""
    data = [{"hs": 99.0, "tp": 99.0}]
    matrix = build_scatter_matrix(
        data,
        hs_bins=[0, 1, 2, 3],
        tp_bins=[0, 5, 10, 15],
    )
    assert matrix.sum() == 0


def test_scatter_matrix_missing_keys_ignored():
    """Records missing hs or tp keys are skipped."""
    data = [{"hs": 1.0}, {"tp": 8.0}, {"hs": 1.5, "tp": 9.0}]
    matrix = build_scatter_matrix(data, normalize=False)
    assert matrix.sum() == 1


def test_scatter_matrix_none_values_ignored():
    """Records with None hs or tp are skipped."""
    data = [{"hs": None, "tp": 8.0}, {"hs": 1.5, "tp": None}]
    matrix = build_scatter_matrix(data, normalize=False)
    assert matrix.sum() == 0


# ---------------------------------------------------------------------------
# parse_stdmet_line
# ---------------------------------------------------------------------------

def test_parse_stdmet_line_valid():
    """Parse a standard NDBC stdmet line."""
    line = "2023 01 15 00 30  1.2  8  9.5 180 15.2"
    record = parse_stdmet_line(line)
    assert record is not None


def test_parse_stdmet_line_returns_dict():
    """parse_stdmet_line returns a dict with expected keys."""
    line = "2024 01 15 12 00 180  5.0  6.0   1.2   8.0   5.5 170  1015.0  22.5  24.0  18.0   MM   MM    MM"
    record = parse_stdmet_line(line)
    assert isinstance(record, dict)
    assert "observation_time" in record


def test_parse_stdmet_line_wave_fields():
    """parse_stdmet_line extracts wave height and period."""
    # Format: YY MM DD hh mm WDIR WSPD GST WVHT DPD APD MWD PRES ATMP WTMP DEWP VIS PTDY TIDE
    line = "2024 06 01 12 00 270  8.0  9.5   2.3  10.0   7.1 265  1013.0  20.0  22.0  16.0   MM   MM    MM"
    record = parse_stdmet_line(line)
    assert record is not None
    assert record.get("hs") == pytest.approx(2.3)
    assert record.get("dpd") == pytest.approx(10.0)


def test_parse_stdmet_line_missing_values():
    """parse_stdmet_line maps MM sentinel to None."""
    line = "2024 01 15 12 00 MM  MM  MM   MM   MM   MM  MM  MM  MM  MM  MM  MM  MM  MM"
    record = parse_stdmet_line(line)
    assert record is not None
    assert record.get("hs") is None


def test_parse_stdmet_line_comment_line_returns_none():
    """Header/comment lines beginning with # return None."""
    line = "#YY  MM DD hh mm WDIR WSPD GST  WVHT   DPD"
    record = parse_stdmet_line(line)
    assert record is None


def test_parse_stdmet_line_empty_returns_none():
    """Empty string returns None."""
    assert parse_stdmet_line("") is None


def test_parse_stdmet_line_too_short_returns_none():
    """Fewer than 5 tokens returns None."""
    assert parse_stdmet_line("2024 01 15") is None


# ---------------------------------------------------------------------------
# filter_by_season
# ---------------------------------------------------------------------------

def test_filter_by_season_returns_dataframe():
    """filter_by_season returns a pandas DataFrame."""
    df = pd.DataFrame({
        "time": pd.date_range("2020-01-01", periods=12, freq="MS"),
        "hs": np.ones(12),
    })
    result = filter_by_season(df, months=[1, 2, 3], time_col="time")
    assert isinstance(result, pd.DataFrame)


def test_filter_by_season_correct_months():
    """filter_by_season keeps only rows in specified months."""
    df = pd.DataFrame({
        "time": pd.date_range("2020-01-01", periods=12, freq="MS"),
        "hs": np.arange(12, dtype=float),
    })
    result = filter_by_season(df, months=[6, 7, 8], time_col="time")
    assert len(result) == 3
    assert all(result["time"].dt.month.isin([6, 7, 8]))


def test_filter_by_season_empty_months_returns_empty():
    """Passing an empty months list returns an empty DataFrame."""
    df = pd.DataFrame({
        "time": pd.date_range("2020-01-01", periods=12, freq="MS"),
        "hs": np.ones(12),
    })
    result = filter_by_season(df, months=[], time_col="time")
    assert len(result) == 0


def test_filter_by_season_all_months():
    """Passing all 12 months returns the full DataFrame."""
    df = pd.DataFrame({
        "time": pd.date_range("2020-01-01", periods=12, freq="MS"),
        "hs": np.ones(12),
    })
    result = filter_by_season(df, months=list(range(1, 13)), time_col="time")
    assert len(result) == 12


def test_filter_by_season_default_time_col():
    """filter_by_season uses 'time' as default column name."""
    df = pd.DataFrame({
        "time": pd.date_range("2020-01-01", periods=4, freq="QS"),
        "hs": np.ones(4),
    })
    # Should not raise even without explicit time_col argument
    result = filter_by_season(df, months=[1])
    assert isinstance(result, pd.DataFrame)


# ---------------------------------------------------------------------------
# parse_stdmet_file
# ---------------------------------------------------------------------------

def test_parse_stdmet_file_returns_list():
    """parse_stdmet_file returns a list of dicts."""
    records = parse_stdmet_file(_SAMPLE_DATA_FILE)
    assert isinstance(records, list)


def test_parse_stdmet_file_nonempty():
    """parse_stdmet_file returns at least one record from the sample file."""
    records = parse_stdmet_file(_SAMPLE_DATA_FILE)
    assert len(records) > 0


def test_parse_stdmet_file_has_hs():
    """Records from parse_stdmet_file contain 'hs' key."""
    records = parse_stdmet_file(_SAMPLE_DATA_FILE)
    assert all("hs" in r for r in records)


def test_parse_stdmet_file_string_path():
    """parse_stdmet_file accepts a plain string path."""
    records = parse_stdmet_file(str(_SAMPLE_DATA_FILE))
    assert isinstance(records, list)


def test_parse_stdmet_file_missing_path_returns_empty():
    """parse_stdmet_file returns empty list when file does not exist."""
    records = parse_stdmet_file("/nonexistent/path/to/file.txt")
    assert records == []


# ---------------------------------------------------------------------------
# fit_weibull_hs
# ---------------------------------------------------------------------------

def _hs_series(n: int = 200, seed: int = 0) -> list:
    """Generate synthetic Hs values (positive float list) for Weibull tests."""
    rng = np.random.default_rng(seed)
    return list(rng.weibull(2.0, size=n) * 2.0 + 0.3)


def test_fit_weibull_hs_returns_dict():
    """fit_weibull_hs returns a dict."""
    result = fit_weibull_hs(_hs_series())
    assert isinstance(result, dict)


def test_fit_weibull_2p_keys():
    """2-parameter Weibull result has 'scale' and 'shape' keys."""
    result = fit_weibull_hs(_hs_series(), n_params=2)
    assert "scale" in result
    assert "shape" in result


def test_fit_weibull_3p_keys():
    """3-parameter Weibull result has 'scale', 'shape', and 'loc' keys."""
    result = fit_weibull_hs(_hs_series(), n_params=3)
    assert "scale" in result
    assert "shape" in result
    assert "loc" in result


def test_fit_weibull_scale_positive():
    """Weibull scale parameter must be positive."""
    result = fit_weibull_hs(_hs_series(), n_params=2)
    assert result["scale"] > 0


def test_fit_weibull_shape_positive():
    """Weibull shape parameter must be positive."""
    result = fit_weibull_hs(_hs_series(), n_params=2)
    assert result["shape"] > 0


def test_fit_weibull_n_params_2_is_default():
    """Default n_params is 2 (2-parameter Weibull)."""
    r2 = fit_weibull_hs(_hs_series())
    r2_explicit = fit_weibull_hs(_hs_series(), n_params=2)
    assert set(r2.keys()) == set(r2_explicit.keys())


def test_fit_weibull_invalid_n_params_raises():
    """n_params other than 2 or 3 raises ValueError."""
    with pytest.raises(ValueError):
        fit_weibull_hs(_hs_series(), n_params=4)


def test_fit_weibull_empty_raises():
    """Empty Hs list raises ValueError."""
    with pytest.raises(ValueError):
        fit_weibull_hs([])


def test_fit_weibull_too_few_points_raises():
    """Fewer than 3 data points raises ValueError."""
    with pytest.raises(ValueError):
        fit_weibull_hs([1.0, 2.0])


def test_fit_weibull_hs_from_file():
    """fit_weibull_hs works on Hs values parsed from sample data file."""
    records = parse_stdmet_file(_SAMPLE_DATA_FILE)
    hs_values = [r["hs"] for r in records if r.get("hs") is not None]
    assert len(hs_values) > 0
    result = fit_weibull_hs(hs_values, n_params=2)
    assert "scale" in result and "shape" in result


# ---------------------------------------------------------------------------
# wave_rose
# ---------------------------------------------------------------------------

def _wave_records(n: int = 100, seed: int = 42) -> list:
    """Generate synthetic records with hs and mwd."""
    rng = np.random.default_rng(seed)
    hs_vals = rng.weibull(2.0, size=n) * 2.0 + 0.5
    mwd_vals = rng.uniform(0, 360, size=n)
    return [{"hs": float(h), "mwd": float(d)} for h, d in zip(hs_vals, mwd_vals)]


def test_wave_rose_returns_dict():
    """wave_rose returns a dict."""
    result = wave_rose(_wave_records())
    assert isinstance(result, dict)


def test_wave_rose_has_sectors():
    """wave_rose result has 'sectors' key."""
    result = wave_rose(_wave_records())
    assert "sectors" in result


def test_wave_rose_has_mean_hs():
    """wave_rose result has 'mean_hs' key."""
    result = wave_rose(_wave_records())
    assert "mean_hs" in result


def test_wave_rose_sector_count_default():
    """Default wave_rose uses 8 directional sectors."""
    result = wave_rose(_wave_records())
    assert len(result["sectors"]) == 8


def test_wave_rose_sector_count_custom():
    """wave_rose respects custom n_sectors argument."""
    result = wave_rose(_wave_records(), n_sectors=16)
    assert len(result["sectors"]) == 16


def test_wave_rose_sectors_are_strings():
    """wave_rose sector keys are strings describing direction ranges."""
    result = wave_rose(_wave_records())
    assert all(isinstance(s, str) for s in result["sectors"])


def test_wave_rose_mean_hs_nonnegative():
    """wave_rose mean_hs values are non-negative."""
    result = wave_rose(_wave_records())
    assert all(v >= 0 for v in result["mean_hs"].values())


def test_wave_rose_frequency_sums_to_one():
    """wave_rose frequency values sum to 1.0."""
    result = wave_rose(_wave_records())
    assert "frequency" in result
    total = sum(result["frequency"].values())
    assert abs(total - 1.0) < 1e-6


def test_wave_rose_empty_records_returns_empty_sectors():
    """wave_rose with empty records returns sectors with zero mean_hs."""
    result = wave_rose([])
    assert isinstance(result, dict)
    assert all(v == 0.0 for v in result["mean_hs"].values())


def test_wave_rose_records_missing_mwd_skipped():
    """wave_rose skips records without 'mwd' key."""
    records = [{"hs": 1.5}, {"hs": 2.0}, {"hs": 1.8, "mwd": 180.0}]
    result = wave_rose(records)
    assert isinstance(result, dict)
    # One valid record: mwd=180 => sector index int(180/45)=4 => "180-225deg"
    assert result["mean_hs"].get("180-225deg") == pytest.approx(1.8, rel=1e-4)


def test_wave_rose_from_file():
    """wave_rose works on records parsed from sample data file."""
    records = parse_stdmet_file(_SAMPLE_DATA_FILE)
    result = wave_rose(records)
    assert isinstance(result, dict)
    assert "sectors" in result
