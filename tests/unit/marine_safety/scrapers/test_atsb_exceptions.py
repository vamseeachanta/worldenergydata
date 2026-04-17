"""Tests for ATSB scraper exception classes."""

import pytest

from worldenergydata.marine_safety.scrapers.atsb_exceptions import (
    ATSBConnectionError,
    ATSBDataValidationError,
)


class TestATSBDataValidationError:
    def test_default_message(self):
        err = ATSBDataValidationError(
            field="event_date",
            value="invalid",
            reason="not a valid date",
        )
        msg = str(err)
        assert "event_date" in msg
        assert "not a valid date" in msg

    def test_with_atsb_id(self):
        err = ATSBDataValidationError(
            field="event_date",
            value="bad",
            reason="invalid format",
            atsb_id="MO-2022-001",
        )
        msg = str(err)
        assert "MO-2022-001" in msg

    def test_custom_message(self):
        err = ATSBDataValidationError(
            field="status",
            value="bad",
            reason="unknown",
            message="Custom validation error",
        )
        assert "Custom validation error" in str(err)

    def test_is_validation_error(self):
        from worldenergydata.marine_safety.exceptions import ValidationError

        err = ATSBDataValidationError(field="f", value="v", reason="r")
        assert isinstance(err, ValidationError)


class TestATSBConnectionError:
    def test_default_message(self):
        err = ATSBConnectionError()
        assert "ATSB" in str(err)

    def test_custom_message(self):
        err = ATSBConnectionError(message="Timeout occurred")
        assert "Timeout" in str(err)

    def test_with_cause(self):
        cause = ConnectionError("network down")
        err = ATSBConnectionError(cause=cause)
        assert "ATSB" in str(err)

    def test_is_scraper_error(self):
        from worldenergydata.marine_safety.exceptions import ScraperError

        err = ATSBConnectionError()
        assert isinstance(err, ScraperError)
