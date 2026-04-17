"""Tests for Mexico CNH module exception hierarchy."""

from worldenergydata.common.exceptions import ModuleError
from worldenergydata.mexico_cnh.errors import (
    MexicoCNHConfigurationError,
    MexicoCNHError,
    MexicoCNHParseError,
    MexicoCNHScraperError,
    MexicoCNHTimeoutError,
    MexicoCNHValidationError,
)


class TestMexicoCNHError:
    """Tests for base MexicoCNHError."""

    def test_create_basic(self):
        err = MexicoCNHError("Test error")
        assert err.module_name == "mexico_cnh"
        assert err.code == "MEXICO_CNH_ERROR"

    def test_inherits_from_module_error(self):
        err = MexicoCNHError("Test")
        assert isinstance(err, ModuleError)


class TestMexicoCNHScraperError:
    """Tests for MexicoCNHScraperError."""

    def test_create_with_url_and_element(self):
        err = MexicoCNHScraperError(
            "Scraping failed", url="https://sih.cnh.gob.mx", element="#table"
        )
        assert err.url == "https://sih.cnh.gob.mx"
        assert err.element == "#table"

    def test_page_load_failed_factory(self):
        err = MexicoCNHScraperError.page_load_failed(
            "https://sih.cnh.gob.mx", "connection refused"
        )
        assert err.code == "MEXICO_CNH_PAGE_LOAD_FAILED"
        assert "connection refused" in err.message

    def test_page_load_failed_without_reason(self):
        err = MexicoCNHScraperError.page_load_failed("https://test.com")
        assert "https://test.com" in err.message

    def test_element_not_found_factory(self):
        err = MexicoCNHScraperError.element_not_found("#data-table")
        assert err.code == "MEXICO_CNH_ELEMENT_NOT_FOUND"

    def test_javascript_error_factory(self):
        err = MexicoCNHScraperError.javascript_error(
            "https://test.com", "undefined variable"
        )
        assert err.code == "MEXICO_CNH_JS_ERROR"

    def test_browser_init_failed_factory(self):
        err = MexicoCNHScraperError.browser_init_failed("chromedriver not found")
        assert err.code == "MEXICO_CNH_BROWSER_INIT_FAILED"

    def test_browser_init_failed_without_reason(self):
        err = MexicoCNHScraperError.browser_init_failed()
        assert "Selenium" in err.message


class TestMexicoCNHTimeoutError:
    """Tests for MexicoCNHTimeoutError."""

    def test_create_default(self):
        err = MexicoCNHTimeoutError()
        assert "timed out" in err.message

    def test_create_with_timeout(self):
        err = MexicoCNHTimeoutError(timeout_seconds=30)
        assert err.timeout_seconds == 30

    def test_page_timeout_factory(self):
        err = MexicoCNHTimeoutError.page_timeout("https://test.com", 60)
        assert err.code == "MEXICO_CNH_PAGE_TIMEOUT"
        assert err.timeout_seconds == 60

    def test_element_timeout_factory(self):
        err = MexicoCNHTimeoutError.element_timeout(
            "#table", 30, url="https://test.com"
        )
        assert err.code == "MEXICO_CNH_ELEMENT_TIMEOUT"
        assert err.timeout_seconds == 30

    def test_inherits_from_scraper_error(self):
        err = MexicoCNHTimeoutError()
        assert isinstance(err, MexicoCNHScraperError)


class TestMexicoCNHParseError:
    """Tests for MexicoCNHParseError."""

    def test_create_with_data_type(self):
        err = MexicoCNHParseError("Parse failed", data_type="production")
        assert err.data_type == "production"

    def test_html_parse_failed_factory(self):
        err = MexicoCNHParseError.html_parse_failed("malformed HTML")
        assert err.code == "MEXICO_CNH_HTML_PARSE_FAILED"
        assert err.data_type == "html"

    def test_html_parse_failed_without_reason(self):
        err = MexicoCNHParseError.html_parse_failed()
        assert "HTML" in err.message

    def test_excel_parse_failed_factory(self):
        err = MexicoCNHParseError.excel_parse_failed("data.xlsx", "corrupt file")
        assert err.code == "MEXICO_CNH_EXCEL_PARSE_FAILED"
        assert err.source_file == "data.xlsx"

    def test_pdf_parse_failed_factory(self):
        err = MexicoCNHParseError.pdf_parse_failed("report.pdf", "password protected")
        assert err.code == "MEXICO_CNH_PDF_PARSE_FAILED"
        assert err.source_file == "report.pdf"

    def test_json_parse_failed_factory(self):
        err = MexicoCNHParseError.json_parse_failed("invalid syntax")
        assert err.code == "MEXICO_CNH_JSON_PARSE_FAILED"

    def test_missing_field_factory(self):
        err = MexicoCNHParseError.missing_field("well_name", "production")
        assert err.code == "MEXICO_CNH_MISSING_FIELD"
        assert err.context["field"] == "well_name"


class TestMexicoCNHValidationError:
    """Tests for MexicoCNHValidationError."""

    def test_create_empty(self):
        err = MexicoCNHValidationError("Validation failed")
        assert err.errors == []

    def test_add_error(self):
        err = MexicoCNHValidationError("Validation failed")
        err.add_error("field", "type", "Wrong type", "value")
        assert err.has_errors() is True

    def test_to_dict_with_errors(self):
        err = MexicoCNHValidationError("Validation failed")
        err.add_error("f1", "required", "Missing")
        result = err.to_dict()
        assert "validation_errors" in result

    def test_from_errors_factory(self):
        errors = [{"field": "f1", "type": "required", "message": "Missing"}]
        err = MexicoCNHValidationError.from_errors(errors)
        assert len(err.errors) == 1

    def test_invalid_clave_pozo(self):
        err = MexicoCNHValidationError.invalid_clave_pozo("INVALID", "wrong format")
        assert err.code == "MEXICO_CNH_INVALID_CLAVE_POZO"
        assert err.has_errors() is True

    def test_invalid_coordinates(self):
        err = MexicoCNHValidationError.invalid_coordinates(
            10.0, -120.0, "outside Mexico"
        )
        assert err.code == "MEXICO_CNH_INVALID_COORDINATES"


class TestMexicoCNHConfigurationError:
    """Tests for MexicoCNHConfigurationError."""

    def test_missing_setting(self):
        err = MexicoCNHConfigurationError.missing_setting("chrome_driver_path")
        assert err.code == "MEXICO_CNH_CONFIG_MISSING"

    def test_invalid_value(self):
        err = MexicoCNHConfigurationError.invalid_value(
            "timeout", -1, "must be positive"
        )
        assert err.code == "MEXICO_CNH_CONFIG_INVALID"

    def test_selenium_not_configured(self):
        err = MexicoCNHConfigurationError.selenium_not_configured()
        assert err.code == "MEXICO_CNH_SELENIUM_NOT_CONFIGURED"
