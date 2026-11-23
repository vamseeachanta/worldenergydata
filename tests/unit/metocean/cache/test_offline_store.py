"""Tests for metocean.cache.offline_store OfflineStore."""

from datetime import datetime
from pathlib import Path

import pytest

from worldenergydata.metocean.cache.offline_store import OfflineStore
from worldenergydata.metocean.constants import DataSource


@pytest.fixture
def store(tmp_path):
    return OfflineStore(store_dir=tmp_path / "offline")


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestOfflineStoreInit:
    def test_creates_directory(self, tmp_path):
        store_dir = tmp_path / "new_store"
        store = OfflineStore(store_dir=store_dir)
        assert store.store_dir.exists()

    def test_store_dir_set(self, store):
        assert store.store_dir.exists()


# ---------------------------------------------------------------------------
# store / retrieve
# ---------------------------------------------------------------------------


class TestStoreAndRetrieve:
    def test_store_creates_file(self, store):
        dt = datetime(2024, 6, 15)
        records = [{"temp": 22.5, "wave_height": 1.2}]
        path = store.store(DataSource.NDBC, "44025", dt, records)
        assert Path(path).exists()
        assert path.suffix == ".gz"

    def test_store_with_metadata(self, store):
        dt = datetime(2024, 6, 15)
        records = [{"temp": 22.5}]
        meta = {"quality": "good", "sensor": "buoy"}
        path = store.store(DataSource.NDBC, "44025", dt, records, metadata=meta)
        assert Path(path).exists()

    def test_retrieve_existing(self, store):
        dt = datetime(2024, 6, 15)
        records = [{"temp": 22.5}, {"temp": 23.0}]
        store.store(DataSource.NDBC, "44025", dt, records)
        result = store.retrieve(DataSource.NDBC, "44025", dt)
        assert result is not None
        assert len(result) == 2
        assert result[0]["temp"] == 22.5

    def test_retrieve_nonexistent(self, store):
        dt = datetime(2024, 6, 15)
        result = store.retrieve(DataSource.NDBC, "99999", dt)
        assert result is None

    def test_retrieve_with_metadata(self, store):
        dt = datetime(2024, 6, 15)
        records = [{"temp": 22.5}]
        meta = {"quality": "good"}
        store.store(DataSource.NDBC, "44025", dt, records, metadata=meta)
        result = store.retrieve_with_metadata(DataSource.NDBC, "44025", dt)
        assert result is not None
        assert result["metadata"]["quality"] == "good"
        assert result["record_count"] == 1

    def test_retrieve_with_metadata_nonexistent(self, store):
        dt = datetime(2024, 6, 15)
        result = store.retrieve_with_metadata(DataSource.NDBC, "99999", dt)
        assert result is None


# ---------------------------------------------------------------------------
# has_data
# ---------------------------------------------------------------------------


class TestHasData:
    def test_has_data_true(self, store):
        dt = datetime(2024, 6, 15)
        store.store(DataSource.NDBC, "44025", dt, [{"temp": 22}])
        assert store.has_data(DataSource.NDBC, "44025", dt) is True

    def test_has_data_false(self, store):
        dt = datetime(2024, 6, 15)
        assert store.has_data(DataSource.NDBC, "99999", dt) is False


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDelete:
    def test_delete_existing(self, store):
        dt = datetime(2024, 6, 15)
        store.store(DataSource.NDBC, "44025", dt, [{"temp": 22}])
        assert store.delete(DataSource.NDBC, "44025", dt) is True
        assert store.has_data(DataSource.NDBC, "44025", dt) is False

    def test_delete_nonexistent(self, store):
        dt = datetime(2024, 6, 15)
        assert store.delete(DataSource.NDBC, "99999", dt) is False

    def test_delete_station(self, store):
        dt1 = datetime(2024, 6, 15)
        dt2 = datetime(2024, 6, 16)
        store.store(DataSource.NDBC, "44025", dt1, [{"temp": 22}])
        store.store(DataSource.NDBC, "44025", dt2, [{"temp": 23}])
        deleted = store.delete_station(DataSource.NDBC, "44025")
        assert deleted == 2

    def test_delete_station_nonexistent(self, store):
        assert store.delete_station(DataSource.NDBC, "99999") == 0


# ---------------------------------------------------------------------------
# list_available / list_stations
# ---------------------------------------------------------------------------


class TestListMethods:
    def test_list_available_empty(self, store):
        result = store.list_available()
        assert result == []

    def test_list_available_with_data(self, store):
        store.store(DataSource.NDBC, "44025", datetime(2024, 6, 15), [{"t": 1}])
        store.store(DataSource.NDBC, "44025", datetime(2024, 6, 16), [{"t": 2}])
        result = store.list_available()
        assert len(result) == 2
        assert all("source" in r for r in result)
        assert all("station_id" in r for r in result)

    def test_list_available_filter_source(self, store):
        store.store(DataSource.NDBC, "44025", datetime(2024, 6, 15), [{"t": 1}])
        store.store(DataSource.COOPS, "8518750", datetime(2024, 6, 15), [{"t": 2}])
        result = store.list_available(source=DataSource.NDBC)
        assert len(result) == 1
        assert result[0]["source"] == "ndbc"

    def test_list_available_filter_station(self, store):
        store.store(DataSource.NDBC, "44025", datetime(2024, 6, 15), [{"t": 1}])
        store.store(DataSource.NDBC, "44066", datetime(2024, 6, 15), [{"t": 2}])
        result = store.list_available(station_id="44025")
        assert len(result) == 1

    def test_list_stations_empty(self, store):
        assert store.list_stations() == []

    def test_list_stations_with_data(self, store):
        store.store(DataSource.NDBC, "44025", datetime(2024, 6, 15), [{"t": 1}])
        store.store(DataSource.NDBC, "44025", datetime(2024, 6, 16), [{"t": 2}])
        stations = store.list_stations()
        assert len(stations) == 1
        assert stations[0]["station_id"] == "44025"
        assert stations[0]["file_count"] == 2

    def test_list_stations_filter_source(self, store):
        store.store(DataSource.NDBC, "44025", datetime(2024, 6, 15), [{"t": 1}])
        store.store(DataSource.COOPS, "8518750", datetime(2024, 6, 15), [{"t": 2}])
        stations = store.list_stations(source=DataSource.NDBC)
        assert len(stations) == 1
        assert stations[0]["source"] == "ndbc"


# ---------------------------------------------------------------------------
# status / compact
# ---------------------------------------------------------------------------


class TestStatusAndCompact:
    def test_status_empty(self, store):
        status = store.status()
        assert status["total_files"] == 0
        assert status["total_size_bytes"] == 0

    def test_status_with_data(self, store):
        store.store(DataSource.NDBC, "44025", datetime(2024, 6, 15), [{"t": 1}])
        status = store.status()
        assert status["total_files"] == 1
        assert status["total_size_bytes"] > 0
        assert "ndbc" in status["sources_count"]

    def test_compact_empty(self, store):
        result = store.compact()
        assert result["removed_directories"] == 0

    def test_compact_removes_empty_dirs(self, store):
        # Create then delete data so empty dirs remain
        dt = datetime(2024, 6, 15)
        store.store(DataSource.NDBC, "44025", dt, [{"t": 1}])
        # Delete the file but leave dirs
        filepath = store.store_dir / "ndbc" / "44025" / "2024" / "20240615.json.gz"
        filepath.unlink()
        result = store.compact()
        assert result["removed_directories"] >= 1
