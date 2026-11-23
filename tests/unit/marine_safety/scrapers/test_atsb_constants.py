"""Tests for ATSB scraper constants and mappings."""

import re

import pytest

from worldenergydata.marine_safety.constants import IncidentStatus, IncidentType
from worldenergydata.marine_safety.scrapers.atsb_constants import (
    ATSB_ID_PATTERN,
    AUSTRALIAN_STATES,
    BASE_URL,
    DEFAULT_MIN_DATE_YEAR,
    DEFAULT_PAGE_SIZE,
    INCIDENT_TYPE_MAPPING,
    MARINE_URL,
    MAX_PAGES,
    STATUS_MAPPING,
)


class TestATSBIDPattern:
    def test_standard_format(self):
        assert ATSB_ID_PATTERN.match("MO-2022-001")

    def test_no_dashes(self):
        assert ATSB_ID_PATTERN.match("MO2022001")

    def test_with_prefix(self):
        assert ATSB_ID_PATTERN.match("342-MO-2021-001")

    def test_mr_prefix(self):
        assert ATSB_ID_PATTERN.match("MR-2022-001")

    def test_case_insensitive(self):
        assert ATSB_ID_PATTERN.match("mo-2022-001")

    def test_invalid(self):
        assert ATSB_ID_PATTERN.match("INVALID") is None


class TestAustralianStates:
    def test_nsw(self):
        assert AUSTRALIAN_STATES["nsw"] == "NSW"
        assert AUSTRALIAN_STATES["new south wales"] == "NSW"

    def test_vic(self):
        assert AUSTRALIAN_STATES["vic"] == "VIC"
        assert AUSTRALIAN_STATES["victoria"] == "VIC"

    def test_qld(self):
        assert AUSTRALIAN_STATES["qld"] == "QLD"
        assert AUSTRALIAN_STATES["queensland"] == "QLD"

    def test_wa(self):
        assert AUSTRALIAN_STATES["wa"] == "WA"
        assert AUSTRALIAN_STATES["western australia"] == "WA"

    def test_sa(self):
        assert AUSTRALIAN_STATES["sa"] == "SA"

    def test_tas(self):
        assert AUSTRALIAN_STATES["tas"] == "TAS"

    def test_nt(self):
        assert AUSTRALIAN_STATES["nt"] == "NT"

    def test_act(self):
        assert AUSTRALIAN_STATES["act"] == "ACT"

    def test_count(self):
        assert len(AUSTRALIAN_STATES) == 16


class TestIncidentTypeMapping:
    def test_collision(self):
        assert INCIDENT_TYPE_MAPPING["collision"] == IncidentType.COLLISION

    def test_grounding(self):
        assert INCIDENT_TYPE_MAPPING["grounding"] == IncidentType.GROUNDING

    def test_fire(self):
        assert INCIDENT_TYPE_MAPPING["fire"] == IncidentType.FIRE

    def test_capsizing(self):
        assert INCIDENT_TYPE_MAPPING["capsizing"] == IncidentType.CAPSIZING

    def test_flooding(self):
        assert INCIDENT_TYPE_MAPPING["flooding"] == IncidentType.FLOODING

    def test_structural_failure(self):
        assert (
            INCIDENT_TYPE_MAPPING["structural failure"]
            == IncidentType.STRUCTURAL_FAILURE
        )

    def test_pollution(self):
        assert INCIDENT_TYPE_MAPPING["pollution"] == IncidentType.POLLUTION

    def test_weather(self):
        assert INCIDENT_TYPE_MAPPING["weather"] == IncidentType.WEATHER_RELATED

    def test_mapping_count(self):
        assert len(INCIDENT_TYPE_MAPPING) == 33


class TestStatusMapping:
    def test_active(self):
        assert STATUS_MAPPING["active"] == IncidentStatus.UNDER_INVESTIGATION

    def test_final(self):
        assert STATUS_MAPPING["final"] == IncidentStatus.FINAL_REPORT

    def test_closed(self):
        assert STATUS_MAPPING["closed"] == IncidentStatus.CLOSED

    def test_count(self):
        assert len(STATUS_MAPPING) == 7


class TestURLConstants:
    def test_base_url(self):
        assert "atsb.gov.au" in BASE_URL

    def test_marine_url(self):
        assert "marine" in MARINE_URL


class TestDefaults:
    def test_min_date_year(self):
        assert DEFAULT_MIN_DATE_YEAR == 2003

    def test_page_size(self):
        assert DEFAULT_PAGE_SIZE == 20

    def test_max_pages(self):
        assert MAX_PAGES == 100
