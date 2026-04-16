"""Tests for data freshness metadata generation and CLI status command."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULES_DIR = REPO_ROOT / "data" / "modules"
GENERATE_SCRIPT = REPO_ROOT / "scripts" / "generate_metadata.py"


# ---------------------------------------------------------------------------
# Metadata generation script
# ---------------------------------------------------------------------------


class TestGenerateMetadata:
    """Verify scripts/generate_metadata.py runs and produces valid output."""

    def test_script_runs_without_error(self):
        """The generate_metadata.py script exits 0."""
        result = subprocess.run(
            [sys.executable, str(GENERATE_SCRIPT)],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, (
            f"generate_metadata.py failed:\n{result.stderr}"
        )

    def test_metadata_json_created_for_each_module(self):
        """Every module directory should have a _metadata.json after running."""
        # Run the script first to ensure files exist
        subprocess.run(
            [sys.executable, str(GENERATE_SCRIPT)],
            capture_output=True,
            cwd=str(REPO_ROOT),
        )
        if not MODULES_DIR.is_dir():
            pytest.skip("data/modules/ not present")

        for mod_dir in sorted(MODULES_DIR.iterdir()):
            if not mod_dir.is_dir():
                continue
            meta_path = mod_dir / "_metadata.json"
            assert meta_path.exists(), f"Missing _metadata.json in {mod_dir.name}"

    def test_metadata_json_has_required_fields(self):
        """Each _metadata.json must contain the expected top-level keys."""
        required_keys = {
            "module",
            "last_refresh",
            "record_count",
            "file_count",
            "total_size_bytes",
            "source_url",
            "format",
            "files",
        }
        if not MODULES_DIR.is_dir():
            pytest.skip("data/modules/ not present")

        for mod_dir in sorted(MODULES_DIR.iterdir()):
            if not mod_dir.is_dir():
                continue
            meta_path = mod_dir / "_metadata.json"
            if not meta_path.exists():
                continue
            data = json.loads(meta_path.read_text())
            missing = required_keys - set(data.keys())
            assert not missing, (
                f"{mod_dir.name}/_metadata.json missing keys: {missing}"
            )

    def test_metadata_record_count_non_negative(self):
        """record_count must be >= 0 for every module."""
        if not MODULES_DIR.is_dir():
            pytest.skip("data/modules/ not present")

        for mod_dir in sorted(MODULES_DIR.iterdir()):
            if not mod_dir.is_dir():
                continue
            meta_path = mod_dir / "_metadata.json"
            if not meta_path.exists():
                continue
            data = json.loads(meta_path.read_text())
            assert data["record_count"] >= 0, (
                f"{mod_dir.name} has negative record_count"
            )


# ---------------------------------------------------------------------------
# CLI status command
# ---------------------------------------------------------------------------


class TestCLIStatus:
    """Verify the ``worldenergydata status`` command doesn't crash."""

    def test_status_command_exits_zero(self):
        """CLI status command should exit 0."""
        result = subprocess.run(
            [sys.executable, "-m", "worldenergydata.cli.main", "status"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, (
            f"CLI status failed:\nstdout={result.stdout}\nstderr={result.stderr}"
        )
