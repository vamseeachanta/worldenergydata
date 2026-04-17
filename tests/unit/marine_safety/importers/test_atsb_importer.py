"""Tests for ATSB marine incident data importer pure-logic methods."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from worldenergydata.marine_safety.constants import (
    DataSource,
    IncidentStatus,
    IncidentType,
    VesselType,
)
from worldenergydata.marine_safety.importers.atsb_importer import ATSBImporter


@pytest.fixture
def importer(tmp_path):
    """Create an ATSBImporter with a mock session and dummy file."""
    source = tmp_path / "dummy.csv"
    source.write_text("header\n")
    session = MagicMock()
    return ATSBImporter(source_path=source, session=session)


# ---------------------------------------------------------------------------
# Constants / class attributes
# ---------------------------------------------------------------------------


class TestATSBConstants:
    def test_field_mappings_not_empty(self):
        assert len(ATSBImporter.FIELD_MAPPINGS) > 20

    def test_australian_states_nsw(self):
        assert ATSBImporter.AUSTRALIAN_STATES["nsw"] == "NSW"
        assert ATSBImporter.AUSTRALIAN_STATES["new south wales"] == "NSW"

    def test_occurrence_type_mappings(self):
        assert (
            ATSBImporter.OCCURRENCE_TYPE_MAPPINGS["grounding"]
            == IncidentType.GROUNDING.value
        )
        assert (
            ATSBImporter.OCCURRENCE_TYPE_MAPPINGS["collision"]
            == IncidentType.COLLISION.value
        )
        assert ATSBImporter.OCCURRENCE_TYPE_MAPPINGS["fire"] == IncidentType.FIRE.value

    def test_vessel_type_mappings(self):
        assert ATSBImporter.VESSEL_TYPE_MAPPINGS["tanker"] == VesselType.TANKER.value
        assert ATSBImporter.VESSEL_TYPE_MAPPINGS["tug"] == VesselType.TUG.value
        assert ATSBImporter.VESSEL_TYPE_MAPPINGS["fpso"] == VesselType.FPSO.value

    def test_status_mappings(self):
        assert (
            ATSBImporter.STATUS_MAPPINGS["final"] == IncidentStatus.FINAL_REPORT.value
        )
        assert (
            ATSBImporter.STATUS_MAPPINGS["active"]
            == IncidentStatus.UNDER_INVESTIGATION.value
        )
        assert ATSBImporter.STATUS_MAPPINGS["closed"] == IncidentStatus.CLOSED.value


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestATSBImporterInit:
    def test_auto_detect_csv(self, tmp_path):
        source = tmp_path / "data.csv"
        source.write_text("header\n")
        imp = ATSBImporter(source_path=source, session=MagicMock())
        assert imp.file_format == "csv"

    def test_auto_detect_json(self, tmp_path):
        source = tmp_path / "data.json"
        source.write_text('{"data": []}')
        imp = ATSBImporter(source_path=source, session=MagicMock())
        assert imp.file_format == "json"

    def test_auto_detect_unsupported(self, tmp_path):
        source = tmp_path / "data.xml"
        source.write_text("<root/>")
        with pytest.raises(ValueError, match="Cannot auto-detect"):
            ATSBImporter(source_path=source, session=MagicMock())

    def test_explicit_format(self, tmp_path):
        source = tmp_path / "data.txt"
        source.write_text("data")
        imp = ATSBImporter(source_path=source, session=MagicMock(), file_format="csv")
        assert imp.file_format == "csv"

    def test_caches_initialized(self, importer):
        assert importer._location_cache == {}
        assert importer._vessel_cache == {}


# ---------------------------------------------------------------------------
# _normalize_state
# ---------------------------------------------------------------------------


class TestNormalizeState:
    def test_standard_abbreviation(self, importer):
        assert importer._normalize_state("nsw") == "NSW"
        assert importer._normalize_state("vic") == "VIC"
        assert importer._normalize_state("qld") == "QLD"
        assert importer._normalize_state("wa") == "WA"
        assert importer._normalize_state("sa") == "SA"
        assert importer._normalize_state("tas") == "TAS"
        assert importer._normalize_state("nt") == "NT"
        assert importer._normalize_state("act") == "ACT"

    def test_full_names(self, importer):
        assert importer._normalize_state("new south wales") == "NSW"
        assert importer._normalize_state("western australia") == "WA"
        assert importer._normalize_state("tasmania") == "TAS"

    def test_dotted_abbreviations(self, importer):
        assert importer._normalize_state("n.s.w.") == "NSW"

    def test_short_unknown_uppercased(self, importer):
        assert importer._normalize_state("TX") == "TX"

    def test_long_unknown_returned_as_is(self, importer):
        assert importer._normalize_state("Unknown Region") == "Unknown Region"

    def test_none(self, importer):
        assert importer._normalize_state(None) is None

    def test_empty(self, importer):
        assert importer._normalize_state("") is None

    def test_whitespace(self, importer):
        assert importer._normalize_state("  nsw  ") == "NSW"


# ---------------------------------------------------------------------------
# _map_occurrence_type
# ---------------------------------------------------------------------------


class TestMapOccurrenceType:
    def test_exact_match(self, importer):
        assert (
            importer._map_occurrence_type("grounding") == IncidentType.GROUNDING.value
        )
        assert (
            importer._map_occurrence_type("collision") == IncidentType.COLLISION.value
        )
        assert importer._map_occurrence_type("fire") == IncidentType.FIRE.value
        assert (
            importer._map_occurrence_type("explosion") == IncidentType.EXPLOSION.value
        )

    def test_case_insensitive(self, importer):
        assert (
            importer._map_occurrence_type("GROUNDING") == IncidentType.GROUNDING.value
        )
        assert importer._map_occurrence_type("Fire") == IncidentType.FIRE.value

    def test_partial_match(self, importer):
        result = importer._map_occurrence_type("fire/explosion at sea")
        assert result in (IncidentType.FIRE.value, IncidentType.EXPLOSION.value)

    def test_unknown(self, importer):
        assert (
            importer._map_occurrence_type("xyz unknown event")
            == IncidentType.OTHER.value
        )

    def test_empty(self, importer):
        assert importer._map_occurrence_type("") == IncidentType.OTHER.value

    def test_none_like(self, importer):
        assert importer._map_occurrence_type(None) == IncidentType.OTHER.value

    def test_flooding(self, importer):
        assert importer._map_occurrence_type("flooding") == IncidentType.FLOODING.value

    def test_capsizing(self, importer):
        assert (
            importer._map_occurrence_type("capsizing") == IncidentType.CAPSIZING.value
        )

    def test_equipment_failure(self, importer):
        assert (
            importer._map_occurrence_type("equipment failure")
            == IncidentType.EQUIPMENT_FAILURE.value
        )

    def test_weather(self, importer):
        assert (
            importer._map_occurrence_type("heavy weather")
            == IncidentType.WEATHER_RELATED.value
        )


# ---------------------------------------------------------------------------
# _map_vessel_type
# ---------------------------------------------------------------------------


class TestMapVesselType:
    def test_exact_match(self, importer):
        assert importer._map_vessel_type("tanker") == VesselType.TANKER.value
        assert importer._map_vessel_type("tug") == VesselType.TUG.value
        assert importer._map_vessel_type("fpso") == VesselType.FPSO.value

    def test_case_insensitive(self, importer):
        assert importer._map_vessel_type("TANKER") == VesselType.TANKER.value

    def test_partial_match(self, importer):
        assert importer._map_vessel_type("large oil tanker") == VesselType.TANKER.value

    def test_unknown(self, importer):
        assert importer._map_vessel_type("submarine") == VesselType.OTHER.value

    def test_empty(self, importer):
        assert importer._map_vessel_type("") == VesselType.OTHER.value

    def test_none_like(self, importer):
        assert importer._map_vessel_type(None) == VesselType.OTHER.value

    def test_offshore(self, importer):
        assert (
            importer._map_vessel_type("drilling rig") == VesselType.DRILLING_RIG.value
        )
        assert (
            importer._map_vessel_type("supply vessel") == VesselType.SUPPLY_VESSEL.value
        )

    def test_research(self, importer):
        assert (
            importer._map_vessel_type("research vessel")
            == VesselType.RESEARCH_VESSEL.value
        )


# ---------------------------------------------------------------------------
# _map_status
# ---------------------------------------------------------------------------


class TestMapStatus:
    def test_exact_match(self, importer):
        assert importer._map_status("final") == IncidentStatus.FINAL_REPORT.value
        assert importer._map_status("closed") == IncidentStatus.CLOSED.value
        assert (
            importer._map_status("active") == IncidentStatus.UNDER_INVESTIGATION.value
        )

    def test_case_insensitive(self, importer):
        assert importer._map_status("FINAL") == IncidentStatus.FINAL_REPORT.value

    def test_partial_match(self, importer):
        assert (
            importer._map_status("final report published")
            == IncidentStatus.FINAL_REPORT.value
        )

    def test_unknown(self, importer):
        assert importer._map_status("xyz") == IncidentStatus.REPORTED.value

    def test_empty(self, importer):
        assert importer._map_status("") == IncidentStatus.REPORTED.value

    def test_none_like(self, importer):
        assert importer._map_status(None) == IncidentStatus.REPORTED.value


# ---------------------------------------------------------------------------
# _build_location_description
# ---------------------------------------------------------------------------


class TestBuildLocationDescription:
    def test_all_parts(self, importer):
        parsed = {"water_body": "Coral Sea", "city": "Brisbane", "state": "QLD"}
        result = importer._build_location_description(parsed)
        assert "Coral Sea" in result
        assert "Brisbane" in result
        assert "QLD" in result
        assert "Australia" in result

    def test_state_only(self, importer):
        parsed = {"state": "NSW"}
        result = importer._build_location_description(parsed)
        assert "NSW" in result
        assert "Australia" in result

    def test_no_parts(self, importer):
        parsed = {}
        result = importer._build_location_description(parsed)
        assert result == "Australian waters"


# ---------------------------------------------------------------------------
# _generate_title
# ---------------------------------------------------------------------------


class TestGenerateTitle:
    def test_with_all_fields(self, importer):
        parsed = {
            "vessel_name": "MV Explorer",
            "incident_type": "grounding",
            "source_incident_id": "MO-2024-001",
        }
        title = importer._generate_title(parsed)
        assert "MV Explorer" in title
        assert "Grounding" in title
        assert "MO-2024-001" in title

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
        assert importer._calculate_severity(3, 0, 2) == 4

    def test_moderate_fatalities(self, importer):
        assert importer._calculate_severity(1, 0, 0) == 3

    def test_moderate_injuries(self, importer):
        assert importer._calculate_severity(0, 10, 0) == 3

    def test_minor(self, importer):
        assert importer._calculate_severity(0, 1, 0) == 2

    def test_minimal(self, importer):
        assert importer._calculate_severity(0, 0, 0) == 1


# ---------------------------------------------------------------------------
# _parse_nested_record
# ---------------------------------------------------------------------------


class TestParseNestedRecord:
    def test_basic(self, importer):
        raw = {
            "source_id": "MO-2024-001",
            "event_date": "2024-01-15",
            "incident_type": "grounding",
            "status": "final",
            "title": "Test Incident",
            "description": "Details here",
            "location": {
                "latitude": -33.8,
                "longitude": 151.2,
                "state": "NSW",
                "description": "Sydney Harbour",
                "city": "Sydney",
            },
            "vessel": {
                "name": "MV Test",
                "type": "tanker",
                "flag": "AUS",
                "gross_tonnage": 50000,
            },
            "casualties": {
                "fatalities": 0,
                "injuries": 2,
                "missing": 0,
            },
        }
        parsed = importer._parse_nested_record(raw)
        assert parsed["source_incident_id"] == "MO-2024-001"
        assert parsed["latitude"] == -33.8
        assert parsed["vessel_name"] == "MV Test"
        assert parsed["fatalities"] == 0
        assert parsed["injuries"] == 2

    def test_missing_nested(self, importer):
        raw = {"source_id": "MO-2024-002", "event_date": "2024-01-01"}
        parsed = importer._parse_nested_record(raw)
        assert parsed["source_incident_id"] == "MO-2024-002"


# ---------------------------------------------------------------------------
# _parse_flat_record
# ---------------------------------------------------------------------------


class TestParseFlatRecord:
    def test_basic(self, importer):
        raw = {
            "ATSB_ID": "MO-2024-001",
            "OCCURRENCE_DATE": "2024-01-15",
            "VESSEL_NAME": "MV Flat",
            "LATITUDE": "-33.8",
        }
        parsed = importer._parse_flat_record(raw)
        assert parsed["source_incident_id"] == "MO-2024-001"
        assert parsed["incident_date"] == "2024-01-15"
        assert parsed["vessel_name"] == "MV Flat"
        assert parsed["latitude"] == "-33.8"

    def test_empty_values_skipped(self, importer):
        raw = {"ATSB_ID": "MO-2024-002", "VESSEL_NAME": ""}
        parsed = importer._parse_flat_record(raw)
        assert "vessel_name" not in parsed

    def test_uppercase_fallback(self, importer):
        raw = {"atsb_id": "MO-2024-003"}
        parsed = importer._parse_flat_record(raw)
        assert parsed["source_incident_id"] == "MO-2024-003"


# ---------------------------------------------------------------------------
# _get_atsb_id
# ---------------------------------------------------------------------------


class TestGetATSBId:
    def test_atsb_id_field(self, importer):
        row = {"ATSB_ID": "MO-2024-001"}
        assert importer._get_atsb_id(row) == "MO-2024-001"

    def test_investigation_number(self, importer):
        row = {"INVESTIGATION_NUMBER": "MO-2024-002"}
        assert importer._get_atsb_id(row) == "MO-2024-002"

    def test_source_id(self, importer):
        row = {"source_id": "MO-2024-003"}
        assert importer._get_atsb_id(row) == "MO-2024-003"

    def test_strips_whitespace(self, importer):
        row = {"ATSB_ID": "  MO-2024-004  "}
        assert importer._get_atsb_id(row) == "MO-2024-004"

    def test_no_id_found(self, importer):
        row = {"OTHER_FIELD": "value"}
        assert importer._get_atsb_id(row) is None

    def test_empty_value(self, importer):
        row = {"ATSB_ID": ""}
        assert importer._get_atsb_id(row) is None


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
