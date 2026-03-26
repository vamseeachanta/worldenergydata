"""Tests for SODIR refresh adapter — wired to SodirAPIClient with Parquet output."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from worldenergydata.scheduler.jobs.sodir_refresh import (
    SODIR_DATASETS,
    SodirRefreshJob,
)
from worldenergydata.sodir.errors import SodirAPIError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_BLOCKS = [
    {"npdidBlock": "1", "blockName": "Block A", "blockArea": "North Sea"},
    {"npdidBlock": "2", "blockName": "Block B", "blockArea": "Norwegian Sea"},
]

FAKE_WELLBORES = [
    {"npdidWellbore": "100", "wellboreName": "Well-1", "wellboreType": "EXPLORATION"},
    {"npdidWellbore": "101", "wellboreName": "Well-2", "wellboreType": "DEVELOPMENT"},
    {"npdidWellbore": "102", "wellboreName": "Well-3", "wellboreType": "EXPLORATION"},
]

FAKE_FIELDS = [
    {"npdidField": "500", "fieldName": "Troll", "fieldOperator": "Equinor"},
]


def _mock_client_get(endpoint, params=None):
    """Return fake data based on table_id query parameter."""
    table = params.get("table") if params else None
    data_map = {
        "1001": FAKE_BLOCKS,
        "5000": FAKE_WELLBORES,
        "7100": FAKE_FIELDS,
    }
    return {"data": data_map.get(table, [])}


@pytest.fixture
def job():
    return SodirRefreshJob()


@pytest.fixture
def config(tmp_path):
    return {
        "base_url": "https://factmaps.sodir.no",
        "output_dir": str(tmp_path),
    }


# ---------------------------------------------------------------------------
# Test 1: Creates SodirAPIClient with factmaps URL and fetches key endpoints
# ---------------------------------------------------------------------------


@patch("worldenergydata.scheduler.jobs.sodir_refresh.SodirAPIClient")
def test_creates_client_and_fetches_endpoints(mock_cls, job, config):
    """SodirRefreshJob.run() creates SodirAPIClient with factmaps base URL
    and fetches data from blocks, wellbores, and fields endpoints."""
    mock_instance = MagicMock()
    mock_instance.get.side_effect = _mock_client_get
    mock_cls.return_value = mock_instance

    result = job.run(config)

    mock_cls.assert_called_once_with(base_url="https://factmaps.sodir.no")
    assert result.status == "success"
    # Should have called get() once per dataset
    assert mock_instance.get.call_count == len(SODIR_DATASETS)


# ---------------------------------------------------------------------------
# Test 2: Converts fetched data to DataFrames and writes Parquet files
# ---------------------------------------------------------------------------


@patch("worldenergydata.scheduler.jobs.sodir_refresh.SodirAPIClient")
def test_writes_parquet_files(mock_cls, job, config, tmp_path):
    """SodirRefreshJob.run() converts data to DataFrame and writes Parquet."""
    mock_instance = MagicMock()
    mock_instance.get.side_effect = _mock_client_get
    mock_cls.return_value = mock_instance

    result = job.run(config)

    for dataset_key, filename in SODIR_DATASETS.items():
        parquet_path = tmp_path / filename
        assert parquet_path.exists(), f"Missing {filename}"
        df = pd.read_parquet(parquet_path)
        assert len(df) > 0, f"Empty DataFrame for {dataset_key}"


# ---------------------------------------------------------------------------
# Test 3: Partial failure — one endpoint fails, others continue
# ---------------------------------------------------------------------------


@patch("worldenergydata.scheduler.jobs.sodir_refresh.SodirAPIClient")
def test_partial_failure_continues(mock_cls, job, config, tmp_path):
    """On API error for one endpoint, adapter logs warning and continues."""

    def _partial_fail(endpoint, params=None):
        table = params.get("table") if params else None
        if table == "5000":
            raise SodirAPIError("Connection timeout for wellbores")
        return _mock_client_get(endpoint, params)

    mock_instance = MagicMock()
    mock_instance.get.side_effect = _partial_fail
    mock_cls.return_value = mock_instance

    result = job.run(config)

    # Still succeeds overall (partial)
    assert result.status == "success"
    # Blocks and fields written
    assert (tmp_path / "sodir_blocks.parquet").exists()
    assert (tmp_path / "sodir_fields.parquet").exists()
    # Wellbores NOT written
    assert not (tmp_path / "sodir_wellbores.parquet").exists()


# ---------------------------------------------------------------------------
# Test 4: All endpoints failing returns status="failure"
# ---------------------------------------------------------------------------


@patch("worldenergydata.scheduler.jobs.sodir_refresh.SodirAPIClient")
def test_all_endpoints_fail_returns_failure(mock_cls, job, config):
    """On all endpoints failing, returns status='failure'."""
    mock_instance = MagicMock()
    mock_instance.get.side_effect = SodirAPIError("Server unreachable")
    mock_cls.return_value = mock_instance

    result = job.run(config)

    assert result.status == "failure"
    assert result.records_updated == 0
    assert result.error_msg is not None


# ---------------------------------------------------------------------------
# Test 5: records_updated equals total rows across successful endpoints
# ---------------------------------------------------------------------------


@patch("worldenergydata.scheduler.jobs.sodir_refresh.SodirAPIClient")
def test_records_updated_counts_all_rows(mock_cls, job, config):
    """records_updated equals total rows across all successfully fetched endpoints."""
    mock_instance = MagicMock()
    mock_instance.get.side_effect = _mock_client_get
    mock_cls.return_value = mock_instance

    result = job.run(config)

    expected_total = len(FAKE_BLOCKS) + len(FAKE_WELLBORES) + len(FAKE_FIELDS)
    assert result.records_updated == expected_total
