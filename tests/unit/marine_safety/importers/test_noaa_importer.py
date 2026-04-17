"""Tests for NOAA importer helper methods and constants."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from worldenergydata.marine_safety.constants import IncidentType
from worldenergydata.marine_safety.importers.noaa_importer import NOAAImporter


@pytest.fixture
def importer(tmp_path):
    source = tmp_path / "incidents.csv"
    source.write_text("id,name\n1,Test\n")
    session = MagicMock()
    return NOAAImporter(source_path=source, session=session)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestNOAAConstants:
    def test_threat_type_mappings(self):
        assert NOAAImporter.THREAT_TYPE_MAPPINGS["oil"] == IncidentType.POLLUTION
        assert NOAAImporter.THREAT_TYPE_MAPPINGS["chemical"] == IncidentType.POLLUTION
        assert NOAAImporter.THREAT_TYPE_MAPPINGS["other"] == IncidentType.OTHER

    def test_response_measure_mappings(self):
        m = NOAAImporter.RESPONSE_MEASURE_MAPPINGS
        assert m["measure_skim"] == "skimming"
        assert m["measure_shore"] == "shoreline_cleanup"
        assert m["measure_bio"] == "bioremediation"
        assert m["measure_disperse"] == "dispersants"
        assert m["measure_burn"] == "in_situ_burning"

    def test_cleanup_cost(self):
        assert NOAAImporter.CLEANUP_COST_PER_GALLON == 200


# ---------------------------------------------------------------------------
# _extract_incident_id
# ---------------------------------------------------------------------------


class TestExtractIncidentId:
    def test_valid(self, importer):
        assert importer._extract_incident_id({"id": "12345"}) == "12345"

    def test_strips_whitespace(self, importer):
        assert importer._extract_incident_id({"id": " 123 "}) == "123"

    def test_empty_returns_none(self, importer):
        assert importer._extract_incident_id({"id": ""}) is None

    def test_missing_returns_none(self, importer):
        assert importer._extract_incident_id({}) is None


# ---------------------------------------------------------------------------
# _parse_release_gallons
# ---------------------------------------------------------------------------


class TestParseReleaseGallons:
    def test_valid_number(self, importer):
        assert (
            importer._parse_release_gallons({"max_ptl_release_gallons": "5000"})
            == 5000.0
        )

    def test_float_number(self, importer):
        assert (
            importer._parse_release_gallons({"max_ptl_release_gallons": "1234.5"})
            == 1234.5
        )

    def test_zero_returns_none(self, importer):
        assert importer._parse_release_gallons({"max_ptl_release_gallons": "0"}) is None

    def test_none_string_returns_none(self, importer):
        assert (
            importer._parse_release_gallons({"max_ptl_release_gallons": "None"}) is None
        )

    def test_empty_returns_none(self, importer):
        assert importer._parse_release_gallons({"max_ptl_release_gallons": ""}) is None

    def test_invalid_returns_none(self, importer):
        assert (
            importer._parse_release_gallons({"max_ptl_release_gallons": "abc"}) is None
        )

    def test_missing_key_returns_none(self, importer):
        assert importer._parse_release_gallons({}) is None


# ---------------------------------------------------------------------------
# _parse_coordinates
# ---------------------------------------------------------------------------


class TestParseCoordinates:
    def test_valid_coords(self, importer):
        result = importer._parse_coordinates({"lat": "29.5", "lon": "-89.5"})
        assert result == pytest.approx((29.5, -89.5))

    def test_missing_lat(self, importer):
        assert importer._parse_coordinates({"lon": "-89.5"}) is None

    def test_missing_lon(self, importer):
        assert importer._parse_coordinates({"lat": "29.5"}) is None

    def test_empty_strings(self, importer):
        assert importer._parse_coordinates({"lat": "", "lon": ""}) is None

    def test_invalid_lat(self, importer):
        assert importer._parse_coordinates({"lat": "abc", "lon": "-89.5"}) is None

    def test_out_of_range_lat(self, importer):
        assert importer._parse_coordinates({"lat": "91", "lon": "-89.5"}) is None

    def test_out_of_range_lon(self, importer):
        assert importer._parse_coordinates({"lat": "29", "lon": "-181"}) is None


# ---------------------------------------------------------------------------
# _build_base_record
# ---------------------------------------------------------------------------


class TestBuildBaseRecord:
    def test_oil_threat(self, importer):
        dt = datetime(2024, 1, 15)
        rec = importer._build_base_record("ID1", dt, {"threat": "oil"})
        assert rec["source_agency"] == "NOAA_ORR"
        assert rec["source_incident_id"] == "ID1"
        assert rec["incident_date"] == dt
        assert rec["incident_type"] == IncidentType.POLLUTION

    def test_unknown_threat(self, importer):
        dt = datetime(2024, 1, 15)
        rec = importer._build_base_record("ID2", dt, {"threat": "unknown"})
        assert rec["incident_type"] == IncidentType.OTHER


# ---------------------------------------------------------------------------
# _add_title_and_description
# ---------------------------------------------------------------------------


class TestAddTitleAndDescription:
    def test_with_name_and_description(self, importer):
        parsed = {}
        importer._add_title_and_description(
            parsed, {"name": "Oil Spill", "description": "Major incident"}
        )
        assert parsed["title"] == "Oil Spill"
        assert "Oil Spill" in parsed["description"]
        assert "Major incident" in parsed["description"]

    def test_name_only(self, importer):
        parsed = {}
        importer._add_title_and_description(parsed, {"name": "Fire", "description": ""})
        assert parsed["title"] == "Fire"
        assert "description" not in parsed

    def test_truncates_name(self, importer):
        parsed = {}
        long_name = "X" * 600
        importer._add_title_and_description(
            parsed, {"name": long_name, "description": ""}
        )
        assert len(parsed["title"]) == 500

    def test_empty(self, importer):
        parsed = {}
        importer._add_title_and_description(parsed, {"name": "", "description": ""})
        assert "title" not in parsed
        assert "description" not in parsed


# ---------------------------------------------------------------------------
# _add_estimated_damage
# ---------------------------------------------------------------------------


class TestAddEstimatedDamage:
    def test_with_gallons(self, importer):
        parsed = {}
        importer._add_estimated_damage(parsed, {"max_ptl_release_gallons": "100"})
        assert parsed["estimated_damage_usd"] == Decimal("20000")

    def test_no_gallons(self, importer):
        parsed = {}
        importer._add_estimated_damage(parsed, {"max_ptl_release_gallons": ""})
        assert "estimated_damage_usd" not in parsed


# ---------------------------------------------------------------------------
# _add_location_data
# ---------------------------------------------------------------------------


class TestAddLocationData:
    def test_with_coords_and_name(self, importer):
        parsed = {}
        importer._add_location_data(
            parsed, {"lat": "30.0", "lon": "-90.0", "location": "Gulf of Mexico"}
        )
        assert parsed["location"]["latitude"] == pytest.approx(30.0)
        assert parsed["location"]["longitude"] == pytest.approx(-90.0)
        assert parsed["location"]["location_name"] == "Gulf of Mexico"

    def test_no_data(self, importer):
        parsed = {}
        importer._add_location_data(parsed, {"lat": "", "lon": "", "location": ""})
        assert "location" not in parsed
