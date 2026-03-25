"""Tests for vessel fleet CSV storage export_records_to_csv."""

import pytest

from worldenergydata.vessel_fleet.storage.csv import export_records_to_csv


class TestExportRecordsToCsv:
    def test_export_records(self, tmp_path):
        records = [
            {"name": "Rig A", "type": "Drillship"},
            {"name": "Rig B", "type": "Semi"},
        ]
        outpath = tmp_path / "output.csv"
        result = export_records_to_csv(records, outpath)
        assert result == outpath
        assert outpath.exists()
        content = outpath.read_text()
        assert "name,type" in content
        assert "Rig A" in content
        assert "Rig B" in content

    def test_empty_records(self, tmp_path):
        outpath = tmp_path / "empty.csv"
        result = export_records_to_csv([], outpath)
        assert result == outpath
        assert outpath.exists()
        assert outpath.read_text() == ""

    def test_creates_parent_dirs(self, tmp_path):
        outpath = tmp_path / "sub" / "dir" / "output.csv"
        records = [{"a": 1}]
        export_records_to_csv(records, outpath)
        assert outpath.exists()

    def test_returns_path(self, tmp_path):
        outpath = tmp_path / "out.csv"
        result = export_records_to_csv([{"a": 1}], outpath)
        from pathlib import Path
        assert isinstance(result, Path)

    def test_string_path(self, tmp_path):
        outpath = str(tmp_path / "str_out.csv")
        result = export_records_to_csv([{"a": 1}], outpath)
        from pathlib import Path
        assert Path(outpath).exists()
