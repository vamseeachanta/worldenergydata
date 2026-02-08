"""Tests for LNG terminal data exporters."""

import csv
import json
from pathlib import Path

import pytest

from worldenergydata.lng_terminals.collectors.seed_collector import (
    SeedCollector,
)
from worldenergydata.lng_terminals.exceptions import LNGExportError
from worldenergydata.lng_terminals.exporters.csv_exporter import CSVExporter
from worldenergydata.lng_terminals.exporters.parquet_exporter import (
    ParquetExporter,
)
from worldenergydata.lng_terminals.models.terminal import LNGTerminal


@pytest.fixture
def sample_terminals() -> list[LNGTerminal]:
    """Get a small set of terminals for testing."""
    collector = SeedCollector()
    all_terminals = collector.collect()
    return all_terminals[:5]  # Just use 5 for speed


@pytest.fixture
def tmp_export_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for exports."""
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    return export_dir


class TestCSVExporter:
    """Test CSV export functionality."""

    def test_export_creates_file(self, sample_terminals, tmp_export_dir):
        exporter = CSVExporter(output_dir=tmp_export_dir)
        path = exporter.export(sample_terminals)
        assert path.exists()
        assert path.suffix == ".csv"

    def test_export_correct_row_count(self, sample_terminals, tmp_export_dir):
        exporter = CSVExporter(output_dir=tmp_export_dir)
        path = exporter.export(sample_terminals)
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == len(sample_terminals)

    def test_export_has_required_columns(self, sample_terminals, tmp_export_dir):
        exporter = CSVExporter(output_dir=tmp_export_dir)
        path = exporter.export(sample_terminals)
        with open(path) as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
        required = {
            "terminal_id",
            "terminal_name",
            "country",
            "terminal_type",
            "status",
        }
        assert required.issubset(set(fieldnames))

    def test_export_empty_raises(self, tmp_export_dir):
        exporter = CSVExporter(output_dir=tmp_export_dir)
        with pytest.raises(LNGExportError):
            exporter.export([])

    def test_export_roundtrip_name(self, sample_terminals, tmp_export_dir):
        """Terminal names should survive CSV roundtrip."""
        exporter = CSVExporter(output_dir=tmp_export_dir)
        path = exporter.export(sample_terminals)
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        exported_names = {r["terminal_name"] for r in rows}
        original_names = {t.terminal_name for t in sample_terminals}
        assert exported_names == original_names

    def test_export_metadata(self, sample_terminals, tmp_export_dir):
        exporter = CSVExporter(output_dir=tmp_export_dir)
        path = exporter.export_metadata(sample_terminals)
        assert path.exists()
        with open(path) as f:
            meta = json.load(f)
        assert meta["total_records"] == len(sample_terminals)
        assert "countries" in meta
        assert "status_distribution" in meta


def _pyarrow_available() -> bool:
    try:
        import pyarrow  # noqa: F401

        return True
    except ImportError:
        return False


_skip_no_pyarrow = pytest.mark.skipif(
    not _pyarrow_available(),
    reason="pyarrow not installed",
)


class TestParquetExporter:
    """Test Parquet export functionality."""

    @_skip_no_pyarrow
    def test_export_creates_file(self, sample_terminals, tmp_export_dir):
        exporter = ParquetExporter(output_dir=tmp_export_dir)
        path = exporter.export(sample_terminals)
        assert path.exists()
        assert path.suffix == ".parquet"

    @_skip_no_pyarrow
    def test_export_correct_row_count(self, sample_terminals, tmp_export_dir):
        import pandas as pd

        exporter = ParquetExporter(output_dir=tmp_export_dir)
        path = exporter.export(sample_terminals)
        df = pd.read_parquet(path)
        assert len(df) == len(sample_terminals)

    @_skip_no_pyarrow
    def test_export_has_required_columns(self, sample_terminals, tmp_export_dir):
        import pandas as pd

        exporter = ParquetExporter(output_dir=tmp_export_dir)
        path = exporter.export(sample_terminals)
        df = pd.read_parquet(path)
        required = {
            "terminal_id",
            "terminal_name",
            "country",
            "terminal_type",
            "status",
        }
        assert required.issubset(set(df.columns))

    def test_export_empty_raises(self, tmp_export_dir):
        exporter = ParquetExporter(output_dir=tmp_export_dir)
        with pytest.raises(LNGExportError):
            exporter.export([])
