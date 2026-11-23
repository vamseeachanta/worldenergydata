"""Tests for Boating Accident Report Database (BARD) importer pure-logic methods."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from worldenergydata.marine_safety.importers.boating_importer import BoatingImporter


@pytest.fixture
def importer(tmp_path):
    """Create a BoatingImporter with a mock session and dummy file."""
    source = tmp_path / "Accidents.csv"
    source.write_text("BARDID,Date,State\n")
    session = MagicMock()
    return BoatingImporter(accidents_file=source, session=session)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestBoatingConstants:
    def test_field_mappings(self):
        m = BoatingImporter.FIELD_MAPPINGS
        assert m["BARDID"] == "source_incident_id"
        assert m["Date"] == "incident_date"
        assert m["State"] == "state_code"
        assert m["Numberdeaths"] == "fatalities"
        assert m["Numberinjured"] == "injuries"

    def test_incident_type_mappings(self):
        m = BoatingImporter.INCIDENT_TYPE_MAPPINGS
        assert m["collision with vessel"] == "collision"
        assert m["grounding"] == "grounding"
        assert m["capsizing"] == "capsizing"
        assert m["fire"] == "fire"
        assert m["explosion"] == "explosion"
        assert m["flooding"] == "flooding"

    def test_vessel_type_mappings(self):
        m = BoatingImporter.VESSEL_TYPE_MAPPINGS
        assert m["personal watercraft"] == "other"
        assert m["cabin motorboat"] == "other"
        assert m["houseboat"] == "passenger"


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestBoatingImporterInit:
    def test_defaults(self, tmp_path):
        source = tmp_path / "acc.csv"
        source.write_text("header\n")
        imp = BoatingImporter(accidents_file=source, session=MagicMock())
        assert imp.vessels_file is None
        assert imp.deaths_file is None
        assert imp.injuries_file is None
        assert imp.vessels_by_bardid == {}
        assert imp.deaths_by_bardid == {}
        assert imp.injuries_by_bardid == {}

    def test_with_related_files(self, tmp_path):
        acc = tmp_path / "acc.csv"
        acc.write_text("header\n")
        vessels = tmp_path / "vessels.csv"
        vessels.write_text("header\n")
        imp = BoatingImporter(
            accidents_file=acc,
            vessels_file=vessels,
            session=MagicMock(),
        )
        assert imp.vessels_file == vessels


# ---------------------------------------------------------------------------
# _extract_incident_id
# ---------------------------------------------------------------------------


class TestExtractIncidentId:
    def test_normal(self, importer):
        assert importer._extract_incident_id({"BARDID": "123"}) == "123"

    def test_strips_whitespace(self, importer):
        assert importer._extract_incident_id({"BARDID": "  456  "}) == "456"

    def test_strips_quotes(self, importer):
        assert importer._extract_incident_id({"BARDID": '"789"'}) == "789"

    def test_empty(self, importer):
        assert importer._extract_incident_id({"BARDID": ""}) is None

    def test_missing(self, importer):
        assert importer._extract_incident_id({}) is None


# ---------------------------------------------------------------------------
# _clean_field_value
# ---------------------------------------------------------------------------


class TestCleanFieldValue:
    def test_normal(self, importer):
        assert importer._clean_field_value("hello") == "hello"

    def test_strips(self, importer):
        assert importer._clean_field_value("  hello  ") == "hello"

    def test_strips_quotes(self, importer):
        assert importer._clean_field_value('"hello"') == "hello"

    def test_empty(self, importer):
        assert importer._clean_field_value("") == ""

    def test_none(self, importer):
        assert importer._clean_field_value(None) == ""


# ---------------------------------------------------------------------------
# _is_valid_field_value
# ---------------------------------------------------------------------------


class TestIsValidFieldValue:
    def test_normal(self, importer):
        assert importer._is_valid_field_value("hello") is True

    def test_empty(self, importer):
        assert importer._is_valid_field_value("") is False

    def test_negative_one(self, importer):
        assert importer._is_valid_field_value("-1") is False

    def test_unknown(self, importer):
        assert importer._is_valid_field_value("Unknown") is False

    def test_unk(self, importer):
        assert importer._is_valid_field_value("Unk") is False


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------


class TestParseDate:
    def test_mm_dd_yy(self, importer):
        result = importer._parse_date("01/15/05")
        assert isinstance(result, datetime)
        assert result.month == 1
        assert result.day == 15

    def test_mm_dd_yyyy(self, importer):
        result = importer._parse_date("12/25/2010")
        assert isinstance(result, datetime)
        assert result.year == 2010

    def test_with_time(self, importer):
        result = importer._parse_date("06/15/08 14:30:00")
        assert isinstance(result, datetime)
        assert result.month == 6

    def test_empty(self, importer):
        assert importer._parse_date("") is None

    def test_none(self, importer):
        assert importer._parse_date(None) is None

    def test_invalid(self, importer):
        assert importer._parse_date("not-a-date") is None


# ---------------------------------------------------------------------------
# _parse_length
# ---------------------------------------------------------------------------


class TestParseLength:
    def test_normal(self, importer):
        result = importer._parse_length("10")
        assert result == pytest.approx(3.048, abs=0.01)

    def test_float(self, importer):
        result = importer._parse_length("20.5")
        assert result == pytest.approx(20.5 * 0.3048, abs=0.01)

    def test_negative_one(self, importer):
        assert importer._parse_length("-1") is None

    def test_unknown(self, importer):
        assert importer._parse_length("Unknown") is None

    def test_empty(self, importer):
        assert importer._parse_length("") is None

    def test_invalid(self, importer):
        assert importer._parse_length("abc") is None


# ---------------------------------------------------------------------------
# _parse_year
# ---------------------------------------------------------------------------


class TestParseYear:
    def test_four_digit(self, importer):
        assert importer._parse_year("2005") == 2005

    def test_two_digit_old(self, importer):
        assert importer._parse_year("95") == 1995

    def test_two_digit_new(self, importer):
        assert importer._parse_year("10") == 2010

    def test_negative_one(self, importer):
        assert importer._parse_year("-1") is None

    def test_unknown(self, importer):
        assert importer._parse_year("Unknown") is None

    def test_empty(self, importer):
        assert importer._parse_year("") is None

    def test_invalid(self, importer):
        assert importer._parse_year("abc") is None

    def test_out_of_range(self, importer):
        assert importer._parse_year("1800") is None


# ---------------------------------------------------------------------------
# _parse_int_safely
# ---------------------------------------------------------------------------


class TestParseIntSafely:
    def test_normal(self, importer):
        assert importer._parse_int_safely("42") == 42

    def test_int(self, importer):
        assert importer._parse_int_safely(10) == 10

    def test_invalid(self, importer):
        assert importer._parse_int_safely("abc") == 0

    def test_none(self, importer):
        assert importer._parse_int_safely(None) == 0

    def test_custom_default(self, importer):
        assert importer._parse_int_safely("abc", -1) == -1


# ---------------------------------------------------------------------------
# _map_vessel_type
# ---------------------------------------------------------------------------


class TestMapVesselType:
    def test_known(self, importer):
        assert importer._map_vessel_type("personal watercraft") == "other"
        assert importer._map_vessel_type("houseboat") == "passenger"

    def test_case_insensitive(self, importer):
        assert importer._map_vessel_type("Personal Watercraft") == "other"

    def test_unknown(self, importer):
        assert importer._map_vessel_type("submarine") == "other"

    def test_empty(self, importer):
        assert importer._map_vessel_type("") == "other"

    def test_none_like(self, importer):
        assert importer._map_vessel_type(None) == "other"


# ---------------------------------------------------------------------------
# _build_base_record
# ---------------------------------------------------------------------------


class TestBuildBaseRecord:
    def test_basic(self, importer):
        raw = {"BARDID": "123", "State": "FL", "Date": "01/15/05"}
        result = importer._build_base_record("123", raw)
        assert result["source_agency"] == "USCG_BARD"
        assert result["source_incident_id"] == "123"
        assert result["state_code"] == "FL"

    def test_skips_invalid(self, importer):
        raw = {"BARDID": "123", "State": "-1"}
        result = importer._build_base_record("123", raw)
        assert "state_code" not in result


# ---------------------------------------------------------------------------
# _add_incident_type
# ---------------------------------------------------------------------------


class TestAddIncidentType:
    def test_known_event(self, importer):
        parsed = {}
        raw = {"AccidentEvent1": "Grounding"}
        importer._add_incident_type(parsed, raw)
        assert parsed["incident_type"] == "grounding"

    def test_unknown_event(self, importer):
        parsed = {}
        raw = {"AccidentEvent1": "xyz"}
        importer._add_incident_type(parsed, raw)
        assert parsed["incident_type"] == "other"

    def test_no_event(self, importer):
        parsed = {}
        raw = {}
        importer._add_incident_type(parsed, raw)
        assert "incident_type" not in parsed


# ---------------------------------------------------------------------------
# _add_damage_estimate
# ---------------------------------------------------------------------------


class TestAddDamageEstimate:
    def test_normal(self, importer):
        parsed = {"estimated_damage_usd": "1,500"}
        importer._add_damage_estimate(parsed)
        assert parsed["estimated_damage_usd"] == 1500.0

    def test_with_dollar_sign(self, importer):
        parsed = {"estimated_damage_usd": "$2,000"}
        importer._add_damage_estimate(parsed)
        assert parsed["estimated_damage_usd"] == 2000.0

    def test_invalid(self, importer):
        parsed = {"estimated_damage_usd": "unknown"}
        importer._add_damage_estimate(parsed)
        assert parsed["estimated_damage_usd"] is None

    def test_missing(self, importer):
        parsed = {}
        importer._add_damage_estimate(parsed)
        assert "estimated_damage_usd" not in parsed


# ---------------------------------------------------------------------------
# _add_location_data
# ---------------------------------------------------------------------------


class TestAddLocationData:
    def test_full(self, importer):
        parsed = {}
        raw = {
            "State": "FL",
            "NearestCityorTown": "Miami",
            "County": "Dade",
            "NameofBodyofWater": "Biscayne Bay",
        }
        importer._add_location_data(parsed, raw)
        assert parsed["location"]["state_code"] == "FL"
        assert parsed["location"]["city"] == "Miami"
        assert parsed["location"]["county"] == "Dade"
        assert parsed["location"]["body_of_water"] == "Biscayne Bay"

    def test_no_state(self, importer):
        parsed = {}
        raw = {}
        importer._add_location_data(parsed, raw)
        assert "location" not in parsed


# ---------------------------------------------------------------------------
# _build_vessel_record
# ---------------------------------------------------------------------------


class TestBuildVesselRecord:
    def test_basic(self, importer):
        vessel_data = {
            "VesselName": "SS Minnow",
            "Vesseltype": "Cabin Motorboat",
            "Length": "20",
            "Yearbuilt": "1995",
            "RegistrationNumber": "FL12345",
        }
        result = importer._build_vessel_record(vessel_data)
        assert result["vessel_name"] == "SS Minnow"
        assert result["vessel_type"] == "other"
        assert result["length_meters"] == pytest.approx(6.096, abs=0.01)
        assert result["year_built"] == 1995
        assert result["registration_number"] == "FL12345"

    def test_empty_fields(self, importer):
        vessel_data = {}
        result = importer._build_vessel_record(vessel_data)
        assert result["vessel_name"] == ""
        assert result["vessel_type"] == "other"
        assert result["length_meters"] is None
        assert result["year_built"] is None


# ---------------------------------------------------------------------------
# _load_related_data
# ---------------------------------------------------------------------------


class TestLoadRelatedData:
    def test_loads_vessels(self, tmp_path):
        acc = tmp_path / "acc.csv"
        acc.write_text("BARDID\n1\n")
        vessels = tmp_path / "vessels.csv"
        vessels.write_text("BARDID,VesselName\n1,Test Boat\n")
        imp = BoatingImporter(
            accidents_file=acc,
            vessels_file=vessels,
            session=MagicMock(),
        )
        imp._load_related_data()
        assert "1" in imp.vessels_by_bardid
        assert imp.vessels_by_bardid["1"][0]["VesselName"] == "Test Boat"

    def test_loads_deaths(self, tmp_path):
        acc = tmp_path / "acc.csv"
        acc.write_text("BARDID\n1\n")
        deaths = tmp_path / "deaths.csv"
        deaths.write_text("BARDID,Name\n1,John\n1,Jane\n")
        imp = BoatingImporter(
            accidents_file=acc,
            deaths_file=deaths,
            session=MagicMock(),
        )
        imp._load_related_data()
        assert len(imp.deaths_by_bardid["1"]) == 2

    def test_loads_injuries(self, tmp_path):
        acc = tmp_path / "acc.csv"
        acc.write_text("BARDID\n1\n")
        injuries = tmp_path / "injuries.csv"
        injuries.write_text("BARDID,InjuryType\n1,Bruise\n1,Cut\n1,Burn\n")
        imp = BoatingImporter(
            accidents_file=acc,
            injuries_file=injuries,
            session=MagicMock(),
        )
        imp._load_related_data()
        assert imp.injuries_by_bardid["1"] == 3

    def test_no_related_files(self, importer):
        importer._load_related_data()
        assert importer.vessels_by_bardid == {}
        assert importer.deaths_by_bardid == {}
        assert importer.injuries_by_bardid == {}
