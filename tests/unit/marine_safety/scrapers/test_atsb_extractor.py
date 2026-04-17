"""Tests for ATSB extractor pure helper functions."""

import pytest

from worldenergydata.marine_safety.constants import IncidentType
from worldenergydata.marine_safety.scrapers.atsb_extractor import (
    map_incident_type,
    normalize_australian_state,
    parse_casualty_count,
)


class TestNormalizeAustralianState:
    def test_nsw(self):
        assert normalize_australian_state("NSW") == "NSW"

    def test_full_name(self):
        assert normalize_australian_state("new south wales") == "NSW"

    def test_victoria(self):
        assert normalize_australian_state("Victoria") == "VIC"

    def test_unknown_state(self):
        assert normalize_australian_state("Unknown") == "UNKNOWN"

    def test_none(self):
        assert normalize_australian_state(None) is None

    def test_empty(self):
        assert normalize_australian_state("") is None

    def test_whitespace(self):
        assert normalize_australian_state("  qld  ") == "QLD"


class TestMapIncidentType:
    def test_collision(self):
        assert map_incident_type("collision") == IncidentType.COLLISION.value

    def test_grounding(self):
        assert map_incident_type("grounding") == IncidentType.GROUNDING.value

    def test_fire(self):
        assert map_incident_type("fire") == IncidentType.FIRE.value

    def test_partial_match(self):
        assert (
            map_incident_type("ship collision with dock")
            == IncidentType.COLLISION.value
        )

    def test_unknown(self):
        assert map_incident_type("unknown_type") == IncidentType.OTHER.value

    def test_case_insensitive(self):
        assert map_incident_type("CAPSIZING") == IncidentType.CAPSIZING.value


class TestParseCasualtyCount:
    def test_number(self):
        assert parse_casualty_count("3 fatalities") == 3

    def test_single(self):
        assert parse_casualty_count("1") == 1

    def test_none_text(self):
        assert parse_casualty_count("None reported") == 0

    def test_no_text(self):
        assert parse_casualty_count("No injuries") == 0

    def test_empty(self):
        assert parse_casualty_count("") == 0

    def test_no_number(self):
        assert parse_casualty_count("several") == 0
