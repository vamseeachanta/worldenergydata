"""Tests for WorldEnergyData common exceptions hierarchy."""

from worldenergydata.common.exceptions import (
    APIError,
    BSEEError,
    CanadaError,
    ConfigError,
    DataError,
    DataSourceError,
    EIAError,
    MexicoCNHError,
    ModuleError,
    ProcessingError,
    SODIRError,
    TexasRRCError,
    ValidationError,
    WorldEnergyDataError,
)


class TestWorldEnergyDataError:
    """Tests for WorldEnergyDataError base class."""

    def test_create_basic(self):
        err = WorldEnergyDataError("Something failed")
        assert err.message == "Something failed"
        assert err.code == "WED_ERROR"
        assert err.context == {}
        assert err.cause is None

    def test_create_with_code(self):
        err = WorldEnergyDataError("Error", code="CUSTOM_CODE")
        assert err.code == "CUSTOM_CODE"

    def test_create_with_context(self):
        ctx = {"key": "value"}
        err = WorldEnergyDataError("Error", context=ctx)
        assert err.context["key"] == "value"

    def test_create_with_cause(self):
        original = ValueError("original")
        err = WorldEnergyDataError("Wrapped", cause=original)
        assert err.cause is original
        assert err.__cause__ is original

    def test_str_representation(self):
        err = WorldEnergyDataError("test error")
        result = str(err)
        assert "[WED_ERROR]" in result
        assert "test error" in result

    def test_str_with_context(self):
        err = WorldEnergyDataError("error", context={"key": "val"})
        result = str(err)
        assert "Context:" in result
        assert "key=val" in result

    def test_repr(self):
        err = WorldEnergyDataError("test")
        result = repr(err)
        assert "WorldEnergyDataError" in result
        assert "test" in result

    def test_to_dict_basic(self):
        err = WorldEnergyDataError("test")
        d = err.to_dict()
        assert d["error"] == "WorldEnergyDataError"
        assert d["code"] == "WED_ERROR"
        assert d["message"] == "test"
        assert "context" not in d
        assert "cause" not in d

    def test_to_dict_with_context(self):
        err = WorldEnergyDataError("test", context={"key": "val"})
        d = err.to_dict()
        assert d["context"]["key"] == "val"

    def test_to_dict_with_cause(self):
        err = WorldEnergyDataError("test", cause=ValueError("orig"))
        d = err.to_dict()
        assert "cause" in d
        assert "orig" in d["cause"]

    def test_is_exception(self):
        err = WorldEnergyDataError("test")
        assert isinstance(err, Exception)


class TestConfigError:
    """Tests for ConfigError."""

    def test_default_code(self):
        err = ConfigError("bad config")
        assert err.code == "CONFIG_ERROR"

    def test_missing_setting(self):
        err = ConfigError.missing_setting("api_key")
        assert err.code == "CONFIG_MISSING"
        assert "api_key" in err.message
        assert err.context["setting"] == "api_key"

    def test_invalid_value(self):
        err = ConfigError.invalid_value("timeout", -1, "must be positive")
        assert err.code == "CONFIG_INVALID"
        assert "must be positive" in err.message
        assert err.context["setting"] == "timeout"
        assert err.context["value"] == "-1"

    def test_inherits_from_base(self):
        err = ConfigError("test")
        assert isinstance(err, WorldEnergyDataError)


class TestDataError:
    """Tests for DataError."""

    def test_default_code(self):
        err = DataError("data issue")
        assert err.code == "DATA_ERROR"

    def test_inherits_from_base(self):
        err = DataError("test")
        assert isinstance(err, WorldEnergyDataError)


class TestDataSourceError:
    """Tests for DataSourceError."""

    def test_create_with_source(self):
        err = DataSourceError("Failed", source="BSEE API")
        assert err.source == "BSEE API"
        assert err.context["source"] == "BSEE API"

    def test_unavailable_with_reason(self):
        err = DataSourceError.unavailable("SODIR API", "server down")
        assert err.code == "SOURCE_UNAVAILABLE"
        assert "server down" in err.message

    def test_unavailable_without_reason(self):
        err = DataSourceError.unavailable("SODIR API")
        assert "SODIR API" in err.message

    def test_timeout(self):
        err = DataSourceError.timeout("EIA API", 30)
        assert err.code == "SOURCE_TIMEOUT"
        assert err.context["timeout"] == 30

    def test_inherits_from_data_error(self):
        err = DataSourceError("test", source="test")
        assert isinstance(err, DataError)


