"""Tests for LNG terminal loader module."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.lng_terminals.constants import (
    SourceReliability,
    TerminalFunction,
    TerminalStatus,
    TerminalType,
)
from worldenergydata.lng_terminals.loaders.terminal_loader import TerminalLoader

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestTerminalLoaderInit:
    def test_with_valid_file(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("terminal_name,country\n")
        loader = TerminalLoader(file_path=f)
        assert loader.file_path == f
        assert loader.source_name == "curated_seed_dataset"

    def test_custom_source_name(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("")
        loader = TerminalLoader(file_path=f, source_name="custom")
        assert loader.source_name == "custom"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            TerminalLoader(file_path=tmp_path / "nonexistent.csv")


# ---------------------------------------------------------------------------
# Static helpers
# ---------------------------------------------------------------------------


class TestGetRequiredStr:
    def test_basic(self):
        row = pd.Series({"name": "  hello  "})
        assert TerminalLoader._get_required_str(row, "name") == "hello"

    def test_missing_raises(self):
        row = pd.Series({"name": None})
        with pytest.raises(ValueError, match="Required field"):
            TerminalLoader._get_required_str(row, "name")

    def test_nan_raises(self):
        row = pd.Series({"name": float("nan")})
        with pytest.raises(ValueError, match="Required field"):
            TerminalLoader._get_required_str(row, "name")


class TestGetOptionalStr:
    def test_basic(self):
        row = pd.Series({"name": "  hello  "})
        assert TerminalLoader._get_optional_str(row, "name") == "hello"

    def test_none(self):
        row = pd.Series({"name": None})
        assert TerminalLoader._get_optional_str(row, "name") is None

    def test_nan(self):
        row = pd.Series({"name": float("nan")})
        assert TerminalLoader._get_optional_str(row, "name") is None

    def test_missing_key(self):
        row = pd.Series({"other": "val"})
        assert TerminalLoader._get_optional_str(row, "name") is None


class TestGetOptionalFloat:
    def test_basic(self):
        row = pd.Series({"val": 3.14})
        assert TerminalLoader._get_optional_float(row, "val") == pytest.approx(3.14)

    def test_none(self):
        row = pd.Series({"val": None})
        assert TerminalLoader._get_optional_float(row, "val") is None

    def test_string_number(self):
        row = pd.Series({"val": "42.5"})
        assert TerminalLoader._get_optional_float(row, "val") == pytest.approx(42.5)


class TestGetOptionalInt:
    def test_basic(self):
        row = pd.Series({"val": 42})
        assert TerminalLoader._get_optional_int(row, "val") == 42

    def test_none(self):
        row = pd.Series({"val": None})
        assert TerminalLoader._get_optional_int(row, "val") is None

    def test_float_truncates(self):
        row = pd.Series({"val": 42.9})
        assert TerminalLoader._get_optional_int(row, "val") == 42


class TestParseTerminalType:
    def test_valid(self):
        assert (
            TerminalLoader._parse_terminal_type("onshore_import")
            == TerminalType.ONSHORE_IMPORT
        )

    def test_with_whitespace(self):
        assert TerminalLoader._parse_terminal_type("  fsru  ") == TerminalType.FSRU

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid terminal_type"):
            TerminalLoader._parse_terminal_type("unknown_type")


class TestParseFunction:
    def test_valid(self):
        assert TerminalLoader._parse_function("import") == TerminalFunction.IMPORT

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid function"):
            TerminalLoader._parse_function("teleport")


class TestParseStatus:
    def test_valid(self):
        assert TerminalLoader._parse_status("operational") == TerminalStatus.OPERATIONAL

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid status"):
            TerminalLoader._parse_status("imaginary")


class TestParseReliability:
    def test_valid(self):
        assert TerminalLoader._parse_reliability("high") == SourceReliability.HIGH
        assert TerminalLoader._parse_reliability("medium") == SourceReliability.MEDIUM
        assert TerminalLoader._parse_reliability("low") == SourceReliability.LOW

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid data_confidence"):
            TerminalLoader._parse_reliability("maybe")


# ---------------------------------------------------------------------------
# Load from CSV
# ---------------------------------------------------------------------------


class TestLoadFromCSV:
    def test_load_basic(self, tmp_path):
        csv_file = tmp_path / "terminals.csv"
        csv_file.write_text(
            "terminal_name,country,terminal_type,function,status,capacity_mtpa\n"
            "Sabine Pass,USA,onshore_liquefaction,export,operational,30.0\n"
        )
        loader = TerminalLoader(file_path=csv_file)
        terminals = loader.load()
        assert len(terminals) == 1
        assert terminals[0].terminal_name == "Sabine Pass"
        assert terminals[0].country == "USA"

    def test_load_skips_invalid_rows(self, tmp_path):
        csv_file = tmp_path / "terminals.csv"
        csv_file.write_text(
            "terminal_name,country,terminal_type,function,status\n"
            "Good,USA,onshore_import,import,operational\n"
            ",,,invalid_type,\n"
        )
        loader = TerminalLoader(file_path=csv_file)
        terminals = loader.load()
        # First row OK, second should fail validation
        assert len(terminals) == 1

    def test_unsupported_format_raises(self, tmp_path):
        f = tmp_path / "data.xlsx"
        f.write_text("")
        loader = TerminalLoader(file_path=f)
        with pytest.raises(ValueError, match="Unsupported file format"):
            loader.load()


class TestIdentifySourcedFields:
    def test_basic(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("")
        loader = TerminalLoader(file_path=f)
        row = pd.Series(
            {
                "terminal_name": "Test",
                "country": "USA",
                "terminal_type": "import",
                "function": "import",
                "status": "operational",
                "latitude": 29.0,
                "longitude": -90.0,
                "capacity_mtpa": None,
            }
        )
        fields = loader._identify_sourced_fields(row)
        assert "terminal_name" in fields
        assert "latitude" in fields
        assert "longitude" in fields
        # None value should not be included
        assert "capacity_mtpa" not in fields
