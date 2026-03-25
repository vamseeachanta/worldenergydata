"""Tests for ATSB transformer transform_investigation function."""

from datetime import date, datetime

import pytest

from worldenergydata.marine_safety.constants import (
    DataSource,
    IncidentStatus,
    IncidentType,
)
from worldenergydata.marine_safety.scrapers.atsb_transformer import (
    transform_investigation,
)


class TestTransformInvestigation:
    def test_minimal_raw_data(self):
        raw = {"atsb_id": "MO-2022-001"}
        result = transform_investigation(raw)
        assert result["source"] == DataSource.ATSB.value
        assert result["source_id"] == "MO-2022-001"
        assert result["location"]["country"] == "Australia"

    def test_location_with_city_and_state(self):
        raw = {
            "atsb_id": "MO-2022-001",
            "location": "Sydney, NSW",
        }
        result = transform_investigation(raw)
        assert result["location"]["city"] == "Sydney"
        assert result["location"]["state"] == "NSW"

    def test_location_no_comma(self):
        raw = {
            "atsb_id": "MO-2022-001",
            "location": "Sydney Harbour",
        }
        result = transform_investigation(raw)
        assert result["location"]["city"] == "Sydney Harbour"

    def test_location_empty(self):
        raw = {"atsb_id": "MO-2022-001", "location": ""}
        result = transform_investigation(raw)
        assert result["location"]["city"] is None

    def test_state_override(self):
        raw = {
            "atsb_id": "MO-2022-001",
            "location": "Sydney, NSW",
            "state": "VIC",
        }
        result = transform_investigation(raw)
        assert result["location"]["state"] == "VIC"

    def test_coordinates(self):
        raw = {
            "atsb_id": "MO-2022-001",
            "latitude": -33.8,
            "longitude": 151.2,
        }
        result = transform_investigation(raw)
        assert result["location"]["latitude"] == -33.8
        assert result["location"]["longitude"] == 151.2

    def test_vessel_info(self):
        raw = {
            "atsb_id": "MO-2022-001",
            "vessel_name": "Pacific Explorer",
            "vessel_type": "bulk carrier",
            "flag_state": "Australia",
            "gross_tonnage": 50000,
        }
        result = transform_investigation(raw)
        assert result["vessel"]["name"] == "Pacific Explorer"
        assert result["vessel"]["type"] == "bulk carrier"
        assert result["vessel"]["flag"] == "Australia"
        assert result["vessel"]["gross_tonnage"] == 50000

    def test_casualties(self):
        raw = {
            "atsb_id": "MO-2022-001",
            "fatalities": 2,
            "injuries": 5,
        }
        result = transform_investigation(raw)
        assert result["casualties"]["fatalities"] == 2
        assert result["casualties"]["injuries"] == 5
        assert result["casualties"]["missing"] == 0

    def test_casualties_default_zero(self):
        raw = {"atsb_id": "MO-2022-001"}
        result = transform_investigation(raw)
        assert result["casualties"]["fatalities"] == 0
        assert result["casualties"]["injuries"] == 0

    def test_occurrence_date(self):
        raw = {
            "atsb_id": "MO-2022-001",
            "occurrence_date": date(2022, 1, 15),
        }
        result = transform_investigation(raw)
        assert result["event_date"] == "2022-01-15"

    def test_no_occurrence_date(self):
        raw = {"atsb_id": "MO-2022-001"}
        result = transform_investigation(raw)
        assert result["event_date"] is None

    def test_incident_type_default(self):
        raw = {"atsb_id": "MO-2022-001"}
        result = transform_investigation(raw)
        assert result["incident_type"] == IncidentType.OTHER.value

    def test_status_default(self):
        raw = {"atsb_id": "MO-2022-001"}
        result = transform_investigation(raw)
        assert result["status"] == IncidentStatus.REPORTED.value

    def test_report_url(self):
        raw = {
            "atsb_id": "MO-2022-001",
            "report_url": "https://example.com/report",
        }
        result = transform_investigation(raw)
        assert result["report_url"] == "https://example.com/report"

    def test_raw_data_preserved(self):
        raw = {"atsb_id": "MO-2022-001", "extra_field": "value"}
        result = transform_investigation(raw)
        assert result["raw_data"] == raw

    def test_scraped_at_present(self):
        raw = {"atsb_id": "MO-2022-001"}
        result = transform_investigation(raw)
        assert "scraped_at" in result
        assert isinstance(result["scraped_at"], str)
