"""Tests for the parquet storage module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from worldenergydata.vessel_fleet.storage.parquet import ParquetStore


class TestParquetStoreInit:
    """Constructor and path handling."""

    def test_creates_directory(self, tmp_path):
        store_dir = tmp_path / "fleet_data"
        store = ParquetStore(base_dir=store_dir)
        assert store.base_dir.exists()

    def test_accepts_string_path(self, tmp_path):
        store = ParquetStore(base_dir=str(tmp_path))
        assert isinstance(store.base_dir, Path)


class TestParquetRoundTrip:
    """Save and load data round-trips."""

    def test_save_and_load_records(self, tmp_path):
        store = ParquetStore(base_dir=tmp_path)
        records = [
            {"VESSEL_NAME": "DEEPWATER TITAN", "YEAR_BUILT": 2014, "LOA_M": 228.0},
            {"VESSEL_NAME": "SLEIPNIR", "YEAR_BUILT": 2019, "LOA_M": 220.0},
        ]
        store.save(records, filename="test_fleet.parquet")
        loaded = store.load("test_fleet.parquet")
        assert len(loaded) == 2
        assert loaded[0]["VESSEL_NAME"] == "DEEPWATER TITAN"
        assert loaded[1]["VESSEL_NAME"] == "SLEIPNIR"
        assert loaded[0]["YEAR_BUILT"] == 2014
        assert loaded[0]["LOA_M"] == 228.0

    def test_save_and_load_empty(self, tmp_path):
        store = ParquetStore(base_dir=tmp_path)
        store.save([], filename="empty.parquet")
        loaded = store.load("empty.parquet")
        assert loaded == []

    def test_load_nonexistent_returns_empty(self, tmp_path):
        store = ParquetStore(base_dir=tmp_path)
        loaded = store.load("nonexistent.parquet")
        assert loaded == []

    def test_preserves_none_values(self, tmp_path):
        store = ParquetStore(base_dir=tmp_path)
        records = [
            {"VESSEL_NAME": "TEST", "YEAR_BUILT": None, "LOA_M": None},
        ]
        store.save(records, filename="nulls.parquet")
        loaded = store.load("nulls.parquet")
        assert loaded[0]["YEAR_BUILT"] is None
        assert loaded[0]["LOA_M"] is None

    def test_save_to_subdirectory(self, tmp_path):
        store = ParquetStore(base_dir=tmp_path)
        records = [{"VESSEL_NAME": "TEST"}]
        store.save(records, filename="sub/dir/test.parquet")
        loaded = store.load("sub/dir/test.parquet")
        assert len(loaded) == 1

    def test_file_exists_after_save(self, tmp_path):
        store = ParquetStore(base_dir=tmp_path)
        records = [{"VESSEL_NAME": "TEST"}]
        store.save(records, filename="check.parquet")
        assert (tmp_path / "check.parquet").exists()


class TestParquetCSVExport:
    """CSV export functionality."""

    def test_export_csv(self, tmp_path):
        store = ParquetStore(base_dir=tmp_path)
        records = [
            {"VESSEL_NAME": "DEEPWATER TITAN", "YEAR_BUILT": 2014},
            {"VESSEL_NAME": "SLEIPNIR", "YEAR_BUILT": 2019},
        ]
        store.save(records, filename="fleet.parquet")
        store.export_csv("fleet.parquet", "fleet.csv")
        csv_path = tmp_path / "fleet.csv"
        assert csv_path.exists()
        content = csv_path.read_text()
        assert "DEEPWATER TITAN" in content
        assert "SLEIPNIR" in content
