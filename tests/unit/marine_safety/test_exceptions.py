"""Tests for Marine Safety module exception hierarchy."""

from worldenergydata.common.exceptions import ModuleError
from worldenergydata.marine_safety.exceptions import (
    ConfigurationError,
)
from worldenergydata.marine_safety.exceptions import (
    ConnectionError as MSConnectionError,
)
from worldenergydata.marine_safety.exceptions import (
    DatabaseError,
    DataTransformationError,
    DuplicateRecordError,
    EnrichmentError,
    FileAccessError,
    FileNotFoundError,
    FileSizeError,
    HTTPError,
    IntegrityError,
    InvalidConfigurationError,
    InvalidDataError,
    MarineSafetyError,
    MissingConfigurationError,
    MissingRequiredFieldError,
    ParsingError,
    ProcessingError,
    QueryError,
    RateLimitError,
    RecordNotFoundError,
    ScraperError,
    StorageError,
    TimeoutError,
    ValidationError,
)


class TestMarineSafetyError:
    def test_basic(self):
        err = MarineSafetyError("test error")
        assert err.module_name == "marine_safety"
        assert "test error" in str(err)

    def test_with_error_code(self):
        err = MarineSafetyError("test", error_code="CUSTOM")
        assert err.code == "CUSTOM"
        assert err.error_code == "CUSTOM"

    def test_with_details(self):
        err = MarineSafetyError("test", details={"key": "val"})
        assert err.details["key"] == "val"
        assert err.context["key"] == "val"

    def test_with_cause(self):
        cause = ValueError("original")
        err = MarineSafetyError("wrapped", cause=cause)
        assert err.cause is cause

    def test_inherits_module_error(self):
        assert isinstance(MarineSafetyError("t"), ModuleError)


class TestConfigurationErrors:
    def test_configuration_error(self):
        err = ConfigurationError("bad config")
        assert isinstance(err, MarineSafetyError)

    def test_invalid_configuration(self):
        err = InvalidConfigurationError("invalid value")
        assert isinstance(err, ConfigurationError)

    def test_missing_configuration(self):
        err = MissingConfigurationError("missing key")
        assert isinstance(err, ConfigurationError)


class TestDatabaseErrors:
    def test_database_error(self):
        err = DatabaseError("db failed")
        assert isinstance(err, MarineSafetyError)

    def test_connection_error(self):
        err = MSConnectionError("conn refused")
        assert isinstance(err, DatabaseError)

    def test_query_error(self):
        err = QueryError("bad sql")
        assert isinstance(err, DatabaseError)

    def test_integrity_error(self):
        err = IntegrityError("constraint violated")
        assert isinstance(err, DatabaseError)

    def test_record_not_found_default_message(self):
        err = RecordNotFoundError("Incident", "12345")
        assert "Incident" in str(err)
        assert "12345" in str(err)
        assert err.code == "RECORD_NOT_FOUND"
        assert err.context["model"] == "Incident"
        assert err.context["identifier"] == "12345"

    def test_record_not_found_custom_message(self):
        err = RecordNotFoundError("Vessel", "IMO-123", message="Custom msg")
        assert "Custom msg" in str(err)

    def test_duplicate_record_default_message(self):
        err = DuplicateRecordError("Incident", "12345")
        assert "12345" in str(err)
        assert "already exists" in str(err)
        assert err.code == "DUPLICATE_RECORD"

    def test_duplicate_record_custom_message(self):
        err = DuplicateRecordError("Vessel", "IMO", message="Already there")
        assert "Already there" in str(err)


class TestValidationErrors:
    def test_validation_error(self):
        err = ValidationError("validation failed")
        assert isinstance(err, MarineSafetyError)

    def test_invalid_data_default_message(self):
        err = InvalidDataError(field="lat", value=999, reason="out of range")
        assert "lat" in str(err)
        assert "out of range" in str(err)
        assert err.code == "INVALID_DATA"
        assert err.context["field"] == "lat"
        assert err.context["value"] == 999
        assert err.context["reason"] == "out of range"

    def test_invalid_data_custom_message(self):
        err = InvalidDataError(field="f", value="v", reason="r", message="Custom")
        assert "Custom" in str(err)

    def test_missing_required_field_default(self):
        err = MissingRequiredFieldError(field="api_number")
        assert "api_number" in str(err)
        assert err.code == "MISSING_REQUIRED_FIELD"
        assert err.context["field"] == "api_number"

    def test_missing_required_field_custom(self):
        err = MissingRequiredFieldError(field="f", message="Custom msg")
        assert "Custom msg" in str(err)


