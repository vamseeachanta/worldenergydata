# ABOUTME: Unit tests for BSEEIncInvImporter (incident investigation raw data importer)
# ABOUTME: Tests normalize_row, parse_date, map_accident_type, map_severity

"""
Tests for worldenergydata.hse.importers.bsee_incinv_importer

Tests the incident investigation file importer which reads
mv_acc_investigations.txt and maps to HSEIncident-compatible dicts.
"""

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root / "src"))

from worldenergydata.hse.importers.bsee_incinv_importer import (
    ACCIDENT_SEVERITY_MAP,
    ACCIDENT_TYPE_MAP,
    BSEEIncInvImporter,
)


@pytest.fixture
def importer(tmp_path):
    """Create importer with a temp data directory."""
    return BSEEIncInvImporter(data_dir=str(tmp_path))


class TestParseDate:
    """Tests for _parse_date method."""

    def test_parse_mdy_format(self, importer):
        """Should parse M/D/YYYY format."""
        result = importer._parse_date("12/19/2009", None)
        assert result == datetime(2009, 12, 19)

    def test_parse_mdy_with_military_time(self, importer):
        """Should parse date with military time."""
        result = importer._parse_date("12/19/2009", "8:05")
        assert result == datetime(2009, 12, 19, 8, 5)

    def test_parse_iso_format(self, importer):
        """Should parse YYYY-MM-DD format."""
        result = importer._parse_date("2009-12-19", None)
        assert result == datetime(2009, 12, 19)

    def test_parse_none_date(self, importer):
        """Should return None for None input."""
        assert importer._parse_date(None, None) is None

    def test_parse_nan_date(self, importer):
        """Should return None for 'nan' string."""
        assert importer._parse_date("nan", None) is None

    def test_parse_invalid_date(self, importer):
        """Should return None for unparseable date."""
        assert importer._parse_date("not-a-date", None) is None

    def test_parse_nan_time_ignored(self, importer):
        """Should parse date but ignore 'nan' time."""
        result = importer._parse_date("12/19/2009", "nan")
        assert result == datetime(2009, 12, 19)

    def test_parse_invalid_time_keeps_date(self, importer):
        """Should keep date even if time parsing fails."""
        result = importer._parse_date("12/19/2009", "invalid")
        assert result == datetime(2009, 12, 19)


class TestMapAccidentType:
    """Tests for _map_accident_type method."""

    def test_pollution_maps_to_spill(self, importer):
        """Pollution should map to 'spill'."""
        assert importer._map_accident_type("pollution") == "spill"

    def test_fire_maps_to_equipment_failure(self, importer):
        """Fire should map to 'equipment_failure'."""
        assert importer._map_accident_type("fire") == "equipment_failure"

    def test_fatality_maps_to_injury(self, importer):
        """Fatality should map to 'injury'."""
        assert importer._map_accident_type("fatality") == "injury"

    def test_injury_maps_to_injury(self, importer):
        """Injury should map to 'injury'."""
        assert importer._map_accident_type("injury") == "injury"

    def test_blowout_maps_to_equipment_failure(self, importer):
        """Blowout should map to 'equipment_failure'."""
        assert importer._map_accident_type("blowout") == "equipment_failure"

    def test_h2s_release_maps_to_spill(self, importer):
        """H2S release should map to 'spill'."""
        assert importer._map_accident_type("h2s release") == "spill"

    def test_unknown_type_defaults_to_equipment_failure(self, importer):
        """Unknown accident types should default to 'equipment_failure'."""
        assert importer._map_accident_type("completely_unknown") == "equipment_failure"

    def test_partial_match_works(self, importer):
        """Keyword matching should work for substrings."""
        assert importer._map_accident_type("major fire and explosion") == "equipment_failure"

    def test_all_mapped_types_are_valid(self, importer):
        """All mapped values should be valid HSEIncident incident_type enums."""
        valid = {"injury", "spill", "equipment_failure", "violation"}
        for mapped in ACCIDENT_TYPE_MAP.values():
            assert mapped in valid


class TestMapSeverity:
    """Tests for _map_severity method."""

    def test_fatality_severity(self, importer):
        """Fatality should map to 'fatality' severity."""
        assert importer._map_severity("fatality") == "fatality"

    def test_blowout_severity(self, importer):
        """Blowout should map to 'lost_time' severity."""
        assert importer._map_severity("blowout") == "lost_time"

    def test_gas_release_severity(self, importer):
        """Gas release should map to 'near_miss' severity."""
        assert importer._map_severity("gas release") == "near_miss"

    def test_unknown_defaults_to_minor(self, importer):
        """Unknown types should default to 'minor' severity."""
        assert importer._map_severity("completely_unknown") == "minor"

    def test_all_mapped_severities_are_valid(self, importer):
        """All mapped severity values should be valid enum values."""
        valid = {"fatality", "lost_time", "recordable", "near_miss", "minor"}
        for mapped in ACCIDENT_SEVERITY_MAP.values():
            assert mapped in valid


