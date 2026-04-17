"""Tests for ATSB parser pure helper functions."""

from datetime import date

import pytest

from worldenergydata.marine_safety.constants import IncidentStatus
from worldenergydata.marine_safety.scrapers.atsb_parser import (
    map_status,
    parse_date,
)


class TestParseDate:
    def test_day_month_year(self):
        assert parse_date("15 January 2022") == date(2022, 1, 15)

    def test_short_month(self):
        assert parse_date("15 Jan 2022") == date(2022, 1, 15)

    def test_slash_format(self):
        assert parse_date("15/01/2022") == date(2022, 1, 15)

    def test_iso_format(self):
        assert parse_date("2022-01-15") == date(2022, 1, 15)

    def test_us_format(self):
        assert parse_date("January 15, 2022") == date(2022, 1, 15)

    def test_us_short(self):
        assert parse_date("Jan 15, 2022") == date(2022, 1, 15)

    def test_none(self):
        assert parse_date(None) is None

    def test_empty(self):
        assert parse_date("") is None

    def test_invalid(self):
        assert parse_date("not a date") is None

    def test_whitespace(self):
        assert parse_date("  15 January 2022  ") == date(2022, 1, 15)


class TestMapStatus:
    def test_active(self):
        assert (
            map_status("Active investigation")
            == IncidentStatus.UNDER_INVESTIGATION.value
        )

    def test_final(self):
        assert map_status("Final report published") == IncidentStatus.FINAL_REPORT.value

    def test_closed(self):
        assert map_status("closed") == IncidentStatus.CLOSED.value

    def test_preliminary(self):
        assert map_status("preliminary") == IncidentStatus.PRELIMINARY_REPORT.value

    def test_completed(self):
        assert map_status("completed") == IncidentStatus.FINAL_REPORT.value

    def test_none(self):
        assert map_status(None) == IncidentStatus.REPORTED.value

    def test_unknown(self):
        assert map_status("unknown status") == IncidentStatus.REPORTED.value