class TestScraperErrors:
    def test_scraper_error(self):
        err = ScraperError("scrape failed")
        assert isinstance(err, MarineSafetyError)

    def test_http_error_default(self):
        err = HTTPError(url="https://example.com", status_code=404)
        assert "example.com" in str(err)
        assert "404" in str(err)
        assert err.code == "HTTP_ERROR"
        assert err.context["url"] == "https://example.com"
        assert err.context["status_code"] == 404

    def test_http_error_custom(self):
        err = HTTPError(url="https://x.com", status_code=500, message="Server error")
        assert "Server error" in str(err)

    def test_parsing_error_default(self):
        err = ParsingError(source="BSEE page", reason="bad HTML")
        assert "BSEE page" in str(err)
        assert "bad HTML" in str(err)
        assert err.code == "PARSING_ERROR"

    def test_parsing_error_custom(self):
        err = ParsingError(source="s", reason="r", message="Custom")
        assert "Custom" in str(err)

    def test_rate_limit_error_default(self):
        err = RateLimitError(source="USCG API")
        assert "USCG API" in str(err)
        assert err.code == "RATE_LIMIT"

    def test_rate_limit_with_retry(self):
        err = RateLimitError(source="API", retry_after=60)
        assert "60" in str(err)
        assert err.context["retry_after"] == 60

    def test_rate_limit_custom(self):
        err = RateLimitError(source="s", retry_after=30, message="Custom")
        assert "Custom" in str(err)

    def test_timeout_error_default(self):
        err = TimeoutError(url="https://slow.com", timeout=30)
        assert "slow.com" in str(err)
        assert "30" in str(err)
        assert err.code == "TIMEOUT"

    def test_timeout_error_custom(self):
        err = TimeoutError(url="u", timeout=5, message="Timed out!")
        assert "Timed out!" in str(err)


class TestStorageErrors:
    def test_storage_error(self):
        err = StorageError("storage failed")
        assert isinstance(err, MarineSafetyError)

    def test_file_not_found_default(self):
        err = FileNotFoundError(path="/tmp/missing.csv")
        assert "/tmp/missing.csv" in str(err)
        assert err.code == "FILE_NOT_FOUND"

    def test_file_not_found_custom(self):
        err = FileNotFoundError(path="/p", message="Gone!")
        assert "Gone!" in str(err)

    def test_file_access_error_default(self):
        err = FileAccessError(path="/tmp/locked.db", reason="permission denied")
        assert "locked.db" in str(err)
        assert "permission denied" in str(err)
        assert err.code == "FILE_ACCESS_ERROR"

    def test_file_access_error_custom(self):
        err = FileAccessError(path="p", reason="r", message="Custom")
        assert "Custom" in str(err)

    def test_file_size_error_default(self):
        err = FileSizeError(path="/tmp/big.csv", size=2000000, max_size=1000000)
        assert "big.csv" in str(err)
        assert "2000000" in str(err)
        assert "1000000" in str(err)
        assert err.code == "FILE_SIZE_ERROR"

    def test_file_size_error_custom(self):
        err = FileSizeError(path="p", size=1, max_size=0, message="Too big")
        assert "Too big" in str(err)


class TestProcessingErrors:
    def test_processing_error(self):
        err = ProcessingError("processing failed")
        assert isinstance(err, MarineSafetyError)

    def test_data_transformation_error(self):
        err = DataTransformationError("transform failed")
        assert isinstance(err, ProcessingError)

    def test_enrichment_error(self):
        err = EnrichmentError("enrichment failed")
        assert isinstance(err, ProcessingError)


class TestInheritanceChain:
    def test_all_inherit_from_base(self):
        classes = [
            ConfigurationError,
            DatabaseError,
            ValidationError,
            ScraperError,
            StorageError,
            ProcessingError,
        ]
        for cls in classes:
            assert issubclass(cls, MarineSafetyError)
            assert issubclass(cls, ModuleError)
