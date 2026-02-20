"""Tests for Metocean module exception hierarchy."""

from worldenergydata.common.exceptions import ModuleError
from worldenergydata.metocean.exceptions import (
    CacheError,
    CacheReadError,
    CacheWriteError,
    ClientError,
    ConfigurationError,
    DataNotFoundError,
    DatabaseError,
    ExportError,
    ExportFormatError,
    ExportWriteError,
    HTTPError,
    InvalidConfigurationError,
    InvalidDataError,
    MetoceanError,
    MissingConfigurationError,
    ParsingError,
    QueryError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)
from worldenergydata.metocean.exceptions import (
    ConnectionError as MetConnectionError,
)


class TestMetoceanError:
    def test_basic(self):
        err = MetoceanError("test")
        assert err.module_name == "metocean"
        assert "test" in str(err)

    def test_with_error_code(self):
        err = MetoceanError("test", error_code="CUSTOM")
        assert err.code == "CUSTOM"
        assert err.error_code == "CUSTOM"

    def test_with_details(self):
        err = MetoceanError("test", details={"k": "v"})
        assert err.details["k"] == "v"

    def test_with_cause(self):
        cause = RuntimeError("orig")
        err = MetoceanError("wrapped", cause=cause)
        assert err.cause is cause

    def test_inherits_module_error(self):
        assert isinstance(MetoceanError("t"), ModuleError)


class TestConfigurationErrors:
    def test_base_config(self):
        err = ConfigurationError("bad config")
        assert isinstance(err, MetoceanError)

    def test_invalid_config(self):
        err = InvalidConfigurationError("invalid")
        assert isinstance(err, ConfigurationError)

    def test_missing_config(self):
        err = MissingConfigurationError("missing")
        assert isinstance(err, ConfigurationError)


class TestDatabaseErrors:
    def test_database_error(self):
        err = DatabaseError("db failed")
        assert isinstance(err, MetoceanError)

    def test_connection_error(self):
        err = MetConnectionError("conn refused")
        assert isinstance(err, DatabaseError)

    def test_query_error(self):
        err = QueryError("bad sql")
        assert isinstance(err, DatabaseError)


class TestValidationErrors:
    def test_validation_error(self):
        err = ValidationError("validation failed")
        assert isinstance(err, MetoceanError)

    def test_invalid_data_default(self):
        err = InvalidDataError(field="lat", value=999, reason="out of range")
        assert "lat" in str(err)
        assert err.code == "METOCEAN_INVALID_DATA"
        assert err.context["field"] == "lat"
        assert err.context["value"] == 999

    def test_invalid_data_custom(self):
        err = InvalidDataError(
            field="f", value="v", reason="r", message="Custom"
        )
        assert "Custom" in str(err)


class TestClientErrors:
    def test_client_error(self):
        err = ClientError("client failed")
        assert isinstance(err, MetoceanError)

    def test_http_error_default(self):
        err = HTTPError(url="https://api.example.com", status_code=404)
        assert err.url == "https://api.example.com"
        assert err.status_code == 404
        assert err.code == "METOCEAN_HTTP_ERROR"
        assert "404" in str(err)

    def test_http_error_custom(self):
        err = HTTPError(url="u", status_code=500, message="Server down")
        assert "Server down" in str(err)

    def test_rate_limit_default(self):
        err = RateLimitError(source="NDBC")
        assert "NDBC" in str(err)
        assert err.code == "METOCEAN_RATE_LIMIT"

    def test_rate_limit_with_retry(self):
        err = RateLimitError(source="NDBC", retry_after=120)
        assert err.retry_after == 120
        assert "120" in str(err)

    def test_rate_limit_custom(self):
        err = RateLimitError(source="s", retry_after=10, message="Custom")
        assert "Custom" in str(err)

    def test_timeout_default(self):
        err = TimeoutError(url="https://slow.api", timeout=30)
        assert err.url == "https://slow.api"
        assert err.timeout == 30
        assert err.code == "METOCEAN_TIMEOUT"

    def test_timeout_custom(self):
        err = TimeoutError(url="u", timeout=5, message="Too slow")
        assert "Too slow" in str(err)

    def test_parsing_error_default(self):
        err = ParsingError(source="NDBC CSV", reason="bad header")
        assert err.source == "NDBC CSV"
        assert err.reason == "bad header"
        assert err.code == "METOCEAN_PARSING_ERROR"

    def test_parsing_error_custom(self):
        err = ParsingError(source="s", reason="r", message="Custom")
        assert "Custom" in str(err)

    def test_data_not_found_default(self):
        err = DataNotFoundError(source="COOPS")
        assert err.source == "COOPS"
        assert err.code == "METOCEAN_DATA_NOT_FOUND"
        assert "COOPS" in str(err)

    def test_data_not_found_custom(self):
        err = DataNotFoundError(source="s", message="No data here")
        assert "No data here" in str(err)


class TestCacheErrors:
    def test_cache_error(self):
        err = CacheError("cache failed")
        assert isinstance(err, MetoceanError)

    def test_cache_read_error(self):
        err = CacheReadError("read failed")
        assert isinstance(err, CacheError)

    def test_cache_write_error(self):
        err = CacheWriteError("write failed")
        assert isinstance(err, CacheError)


class TestExportErrors:
    def test_export_error(self):
        err = ExportError("export failed")
        assert isinstance(err, MetoceanError)

    def test_export_format_default(self):
        err = ExportFormatError(format_name="xml")
        assert "xml" in str(err)
        assert err.code == "METOCEAN_EXPORT_FORMAT"

    def test_export_format_with_supported(self):
        err = ExportFormatError(
            format_name="xml", supported_formats=["csv", "json"]
        )
        assert "csv" in str(err)
        assert "json" in str(err)

    def test_export_format_custom(self):
        err = ExportFormatError(format_name="x", message="Bad format!")
        assert "Bad format!" in str(err)

    def test_export_write_default(self):
        err = ExportWriteError(path="/tmp/out.csv", reason="disk full")
        assert "/tmp/out.csv" in str(err)
        assert "disk full" in str(err)
        assert err.code == "METOCEAN_EXPORT_WRITE"

    def test_export_write_custom(self):
        err = ExportWriteError(path="p", reason="r", message="Write failed!")
        assert "Write failed!" in str(err)


class TestInheritanceChain:
    def test_all_base_classes_inherit_from_metocean(self):
        classes = [
            ConfigurationError,
            DatabaseError,
            ValidationError,
            ClientError,
            CacheError,
            ExportError,
        ]
        for cls in classes:
            assert issubclass(cls, MetoceanError)
            assert issubclass(cls, ModuleError)
