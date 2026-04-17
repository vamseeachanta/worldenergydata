"""Tests for Texas RRC CSV loader module."""

import pytest

from worldenergydata.texas_rrc.data.loaders.csv_loader import CSVLoader

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestCSVLoaderInit:
    def test_defaults(self):
        loader = CSVLoader()
        assert loader.encoding == "utf-8"
        assert loader.delimiter == ","
        assert loader.quotechar == '"'
        assert loader.skip_header is False

    def test_custom(self):
        loader = CSVLoader(encoding="latin-1", delimiter="\t")
        assert loader.encoding == "latin-1"
        assert loader.delimiter == "\t"


# ---------------------------------------------------------------------------
# _normalize_field_name
# ---------------------------------------------------------------------------


class TestNormalizeFieldName:
    def test_basic(self):
        loader = CSVLoader()
        assert loader._normalize_field_name("Field Name") == "field_name"

    def test_with_dashes(self):
        loader = CSVLoader()
        assert loader._normalize_field_name("OG-LEASE-NO") == "og_lease_no"

    def test_special_chars(self):
        loader = CSVLoader()
        result = loader._normalize_field_name("Field (Name) #1")
        assert result == "field_name_1"

    def test_empty(self):
        loader = CSVLoader()
        assert loader._normalize_field_name("") == "unknown"

    def test_consecutive_underscores(self):
        loader = CSVLoader()
        result = loader._normalize_field_name("A  B   C")
        assert "__" not in result

    def test_leading_trailing_whitespace(self):
        loader = CSVLoader()
        result = loader._normalize_field_name("  field  ")
        assert result == "field"


# ---------------------------------------------------------------------------
# _convert_value
# ---------------------------------------------------------------------------


class TestConvertValue:
    def test_empty_string(self):
        loader = CSVLoader()
        assert loader._convert_value("any_field", "") is None

    def test_whitespace_only(self):
        loader = CSVLoader()
        assert loader._convert_value("any_field", "   ") is None

    def test_none_value(self):
        loader = CSVLoader()
        assert loader._convert_value("any_field", None) is None

    def test_numeric_field(self):
        loader = CSVLoader()
        assert loader._convert_value("oil_production", "100.5") == 100.5

    def test_numeric_field_invalid(self):
        loader = CSVLoader()
        assert loader._convert_value("oil_production", "N/A") is None

    def test_integer_field(self):
        loader = CSVLoader()
        assert loader._convert_value("district", "5") == 5

    def test_integer_field_float_input(self):
        loader = CSVLoader()
        assert loader._convert_value("district", "5.0") == 5

    def test_integer_field_invalid(self):
        loader = CSVLoader()
        assert loader._convert_value("district", "abc") is None

    def test_string_field(self):
        loader = CSVLoader()
        result = loader._convert_value("operator_name", "  Exxon Mobil  ")
        assert result == "Exxon Mobil"


# ---------------------------------------------------------------------------
# load_from_string
# ---------------------------------------------------------------------------


class TestLoadFromString:
    def test_basic(self):
        loader = CSVLoader()
        csv = "Name,Value\nAlpha,100\nBeta,200\n"
        records = loader.load_from_string(csv)
        assert len(records) == 2
        assert records[0]["name"] == "Alpha"
        assert records[1]["name"] == "Beta"

    def test_with_field_mapping(self):
        loader = CSVLoader()
        csv = "OG_LEASE_NAME,OG_OIL_PROD\nTest,100\n"
        mapping = {"OG_LEASE_NAME": "lease_name", "OG_OIL_PROD": "oil_production"}
        records = loader.load_from_string(csv, field_mapping=mapping)
        assert records[0]["lease_name"] == "Test"
        assert records[0]["oil_production"] == 100.0

    def test_empty_csv(self):
        loader = CSVLoader()
        records = loader.load_from_string("Name,Value\n")
        assert records == []

    def test_stats(self):
        loader = CSVLoader()
        csv = "A,B\n1,2\n3,4\n"
        loader.load_from_string(csv)
        assert loader.stats["rows_processed"] == 2
        assert loader.stats["errors"] == 0


# ---------------------------------------------------------------------------
# load from file
# ---------------------------------------------------------------------------


class TestLoadFromFile:
    def test_basic(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("Name,Value\nAlpha,100\n")
        loader = CSVLoader()
        records = loader.load(f)
        assert len(records) == 1

    def test_file_not_found(self, tmp_path):
        loader = CSVLoader()
        with pytest.raises(FileNotFoundError):
            loader.load(tmp_path / "nonexistent.csv")

    def test_with_mapping(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("OG_DIST_NO,OG_OIL_PROD\n3,150.5\n")
        loader = CSVLoader()
        mapping = {"OG_DIST_NO": "district", "OG_OIL_PROD": "oil_production"}
        records = loader.load(f, field_mapping=mapping)
        assert records[0]["district"] == 3
        assert records[0]["oil_production"] == 150.5


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_numeric_fields(self):
        assert "oil_production" in CSVLoader.NUMERIC_FIELDS
        assert "gas_production" in CSVLoader.NUMERIC_FIELDS
        assert "latitude" in CSVLoader.NUMERIC_FIELDS

    def test_integer_fields(self):
        assert "district" in CSVLoader.INTEGER_FIELDS
        assert "county_code" in CSVLoader.INTEGER_FIELDS
        assert "lease_number" in CSVLoader.INTEGER_FIELDS
