# ABOUTME: Unit tests for BSEEINCSImporter (Incidents of Non-Compliance importer)
# ABOUTME: Tests normalize_row, parse_date, safe_int, region mapping, multi-record emission

"""
Tests for worldenergydata.hse.importers.bsee_incs_importer

Tests the INCs file importer which reads mv_incs_by_oper.txt and
produces 0-3 violation records per row (one per non-zero INC category).
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root / "src"))

from worldenergydata.hse.importers.bsee_incs_importer import (
    REGION_MAP,
    BSEEINCSImporter,
)


@pytest.fixture
def importer(tmp_path):
    """Create importer with a temp data directory."""
    return BSEEINCSImporter(data_dir=str(tmp_path))


class TestSafeInt:
    """Tests for _safe_int static method."""

    def test_valid_integer_string(self):
        """Should parse valid integer string."""
        assert BSEEINCSImporter._safe_int("42") == 42

    def test_zero_string(self):
        """Should parse '0' correctly."""
        assert BSEEINCSImporter._safe_int("0") == 0

    def test_none_returns_zero(self):
        """Should return 0 for None."""
        assert BSEEINCSImporter._safe_int(None) == 0

    def test_nan_returns_zero(self):
        """Should return 0 for 'nan' string."""
        assert BSEEINCSImporter._safe_int("nan") == 0

    def test_empty_string_returns_zero(self):
        """Should return 0 for empty string."""
        assert BSEEINCSImporter._safe_int("") == 0

    def test_non_numeric_returns_zero(self):
        """Should return 0 for non-numeric string."""
        assert BSEEINCSImporter._safe_int("abc") == 0

    def test_float_string_returns_zero(self):
        """Should return 0 for float string (not valid int)."""
        assert BSEEINCSImporter._safe_int("3.5") == 0


class TestParseDate:
    """Tests for _parse_date method."""

    def test_parse_datetime_with_ampm(self, importer):
        """Should parse 'M/D/YYYY H:MM:SS AM/PM' format."""
        result = importer._parse_date("8/21/2020 2:12:53 PM")
        assert result == datetime(2020, 8, 21, 14, 12, 53)

    def test_parse_date_only(self, importer):
        """Should parse 'M/D/YYYY' format."""
        result = importer._parse_date("8/21/2020")
        assert result == datetime(2020, 8, 21)

    def test_parse_iso_date(self, importer):
        """Should parse 'YYYY-MM-DD' format."""
        result = importer._parse_date("2020-08-21")
        assert result == datetime(2020, 8, 21)

    def test_parse_24h_time(self, importer):
        """Should parse 'M/D/YYYY H:MM:SS' (24hr) format."""
        result = importer._parse_date("8/21/2020 14:12:53")
        assert result == datetime(2020, 8, 21, 14, 12, 53)

    def test_parse_none_returns_none(self, importer):
        """Should return None for None input."""
        assert importer._parse_date(None) is None

    def test_parse_nan_returns_none(self, importer):
        """Should return None for 'nan' string."""
        assert importer._parse_date("nan") is None

    def test_parse_invalid_returns_none(self, importer):
        """Should return None for unparseable string."""
        assert importer._parse_date("not-a-date") is None


class TestNormalizeRow:
    """Tests for _normalize_row method."""

    def test_single_warning_inc(self, importer):
        """Row with only warnings should emit 1 record."""
        row = pd.Series(
            {
                "INC_DATE": "8/21/2020 2:12:53 PM",
                "REGION": "G",
                "BUS_ASC_CODE": "03295",
                "BUS_ASC_NAME": "Fieldwood Energy LLC",
                "WARNING_INCS": "3",
                "COMP_SHUTIN_INCS": "0",
                "FAC_SHUTIN_INCS": "0",
            }
        )
        records = importer._normalize_row(row, 0)
        assert len(records) == 1
        assert records[0]["violation_type"] == "warning"
        assert records[0]["inc_count"] == 3
        assert "INC-20200821-03295-WARNING-0" == records[0]["bsee_incident_id"]

    def test_all_three_inc_categories(self, importer):
        """Row with all 3 non-zero categories should emit 3 records."""
        row = pd.Series(
            {
                "INC_DATE": "8/21/2020 2:12:53 PM",
                "REGION": "G",
                "BUS_ASC_CODE": "03295",
                "BUS_ASC_NAME": "Fieldwood Energy LLC",
                "WARNING_INCS": "1",
                "COMP_SHUTIN_INCS": "2",
                "FAC_SHUTIN_INCS": "3",
            }
        )
        records = importer._normalize_row(row, 0)
        assert len(records) == 3
        types = {r["violation_type"] for r in records}
        assert types == {"warning", "comp_shutin", "fac_shutin"}

    def test_zero_counts_emit_no_records(self, importer):
        """Row with all-zero counts should emit 0 records."""
        row = pd.Series(
            {
                "INC_DATE": "8/21/2020 2:12:53 PM",
                "REGION": "G",
                "BUS_ASC_CODE": "03295",
                "BUS_ASC_NAME": "Fieldwood Energy LLC",
                "WARNING_INCS": "0",
                "COMP_SHUTIN_INCS": "0",
                "FAC_SHUTIN_INCS": "0",
            }
        )
        records = importer._normalize_row(row, 0)
        assert len(records) == 0

    def test_bad_date_returns_empty_list(self, importer):
        """Row with unparseable date should return empty list."""
        row = pd.Series(
            {
                "INC_DATE": "invalid-date",
                "REGION": "G",
                "BUS_ASC_CODE": "03295",
                "BUS_ASC_NAME": "Fieldwood Energy LLC",
                "WARNING_INCS": "1",
                "COMP_SHUTIN_INCS": "0",
                "FAC_SHUTIN_INCS": "0",
            }
        )
        records = importer._normalize_row(row, 0)
        assert len(records) == 0

    def test_region_code_mapping_gulf(self, importer):
        """Region code 'G' should map to 'Gulf of Mexico'."""
        row = pd.Series(
            {
                "INC_DATE": "8/21/2020",
                "REGION": "G",
                "BUS_ASC_CODE": "00001",
                "BUS_ASC_NAME": "Test Operator",
                "WARNING_INCS": "1",
                "COMP_SHUTIN_INCS": "0",
                "FAC_SHUTIN_INCS": "0",
            }
        )
        records = importer._normalize_row(row, 0)
        assert records[0]["region"] == "Gulf of Mexico"

    def test_region_code_mapping_alaska(self, importer):
        """Region code 'A' should map to 'Alaska'."""
        row = pd.Series(
            {
                "INC_DATE": "8/21/2020",
                "REGION": "A",
                "BUS_ASC_CODE": "00001",
                "BUS_ASC_NAME": "Test Operator",
                "WARNING_INCS": "1",
                "COMP_SHUTIN_INCS": "0",
                "FAC_SHUTIN_INCS": "0",
            }
        )
        records = importer._normalize_row(row, 0)
        assert records[0]["region"] == "Alaska"

    def test_region_code_mapping_pacific(self, importer):
        """Region code 'P' should map to 'Pacific'."""
        row = pd.Series(
            {
                "INC_DATE": "8/21/2020",
                "REGION": "P",
                "BUS_ASC_CODE": "00001",
                "BUS_ASC_NAME": "Test Operator",
                "WARNING_INCS": "1",
                "COMP_SHUTIN_INCS": "0",
                "FAC_SHUTIN_INCS": "0",
            }
        )
        records = importer._normalize_row(row, 0)
        assert records[0]["region"] == "Pacific"

    def test_all_records_have_violation_type(self, importer):
        """All emitted records should have incident_type='violation'."""
        row = pd.Series(
            {
                "INC_DATE": "8/21/2020",
                "REGION": "G",
                "BUS_ASC_CODE": "00001",
                "BUS_ASC_NAME": "Test Operator",
                "WARNING_INCS": "1",
                "COMP_SHUTIN_INCS": "1",
                "FAC_SHUTIN_INCS": "1",
            }
        )
        records = importer._normalize_row(row, 0)
        for r in records:
            assert r["incident_type"] == "violation"
            assert r["severity"] == "minor"

    def test_composite_id_includes_operator_code(self, importer):
        """Composite ID should include the operator business associate code."""
        row = pd.Series(
            {
                "INC_DATE": "1/3/1948",
                "REGION": "G",
                "BUS_ASC_CODE": "12345",
                "BUS_ASC_NAME": "Old Operator",
                "WARNING_INCS": "1",
                "COMP_SHUTIN_INCS": "0",
                "FAC_SHUTIN_INCS": "0",
            }
        )
        records = importer._normalize_row(row, 99)
        assert "12345" in records[0]["bsee_incident_id"]
        assert "99" in records[0]["bsee_incident_id"]


class TestRegionMap:
    """Tests for region code constants."""

    def test_all_region_codes_present(self):
        """All expected region codes should be in REGION_MAP."""
        assert "G" in REGION_MAP
        assert "A" in REGION_MAP
        assert "P" in REGION_MAP

    def test_region_names(self):
        """Region names should be correct."""
        assert REGION_MAP["G"] == "Gulf of Mexico"
        assert REGION_MAP["A"] == "Alaska"
        assert REGION_MAP["P"] == "Pacific"


class TestLoadFromFile:
    """Tests for load method with fixture data."""

    def test_load_from_small_fixture(self, tmp_path):
        """Should load and normalize a small fixture file."""
        incs_dir = tmp_path / "INCSRawData"
        incs_dir.mkdir()
        fixture_file = incs_dir / "mv_incs_by_oper.txt"
        fixture_file.write_text(
            '"INC_DATE","REGION","BUS_ASC_CODE","BUS_ASC_NAME",'
            '"WARNING_INCS","COMP_SHUTIN_INCS","FAC_SHUTIN_INCS"\n'
            '8/21/2020 2:12:53 PM,"G","03295","Fieldwood Energy LLC","0","1","0"\n'
            '10/26/2020 2:58:41 PM,"G","03295","Fieldwood Energy LLC","1","1","0"\n'
            '11/5/2020 1:57:31 PM,"A","00100","Alaska Operator","1","0","1"\n'
        )

        importer = BSEEINCSImporter(data_dir=str(tmp_path))
        records = importer.load()

        # Row 1: 1 record (comp_shutin only)
        # Row 2: 2 records (warning + comp_shutin)
        # Row 3: 2 records (warning + fac_shutin)
        assert len(records) == 5

    def test_load_file_not_found_raises(self, tmp_path):
        """Should raise FileNotFoundError for missing data file."""
        importer = BSEEINCSImporter(data_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            importer.load()
