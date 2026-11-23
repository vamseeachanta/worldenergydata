"""
Safety Analysis Module Exceptions

Exception hierarchy for safety analysis operations including
data loading, classification, correlation, and reporting.

Exception Hierarchy:
    SafetyAnalysisError (base, inherits ModuleError)
    |-- SafetyDataError (data loading/processing)
    |-- SafetyClassificationError (NLP/ML classification)
    |-- SafetyCorrelationError (correlation analysis)
    |-- SafetyConfigError (configuration issues)
    |-- OptionalDependencyError (missing optional packages)
"""

from typing import Optional

from worldenergydata.common.exceptions import ModuleError


class SafetyAnalysisError(ModuleError):
    """Base exception for all safety analysis module errors."""

    default_code = "SAFETY_ANALYSIS_ERROR"
    module_name = "safety_analysis"


class SafetyDataError(SafetyAnalysisError):
    """Errors related to safety data loading and processing."""

    default_code = "SAFETY_DATA_ERROR"

    @classmethod
    def invalid_schema(cls, source: str, reason: str) -> "SafetyDataError":
        """Create error for invalid data schema."""
        return cls(
            message=f"Invalid schema for source '{source}': {reason}",
            code="SAFETY_SCHEMA_INVALID",
            context={"source": source, "reason": reason},
        )

    @classmethod
    def load_failed(
        cls, path: str, reason: str, cause: Optional[Exception] = None
    ) -> "SafetyDataError":
        """Create error for failed data loading."""
        return cls(
            message=f"Failed to load safety data from '{path}': {reason}",
            code="SAFETY_LOAD_FAILED",
            context={"path": path, "reason": reason},
            cause=cause,
        )


class SafetyClassificationError(SafetyAnalysisError):
    """Errors related to NLP/ML classification operations."""

    default_code = "SAFETY_CLASSIFICATION_ERROR"

    @classmethod
    def model_not_found(cls, model_name: str) -> "SafetyClassificationError":
        """Create error for missing model."""
        return cls(
            message=f"Classification model '{model_name}' not found",
            code="SAFETY_MODEL_NOT_FOUND",
            context={"model_name": model_name},
        )

    @classmethod
    def training_failed(
        cls, reason: str, cause: Optional[Exception] = None
    ) -> "SafetyClassificationError":
        """Create error for failed training."""
        return cls(
            message=f"Classification training failed: {reason}",
            code="SAFETY_TRAINING_FAILED",
            cause=cause,
        )


class SafetyCorrelationError(SafetyAnalysisError):
    """Errors related to correlation analysis operations."""

    default_code = "SAFETY_CORRELATION_ERROR"

    @classmethod
    def insufficient_data(
        cls, asset_id: str, min_required: int, actual: int
    ) -> "SafetyCorrelationError":
        """Create error for insufficient data points."""
        return cls(
            message=f"Insufficient data for asset '{asset_id}': need {min_required}, got {actual}",
            code="SAFETY_INSUFFICIENT_DATA",
            context={
                "asset_id": asset_id,
                "min_required": min_required,
                "actual": actual,
            },
        )


class SafetyConfigError(SafetyAnalysisError):
    """Errors related to safety analysis configuration."""

    default_code = "SAFETY_CONFIG_ERROR"


class OptionalDependencyError(SafetyAnalysisError):
    """Raised when an optional dependency is not installed."""

    default_code = "OPTIONAL_DEPENDENCY_ERROR"

    @classmethod
    def missing(cls, package: str, extra: str) -> "OptionalDependencyError":
        """Create error for missing optional dependency."""
        return cls(
            message=(
                f"Package '{package}' is required for this feature. "
                f"Install it with: pip install worldenergydata[{extra}]"
            ),
            code="OPTIONAL_DEP_MISSING",
            context={"package": package, "extra": extra},
        )
