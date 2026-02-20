"""Tests for Safety Analysis module exception hierarchy."""

from worldenergydata.common.exceptions import ModuleError
from worldenergydata.safety_analysis.exceptions import (
    OptionalDependencyError,
    SafetyAnalysisError,
    SafetyClassificationError,
    SafetyConfigError,
    SafetyCorrelationError,
    SafetyDataError,
)


class TestSafetyAnalysisError:
    def test_basic(self):
        err = SafetyAnalysisError("test")
        assert err.module_name == "safety_analysis"
        assert isinstance(err, ModuleError)


class TestSafetyDataError:
    def test_invalid_schema(self):
        err = SafetyDataError.invalid_schema("BSEE", "missing columns")
        assert err.code == "SAFETY_SCHEMA_INVALID"
        assert "BSEE" in err.message
        assert "missing columns" in err.message
        assert err.context["source"] == "BSEE"

    def test_load_failed(self):
        cause = FileNotFoundError("not found")
        err = SafetyDataError.load_failed("/data/incidents.csv", "file missing", cause=cause)
        assert err.code == "SAFETY_LOAD_FAILED"
        assert err.cause is cause
        assert err.context["path"] == "/data/incidents.csv"


class TestSafetyClassificationError:
    def test_model_not_found(self):
        err = SafetyClassificationError.model_not_found("incident_type_v2")
        assert err.code == "SAFETY_MODEL_NOT_FOUND"
        assert "incident_type_v2" in err.message
        assert err.context["model_name"] == "incident_type_v2"

    def test_training_failed(self):
        cause = RuntimeError("GPU error")
        err = SafetyClassificationError.training_failed("convergence failed", cause=cause)
        assert err.code == "SAFETY_TRAINING_FAILED"
        assert err.cause is cause


class TestSafetyCorrelationError:
    def test_insufficient_data(self):
        err = SafetyCorrelationError.insufficient_data("WELL-001", 100, 5)
        assert err.code == "SAFETY_INSUFFICIENT_DATA"
        assert "WELL-001" in err.message
        assert err.context["min_required"] == 100
        assert err.context["actual"] == 5


class TestSafetyConfigError:
    def test_basic(self):
        err = SafetyConfigError("bad config")
        assert isinstance(err, SafetyAnalysisError)


class TestOptionalDependencyError:
    def test_missing(self):
        err = OptionalDependencyError.missing("scikit-learn", "ml")
        assert err.code == "OPTIONAL_DEP_MISSING"
        assert "scikit-learn" in err.message
        assert "pip install" in err.message
        assert err.context["package"] == "scikit-learn"
        assert err.context["extra"] == "ml"


class TestInheritance:
    def test_all_inherit_from_base(self):
        classes = [
            SafetyDataError,
            SafetyClassificationError,
            SafetyCorrelationError,
            SafetyConfigError,
            OptionalDependencyError,
        ]
        for cls in classes:
            assert issubclass(cls, SafetyAnalysisError)
            assert issubclass(cls, ModuleError)
