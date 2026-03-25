"""Tests for SIH scraper exception classes and constants."""

import pytest

from worldenergydata.mexico_cnh.scrapers.sih_scraper import (
    DownloadTimeoutError,
    ExportError,
    NavigationError,
    SIHScraper,
    SIHScraperError,
    SeleniumNotInstalledError,
)


# ---------------------------------------------------------------------------
# Exception classes
# ---------------------------------------------------------------------------

class TestSeleniumNotInstalledError:
    def test_is_import_error(self):
        err = SeleniumNotInstalledError()
        assert isinstance(err, ImportError)
        assert "Selenium" in str(err)


class TestSIHScraperError:
    def test_is_exception(self):
        err = SIHScraperError("test error")
        assert isinstance(err, Exception)


class TestNavigationError:
    def test_message(self):
        err = NavigationError("https://example.com", "timeout")
        assert "example.com" in str(err)
        assert "timeout" in str(err)
        assert err.url == "https://example.com"
        assert err.reason == "timeout"

    def test_is_sih_error(self):
        err = NavigationError("url", "reason")
        assert isinstance(err, SIHScraperError)


class TestExportError:
    def test_message(self):
        err = ExportError("Excel", "button not found")
        assert "Excel" in str(err)
        assert "button not found" in str(err)
        assert err.export_type == "Excel"
        assert err.reason == "button not found"


class TestDownloadTimeoutError:
    def test_message(self):
        err = DownloadTimeoutError(60)
        assert "60" in str(err)
        assert err.timeout == 60


# ---------------------------------------------------------------------------
# SIHScraper constants
# ---------------------------------------------------------------------------

class TestSIHScraperConstants:
    def test_sih_url(self):
        assert "hidrocarburos.gob.mx" in SIHScraper.SIH_URL

    def test_production_url(self):
        assert "produccion" in SIHScraper.PRODUCTION_URL

    def test_selectors(self):
        sel = SIHScraper.SELECTORS
        assert "export_button" in sel
        assert "date_from" in sel
        assert "date_to" in sel
        assert "field_select" in sel
        assert "well_select" in sel
        assert "search_button" in sel
        assert "data_table" in sel
        assert "loading_spinner" in sel

    def test_rate_limiting(self):
        assert SIHScraper.MIN_ACTION_DELAY > 0
        assert SIHScraper.PAGE_LOAD_DELAY > 0
