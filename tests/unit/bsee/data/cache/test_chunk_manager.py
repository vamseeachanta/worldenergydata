"""Tests for BSEE chunk-based change detection and cache management."""

import io
import json
import os
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.data.cache.chunk_manager import (
    ChunkManager,
    ChunkMetadata,
)


# ---------------------------------------------------------------------------
# ChunkMetadata
# ---------------------------------------------------------------------------

class TestChunkMetadata:
    def test_init(self):
        meta = ChunkMetadata(
            chunk_id="test_chunk_0",
            checksum="abc123",
            timestamp=datetime(2024, 1, 15, 10, 30),
            size_bytes=1024,
        )
        assert meta.chunk_id == "test_chunk_0"
        assert meta.checksum == "abc123"
        assert meta.timestamp == datetime(2024, 1, 15, 10, 30)
        assert meta.size_bytes == 1024
        assert meta.row_range is None
        assert meta.is_changed is False
        assert meta.download_required is True

    def test_init_with_row_range(self):
        meta = ChunkMetadata(
            chunk_id="c1", checksum="xyz",
            timestamp=datetime(2024, 1, 1), size_bytes=500,
            row_range=(0, 100),
        )
        assert meta.row_range == (0, 100)

    def test_to_dict(self):
        ts = datetime(2024, 6, 15, 12, 0, 0)
        meta = ChunkMetadata(
            chunk_id="c1", checksum="abc", timestamp=ts, size_bytes=2048,
        )
        d = meta.to_dict()
        assert d["chunk_id"] == "c1"
        assert d["checksum"] == "abc"
        assert d["timestamp"] == ts.isoformat()
        assert d["size_bytes"] == 2048
        assert d["row_range"] is None
        assert d["is_changed"] is False
        assert d["download_required"] is True

    def test_to_dict_changed(self):
        meta = ChunkMetadata(
            chunk_id="c2", checksum="def", timestamp=datetime.now(), size_bytes=100,
        )
        meta.is_changed = True
        meta.download_required = False
        d = meta.to_dict()
        assert d["is_changed"] is True
        assert d["download_required"] is False

    def test_from_dict(self):
        data = {
            "chunk_id": "c1",
            "checksum": "abc",
            "timestamp": "2024-06-15T12:00:00",
            "size_bytes": 2048,
            "row_range": [10, 20],
            "is_changed": True,
            "download_required": False,
        }
        meta = ChunkMetadata.from_dict(data)
        assert meta.chunk_id == "c1"
        assert meta.checksum == "abc"
        assert meta.timestamp == datetime(2024, 6, 15, 12, 0, 0)
        assert meta.size_bytes == 2048
        assert meta.is_changed is True
        assert meta.download_required is False

    def test_from_dict_defaults(self):
        data = {
            "chunk_id": "c1",
            "checksum": "abc",
            "timestamp": "2024-01-01T00:00:00",
            "size_bytes": 100,
        }
        meta = ChunkMetadata.from_dict(data)
        assert meta.row_range is None
        assert meta.is_changed is False
        assert meta.download_required is True

    def test_roundtrip(self):
        ts = datetime(2024, 3, 15, 8, 30, 0)
        original = ChunkMetadata(
            chunk_id="test", checksum="hash123", timestamp=ts,
            size_bytes=4096, row_range=(0, 50000),
        )
        original.is_changed = True
        d = original.to_dict()
        restored = ChunkMetadata.from_dict(d)
        assert restored.chunk_id == original.chunk_id
        assert restored.checksum == original.checksum
        assert restored.size_bytes == original.size_bytes
        assert restored.is_changed == original.is_changed


# ---------------------------------------------------------------------------
# ChunkManager init
# ---------------------------------------------------------------------------

