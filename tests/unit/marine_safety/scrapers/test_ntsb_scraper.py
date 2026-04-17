"""Tests for NTSB scraper exception classes, constants, and pure helpers."""

import re
from datetime import date

import pytest

from worldenergydata.marine_safety.constants import (
    DataSource,
    IncidentStatus,
    IncidentType,
)
from worldenergydata.marine_safety.scrapers.ntsb_scraper import (
    NTSBConnectionError,
    NTSBDataValidationError,
    NTSBScraper,
)

# ---------------------------------------------------------------------------
# NTSBDataValidationError
# ---------------------------------------------------------------------------


class TestNTSBDataValidationError:
    def test_default_message(self):
        err = NTSBDataValidationError(field="vessel_name", value="", reason="empty")
        assert "vessel_name" in str(err)
        assert "empty" in str(err)

    def test_with_ntsb_id(self):
        err = NTSBDataValidationError(
            field="event_date", value=None, reason="missing", ntsb_id="MAR-22-01"
        )
        assert "MAR-22-01" in str(err)

    def test_custom_message(self):
        err = NTSBDataValidationError(
            field="f", value="v", reason="r", message="Custom error"
        )
        assert "Custom error" in str(err)

    def test_details(self):
        err = NTSBDataValidationError(
            field="flag", value="XX", reason="invalid country", ntsb_id="DCA22MM001"
        )
        assert err.details["field"] == "flag"
        assert err.details["value"] == "XX"
        assert err.details["ntsb_id"] == "DCA22MM001"


# ---------------------------------------------------------------------------
# NTSBConnectionError
# ---------------------------------------------------------------------------


class TestNTSBConnectionError:
    def test_default_message(self):
        err = NTSBConnectionError()
        assert "CAROL" in str(err)

    def test_custom_message(self):
        err = NTSBConnectionError(message="DNS failure")
        assert "DNS failure" in str(err)

    def test_with_cause(self):
        cause = ConnectionError("timeout")
        err = NTSBConnectionError(cause=cause)
        assert err.details["cause"] is not None


# ---------------------------------------------------------------------------
# NTSBScraper constants
# ---------------------------------------------------------------------------


class TestNTSBScraperConstants:
    def test_base_url(self):
        assert "data.ntsb.gov" in NTSBScraper.BASE_URL

    def test_search_endpoint(self):
        assert NTSBScraper.SEARCH_ENDPOINT.startswith("/")

    def test_export_endpoint(self):
        assert NTSBScraper.EXPORT_ENDPOINT.startswith("/")

    def test_marine_mode(self):
        assert NTSBScraper.MARINE_MODE == "Marine"


# ---------------------------------------------------------------------------
# NTSB_ID_PATTERN
# ---------------------------------------------------------------------------


class TestNTSBIDPattern:
    def test_mar_format(self):
        assert NTSBScraper.NTSB_ID_PATTERN.match("MAR-22-01")

    def test_dca_format(self):
        assert NTSBScraper.NTSB_ID_PATTERN.match("DCA22MM001")

    def test_mab_format(self):
        assert NTSBScraper.NTSB_ID_PATTERN.match("MAB22MM001")

    def test_invalid_format(self):
        assert NTSBScraper.NTSB_ID_PATTERN.match("INVALID123") is None

    def test_case_insensitive(self):
        assert NTSBScraper.NTSB_ID_PATTERN.match("mar-22-01")


# ---------------------------------------------------------------------------
# Incident type mapping
# ---------------------------------------------------------------------------


class TestIncidentTypeMapping:
    def test_collision(self):
        assert NTSBScraper.INCIDENT_TYPE_MAPPING["collision"] == IncidentType.COLLISION

    def test_allision(self):
        assert NTSBScraper.INCIDENT_TYPE_MAPPING["allision"] == IncidentType.COLLISION

    def test_grounding(self):
        assert NTSBScraper.INCIDENT_TYPE_MAPPING["grounding"] == IncidentType.GROUNDING

    def test_fire(self):
        assert NTSBScraper.INCIDENT_TYPE_MAPPING["fire"] == IncidentType.FIRE

    def test_explosion(self):
        assert NTSBScraper.INCIDENT_TYPE_MAPPING["explosion"] == IncidentType.EXPLOSION

    def test_capsizing(self):
        assert NTSBScraper.INCIDENT_TYPE_MAPPING["capsizing"] == IncidentType.CAPSIZING

    def test_sinking(self):
        assert NTSBScraper.INCIDENT_TYPE_MAPPING["sinking"] == IncidentType.CAPSIZING

    def test_pollution(self):
        assert NTSBScraper.INCIDENT_TYPE_MAPPING["pollution"] == IncidentType.POLLUTION


# ---------------------------------------------------------------------------
# Status mapping
# ---------------------------------------------------------------------------


class TestStatusMapping:
    def test_open(self):
        assert NTSBScraper.STATUS_MAPPING["open"] == IncidentStatus.UNDER_INVESTIGATION

    def test_final(self):
        assert NTSBScraper.STATUS_MAPPING["final"] == IncidentStatus.FINAL_REPORT

    def test_closed(self):
        assert NTSBScraper.STATUS_MAPPING["closed"] == IncidentStatus.CLOSED

    def test_archived(self):
        assert NTSBScraper.STATUS_MAPPING["archived"] == IncidentStatus.ARCHIVED

    def test_mapping_count(self):
        assert len(NTSBScraper.STATUS_MAPPING) == 6
