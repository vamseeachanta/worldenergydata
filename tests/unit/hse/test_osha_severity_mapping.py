# ABOUTME: Tests for OSHA severity mapping and lookup table integration
# ABOUTME: Validates degree_of_inj numeric codes map to correct severity levels

"""
Tests for OSHA severity mapping (WRK-160).

Covers:
    - Numeric degree_of_inj codes (1=fatality, 2=lost_time, 3=recordable)
    - Text fallback variants
    - Lookup table loading and field decoding
    - Integration with _normalize_accident_injury
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Severity mapping tests
# ---------------------------------------------------------------------------


class TestDegreeSeverityMapping:
    """Test DEGREE_SEVERITY dict maps numeric codes correctly."""

    def test_import_degree_severity(self):
        from worldenergydata.hse.importers.osha_importer import DEGREE_SEVERITY

        assert isinstance(DEGREE_SEVERITY, dict)
        assert len(DEGREE_SEVERITY) > 0

    def test_numeric_code_1_is_fatality(self):
        from worldenergydata.hse.importers.osha_importer import DEGREE_SEVERITY

        assert DEGREE_SEVERITY["1"] == "fatality"

    def test_numeric_code_2_is_lost_time(self):
        from worldenergydata.hse.importers.osha_importer import DEGREE_SEVERITY

        assert DEGREE_SEVERITY["2"] == "lost_time"

    def test_numeric_code_3_is_recordable(self):
        from worldenergydata.hse.importers.osha_importer import DEGREE_SEVERITY

        assert DEGREE_SEVERITY["3"] == "recordable"

    def test_numeric_code_0_is_near_miss(self):
        from worldenergydata.hse.importers.osha_importer import DEGREE_SEVERITY

        assert DEGREE_SEVERITY["0"] == "near_miss"

    def test_text_fatality_maps_correctly(self):
        from worldenergydata.hse.importers.osha_importer import DEGREE_SEVERITY

        assert DEGREE_SEVERITY["Fatality"] == "fatality"

    def test_text_hospitalized_maps_correctly(self):
        from worldenergydata.hse.importers.osha_importer import DEGREE_SEVERITY

        assert DEGREE_SEVERITY["Hospitalized injury"] == "lost_time"

    def test_text_non_hospitalized_maps_correctly(self):
        from worldenergydata.hse.importers.osha_importer import DEGREE_SEVERITY

        assert DEGREE_SEVERITY["Non Hospitalized injury"] == "recordable"
        assert DEGREE_SEVERITY["Non-hospitalized injury"] == "recordable"

    def test_text_amputation_maps_correctly(self):
        from worldenergydata.hse.importers.osha_importer import DEGREE_SEVERITY

        assert DEGREE_SEVERITY["Amputation"] == "lost_time"

    def test_unknown_code_defaults_to_recordable(self):
        from worldenergydata.hse.importers.osha_importer import DEGREE_SEVERITY

        assert DEGREE_SEVERITY.get("99", "recordable") == "recordable"
        assert DEGREE_SEVERITY.get("", "recordable") == "recordable"


# ---------------------------------------------------------------------------
# Lookup table loading tests
# ---------------------------------------------------------------------------


class TestLookupTableLoading:
    """Test _load_accident_lookups reads CSV correctly."""

    def test_load_real_lookup_file(self):
        from worldenergydata.hse.importers.osha_importer import (
            _load_accident_lookups,
        )

        lookup_path = Path(
            "data/modules/hse/raw/osha/osha_accident_lookup2.csv"
        )
        if not lookup_path.exists():
            pytest.skip("Lookup file not available")

        lookups = _load_accident_lookups(lookup_path)
        assert isinstance(lookups, dict)
        assert len(lookups) > 0

        # DEGR code should be present
        assert "DEGR" in lookups
        assert lookups["DEGR"]["1"] == "Fatality"
        assert lookups["DEGR"]["2"] == "Hospitalized injury"

    def test_load_missing_file_returns_empty(self):
        from worldenergydata.hse.importers.osha_importer import (
            _load_accident_lookups,
        )

        result = _load_accident_lookups(Path("/nonexistent/path.csv"))
        assert result == {}

    def test_lookup_has_expected_code_types(self):
        from worldenergydata.hse.importers.osha_importer import (
            _load_accident_lookups,
        )

        lookup_path = Path(
            "data/modules/hse/raw/osha/osha_accident_lookup2.csv"
        )
        if not lookup_path.exists():
            pytest.skip("Lookup file not available")

        lookups = _load_accident_lookups(lookup_path)
        expected_codes = {"DEGR", "IN", "BD", "SO", "OCC", "HU"}
        found = set(lookups.keys())
        assert expected_codes.issubset(found), (
            f"Missing: {expected_codes - found}"
        )


# ---------------------------------------------------------------------------
# Field decoding tests
# ---------------------------------------------------------------------------


class TestFieldDecoding:
    """Test _decode_field resolves numeric codes to text."""

    def _make_lookups(self):
        return {
            "DEGR": {"1": "Fatality", "2": "Hospitalized injury"},
            "IN": {"5": "BURNS (HEAT)", "6": "CUTS, LACERATIONS"},
            "BD": {"1": "HEAD", "13": "BODY SYSTEMS"},
        }

    def test_decode_known_field(self):
        from worldenergydata.hse.importers.osha_importer import _decode_field

        lookups = self._make_lookups()
        assert _decode_field(lookups, "nature_of_inj", "5") == "BURNS (HEAT)"

    def test_decode_unknown_value_returns_raw(self):
        from worldenergydata.hse.importers.osha_importer import _decode_field

        lookups = self._make_lookups()
        assert _decode_field(lookups, "nature_of_inj", "999") == "999"

    def test_decode_unknown_field_returns_raw(self):
        from worldenergydata.hse.importers.osha_importer import _decode_field

        lookups = self._make_lookups()
        assert _decode_field(lookups, "unknown_field", "5") == "5"

    def test_decode_none_returns_none(self):
        from worldenergydata.hse.importers.osha_importer import _decode_field

        lookups = self._make_lookups()
        assert _decode_field(lookups, "nature_of_inj", None) is None

    def test_decode_body_part(self):
        from worldenergydata.hse.importers.osha_importer import _decode_field

        lookups = self._make_lookups()
        assert _decode_field(lookups, "part_of_body", "1") == "HEAD"


# ---------------------------------------------------------------------------
# Integration: _normalize_accident_injury severity mapping
# ---------------------------------------------------------------------------


class TestNormalizeAccidentInjurySeverity:
    """Test that _normalize_accident_injury maps degree_of_inj correctly."""

    def _make_importer(self):
        from worldenergydata.hse.importers.osha_importer import OSHAImporter

        mock_session = MagicMock()
        # Use a non-existent dir so no real files are loaded
        importer = OSHAImporter(
            db_session=mock_session,
            data_dir="/tmp/test_osha_nonexistent",
            use_filtered=False,
        )
        return importer

    def _make_row(self, degree_of_inj="1"):
        return pd.Series({
            "summary_nr": "100001",
            "rel_insp_nr": "200001",
            "age": "35",
            "sex": "M",
            "nature_of_inj": "5",
            "part_of_body": "1",
            "src_of_injury": "16",
            "event_type": "14",
            "evn_factor": "7",
            "hum_factor": "1",
            "occ_code": "585",
            "degree_of_inj": degree_of_inj,
            "event_date": "2020-01-15 00:00:00",
        })

    def test_degree_1_maps_to_fatality(self):
        importer = self._make_importer()
        row = self._make_row(degree_of_inj="1")
        result = importer._normalize_accident_injury(row)
        assert result is not None
        assert result["severity"] == "fatality"

    def test_degree_2_maps_to_lost_time(self):
        importer = self._make_importer()
        row = self._make_row(degree_of_inj="2")
        result = importer._normalize_accident_injury(row)
        assert result is not None
        assert result["severity"] == "lost_time"

    def test_degree_3_maps_to_recordable(self):
        importer = self._make_importer()
        row = self._make_row(degree_of_inj="3")
        result = importer._normalize_accident_injury(row)
        assert result is not None
        assert result["severity"] == "recordable"

    def test_degree_0_maps_to_near_miss(self):
        importer = self._make_importer()
        row = self._make_row(degree_of_inj="0")
        result = importer._normalize_accident_injury(row)
        assert result is not None
        assert result["severity"] == "near_miss"

    def test_unknown_degree_defaults_to_recordable(self):
        importer = self._make_importer()
        row = self._make_row(degree_of_inj="99")
        result = importer._normalize_accident_injury(row)
        assert result is not None
        assert result["severity"] == "recordable"

    def test_missing_event_date_returns_none(self):
        importer = self._make_importer()
        row = self._make_row()
        row["event_date"] = None
        result = importer._normalize_accident_injury(row)
        assert result is None

    def test_incident_id_format(self):
        importer = self._make_importer()
        row = self._make_row()
        result = importer._normalize_accident_injury(row)
        assert result is not None
        assert result["bsee_incident_id"] == "OSHA-INJ-200001-35-M"

    def test_incident_type_is_injury(self):
        importer = self._make_importer()
        row = self._make_row()
        result = importer._normalize_accident_injury(row)
        assert result is not None
        assert result["incident_type"] == "injury"


# ---------------------------------------------------------------------------
# Inspection type severity mapping
# ---------------------------------------------------------------------------


class TestInspectionTypeSeverity:
    """Test INSPECTION_TYPE_SEVERITY mapping."""

    def test_type_a_is_fatality(self):
        from worldenergydata.hse.importers.osha_importer import (
            INSPECTION_TYPE_SEVERITY,
        )

        assert INSPECTION_TYPE_SEVERITY["A"] == "fatality"

    def test_type_b_is_recordable(self):
        from worldenergydata.hse.importers.osha_importer import (
            INSPECTION_TYPE_SEVERITY,
        )

        assert INSPECTION_TYPE_SEVERITY["B"] == "recordable"

    def test_all_types_have_valid_severity(self):
        from worldenergydata.hse.importers.osha_importer import (
            INSPECTION_TYPE_SEVERITY,
        )

        valid = {"fatality", "lost_time", "recordable", "near_miss", "minor"}
        for key, val in INSPECTION_TYPE_SEVERITY.items():
            assert val in valid, f"Type {key} has invalid severity {val}"
