"""Tests for the EIA US refresh adapter wired to EIAIngestionSync."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from worldenergydata.scheduler.jobs.base import JobResult


class TestEiaUsRefreshJob:
    """Tests for the wired EIA adapter."""

    @patch("worldenergydata.scheduler.jobs.eia_us_refresh.EIAIngestionSync")
    def test_run_calls_run_all_and_returns_success(self, mock_sync_cls, tmp_path):
        """EiaUsRefreshJob.run() calls EIAIngestionSync.run_all() and returns
        JobResult with status='success' and records_updated = sum of records_written."""
        from worldenergydata.scheduler.jobs.eia_us_refresh import EiaUsRefreshJob

        mock_instance = MagicMock()
        mock_instance.run_all.return_value = [
            {"feed": "petroleum_weekly", "records_written": 10, "latest_period": "2024-01-01"},
            {"feed": "gas_storage_weekly", "records_written": 5, "latest_period": "2024-01-08"},
        ]
        mock_instance.output_dir = tmp_path
        mock_sync_cls.return_value = mock_instance

        job = EiaUsRefreshJob()
        result = job.run({"api_key": "test-key-1234567890", "output_dir": str(tmp_path)})

        mock_instance.run_all.assert_called_once()
        assert isinstance(result, JobResult)
        assert result.status == "success"
        assert result.records_updated == 15

    @patch("worldenergydata.scheduler.jobs.eia_us_refresh.EIAIngestionSync")
    def test_run_passes_api_key_from_config(self, mock_sync_cls, tmp_path):
        """EiaUsRefreshJob.run() reads api_key from config dict and passes to EIAIngestionSync."""
        from worldenergydata.scheduler.jobs.eia_us_refresh import EiaUsRefreshJob

        mock_instance = MagicMock()
        mock_instance.run_all.return_value = []
        mock_instance.output_dir = tmp_path
        mock_sync_cls.return_value = mock_instance

        job = EiaUsRefreshJob()
        job.run({"api_key": "my-secret-key-12345", "output_dir": str(tmp_path)})

        mock_sync_cls.assert_called_once()
        call_kwargs = mock_sync_cls.call_args
        assert call_kwargs[1]["api_key"] == "my-secret-key-12345" or call_kwargs[0][0] == "my-secret-key-12345"

    @patch("worldenergydata.scheduler.jobs.eia_us_refresh.EIAIngestionSync")
    def test_run_returns_failure_on_exception(self, mock_sync_cls, tmp_path):
        """On EIAIngestionSync exception, returns JobResult with status='failure'
        and error_msg containing the exception message."""
        from worldenergydata.scheduler.jobs.eia_us_refresh import EiaUsRefreshJob

        mock_instance = MagicMock()
        mock_instance.run_all.side_effect = RuntimeError("Connection timed out")
        mock_sync_cls.return_value = mock_instance

        job = EiaUsRefreshJob()
        result = job.run({"api_key": "test-key-1234567890", "output_dir": str(tmp_path)})

        assert result.status == "failure"
        assert "Connection timed out" in result.error_msg
        assert result.records_updated == 0

    @patch("worldenergydata.scheduler.jobs.eia_us_refresh.EIAIngestionSync")
    def test_run_writes_parquet_for_jsonl_files(self, mock_sync_cls, tmp_path):
        """After successful ingestion, calls write_parquet for each JSONL file that has data."""
        from worldenergydata.scheduler.jobs.eia_us_refresh import EiaUsRefreshJob

        # Create a mock JSONL file in the output directory
        jsonl_path = tmp_path / "eia_petroleum_weekly.jsonl"
        records = [
            {"period": "2024-01-01", "value": 100.5, "_feed": "petroleum_weekly"},
            {"period": "2024-01-08", "value": 200.3, "_feed": "petroleum_weekly"},
        ]
        with jsonl_path.open("w") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")

        mock_instance = MagicMock()
        mock_instance.run_all.return_value = [
            {"feed": "petroleum_weekly", "records_written": 2, "latest_period": "2024-01-08"},
        ]
        mock_instance.output_dir = tmp_path
        mock_sync_cls.return_value = mock_instance

        job = EiaUsRefreshJob()
        result = job.run({"api_key": "test-key-1234567890", "output_dir": str(tmp_path)})

        assert result.status == "success"
        # Check that a parquet file was created
        parquet_files = list(tmp_path.glob("*.parquet"))
        assert len(parquet_files) >= 1, f"Expected parquet files, found: {parquet_files}"
        # Verify the parquet content
        df = pd.read_parquet(parquet_files[0])
        assert len(df) == 2

    @patch("worldenergydata.scheduler.jobs.eia_us_refresh.EIAIngestionSync")
    def test_output_dir_defaults_to_data_eia(self, mock_sync_cls, tmp_path):
        """Output directory defaults to 'data/eia' when not specified in config."""
        from worldenergydata.scheduler.jobs.eia_us_refresh import EiaUsRefreshJob

        mock_instance = MagicMock()
        mock_instance.run_all.return_value = []
        mock_instance.output_dir = Path("data/eia")
        mock_sync_cls.return_value = mock_instance

        job = EiaUsRefreshJob()
        job.run({"api_key": "test-key-1234567890"})

        call_kwargs = mock_sync_cls.call_args[1]
        output_dir = call_kwargs.get("output_dir", None)
        assert output_dir is not None
        assert str(output_dir) == "data/eia"
