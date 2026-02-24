# ABOUTME: Tests for NDBC buoy data ingestion and wave scatter matrix (WRK-316).
# ABOUTME: Verifies NDBCClient facade, parse_stdmet_line, build_scatter_matrix, filter_by_season.
"""Tests for NDBC buoy data ingestion."""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from worldenergydata.metocean.ndbc import (
    NDBCClient,
    build_scatter_matrix,
    filter_by_season,
    parse_stdmet_line,
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
