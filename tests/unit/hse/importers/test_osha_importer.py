"""Tests for OSHA importer module helper functions and constants."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from worldenergydata.hse.importers.osha_importer import (
    DEGREE_SEVERITY,
    INSPECTION_TYPE_SEVERITY,
    INJURY_FIELD_LABELS,
    INJURY_FIELD_LOOKUP_CODES,
    VIOLATION_TYPE_MAP,
    _decode_field,
    _load_accident_lookups,
    _parse_date,
    _safe_float,
    _safe_str,
    build_parser,
    OSHAImporter,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_inspection_severity_fatality(self):
        assert INSPECTION_TYPE_SEVERITY["A"] == "fatality"

    def test_inspection_severity_count(self):
        assert len(INSPECTION_TYPE_SEVERITY) == 12

    def test_violation_type_map(self):
        assert VIOLATION_TYPE_MAP["S"] == "violation"
        assert VIOLATION_TYPE_MAP["W"] == "violation"

    def test_degree_severity_numeric(self):
        assert DEGREE_SEVERITY["1"] == "fatality"
        assert DEGREE_SEVERITY["2"] == "lost_time"
        assert DEGREE_SEVERITY["3"] == "recordable"

    def test_degree_severity_text(self):
        assert DEGREE_SEVERITY["Fatality"] == "fatality"

    def test_lookup_codes(self):
        assert "nature_of_inj" in INJURY_FIELD_LOOKUP_CODES
        assert INJURY_FIELD_LOOKUP_CODES["nature_of_inj"] == "IN"

    def test_injury_labels(self):
        assert INJURY_FIELD_LABELS["nature_of_inj"] == "Nature"


# ---------------------------------------------------------------------------
# _safe_str
# ---------------------------------------------------------------------------

class TestSafeStr:
    def test_normal(self):
        assert _safe_str("hello") == "hello"

    def test_strips(self):
        assert _safe_str("  hello  ") == "hello"

    def test_none(self):
        assert _safe_str(None) is None

    def test_nan(self):
        assert _safe_str(float("nan")) is None

    def test_empty(self):
        assert _safe_str("") is None

    def test_whitespace(self):
        assert _safe_str("   ") is None

    def test_numeric(self):
        assert _safe_str(42) == "42"


# ---------------------------------------------------------------------------
# _safe_float
# ---------------------------------------------------------------------------

class TestSafeFloat:
    def test_normal(self):
        assert _safe_float("3.14") == 3.14

    def test_int(self):
        assert _safe_float(42) == 42.0

    def test_none(self):
        assert _safe_float(None) is None

    def test_nan(self):
        assert _safe_float(float("nan")) is None

    def test_invalid(self):
        assert _safe_float("not a number") is None


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------

class TestParseDate:
    def test_string(self):
        result = _parse_date("2023-01-15")
        assert isinstance(result, datetime)
        assert result.year == 2023

    def test_datetime(self):
        dt = datetime(2023, 1, 15)
        assert _parse_date(dt) == dt

    def test_timestamp(self):
        ts = pd.Timestamp("2023-01-15")
        result = _parse_date(ts)
        assert isinstance(result, datetime)

    def test_none(self):
        assert _parse_date(None) is None

    def test_nan(self):
        assert _parse_date(float("nan")) is None

    def test_invalid(self):
        assert _parse_date("not a date") is None


# ---------------------------------------------------------------------------
# _decode_field
# ---------------------------------------------------------------------------

class TestDecodeField:
    def test_with_lookup(self):
        lookups = {"IN": {"1": "Burn"}}
        result = _decode_field(lookups, "nature_of_inj", "1")
        assert result == "Burn"

    def test_no_lookup(self):
        lookups = {}
        result = _decode_field(lookups, "nature_of_inj", "1")
        assert result == "1"

    def test_none_value(self):
        lookups = {"IN": {"1": "Burn"}}
        assert _decode_field(lookups, "nature_of_inj", None) is None

    def test_unknown_field(self):
        lookups = {"IN": {"1": "Burn"}}
        result = _decode_field(lookups, "unknown_field", "1")
        assert result == "1"


# ---------------------------------------------------------------------------
# _load_accident_lookups
# ---------------------------------------------------------------------------

class TestLoadAccidentLookups:
    def test_missing_file(self, tmp_path):
        result = _load_accident_lookups(tmp_path / "nonexistent.csv")
        assert result == {}

    def test_basic(self, tmp_path):
        csv_content = '"accident_code","accident_number","accident_value"\n"IN","1","Burn"\n"IN","2","Cut"\n'
        path = tmp_path / "lookup.csv"
        path.write_text(csv_content)
        result = _load_accident_lookups(path)
        assert "IN" in result
        assert result["IN"]["1"] == "Burn"
        assert result["IN"]["2"] == "Cut"


# ---------------------------------------------------------------------------
# build_parser
# ---------------------------------------------------------------------------

class TestBuildParser:
    def test_required_args(self):
        parser = build_parser()
        args = parser.parse_args(["--data-dir", "/tmp/osha"])
        assert args.data_dir == "/tmp/osha"
        assert args.no_filtered is False

    def test_all_args(self):
        parser = build_parser()
        args = parser.parse_args([
            "--data-dir", "/tmp/osha",
            "--db-url", "sqlite:///test.db",
            "--no-filtered",
        ])
        assert args.db_url == "sqlite:///test.db"
        assert args.no_filtered is True


# ---------------------------------------------------------------------------
# OSHAImporter._resolve_path
# ---------------------------------------------------------------------------

class TestResolvePath:
    def _make_importer(self, tmp_path):
        mock_session = MagicMock()
        return OSHAImporter(
            db_session=mock_session,
            data_dir=str(tmp_path),
            use_filtered=True,
        )

    def test_prefers_filtered(self, tmp_path):
        filtered = tmp_path / "filtered" / "osha_inspection_oil_gas.csv"
        filtered.parent.mkdir(parents=True)
        filtered.write_text("header\n")
        importer = self._make_importer(tmp_path)
        result = importer._resolve_path("osha_inspection")
        assert result == filtered

    def test_fallback_to_unfiltered(self, tmp_path):
        unfiltered = tmp_path / "osha_inspection.csv"
        unfiltered.write_text("header\n")
        importer = self._make_importer(tmp_path)
        result = importer._resolve_path("osha_inspection")
        assert result == unfiltered

    def test_not_found(self, tmp_path):
        importer = self._make_importer(tmp_path)
        result = importer._resolve_path("nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# OSHAImporter._normalize_inspection
# ---------------------------------------------------------------------------

class TestNormalizeInspection:
    def _make_importer(self, tmp_path):
        mock_session = MagicMock()
        return OSHAImporter(db_session=mock_session, data_dir=str(tmp_path))

    def test_basic(self, tmp_path):
        importer = self._make_importer(tmp_path)
        row = pd.Series({
            "activity_nr": "12345",
            "open_date": "2023-06-15",
            "estab_name": "Acme Oil",
            "insp_type": "A",
            "site_city": "Houston",
            "site_state": "TX",
            "naics_code": "211120",
        })
        result = importer._normalize_inspection(row)
        assert result["bsee_incident_id"] == "OSHA-INSP-12345"
        assert result["severity"] == "fatality"
        assert "Houston" in result["description"]

    def test_missing_activity_nr(self, tmp_path):
        importer = self._make_importer(tmp_path)
        row = pd.Series({"open_date": "2023-06-15"})
        assert importer._normalize_inspection(row) is None

    def test_missing_date(self, tmp_path):
        importer = self._make_importer(tmp_path)
        row = pd.Series({"activity_nr": "12345"})
        assert importer._normalize_inspection(row) is None


# ---------------------------------------------------------------------------
# OSHAImporter._normalize_accident
# ---------------------------------------------------------------------------

class TestNormalizeAccident:
    def _make_importer(self, tmp_path):
        mock_session = MagicMock()
        return OSHAImporter(db_session=mock_session, data_dir=str(tmp_path))

    def test_basic(self, tmp_path):
        importer = self._make_importer(tmp_path)
        row = pd.Series({
            "summary_nr": "99999",
            "event_date": "2023-06-15",
            "estab_name": "Oil Co",
            "event_desc": "Explosion at rig",
        })
        result = importer._normalize_accident(row)
        assert result["bsee_incident_id"] == "OSHA-ACC-99999"
        assert result["incident_type"] == "injury"
        assert "Explosion" in result["description"]

    def test_falls_back_to_activity_nr(self, tmp_path):
        importer = self._make_importer(tmp_path)
        row = pd.Series({
            "activity_nr": "88888",
            "event_date": "2023-01-01",
        })
        result = importer._normalize_accident(row)
        assert "88888" in result["bsee_incident_id"]


# ---------------------------------------------------------------------------
# OSHAImporter._normalize_accident_injury
# ---------------------------------------------------------------------------

class TestNormalizeAccidentInjury:
    def _make_importer(self, tmp_path):
        mock_session = MagicMock()
        return OSHAImporter(db_session=mock_session, data_dir=str(tmp_path))

    def test_basic(self, tmp_path):
        importer = self._make_importer(tmp_path)
        row = pd.Series({
            "rel_insp_nr": "77777",
            "event_date": "2023-06-15",
            "age": "35",
            "sex": "M",
            "degree_of_inj": "1",
            "nature_of_inj": "5",
        })
        result = importer._normalize_accident_injury(row)
        assert "77777" in result["bsee_incident_id"]
        assert result["severity"] == "fatality"

    def test_missing_rel_insp_nr(self, tmp_path):
        importer = self._make_importer(tmp_path)
        row = pd.Series({"event_date": "2023-01-01"})
        assert importer._normalize_accident_injury(row) is None
