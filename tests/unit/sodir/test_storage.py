"""Tests for SODIR data storage module."""

import json

import pandas as pd
import pytest

from worldenergydata.sodir.storage import DataStorage


class TestDataStorageInit:
    def test_init_with_string(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        assert storage.base_path == tmp_path / "sodir"
        assert (tmp_path / "sodir" / "raw").is_dir()
        assert (tmp_path / "sodir" / "processed").is_dir()

    def test_init_with_dict(self, tmp_path):
        storage = DataStorage({"base_path": str(tmp_path / "sodir")})
        assert storage.base_path == tmp_path / "sodir"

    def test_init_with_dict_path_key(self, tmp_path):
        storage = DataStorage({"path": str(tmp_path / "sodir")})
        assert storage.base_path == tmp_path / "sodir"

    def test_init_default(self):
        storage = DataStorage()
        assert str(storage.base_path) == "data/sodir"

    def test_creates_subdirectories(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        for subdir in ["raw", "processed", "analysis", "cache", "exports"]:
            assert (tmp_path / "sodir" / subdir).is_dir()


class TestSaveRawData:
    def test_save_dict(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        path = storage.save_raw_data({"key": "value"}, "fields", "20240101")
        assert "raw" in path
        with open(path) as f:
            data = json.load(f)
        assert data["key"] == "value"

    def test_save_list(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        path = storage.save_raw_data([1, 2, 3], "wellbores", "20240101")
        with open(path) as f:
            data = json.load(f)
        assert data == [1, 2, 3]

    def test_save_non_serializable(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        path = storage.save_raw_data("plain string", "blocks", "20240101")
        with open(path) as f:
            data = json.load(f)
        assert data["data"] == "plain string"

    def test_auto_timestamp(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        path = storage.save_raw_data({"a": 1}, "fields")
        assert "fields_" in path


class TestSaveProcessedData:
    def test_save_parquet(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        df = pd.DataFrame({"name": ["F1", "F2"], "value": [100, 200]})
        path = storage.save_processed_data(df, "fields", format="parquet")
        assert path.endswith(".parquet")
        loaded = pd.read_parquet(path)
        assert len(loaded) == 2

    def test_save_csv(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        df = pd.DataFrame({"name": ["F1"], "value": [100]})
        path = storage.save_processed_data(df, "fields", format="csv")
        assert path.endswith(".csv")

    def test_save_json_format(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        df = pd.DataFrame({"name": ["F1"], "value": [100]})
        path = storage.save_processed_data(df, "fields", format="json")
        assert path.endswith(".json")

    def test_unsupported_format_raises(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        df = pd.DataFrame({"a": [1]})
        with pytest.raises(ValueError, match="Unsupported format"):
            storage.save_processed_data(df, "fields", format="xlsx")

    def test_save_list_of_dicts(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        data = [{"name": "F1"}, {"name": "F2"}]
        path = storage.save_processed_data(data, "fields", format="csv")
        loaded = pd.read_csv(path)
        assert len(loaded) == 2

    def test_save_single_dict(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        data = {"name": "F1", "value": 100}
        path = storage.save_processed_data(data, "fields", format="csv")
        loaded = pd.read_csv(path)
        assert len(loaded) == 1


class TestLoadProcessedData:
    def test_load_parquet(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        df = pd.DataFrame({"name": ["F1"], "value": [100]})
        storage.save_processed_data(df, "fields", format="parquet")
        loaded = storage.load_processed_data("fields")
        assert len(loaded) == 1

    def test_load_csv_fallback(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        df = pd.DataFrame({"name": ["F1"], "value": [100]})
        storage.save_processed_data(df, "fields", format="csv")
        loaded = storage.load_processed_data("fields")
        assert len(loaded) == 1

    def test_not_found_raises(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        with pytest.raises(FileNotFoundError, match="No processed data"):
            storage.load_processed_data("nonexistent")


class TestSaveGenericRoute:
    def test_save_dataframe(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        df = pd.DataFrame({"a": [1]})
        path = storage.save("fields", {"data": df})
        assert "processed" in path

    def test_save_list_data(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        path = storage.save("fields", {"data": [1, 2, 3]})
        assert "raw" in path


class TestSaveAnalysisResults:
    def test_save(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        path = storage.save_analysis_results({"metric": 42}, "portfolio")
        assert "analysis" in path
        with open(path) as f:
            data = json.load(f)
        assert data["metric"] == 42


class TestGetAvailableDatasets:
    def test_empty(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        result = storage.get_available_datasets()
        assert result["raw"] == []
        assert result["processed"] == []
        assert result["analysis"] == []

    def test_with_files(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        storage.save_raw_data({"a": 1}, "fields", "20240101")
        result = storage.get_available_datasets()
        assert len(result["raw"]) == 1


class TestClearCache:
    def test_clear(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        cache_file = tmp_path / "sodir" / "cache" / "test.json"
        cache_file.write_text("{}")
        storage.clear_cache()
        assert not cache_file.exists()


class TestExportData:
    def test_export_csv(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        df = pd.DataFrame({"a": [1, 2]})
        path = storage.export_data(df, "report", format="csv")
        assert "exports" in path
        assert path.endswith(".csv")

    def test_export_json(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        df = pd.DataFrame({"a": [1, 2]})
        path = storage.export_data(df, "report", format="json")
        assert path.endswith(".json")

    def test_unsupported_raises(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        df = pd.DataFrame({"a": [1]})
        with pytest.raises(ValueError, match="Unsupported export format"):
            storage.export_data(df, "report", format="xml")


class TestGetStorageInfo:
    def test_basic(self, tmp_path):
        storage = DataStorage(str(tmp_path / "sodir"))
        info = storage.get_storage_info()
        assert info["base_path"] == str(tmp_path / "sodir")
        assert "total_size_bytes" in info
        assert "directories" in info
        assert "raw" in info["directories"]
