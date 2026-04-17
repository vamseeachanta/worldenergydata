"""Tests for NTSB marine incident data importer pure-logic methods."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from worldenergydata.marine_safety.constants import (
    DataSource,
    IncidentStatus,
    IncidentType,
    VesselType,
)
from worldenergydata.marine_safety.importers.ntsb_importer import NTSBImporter


@pytest.fixture
def importer(tmp_path):
    """Create an NTSBImporter with a mock session and dummy file."""
    source = tmp_path / "ntsb.csv"
    source.write_text("header\n")
    session = MagicMock()
    return NTSBImporter(source_path=source, session=session)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestNTSBConstants:
    def test_field_mappings_not_empty(self):
        assert len(NTSBImporter.FIELD_MAPPINGS) > 20

    def test_accident_type_mappings(self):
        m = NTSBImporter.ACCIDENT_TYPE_MAPPINGS
        assert m["grounding"] == IncidentType.GROUNDING.value
        assert m["collision"] == IncidentType.COLLISION.value
        assert m["fire"] == IncidentType.FIRE.value

    def test_vessel_type_mappings(self):
        m = NTSBImporter.VESSEL_TYPE_MAPPINGS
        assert m["tanker"] == VesselType.TANKER.value
        assert m["tug"] == VesselType.TUG.value
        assert m["barge"] == VesselType.CARGO_VESSEL.value

    def test_status_mappings(self):
        m = NTSBImporter.STATUS_MAPPINGS
        assert m["final"] == IncidentStatus.FINAL_REPORT.value
        assert m["open"] == IncidentStatus.UNDER_INVESTIGATION.value
        assert m["closed"] == IncidentStatus.CLOSED.value


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestNTSBImporterInit:
    def test_defaults(self, tmp_path):
        source = tmp_path / "data.csv"
        source.write_text("header\n")
        imp = NTSBImporter(source_path=source, session=MagicMock())
        assert imp.file_format == "csv"
        assert imp.marine_only is True

    def test_custom_marine_only(self, tmp_path):
        source = tmp_path / "data.csv"
        source.write_text("header\n")
        imp = NTSBImporter(
            source_path=source,
            session=MagicMock(),
            marine_only=False,
        )
        assert imp.marine_only is False


# ---------------------------------------------------------------------------
# _get_ntsb_id
# ---------------------------------------------------------------------------


class TestGetNTSBId:
    def test_ntsb_id_field(self, importer):
        row = {"NTSB_ID": "MAR24AB001"}
        assert importer._get_ntsb_id(row) == "MAR24AB001"

    def test_ntsbid_field(self, importer):
        row = {"NTSBID": "MAR24AB002"}
        assert importer._get_ntsb_id(row) == "MAR24AB002"

    def test_accident_number(self, importer):
        row = {"ACCIDENT_NUMBER": "MAR24AB003"}
        assert importer._get_ntsb_id(row) == "MAR24AB003"

    def test_mkey(self, importer):
        row = {"MKEY": "MAR24AB004"}
        assert importer._get_ntsb_id(row) == "MAR24AB004"

    def test_strips_whitespace(self, importer):
        row = {"NTSB_ID": "  MAR24AB005  "}
        assert importer._get_ntsb_id(row) == "MAR24AB005"

    def test_no_id(self, importer):
        row = {"OTHER_FIELD": "value"}
        assert importer._get_ntsb_id(row) is None

    def test_empty_value(self, importer):
        row = {"NTSB_ID": ""}
        assert importer._get_ntsb_id(row) is None


# ---------------------------------------------------------------------------
# _map_accident_type
# ---------------------------------------------------------------------------


class TestMapAccidentType:
    def test_exact_match(self, importer):
        assert importer._map_accident_type("grounding") == IncidentType.GROUNDING.value
        assert importer._map_accident_type("collision") == IncidentType.COLLISION.value
        assert importer._map_accident_type("fire") == IncidentType.FIRE.value

    def test_case_insensitive(self, importer):
        assert importer._map_accident_type("GROUNDING") == IncidentType.GROUNDING.value

    def test_partial_match(self, importer):
        result = importer._map_accident_type("collision with vessel at sea")
        assert result == IncidentType.COLLISION.value

    def test_unknown(self, importer):
        assert importer._map_accident_type("unknown event") == IncidentType.OTHER.value

    def test_empty(self, importer):
        assert importer._map_accident_type("") == IncidentType.OTHER.value

    def test_none(self, importer):
        assert importer._map_accident_type(None) == IncidentType.OTHER.value


# ---------------------------------------------------------------------------
# _map_vessel_type
# ---------------------------------------------------------------------------


class TestMapVesselType:
    def test_exact_match(self, importer):
        assert importer._map_vessel_type("tanker") == VesselType.TANKER.value
        assert importer._map_vessel_type("tug") == VesselType.TUG.value
        assert (
            importer._map_vessel_type("cargo vessel") == VesselType.CARGO_VESSEL.value
        )

    def test_case_insensitive(self, importer):
        assert importer._map_vessel_type("TANKER") == VesselType.TANKER.value

    def test_partial_match(self, importer):
        assert importer._map_vessel_type("large oil tanker") == VesselType.TANKER.value

    def test_unknown(self, importer):
        assert importer._map_vessel_type("unknown vessel") == VesselType.OTHER.value

    def test_empty(self, importer):
        assert importer._map_vessel_type("") == VesselType.OTHER.value

    def test_none(self, importer):
        assert importer._map_vessel_type(None) == VesselType.OTHER.value


# ---------------------------------------------------------------------------
# _map_status
# ---------------------------------------------------------------------------


class TestMapStatus:
    def test_exact_match(self, importer):
        assert importer._map_status("final") == IncidentStatus.FINAL_REPORT.value
        assert importer._map_status("closed") == IncidentStatus.CLOSED.value
        assert importer._map_status("open") == IncidentStatus.UNDER_INVESTIGATION.value
        assert (
            importer._map_status("preliminary")
            == IncidentStatus.PRELIMINARY_REPORT.value
        )

    def test_case_insensitive(self, importer):
        assert importer._map_status("FINAL") == IncidentStatus.FINAL_REPORT.value

    def test_partial_match(self, importer):
        assert (
            importer._map_status("probable cause determined")
            == IncidentStatus.FINAL_REPORT.value
        )

    def test_unknown(self, importer):
        assert importer._map_status("xyz") == IncidentStatus.REPORTED.value

    def test_empty(self, importer):
        assert importer._map_status("") == IncidentStatus.REPORTED.value

    def test_none(self, importer):
        assert importer._map_status(None) == IncidentStatus.REPORTED.value


# ---------------------------------------------------------------------------
# _build_location_description
# ---------------------------------------------------------------------------


class TestBuildLocationDescription:
    def test_all_parts(self, importer):
        parsed = {
            "water_body": "Gulf of Mexico",
            "city": "Houston",
            "state": "TX",
            "country": "USA",
        }
        result = importer._build_location_description(parsed)
        assert "Gulf of Mexico" in result
        assert "Houston" in result
        assert "TX" in result
        assert "USA" in result

    def test_city_state_only(self, importer):
        parsed = {"city": "Seattle", "state": "WA"}
        result = importer._build_location_description(parsed)
        assert "Seattle" in result
        assert "WA" in result

    def test_no_parts(self, importer):
        parsed = {}
        result = importer._build_location_description(parsed)
        assert result is None


# ---------------------------------------------------------------------------
# _generate_title
# ---------------------------------------------------------------------------


class TestGenerateTitle:
    def test_with_all_fields(self, importer):
        parsed = {
            "vessel_name": "MV Cargo King",
            "incident_type": "collision",
            "source_incident_id": "MAR24AB001",
        }
        title = importer._generate_title(parsed)
        assert "MV Cargo King" in title
        assert "Collision" in title
        assert "MAR24AB001" in title

    def test_defaults(self, importer):
        parsed = {}
        title = importer._generate_title(parsed)
        assert "Unknown Vessel" in title


# ---------------------------------------------------------------------------
# _calculate_severity
# ---------------------------------------------------------------------------


class TestCalculateSeverity:
    def test_catastrophic(self, importer):
        assert importer._calculate_severity(10, 0, 0) == 5
        assert importer._calculate_severity(5, 0, 5) == 5

    def test_serious(self, importer):
        assert importer._calculate_severity(5, 0, 0) == 4

    def test_moderate_fatalities(self, importer):
        assert importer._calculate_severity(1, 0, 0) == 3

    def test_moderate_injuries(self, importer):
        assert importer._calculate_severity(0, 10, 0) == 3

    def test_minor(self, importer):
        assert importer._calculate_severity(0, 1, 0) == 2

    def test_minimal(self, importer):
        assert importer._calculate_severity(0, 0, 0) == 1


# ---------------------------------------------------------------------------
# clear_caches
# ---------------------------------------------------------------------------


class TestClearCaches:
    def test_clears(self, importer):
        importer._location_cache["key1"] = 1
        importer._vessel_cache["key2"] = 2
        importer.clear_caches()
        assert importer._location_cache == {}
        assert importer._vessel_cache == {}
