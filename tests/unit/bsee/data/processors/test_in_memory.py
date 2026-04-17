"""Tests for BSEE in-memory data processor module."""

import io
import pickle
import zipfile

import pandas as pd
import pytest

from worldenergydata.bsee.data.processors.in_memory import MemoryProcessor

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestMemoryProcessorInit:
    def test_defaults(self):
        proc = MemoryProcessor()
        assert proc.processed_data == {}
        assert proc.zip_file_list == []
        assert proc.memory_threshold_mb == 1000
        assert proc.chunk_size_rows == 100000
        assert proc.use_optimized is True

    def test_non_optimized(self):
        proc = MemoryProcessor(use_optimized=False)
        assert proc.use_optimized is False


# ---------------------------------------------------------------------------
# get_memory_usage
# ---------------------------------------------------------------------------


class TestGetMemoryUsage:
    def test_returns_dict(self):
        proc = MemoryProcessor(use_optimized=False)
        mem = proc.get_memory_usage()
        assert "rss_mb" in mem
        assert "vms_mb" in mem
        assert "percent" in mem


# ---------------------------------------------------------------------------
# estimate_memory_usage
# ---------------------------------------------------------------------------


class TestEstimateMemoryUsage:
    def test_basic(self):
        proc = MemoryProcessor(use_optimized=False)
        data = b"x" * (1024 * 1024)  # 1 MB
        estimates = proc.estimate_memory_usage(data)
        assert estimates["zip_size_mb"] == pytest.approx(1.0, abs=0.01)
        assert estimates["estimated_df_size_mb"] == pytest.approx(2.5, abs=0.1)
        assert estimates["overhead_mb"] == 50
        assert estimates["total_estimate_mb"] > 0


# ---------------------------------------------------------------------------
# cleanup_memory
# ---------------------------------------------------------------------------


class TestCleanupMemory:
    def test_runs_without_error(self):
        proc = MemoryProcessor(use_optimized=False)
        proc.cleanup_memory()  # Should not raise


# ---------------------------------------------------------------------------
# check_memory_availability
# ---------------------------------------------------------------------------


class TestCheckMemoryAvailability:
    def test_small_estimate(self):
        proc = MemoryProcessor(use_optimized=False)
        assert proc.check_memory_availability(1.0) is True

    def test_huge_estimate(self):
        proc = MemoryProcessor(use_optimized=False)
        # Even if psutil is available, 1 TB should likely fail
        result = proc.check_memory_availability(1_000_000)
        # May or may not fail depending on machine, just test it doesn't raise
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# validate_data_integrity
# ---------------------------------------------------------------------------


class TestValidateDataIntegrity:
    def test_empty(self):
        proc = MemoryProcessor(use_optimized=False)
        assert proc.validate_data_integrity({}) is False

    def test_valid_data(self):
        proc = MemoryProcessor(use_optimized=False)
        data = {"test.txt": {"data": pd.DataFrame({"A": [1, 2, 3]})}}
        assert proc.validate_data_integrity(data) is True

    def test_empty_dataframe(self):
        proc = MemoryProcessor(use_optimized=False)
        data = {"test.txt": {"data": pd.DataFrame()}}
        assert proc.validate_data_integrity(data) is False

    def test_null_columns(self):
        proc = MemoryProcessor(use_optimized=False)
        data = {"test.txt": {"data": pd.DataFrame({"A": [1, 2], "B": [None, None]})}}
        # Valid but with warning about null columns
        assert proc.validate_data_integrity(data) is True


# ---------------------------------------------------------------------------
# save_dataframe_to_binary
# ---------------------------------------------------------------------------


class TestSaveDataframeToBinary:
    def test_basic(self, tmp_path):
        proc = MemoryProcessor(use_optimized=False)
        df = pd.DataFrame({"A": [1, 2, 3], "B": ["x", "y", "z"]})
        result = proc.save_dataframe_to_binary(df, str(tmp_path), "test_file.txt")
        assert "test_file.bin" in result
        # Verify file can be loaded back
        with open(result, "rb") as f:
            loaded = pickle.load(f)
        assert len(loaded) == 3
        assert list(loaded.columns) == ["A", "B"]

    def test_creates_directory(self, tmp_path):
        proc = MemoryProcessor(use_optimized=False)
        df = pd.DataFrame({"A": [1]})
        out_dir = str(tmp_path / "sub" / "dir")
        proc.save_dataframe_to_binary(df, out_dir, "test.txt")
        assert (tmp_path / "sub" / "dir" / "test.bin").exists()


# ---------------------------------------------------------------------------
# save_to_binary
# ---------------------------------------------------------------------------


class TestSaveToBinary:
    def test_dict_with_data(self, tmp_path):
        proc = MemoryProcessor(use_optimized=False)
        data = {
            "file_a.txt": {"data": pd.DataFrame({"X": [1, 2]})},
            "file_b.txt": {"data": pd.DataFrame({"Y": [3, 4]})},
        }
        proc.save_to_binary(data, str(tmp_path), "prefix")
        assert (tmp_path / "file_a.bin").exists()
        assert (tmp_path / "file_b.bin").exists()

    def test_raw_dataframe(self, tmp_path):
        proc = MemoryProcessor(use_optimized=False)
        data = {"file_c.txt": pd.DataFrame({"Z": [5, 6]})}
        proc.save_to_binary(data, str(tmp_path), "prefix")
        assert (tmp_path / "file_c.bin").exists()


# ---------------------------------------------------------------------------
# process_zip_in_memory
# ---------------------------------------------------------------------------


def _make_zip_bytes(files: dict) -> bytes:
    """Helper to create a zip file in memory."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


class TestProcessZipInMemory:
    def test_basic(self):
        proc = MemoryProcessor(use_optimized=False)
        csv_content = "A,B\n1,hello\n2,world\n"
        zip_data = _make_zip_bytes({"data.txt": csv_content})
        result = proc.process_zip_in_memory(zip_data)
        assert "data.txt" in result
        assert len(result["data.txt"]) == 2

    def test_skips_non_txt(self):
        proc = MemoryProcessor(use_optimized=False)
        zip_data = _make_zip_bytes({"data.csv": "A\n1\n", "data.txt": "B\n2\n"})
        result = proc.process_zip_in_memory(zip_data)
        # Only .txt files processed
        assert "data.txt" in result
        assert "data.csv" not in result

    def test_skips_directories(self):
        proc = MemoryProcessor(use_optimized=False)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("subdir/", "")
            zf.writestr("subdir/data.txt", "A\n1\n")
        result = proc.process_zip_in_memory(buf.getvalue())
        assert "subdir/data.txt" in result

    def test_bad_zip(self):
        proc = MemoryProcessor(use_optimized=False)
        result = proc.process_zip_in_memory(b"not a zip file")
        assert result == {}

    def test_stores_file_list(self):
        proc = MemoryProcessor(use_optimized=False)
        zip_data = _make_zip_bytes({"a.txt": "X\n1\n", "b.txt": "Y\n2\n"})
        proc.process_zip_in_memory(zip_data)
        assert "a.txt" in proc.zip_file_list
        assert "b.txt" in proc.zip_file_list
