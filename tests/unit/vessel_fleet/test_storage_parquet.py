"""Tests for vessel fleet ParquetStore save, load, export_csv, list_files."""

import pytest

from worldenergydata.vessel_fleet.storage.parquet import ParquetStore


class TestParquetStoreInit:
    def test_creates_directory(self, tmp_path):
        store_dir = tmp_path / "store"
        store = ParquetStore(store_dir)
        assert store_dir.exists()

    def test_base_dir(self, tmp_path):
        store = ParquetStore(tmp_path)
        assert store.base_dir == tmp_path


class TestSave:
    def test_save_records(self, tmp_path):
        store = ParquetStore(tmp_path)
        records = [
            {"name": "Rig A", "depth": 10000},
            {"name": "Rig B", "depth": 5000},
        ]
        path = store.save(records, "rigs.parquet")
        assert path.exists()

    def test_save_empty(self, tmp_path):
        store = ParquetStore(tmp_path)
        path = store.save([], "empty.parquet")
        assert path.exists()

    def test_save_returns_path(self, tmp_path):
        store = ParquetStore(tmp_path)
        path = store.save([{"a": 1}], "test.parquet")
        assert path == tmp_path / "test.parquet"


class TestLoad:
    def test_load_records(self, tmp_path):
        store = ParquetStore(tmp_path)
        records = [{"name": "Rig A", "depth": 10000}]
        store.save(records, "rigs.parquet")
        loaded = store.load("rigs.parquet")
        assert len(loaded) == 1
        assert loaded[0]["name"] == "Rig A"
        assert loaded[0]["depth"] == 10000

    def test_load_missing_file(self, tmp_path):
        store = ParquetStore(tmp_path)
        loaded = store.load("nonexistent.parquet")
        assert loaded == []

    def test_load_empty_file(self, tmp_path):
        store = ParquetStore(tmp_path)
        store.save([], "empty.parquet")
        loaded = store.load("empty.parquet")
        assert loaded == []

    def test_roundtrip(self, tmp_path):
        store = ParquetStore(tmp_path)
        records = [
            {"name": "A", "val": 1},
            {"name": "B", "val": 2},
        ]
        store.save(records, "data.parquet")
        loaded = store.load("data.parquet")
        assert len(loaded) == 2
        names = {r["name"] for r in loaded}
        assert names == {"A", "B"}


class TestExportCsv:
    def test_export(self, tmp_path):
        store = ParquetStore(tmp_path)
        store.save([{"name": "Rig"}], "rigs.parquet")
        csv_path = store.export_csv("rigs.parquet", "rigs.csv")
        assert csv_path.exists()
        content = csv_path.read_text()
        assert "Rig" in content


class TestListFiles:
    def test_list_files(self, tmp_path):
        store = ParquetStore(tmp_path)
        store.save([{"a": 1}], "file1.parquet")
        store.save([{"b": 2}], "file2.parquet")
        files = store.list_files()
        assert len(files) == 2

    def test_list_empty(self, tmp_path):
        store = ParquetStore(tmp_path)
        files = store.list_files()
        assert files == []