class TestChunkManagerInit:
    def test_custom_cache_dir(self, tmp_path):
        cache_dir = tmp_path / "my_cache"
        mgr = ChunkManager(cache_dir=cache_dir)
        assert mgr.cache_dir == cache_dir
        assert cache_dir.exists()
        assert (cache_dir / "chunks").exists()

    def test_config_defaults(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        assert mgr.chunk_size_mb == 10
        assert mgr.chunk_size_bytes == 10 * 1024 * 1024
        assert mgr.row_chunk_size == 50000
        assert mgr.ttl_hours == 24


# ---------------------------------------------------------------------------
# Metadata persistence
# ---------------------------------------------------------------------------

class TestMetadataPersistence:
    def test_save_and_load_metadata(self, tmp_path):
        cache_dir = tmp_path / "cache"
        mgr = ChunkManager(cache_dir=cache_dir)
        chunk = ChunkMetadata(
            chunk_id="well_chunk_0",
            checksum="abc123",
            timestamp=datetime(2024, 1, 1),
            size_bytes=1024,
        )
        mgr._update_metadata(
            "well", [chunk],
            {"ETag": '"etag1"', "Last-Modified": "Mon, 01 Jan 2024", "Content-Length": "1024"},
        )
        # Reload from disk
        mgr2 = ChunkManager(cache_dir=cache_dir)
        assert "well" in mgr2.metadata
        assert "chunks" in mgr2.metadata["well"]
        assert "well_chunk_0" in mgr2.metadata["well"]["chunks"]
        assert mgr2.metadata["well"]["file_metadata"]["etag"] == "etag1"

    def test_load_empty_metadata(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        assert mgr.metadata == {}

    def test_corrupted_metadata_file(self, tmp_path):
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "chunks").mkdir()
        meta_file = cache_dir / "chunk_metadata.json"
        meta_file.write_text("not valid json!!!")
        mgr = ChunkManager(cache_dir=cache_dir)
        assert mgr.metadata == {}


# ---------------------------------------------------------------------------
# Cache chunk operations
# ---------------------------------------------------------------------------

class TestCacheChunkOperations:
    def test_cache_chunk(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        mgr._cache_chunk("chunk_0", b"test data", "well")
        cache_file = mgr.chunk_cache_dir / "well_chunk_0.cache"
        assert cache_file.exists()
        assert cache_file.read_bytes() == b"test data"

    def test_get_cached_chunk_exists(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        mgr._cache_chunk("chunk_0", b"cached bytes", "production")
        result = mgr._get_cached_chunk("chunk_0", "production")
        assert result == b"cached bytes"

    def test_get_cached_chunk_not_exists(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        result = mgr._get_cached_chunk("nonexistent", "well")
        assert result is None

    def test_get_cached_chunk_expired(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        mgr.ttl_hours = 0
        mgr._cache_chunk("chunk_0", b"old data", "well")
        cache_file = mgr.chunk_cache_dir / "well_chunk_0.cache"
        old_time = (datetime.now() - timedelta(hours=25)).timestamp()
        os.utime(cache_file, (old_time, old_time))
        result = mgr._get_cached_chunk("chunk_0", "well")
        assert result is None

    def test_cache_complete_file(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        mgr._cache_complete_file("well", b"complete file data")
        cache_file = mgr.cache_dir / "well_complete.cache"
        assert cache_file.exists()
        assert cache_file.read_bytes() == b"complete file data"

    def test_load_from_cache(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        mgr._cache_complete_file("production", b"production data")
        result = mgr._load_from_cache("production")
        assert result == b"production data"

    def test_load_from_cache_not_exists(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        result = mgr._load_from_cache("nonexistent")
        assert result is None

    def test_load_from_cache_expired(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        mgr.ttl_hours = 0
        mgr._cache_complete_file("well", b"data")
        cache_file = mgr.cache_dir / "well_complete.cache"
        old_time = (datetime.now() - timedelta(hours=25)).timestamp()
        os.utime(cache_file, (old_time, old_time))
        result = mgr._load_from_cache("well")
        assert result is None


# ---------------------------------------------------------------------------
# clear_cache
# ---------------------------------------------------------------------------

class TestClearCache:
    def test_clear_specific_type(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        mgr._cache_complete_file("well", b"well data")
        mgr._cache_complete_file("production", b"prod data")
        chunk = ChunkMetadata("c0", "hash", datetime.now(), 100)
        mgr._update_metadata("well", [chunk], {"Content-Length": "100"})
        mgr._update_metadata("production", [chunk], {"Content-Length": "100"})
        mgr.clear_cache("well")
        assert not (mgr.cache_dir / "well_complete.cache").exists()
        assert (mgr.cache_dir / "production_complete.cache").exists()
        assert "well" not in mgr.metadata
        assert "production" in mgr.metadata

    def test_clear_all(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        mgr._cache_complete_file("well", b"data1")
        mgr._cache_complete_file("production", b"data2")
        chunk = ChunkMetadata("c0", "hash", datetime.now(), 100)
        mgr._update_metadata("well", [chunk], {"Content-Length": "100"})
        mgr.clear_cache()
        assert mgr.metadata == {}


# ---------------------------------------------------------------------------
# get_cache_stats
# ---------------------------------------------------------------------------

class TestGetCacheStats:
    def test_empty(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        stats = mgr.get_cache_stats()
        assert stats["total_size_mb"] == 0
        assert stats["chunk_count"] == 0
        assert stats["data_types"] == {}

    def test_with_data(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        mgr._cache_complete_file("well", b"x" * 1024)
        mgr._cache_chunk("chunk_0", b"y" * 512, "well")
        chunk = ChunkMetadata("well_chunk_0", "hash", datetime.now(), 512)
        mgr._update_metadata("well", [chunk], {"Content-Length": "1024"})
        stats = mgr.get_cache_stats()
        assert stats["total_size_mb"] > 0
        assert stats["chunk_count"] >= 1
        assert "well" in stats["data_types"]
        assert stats["oldest_cache"] is not None
        assert stats["newest_cache"] is not None


# ---------------------------------------------------------------------------
# _identify_dataframe_changes
# ---------------------------------------------------------------------------

class TestIdentifyDataframeChanges:
    def test_no_changes(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        df1 = pd.DataFrame({"A": [1, 2, 3], "B": ["x", "y", "z"]})
        df2 = df1.copy()
        changes = mgr._identify_dataframe_changes(df1, df2)
        assert changes["has_changes"] is False

    def test_update_changes(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        df1 = pd.DataFrame({"A": [1, 2, 3]})
        df2 = pd.DataFrame({"A": [1, 99, 3]})
        changes = mgr._identify_dataframe_changes(df1, df2)
        assert changes["has_changes"] is True
        assert changes["type"] == "update"
        assert 1 in changes["changed_indices"]

    def test_append_changes(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        df1 = pd.DataFrame({"A": [1, 2]})
        df2 = pd.DataFrame({"A": [1, 2, 3, 4]})
        changes = mgr._identify_dataframe_changes(df1, df2)
        assert changes["has_changes"] is True
        assert changes["type"] == "append"
        assert changes["new_rows"] == 2
        assert changes["start_index"] == 2

    def test_full_replacement_shorter(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        df1 = pd.DataFrame({"A": [1, 2, 3]})
        df2 = pd.DataFrame({"A": [1]})
        changes = mgr._identify_dataframe_changes(df1, df2)
        assert changes["has_changes"] is True
        assert changes["type"] == "full_replacement"

    def test_full_replacement_different_data(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        df1 = pd.DataFrame({"A": [1, 2]})
        df2 = pd.DataFrame({"A": [99, 100, 200]})
        changes = mgr._identify_dataframe_changes(df1, df2)
        assert changes["has_changes"] is True
        assert changes["type"] == "full_replacement"


# ---------------------------------------------------------------------------
# _extract_zip_data
# ---------------------------------------------------------------------------

def _make_zip(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


class TestExtractZipData:
    def test_extracts_csv(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        zip_data = _make_zip({"data.csv": "A,B\n1,2\n3,4\n"})
        result = mgr._extract_zip_data(zip_data)
        assert "data.csv" in result
        assert len(result["data.csv"]) == 2

    def test_extracts_txt(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        zip_data = _make_zip({"data.txt": "X,Y\n10,20\n"})
        result = mgr._extract_zip_data(zip_data)
        assert "data.txt" in result

    def test_skips_other_formats(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        zip_data = _make_zip({"data.csv": "A\n1\n", "readme.pdf": "binary content"})
        result = mgr._extract_zip_data(zip_data)
        assert "data.csv" in result
        assert "readme.pdf" not in result

    def test_invalid_zip(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        result = mgr._extract_zip_data(b"not a zip")
        assert result == {}


# ---------------------------------------------------------------------------
# process_incremental_changes
# ---------------------------------------------------------------------------

class TestProcessIncrementalChanges:
    def test_no_previous_data(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        zip_data = _make_zip({"data.csv": "A\n1\n2\n"})
        result = mgr.process_incremental_changes(zip_data, "well")
        assert len(result) == 2

    def test_with_previous_no_changes(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        prev = pd.DataFrame({"A": [1, 2]})
        zip_data = _make_zip({"data.csv": "A\n1\n2\n"})
        result = mgr.process_incremental_changes(zip_data, "well", prev)
        assert len(result) == 2

    def test_with_previous_append(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        prev = pd.DataFrame({"A": [1, 2]})
        zip_data = _make_zip({"data.csv": "A\n1\n2\n3\n4\n"})
        result = mgr.process_incremental_changes(zip_data, "well", prev)
        assert len(result) == 4

    def test_invalid_zip_returns_previous(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        prev = pd.DataFrame({"A": [1]})
        result = mgr.process_incremental_changes(b"bad data", "well", prev)
        assert len(result) == 1

    def test_invalid_zip_no_previous(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        result = mgr.process_incremental_changes(b"bad data", "well")
        assert result.empty


# ---------------------------------------------------------------------------
# _update_file_metadata
# ---------------------------------------------------------------------------

class TestUpdateFileMetadata:
    def test_basic(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        headers = {"ETag": '"etag_value"', "Last-Modified": "Mon, 01 Jan 2024"}
        mgr._update_file_metadata("well", headers, b"some data")
        assert "well" in mgr.metadata
        fm = mgr.metadata["well"]["file_metadata"]
        assert fm["etag"] == "etag_value"
        assert fm["content_length"] == 9
        assert "checksum" in fm
        assert "last_checked" in fm

    def test_new_data_type(self, tmp_path):
        mgr = ChunkManager(cache_dir=tmp_path / "cache")
        mgr._update_file_metadata("new_type", {}, b"data")
        assert "new_type" in mgr.metadata
