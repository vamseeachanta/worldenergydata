"""Tests for LNG Terminal module exception hierarchy."""

from worldenergydata.common.exceptions import ModuleError
from worldenergydata.lng_terminals.exceptions import (
    LNGCollectionError,
    LNGDataError,
    LNGExportError,
    LNGProcessingError,
    LNGTerminalError,
    LNGValidationError,
)


class TestLNGTerminalError:
    def test_basic(self):
        err = LNGTerminalError("test")
        assert err.module_name == "lng_terminals"
        assert isinstance(err, ModuleError)


class TestLNGDataError:
    def test_missing_with_reason(self):
        err = LNGDataError.missing("imports", "file not found")
        assert err.code == "LNG_DATA_MISSING"
        assert "imports" in err.message
        assert "file not found" in err.message

    def test_missing_without_reason(self):
        err = LNGDataError.missing("exports")
        assert "exports" in err.message

    def test_malformed(self):
        err = LNGDataError.malformed("capacity", "invalid column")
        assert err.code == "LNG_DATA_MALFORMED"
        assert "capacity" in err.message
        assert "invalid column" in err.message


class TestLNGCollectionError:
    def test_basic(self):
        err = LNGCollectionError("failed", source="FERC")
        assert err.source == "FERC"
        assert err.context["source"] == "FERC"

    def test_source_unavailable_with_reason(self):
        err = LNGCollectionError.source_unavailable("EIA", "server down")
        assert err.code == "LNG_SOURCE_UNAVAILABLE"
        assert "server down" in err.message

    def test_source_unavailable_without_reason(self):
        err = LNGCollectionError.source_unavailable("EIA")
        assert "EIA" in err.message

    def test_fetch_failed(self):
        cause = RuntimeError("network error")
        err = LNGCollectionError.fetch_failed("EIA", "timeout", cause=cause)
        assert err.code == "LNG_FETCH_FAILED"
        assert err.cause is cause


class TestLNGValidationError:
    def test_basic(self):
        err = LNGValidationError("validation failed")
        assert err.errors == []

    def test_required_field(self):
        err = LNGValidationError.required_field("terminal_name")
        assert err.code == "LNG_REQUIRED_FIELD"
        assert len(err.errors) == 1
        assert err.errors[0]["field"] == "terminal_name"

    def test_invalid_value(self):
        err = LNGValidationError.invalid_value("capacity", -100, "must be positive")
        assert err.code == "LNG_INVALID_VALUE"
        assert "must be positive" in err.message

    def test_from_errors(self):
        errors = [
            {"field": "f1", "type": "required"},
            {"field": "f2", "type": "invalid"},
        ]
        err = LNGValidationError.from_errors(errors)
        assert err.code == "LNG_VALIDATION_FAILED"
        assert len(err.errors) == 2
        assert "2 error" in err.message


class TestLNGProcessingError:
    def test_basic(self):
        err = LNGProcessingError("failed", operation="normalize")
        assert err.operation == "normalize"
        assert err.context["operation"] == "normalize"

    def test_failed(self):
        cause = ValueError("bad data")
        err = LNGProcessingError.failed("aggregate", "bad input", cause=cause)
        assert err.code == "LNG_PROCESSING_FAILED"
        assert err.cause is cause


class TestLNGExportError:
    def test_write_failed(self):
        err = LNGExportError.write_failed("/tmp/out.csv", "disk full")
        assert err.code == "LNG_EXPORT_WRITE_FAILED"
        assert "/tmp/out.csv" in err.message

    def test_unsupported_format_with_supported(self):
        err = LNGExportError.unsupported_format("xml", ["csv", "json"])
        assert err.code == "LNG_EXPORT_FORMAT"
        assert "xml" in err.message
        assert "csv" in err.message

    def test_unsupported_format_without_supported(self):
        err = LNGExportError.unsupported_format("xml")
        assert "xml" in err.message


class TestInheritance:
    def test_all_inherit_from_base(self):
        classes = [
            LNGDataError,
            LNGCollectionError,
            LNGValidationError,
            LNGProcessingError,
            LNGExportError,
        ]
        for cls in classes:
            assert issubclass(cls, LNGTerminalError)
            assert issubclass(cls, ModuleError)
