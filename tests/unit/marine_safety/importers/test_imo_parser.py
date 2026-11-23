"""Tests for IMO GISIS data parser functions."""

from decimal import Decimal

from worldenergydata.marine_safety.importers.imo_parser import (
    build_environmental_impact,
    build_location_description,
    calculate_severity,
    generate_title,
    map_casualty_type,
    map_ship_type,
    map_status,
    parse_contributing_factors,
    parse_position,
)


class TestParsePosition:
    def test_decimal_format(self):
        lat, lon = parse_position("12.345, -67.890")
        assert lat == Decimal("12.345")
        assert lon == Decimal("-67.890")

    def test_decimal_with_semicolon(self):
        lat, lon = parse_position("51.5; -0.1")
        assert lat == Decimal("51.5")
        assert lon == Decimal("-0.1")

    def test_dms_format(self):
        lat, lon = parse_position("12 30 N, 067 45 W")
        assert lat is not None
        assert lon is not None
        assert lat > 0  # North
        assert lon < 0  # West

    def test_dms_with_seconds(self):
        lat, lon = parse_position("12 30 45 N, 067 45 30 W")
        assert lat is not None
        assert lon is not None

    def test_empty_string(self):
        lat, lon = parse_position("")
        assert lat is None
        assert lon is None

    def test_none_input(self):
        lat, lon = parse_position(None)
        assert lat is None
        assert lon is None

    def test_invalid_format(self):
        lat, lon = parse_position("not a position")
        assert lat is None
        assert lon is None

    def test_out_of_range_latitude(self):
        lat, lon = parse_position("100.0, 50.0")
        assert lat is None
        assert lon is None

    def test_out_of_range_longitude(self):
        lat, lon = parse_position("50.0, 200.0")
        assert lat is None
        assert lon is None

    def test_south_west(self):
        lat, lon = parse_position("33 52 S, 151 12 E")
        assert lat is not None
        assert lon is not None
        assert lat < 0  # South
        assert lon > 0  # East


class TestMapCasualtyType:
    def test_empty(self):
        result = map_casualty_type("")
        assert result is not None  # Should return default

    def test_none(self):
        result = map_casualty_type(None)
        assert result is not None  # Should return default

    def test_unknown_type(self):
        result = map_casualty_type("very unusual incident")
        assert result is not None


class TestMapShipType:
    def test_empty(self):
        result = map_ship_type("")
        assert result is not None

    def test_none(self):
        result = map_ship_type(None)
        assert result is not None

    def test_unknown_type(self):
        result = map_ship_type("flying saucer")
        assert result is not None


class TestMapStatus:
    def test_empty(self):
        result = map_status("")
        assert result is not None

    def test_none(self):
        result = map_status(None)
        assert result is not None

    def test_unknown(self):
        result = map_status("very unusual status")
        assert result is not None


class TestParseContributingFactors:
    def test_empty(self):
        assert parse_contributing_factors("") == []

    def test_none(self):
        assert parse_contributing_factors(None) == []

    def test_single_factor(self):
        result = parse_contributing_factors("human error")
        assert len(result) >= 1

    def test_comma_separated(self):
        result = parse_contributing_factors("mechanical failure, human error")
        assert len(result) >= 1

    def test_semicolon_separated(self):
        result = parse_contributing_factors("equipment failure; weather")
        assert len(result) >= 1

    def test_slash_separated(self):
        result = parse_contributing_factors("fire/explosion")
        assert len(result) >= 1

    def test_unknown_factor(self):
        result = parse_contributing_factors("completely unknown factor xyz")
        assert len(result) >= 1


class TestBuildLocationDescription:
    def test_all_fields(self):
        parsed = {
            "area": "North Sea",
            "waters": "Territorial waters",
            "investigating_state": "Norway",
        }
        result = build_location_description(parsed)
        assert "North Sea" in result
        assert "Territorial waters" in result
        assert "Norway" in result

    def test_area_only(self):
        parsed = {"area": "Mediterranean Sea"}
        result = build_location_description(parsed)
        assert result == "Mediterranean Sea"

    def test_waters_only(self):
        parsed = {"waters": "International waters"}
        result = build_location_description(parsed)
        assert result == "International waters"

    def test_investigating_state_only(self):
        parsed = {"investigating_state": "UK"}
        result = build_location_description(parsed)
        assert "UK" in result
        assert "Waters of" in result

    def test_empty(self):
        result = build_location_description({})
        assert result is None

    def test_none_values(self):
        parsed = {"area": None, "waters": None}
        result = build_location_description(parsed)
        assert result is None


class TestBuildEnvironmentalImpact:
    def test_both_fields(self):
        parsed = {"pollution_type": "Oil", "pollution_quantity": "100 tonnes"}
        result = build_environmental_impact(parsed)
        assert "Oil" in result
        assert "100 tonnes" in result

    def test_type_only(self):
        parsed = {"pollution_type": "Chemical"}
        result = build_environmental_impact(parsed)
        assert "Chemical" in result

    def test_quantity_only(self):
        parsed = {"pollution_quantity": "50 tonnes"}
        result = build_environmental_impact(parsed)
        assert "50 tonnes" in result

    def test_empty(self):
        result = build_environmental_impact({})
        assert result == ""

    def test_none_values(self):
        result = build_environmental_impact({"pollution_type": None})
        assert result == ""


class TestGenerateTitle:
    def test_with_imo_number(self):
        parsed = {
            "vessel_name": "MV Explorer",
            "incident_type": "collision",
            "imo_number": "1234567",
        }
        result = generate_title(parsed)
        assert "Collision" in result
        assert "MV Explorer" in result
        assert "IMO 1234567" in result

    def test_without_imo_number(self):
        parsed = {
            "vessel_name": "MV Explorer",
            "incident_type": "grounding",
        }
        result = generate_title(parsed)
        assert "Grounding" in result
        assert "MV Explorer" in result
        assert "IMO" not in result

    def test_default_vessel_name(self):
        parsed = {"incident_type": "fire"}
        result = generate_title(parsed)
        assert "Unknown Vessel" in result
        assert "Fire" in result

    def test_underscore_incident_type(self):
        parsed = {
            "vessel_name": "Test Ship",
            "incident_type": "hull_failure",
        }
        result = generate_title(parsed)
        assert "Hull Failure" in result

    def test_empty_imo_number(self):
        parsed = {
            "vessel_name": "Test Ship",
            "incident_type": "fire",
            "imo_number": "",
        }
        result = generate_title(parsed)
        assert "IMO" not in result


class TestCalculateSeverity:
    def test_catastrophic(self):
        assert calculate_severity(10, 0, 0) == 5
        assert calculate_severity(5, 0, 5) == 5
        assert calculate_severity(0, 0, 10) == 5

    def test_serious(self):
        assert calculate_severity(5, 0, 0) == 4
        assert calculate_severity(3, 0, 2) == 4

    def test_moderate_from_fatalities(self):
        assert calculate_severity(1, 0, 0) == 3
        assert calculate_severity(0, 0, 1) == 3

    def test_moderate_from_injuries(self):
        assert calculate_severity(0, 10, 0) == 3
        assert calculate_severity(0, 50, 0) == 3

    def test_minor(self):
        assert calculate_severity(0, 1, 0) == 2
        assert calculate_severity(0, 5, 0) == 2

    def test_minimal(self):
        assert calculate_severity(0, 0, 0) == 1