class TestValidationError:
    """Tests for ValidationError."""

    def test_create_empty(self):
        err = ValidationError("Validation failed")
        assert err.errors == []
        assert err.has_errors() is False

    def test_add_error(self):
        err = ValidationError("Validation failed")
        err.add_error("field1", "required", "Field is required")
        assert err.has_errors() is True
        assert len(err.errors) == 1
        assert err.errors[0]["field"] == "field1"
        assert err.errors[0]["type"] == "required"

    def test_add_error_with_value(self):
        err = ValidationError("Validation failed")
        err.add_error("age", "range", "Too high", 999)
        assert err.errors[0]["value"] == "999"

    def test_add_error_none_value(self):
        err = ValidationError("Validation failed")
        err.add_error("field", "required", "Missing")
        assert err.errors[0]["value"] is None

    def test_to_dict_with_errors(self):
        err = ValidationError("Validation failed")
        err.add_error("f1", "required", "Missing")
        d = err.to_dict()
        assert "validation_errors" in d
        assert len(d["validation_errors"]) == 1

    def test_to_dict_without_errors(self):
        err = ValidationError("Validation failed")
        d = err.to_dict()
        assert "validation_errors" not in d

    def test_from_errors(self):
        errors = [
            {"field": "f1", "type": "required", "message": "Missing"},
            {"field": "f2", "type": "type", "message": "Wrong type"},
        ]
        err = ValidationError.from_errors(errors)
        assert err.code == "VALIDATION_FAILED"
        assert len(err.errors) == 2
        assert "2 error" in err.message

    def test_required_field(self):
        err = ValidationError.required_field("username")
        assert err.code == "REQUIRED_FIELD"
        assert "username" in err.message
        assert err.has_errors() is True

    def test_invalid_type(self):
        err = ValidationError.invalid_type("age", "int", "str")
        assert err.code == "INVALID_TYPE"
        assert err.has_errors() is True
        assert err.context["expected"] == "int"
        assert err.context["actual"] == "str"

    def test_inherits_from_data_error(self):
        err = ValidationError("test")
        assert isinstance(err, DataError)


class TestProcessingError:
    """Tests for ProcessingError."""

    def test_create_with_operation(self):
        err = ProcessingError("Failed", operation="aggregate")
        assert err.operation == "aggregate"
        assert err.context["operation"] == "aggregate"

    def test_failed_factory(self):
        err = ProcessingError.failed("normalize", "invalid input")
        assert err.code == "PROCESSING_FAILED"
        assert "normalize" in err.message

    def test_failed_with_cause(self):
        cause = ValueError("bad value")
        err = ProcessingError.failed("calc", "error", cause=cause)
        assert err.cause is cause

    def test_inherits_from_data_error(self):
        err = ProcessingError("test", operation="test")
        assert isinstance(err, DataError)


class TestAPIError:
    """Tests for APIError."""

    def test_create_with_api(self):
        err = APIError("Failed", api_name="SODIR")
        assert err.api_name == "SODIR"
        assert err.context["api"] == "SODIR"

    def test_create_with_status(self):
        err = APIError("Failed", api_name="SODIR", status_code=500)
        assert err.status_code == 500
        assert err.context["status_code"] == 500

    def test_request_failed(self):
        err = APIError.request_failed("EIA", 404, "Not found")
        assert err.code == "API_REQUEST_FAILED"
        assert err.status_code == 404

    def test_request_failed_truncates_response(self):
        long_body = "x" * 1000
        err = APIError.request_failed("EIA", 500, long_body)
        assert len(err.context["response"]) == 500

    def test_rate_limited(self):
        err = APIError.rate_limited("EIA", retry_after=60)
        assert err.code == "API_RATE_LIMITED"
        assert err.status_code == 429
        assert err.context["retry_after"] == 60

    def test_rate_limited_without_retry(self):
        err = APIError.rate_limited("EIA")
        assert err.status_code == 429

    def test_inherits_from_base(self):
        err = APIError("test", api_name="test")
        assert isinstance(err, WorldEnergyDataError)


class TestModuleError:
    """Tests for ModuleError and subclasses."""

    def test_module_error_base(self):
        err = ModuleError("test")
        assert err.code == "MODULE_ERROR"
        assert err.context["module"] == "unknown"

    def test_bsee_error(self):
        err = BSEEError("BSEE problem")
        assert err.code == "BSEE_ERROR"
        assert err.context["module"] == "bsee"
        assert isinstance(err, ModuleError)

    def test_sodir_error(self):
        err = SODIRError("SODIR problem")
        assert err.code == "SODIR_ERROR"
        assert err.context["module"] == "sodir"

    def test_eia_error(self):
        err = EIAError("EIA problem")
        assert err.code == "EIA_ERROR"
        assert err.context["module"] == "eia"

    def test_texas_rrc_error(self):
        err = TexasRRCError("RRC problem")
        assert err.code == "TEXAS_RRC_ERROR"
        assert err.context["module"] == "texas_rrc"

    def test_canada_error(self):
        err = CanadaError("Canada problem")
        assert err.code == "CANADA_ERROR"
        assert err.context["module"] == "canada"

    def test_mexico_cnh_error(self):
        err = MexicoCNHError("Mexico problem")
        assert err.code == "MEXICO_CNH_ERROR"
        assert err.context["module"] == "mexico_cnh"

    def test_all_inherit_from_module_error(self):
        for cls in [
            BSEEError,
            SODIRError,
            EIAError,
            TexasRRCError,
            CanadaError,
            MexicoCNHError,
        ]:
            assert issubclass(cls, ModuleError)

    def test_all_inherit_from_base(self):
        for cls in [
            BSEEError,
            SODIRError,
            EIAError,
            TexasRRCError,
            CanadaError,
            MexicoCNHError,
        ]:
            assert issubclass(cls, WorldEnergyDataError)
