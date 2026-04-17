"""Tests for LNG terminals CSV and Parquet exporters."""

import csv
import json
from datetime import datetime, timezone

import pytest

from worldenergydata.lng_terminals.constants import (
    Region,
    TerminalFunction,
    TerminalStatus,
    TerminalType,
)
from worldenergydata.lng_terminals.exporters.csv_exporter import CSVExporter
from worldenergydata.lng_terminals.exporters.parquet_exporter import ParquetExporter
from worldenergydata.lng_terminals.models.terminal import LNGTerminal


def _make_terminal(**overrides):
    defaults = dict(
        terminal_name="Test Terminal",
        country="USA",
        terminal_type=TerminalType.ONSHORE_IMPORT,
        function=TerminalFunction.IMPORT,
        status=TerminalStatus.OPERATIONAL,
        capacity_mtpa=10.0,
        year_commissioned=2020,
        region=Region.NORTH_AMERICA,
        operator="TestOp",
        last_updated=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return LNGTerminal(**defaults)


# ---------------------------------------------------------------------------
# CSVExporter
# ---------------------------------------------------------------------------


class TestCSVExporterInit:
    def test_with_path(self, tmp_path):
        exporter = CSVExporter(output_dir=tmp_path)
        assert exporter.output_dir == tmp_path

    def test_creates_directory(self, tmp_path):
        out = tmp_path / "subdir"
        CSVExporter(output_dir=out)
        assert out.is_dir()


class TestCSVExport:
    def test_empty_raises(self, tmp_path):
        exporter = CSVExporter(output_dir=tmp_path)
        with pytest.raises(Exception):
            exporter.export([])

    def test_basic_export(self, tmp_path):
        exporter = CSVExporter(output_dir=tmp_path)
        terminals = [_make_terminal(terminal_name="Sabine Pass")]
        path = exporter.export(terminals, "test.csv")
        assert path.exists()
        assert path.name == "test.csv"

    def test_csv_has_headers(self, tmp_path):
        exporter = CSVExporter(output_dir=tmp_path)
        terminals = [_make_terminal()]
        path = exporter.export(terminals)
        with open(path, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert "terminal_name" in rows[0]

    def test_multiple_terminals(self, tmp_path):
        exporter = CSVExporter(output_dir=tmp_path)
        terminals = [
            _make_terminal(terminal_name="A"),
            _make_terminal(terminal_name="B"),
        ]
        path = exporter.export(terminals, "multi.csv")
        with open(path, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2


class TestCSVExportMetadata:
    def test_basic(self, tmp_path):
        exporter = CSVExporter(output_dir=tmp_path)
        terminals = [
            _make_terminal(country="USA"),
            _make_terminal(country="QAT"),
        ]
        path = exporter.export_metadata(terminals)
        with open(path) as f:
            meta = json.load(f)
        assert meta["total_records"] == 2
        assert "USA" in meta["countries"]
        assert "QAT" in meta["countries"]

    def test_status_distribution(self, tmp_path):
        exporter = CSVExporter(output_dir=tmp_path)
        terminals = [
            _make_terminal(status=TerminalStatus.OPERATIONAL),
            _make_terminal(status=TerminalStatus.PLANNED),
        ]
        path = exporter.export_metadata(terminals)
        with open(path) as f:
            meta = json.load(f)
        assert meta["status_distribution"]["operational"] == 1
        assert meta["status_distribution"]["planned"] == 1


class TestCountByAttr:
    def test_basic(self):
        terminals = [
            _make_terminal(status=TerminalStatus.OPERATIONAL),
            _make_terminal(status=TerminalStatus.OPERATIONAL),
            _make_terminal(status=TerminalStatus.PLANNED),
        ]
        result = CSVExporter._count_by_attr(terminals, "status")
        assert result["operational"] == 2
        assert result["planned"] == 1


# ---------------------------------------------------------------------------
# ParquetExporter
# ---------------------------------------------------------------------------


class TestParquetExporterInit:
    def test_with_path(self, tmp_path):
        exporter = ParquetExporter(output_dir=tmp_path)
        assert exporter.output_dir == tmp_path


class TestParquetExport:
    def test_empty_raises(self, tmp_path):
        exporter = ParquetExporter(output_dir=tmp_path)
        with pytest.raises(Exception):
            exporter.export([])

    def test_basic_export(self, tmp_path):
        import pandas as pd

        exporter = ParquetExporter(output_dir=tmp_path)
        terminals = [_make_terminal(terminal_name="Sabine Pass")]
        path = exporter.export(terminals, "test.parquet")
        assert path.exists()
        loaded = pd.read_parquet(path)
        assert len(loaded) == 1

    def test_multiple_terminals(self, tmp_path):
        import pandas as pd

        exporter = ParquetExporter(output_dir=tmp_path)
        terminals = [
            _make_terminal(terminal_name="A"),
            _make_terminal(terminal_name="B"),
        ]
        path = exporter.export(terminals, "multi.parquet")
        loaded = pd.read_parquet(path)
        assert len(loaded) == 2