class TestNormalizeRow:
    """Tests for _normalize_row method."""

    def test_normalize_pollution_row(self, importer):
        """Should normalize a pollution incident row."""
        row = pd.Series({
            "DATE_OCCURRED": "12/19/2009",
            "MILITARY_TIME": "8:05",
            "LEASE_NUMBER": "G15610",
            "AREA_BLOCK": "GC 782",
            "ACCIDENT_TYPE": "- Pollution ",
            "PANEL_DISTRICT": "DISTRICT",
            "STATUS": "Complete",
        })
        result = importer._normalize_row(row, 0)
        assert result is not None
        assert result["bsee_incident_id"] == "INCINV-20091219-G15610-0"
        assert result["incident_type"] == "spill"
        assert result["severity"] == "minor"
        assert result["investigation_status"] == "Complete"

    def test_normalize_fatality_row(self, importer):
        """Should normalize a fatality incident row."""
        row = pd.Series({
            "DATE_OCCURRED": "3/15/2020",
            "MILITARY_TIME": "14:30",
            "LEASE_NUMBER": "G99999",
            "AREA_BLOCK": "MC 100",
            "ACCIDENT_TYPE": "- Fatality ",
            "PANEL_DISTRICT": "DISTRICT",
            "STATUS": "Complete",
        })
        result = importer._normalize_row(row, 5)
        assert result is not None
        assert result["incident_type"] == "injury"
        assert result["severity"] == "fatality"
        assert result["bsee_incident_id"] == "INCINV-20200315-G99999-5"

    def test_normalize_row_with_bad_date_returns_none(self, importer):
        """Should return None for row with unparseable date."""
        row = pd.Series({
            "DATE_OCCURRED": "invalid",
            "MILITARY_TIME": "",
            "LEASE_NUMBER": "G15610",
            "AREA_BLOCK": "GC 782",
            "ACCIDENT_TYPE": "- Pollution ",
            "PANEL_DISTRICT": "DISTRICT",
            "STATUS": "Complete",
        })
        result = importer._normalize_row(row, 0)
        assert result is None

    def test_normalize_row_with_missing_fields(self, importer):
        """Should handle missing optional fields gracefully."""
        row = pd.Series({
            "DATE_OCCURRED": "12/19/2009",
            "MILITARY_TIME": "",
            "LEASE_NUMBER": "",
            "AREA_BLOCK": "",
            "ACCIDENT_TYPE": "- Fire ",
            "PANEL_DISTRICT": "",
            "STATUS": "",
        })
        result = importer._normalize_row(row, 0)
        assert result is not None
        assert result["lease_number"] is None
        assert result["block_number"] is None


class TestLoadFromFile:
    """Tests for load method with actual file data."""

    def test_load_from_small_fixture(self, tmp_path):
        """Should load and normalize a small fixture file."""
        # Create fixture file
        incinv_dir = tmp_path / "IncInvRawData"
        incinv_dir.mkdir()
        fixture_file = incinv_dir / "mv_acc_investigations.txt"
        fixture_file.write_text(
            '"DATE_OCCURRED","MILITARY_TIME","LEASE_NUMBER","AREA_BLOCK",'
            '"ACCIDENT_TYPE","PANEL_DISTRICT","STATUS"\n'
            '12/19/2009,"8:05","G15610","GC 782","- Pollution ","DISTRICT","Complete"\n'
            '10/16/2013,"8:30","G15610","GC 782","- Fatality ","DISTRICT","Complete"\n'
            '3/1/2020,"10:00","G20000","MC 100","- Fire ","DISTRICT","In Progress"\n'
        )

        importer = BSEEIncInvImporter(data_dir=str(tmp_path))
        records = importer.load()

        assert len(records) == 3
        assert records[0]["incident_type"] == "spill"
        assert records[1]["incident_type"] == "injury"
        assert records[1]["severity"] == "fatality"
        assert records[2]["incident_type"] == "equipment_failure"

    def test_load_file_not_found_raises(self, tmp_path):
        """Should raise FileNotFoundError for missing data file."""
        importer = BSEEIncInvImporter(data_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            importer.load()
