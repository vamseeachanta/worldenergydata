"""Tests for ATSB validator pure helper functions."""

from datetime import date

import pytest

from worldenergydata.marine_safety.scrapers.atsb_validator import (
    validate_atsb_id,
    validate_investigation_data,
)


class TestValidateATSBId:
    def test_standard(self):
        assert validate_atsb_id("MO-2022-001") is True

    def test_no_dashes(self):
        assert validate_atsb_id("MO2022001") is True

    def test_with_prefix(self):
        assert validate_atsb_id("342-MO-2021-001") is True

    def test_mr_prefix(self):
        assert validate_atsb_id("MR-2022-001") is True

    def test_flexible_pattern(self):
        assert validate_atsb_id("MO2022001") is True

    def test_empty(self):
        assert validate_atsb_id("") is False

    def test_invalid(self):
        assert validate_atsb_id("INVALID") is False

    def test_whitespace_stripped(self):
        assert validate_atsb_id("  MO-2022-001  ") is True


class TestValidateInvestigationData:
    def test_valid_data(self):
        data = {
            "source_id": "MO-2022-001",
            "source": "atsb",
            "event_date": "2022-01-15",
        }
        assert validate_investigation_data(data, date(2003, 1, 1)) is True

    def test_missing_source_id(self):
        data = {"source": "atsb"}
        assert validate_investigation_data(data, date(2003, 1, 1)) is False

    def test_missing_source(self):
        data = {"source_id": "MO-2022-001"}
        assert validate_investigation_data(data, date(2003, 1, 1)) is False

    def test_negative_fatalities(self):
        data = {
            "source_id": "MO-2022-001",
            "source": "atsb",
            "casualties": {"fatalities": -1},
        }
        assert validate_investigation_data(data, date(2003, 1, 1)) is False

    def test_invalid_latitude(self):
        data = {
            "source_id": "MO-2022-001",
            "source": "atsb",
            "location": {"latitude": 100},
        }
        assert validate_investigation_data(data, date(2003, 1, 1)) is False

    def test_invalid_longitude(self):
        data = {
            "source_id": "MO-2022-001",
            "source": "atsb",
            "location": {"longitude": 200},
        }
        assert validate_investigation_data(data, date(2003, 1, 1)) is False

    def test_valid_coordinates(self):
        data = {
            "source_id": "MO-2022-001",
            "source": "atsb",
            "location": {"latitude": -33.8, "longitude": 151.2},
        }
        assert validate_investigation_data(data, date(2003, 1, 1)) is True

    def test_no_date(self):
        data = {"source_id": "MO-2022-001", "source": "atsb"}
        assert validate_investigation_data(data, date(2003, 1, 1)) is True
