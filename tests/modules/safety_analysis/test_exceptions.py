"""Tests for safety analysis exception hierarchy."""

from worldenergydata.common.exceptions import ModuleError, WorldEnergyDataError
from worldenergydata.modules.safety_analysis.exceptions import (
    OptionalDependencyError,
    SafetyAnalysisError,
    SafetyClassificationError,
    SafetyCorrelationError,
    SafetyDataError,
)


class TestSafetyAnalysisError:
    def test_inherits_module_error(self):
        assert issubclass(SafetyAnalysisError, ModuleError)
        assert issubclass(SafetyAnalysisError, WorldEnergyDataError)

    def test_default_code(self):
        err = SafetyAnalysisError("test error")
        assert err.code == "SAFETY_ANALYSIS_ERROR"
        assert err.context["module"] == "safety_analysis"

    def test_custom_code(self):
        err = SafetyAnalysisError("test", code="CUSTOM")
        assert err.code == "CUSTOM"

    def test_to_dict(self):
        err = SafetyAnalysisError("test error", context={"key": "val"})
        d = err.to_dict()
        assert d["error"] == "SafetyAnalysisError"
        assert d["message"] == "test error"

    def test_str_format(self):
        err = SafetyAnalysisError("test error")
        assert "SAFETY_ANALYSIS_ERROR" in str(err)
        assert "test error" in str(err)


class TestSafetyDataError:
    def test_inherits_safety_analysis_error(self):
        assert issubclass(SafetyDataError, SafetyAnalysisError)

    def test_invalid_schema(self):
        err = SafetyDataError.invalid_schema("my_source", "missing columns")
        assert err.code == "SAFETY_SCHEMA_INVALID"
        assert "my_source" in err.message
        assert err.context["source"] == "my_source"

    def test_load_failed(self):
        cause = FileNotFoundError("no file")
        err = SafetyDataError.load_failed("/tmp/data.csv", "not found", cause=cause)
        assert err.code == "SAFETY_LOAD_FAILED"
        assert "/tmp/data.csv" in err.message
        assert err.cause is cause


class TestSafetyClassificationError:
    def test_model_not_found(self):
        err = SafetyClassificationError.model_not_found("my_model")
        assert err.code == "SAFETY_MODEL_NOT_FOUND"
        assert "my_model" in err.message

    def test_training_failed(self):
        err = SafetyClassificationError.training_failed("convergence issue")
        assert err.code == "SAFETY_TRAINING_FAILED"
        assert "convergence" in err.message


class TestSafetyCorrelationError:
    def test_insufficient_data(self):
        err = SafetyCorrelationError.insufficient_data("RIG-001", 30, 5)
        assert err.code == "SAFETY_INSUFFICIENT_DATA"
        assert err.context["asset_id"] == "RIG-001"
        assert err.context["min_required"] == 30
        assert err.context["actual"] == 5


class TestOptionalDependencyError:
    def test_missing(self):
        err = OptionalDependencyError.missing("torch", "safety-bert")
        assert err.code == "OPTIONAL_DEP_MISSING"
        assert "torch" in err.message
        assert "safety-bert" in err.message
        assert "pip install" in err.message
