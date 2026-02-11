"""Unit tests for the BSEE full-refresh orchestrator script."""

import io
import pickle
import sys
import zipfile
from pathlib import Path

import pandas as pd
import pytest

# Add scripts dir to path for import
_scripts_dir = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(_scripts_dir))
from refresh_bsee_all import (
    BSEERefreshOrchestrator,
    RefreshResult,
    is_lfs_stub,
)

from worldenergydata.bsee.data.refresh.url_registry import DatasetSpec


# -- helpers -----------------------------------------------------------------

def _make_lfs_stub(path: Path) -> None:
    """Write a realistic Git LFS pointer stub to *path*."""
    path.write_bytes(
        b"version https://git-lfs.github.com/spec/v1\n"
        b"oid sha256:abc123def456\n"
        b"size 12345\n"
    )


def _make_real_bin(path: Path, data: dict | None = None) -> bytes:
    """Pickle *data* (default ``{"test": 1}``) into *path* and return raw bytes."""
    payload = pickle.dumps(data or {"test": 1})
    path.write_bytes(payload)
    return payload


def _make_csv_zip(csv_name: str, csv_content: str) -> bytes:
    """Return in-memory ZIP bytes containing one CSV file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(csv_name, csv_content)
    return buf.getvalue()


def _make_project_tree(tmp_path: Path, bin_dir_name: str) -> Path:
    """Create the expected ``data/modules/bsee/bin/<bin_dir_name>`` tree
    under *tmp_path* (acting as project root) and return the bin_dir path."""
    bin_dir = tmp_path / "data" / "modules" / "bsee" / "bin" / bin_dir_name
    bin_dir.mkdir(parents=True, exist_ok=True)
    return bin_dir


# -- LFS stub detection ------------------------------------------------------

class TestIsLfsStub:
    def test_is_lfs_stub_true(self, tmp_path: Path):
        stub = tmp_path / "stub.bin"
        _make_lfs_stub(stub)
        assert is_lfs_stub(stub) is True

    def test_is_lfs_stub_false(self, tmp_path: Path):
        real = tmp_path / "real.bin"
        _make_real_bin(real)
        assert is_lfs_stub(real) is False

    def test_is_lfs_stub_missing_file(self, tmp_path: Path):
        missing = tmp_path / "no_such_file.bin"
        assert is_lfs_stub(missing) is False


# -- ZIP-to-bin processing ---------------------------------------------------

class TestProcessZipToBins:
    def test_process_zip_to_bins(self, tmp_path: Path):
        csv_text = "col1,col2\n1,2\n3,4\n"
        zip_bytes = _make_csv_zip("test_data.txt", csv_text)

        bin_dir = _make_project_tree(tmp_path, "target_bins")
        stub_bin = bin_dir / "test_data.bin"
        _make_lfs_stub(stub_bin)

        spec = DatasetSpec(
            bin_dir="target_bins",
            zip_url="https://example.com/fake.zip",
            expected_bins=["test_data.bin"],
        )

        orch = BSEERefreshOrchestrator(project_root=tmp_path)
        result = orch._process_zip_to_bins(zip_bytes, spec)

        assert result.status == "success"
        assert result.bins_written >= 1

        df = pickle.loads(stub_bin.read_bytes())
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    def test_skip_real_files(self, tmp_path: Path):
        csv_text = "a,b\n10,20\n"
        zip_bytes = _make_csv_zip("keep_me.txt", csv_text)

        bin_dir = _make_project_tree(tmp_path, "keep_dir")
        real_bin = bin_dir / "keep_me.bin"
        original_bytes = _make_real_bin(real_bin, {"keep": True})

        spec = DatasetSpec(
            bin_dir="keep_dir",
            zip_url="https://example.com/fake.zip",
            expected_bins=["keep_me.bin"],
        )

        orch = BSEERefreshOrchestrator(project_root=tmp_path)
        orch._process_zip_to_bins(zip_bytes, spec)

        assert real_bin.read_bytes() == original_bytes


# -- dry-run mode ------------------------------------------------------------

class TestDryRun:
    def test_dry_run_no_files_written(self, tmp_path: Path):
        bin_dir = _make_project_tree(tmp_path, "dry_bins")
        stub = bin_dir / "some.bin"
        _make_lfs_stub(stub)
        original = stub.read_bytes()

        spec = DatasetSpec(
            bin_dir="dry_bins",
            zip_url="https://example.com/fake.zip",
            expected_bins=["some.bin"],
        )

        orch = BSEERefreshOrchestrator(project_root=tmp_path, dry_run=True)
        result = orch.refresh_single(spec)

        assert result.status == "skipped"
        assert stub.read_bytes() == original


# -- RefreshResult summary ----------------------------------------------------

class TestRefreshResultSummary:
    def test_refresh_result_summary(self):
        results = [
            RefreshResult(bin_dir="a", status="success", bins_written=3),
            RefreshResult(bin_dir="b", status="success", bins_written=2),
            RefreshResult(bin_dir="c", status="failed", bins_written=0),
            RefreshResult(bin_dir="d", status="skipped", bins_written=0),
        ]

        success_count = sum(1 for r in results if r.status == "success")
        failed_count = sum(1 for r in results if r.status == "failed")
        total_bins = sum(r.bins_written for r in results)

        assert success_count == 2
        assert failed_count == 1
        assert total_bins == 5
