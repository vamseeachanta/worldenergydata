"""Tests for safety_analysis.taxonomy.cli argument parsing and CSV loading."""

import csv

import pytest

from worldenergydata.safety_analysis.taxonomy.cli import (
    _load_csv_records,
    _parse_args,
    _print_distribution,
)


class TestParseArgs:
    def test_classify_command(self):
        args = _parse_args(
            [
                "classify",
                "--source",
                "bsee",
                "--input",
                "/tmp/data.csv",
                "--output",
                "/tmp/out.csv",
            ]
        )
        assert args.command == "classify"
        assert args.source == "bsee"
        assert str(args.input) == "/tmp/data.csv"
        assert str(args.output) == "/tmp/out.csv"
        assert args.limit == 0

    def test_classify_with_limit(self):
        args = _parse_args(
            [
                "classify",
                "--source",
                "osha",
                "--input",
                "/tmp/data.csv",
                "--output",
                "/tmp/out.csv",
                "--limit",
                "100",
            ]
        )
        assert args.limit == 100

    def test_classify_all_sources(self):
        for source in ["bsee", "osha", "marine_safety", "phmsa", "epa_tri"]:
            args = _parse_args(
                [
                    "classify",
                    "--source",
                    source,
                    "--input",
                    "/tmp/in.csv",
                    "--output",
                    "/tmp/out.csv",
                ]
            )
            assert args.source == source

    def test_taxonomy_command(self):
        args = _parse_args(["taxonomy"])
        assert args.command == "taxonomy"

    def test_summary_command(self):
        args = _parse_args(["summary"])
        assert args.command == "summary"

    def test_missing_command_raises(self):
        with pytest.raises(SystemExit):
            _parse_args([])

    def test_classify_missing_source_raises(self):
        with pytest.raises(SystemExit):
            _parse_args(
                ["classify", "--input", "/tmp/in.csv", "--output", "/tmp/out.csv"]
            )

    def test_classify_invalid_source_raises(self):
        with pytest.raises(SystemExit):
            _parse_args(
                [
                    "classify",
                    "--source",
                    "invalid",
                    "--input",
                    "/tmp/in.csv",
                    "--output",
                    "/tmp/out.csv",
                ]
            )


class TestLoadCsvRecords:
    def test_load_basic_csv(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,value\nAlpha,10\nBeta,20\n")
        records = _load_csv_records(csv_file)
        assert len(records) == 2
        assert records[0]["name"] == "Alpha"
        assert records[0]["value"] == "10"

    def test_load_strips_whitespace(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(" name , value \n Alpha , 10 \n")
        records = _load_csv_records(csv_file)
        assert records[0]["name"] == "Alpha"
        assert records[0]["value"] == "10"

    def test_load_empty_csv(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("name,value\n")
        records = _load_csv_records(csv_file)
        assert records == []

    def test_load_strips_quotes(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text('"name","value"\n"Alpha","10"\n')
        records = _load_csv_records(csv_file)
        assert records[0]["name"] == "Alpha"


class TestPrintDistribution:
    def test_print_distribution(self, capsys):
        class MockResult:
            def __init__(self, activity, activity_name, match_method):
                self.activity = activity
                self.activity_name = activity_name
                self.match_method = match_method

        results = [
            MockResult("A01", "Drilling", "keyword"),
            MockResult("A01", "Drilling", "keyword"),
            MockResult("A02", "Production", "regex"),
        ]
        _print_distribution(results)
        captured = capsys.readouterr()
        assert "Activity Distribution" in captured.out
        assert "Match Method Distribution" in captured.out
        assert "Drilling" in captured.out
