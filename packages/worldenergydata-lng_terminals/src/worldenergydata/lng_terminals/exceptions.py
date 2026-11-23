"""
LNG Terminal module exceptions.

Defines a hierarchy of exceptions for LNG terminal data collection,
validation, processing, and export operations.

Exception Hierarchy:
    LNGTerminalError (ModuleError)
    |-- LNGDataError (general data issues)
    |-- LNGCollectionError (collector failures)
    |-- LNGValidationError (validation failures)
    |-- LNGProcessingError (processing failures)
    |-- LNGExportError (export failures)
"""

from typing import Any, Dict, List, Optional

from worldenergydata.common.exceptions import ModuleError


class LNGTerminalError(ModuleError):
    """Base exception for all LNG Terminal module errors."""

    default_code = "LNG_TERMINAL_ERROR"
    module_name = "lng_terminals"


class LNGDataError(LNGTerminalError):
    """Raised when LNG terminal data is missing, malformed, or inconsistent."""

    default_code = "LNG_DATA_ERROR"

    @classmethod
    def missing(cls, dataset: str, reason: str = "") -> "LNGDataError":
        """Create error for missing data."""
        msg = f"LNG dataset '{dataset}' is missing"
        if reason:
            msg += f": {reason}"
        return cls(message=msg, code="LNG_DATA_MISSING", context={"dataset": dataset})

    @classmethod
    def malformed(cls, dataset: str, reason: str) -> "LNGDataError":
        """Create error for malformed data."""
        return cls(
            message=f"LNG dataset '{dataset}' is malformed: {reason}",
            code="LNG_DATA_MALFORMED",
            context={"dataset": dataset, "reason": reason},
        )


class LNGCollectionError(LNGTerminalError):
    """Raised when LNG terminal data collection fails."""

    default_code = "LNG_COLLECTION_ERROR"

    def __init__(
        self,
        message: str,
        source: str,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        context = context or {}
        context["source"] = source
        super().__init__(message, code, context, cause)
        self.source = source

    @classmethod
    def source_unavailable(cls, source: str, reason: str = "") -> "LNGCollectionError":
        """Create error for an unavailable collection source."""
        msg = f"LNG source '{source}' is unavailable"
        if reason:
            msg += f": {reason}"
        return cls(message=msg, source=source, code="LNG_SOURCE_UNAVAILABLE")

    @classmethod
    def fetch_failed(
        cls, source: str, reason: str, cause: Optional[Exception] = None
    ) -> "LNGCollectionError":
        """Create error for a failed fetch operation."""
        return cls(
            message=f"Failed to fetch from LNG source '{source}': {reason}",
            source=source,
            code="LNG_FETCH_FAILED",
            cause=cause,
        )


class LNGValidationError(LNGTerminalError):
    """Raised when LNG terminal data fails validation."""

    default_code = "LNG_VALIDATION_ERROR"

    def __init__(
        self,
        message: str,
        errors: Optional[List[Dict[str, Any]]] = None,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, code, context, cause)
        self.errors = errors or []

    @classmethod
    def required_field(cls, field: str) -> "LNGValidationError":
        """Create error for a missing required field."""
        return cls(
            message=f"Required LNG field '{field}' is missing",
            errors=[{"field": field, "type": "required"}],
            code="LNG_REQUIRED_FIELD",
            context={"field": field},
        )

    @classmethod
    def invalid_value(cls, field: str, value: Any, reason: str) -> "LNGValidationError":
        """Create error for an invalid field value."""
        return cls(
            message=f"Invalid value for LNG field '{field}': {reason}",
            errors=[{"field": field, "type": "invalid", "value": str(value)}],
            code="LNG_INVALID_VALUE",
            context={"field": field, "value": str(value), "reason": reason},
        )

    @classmethod
    def from_errors(cls, errors: List[Dict[str, Any]]) -> "LNGValidationError":
        """Create error from a list of validation error details."""
        count = len(errors)
        return cls(
            message=f"LNG validation failed with {count} error(s)",
            errors=errors,
            code="LNG_VALIDATION_FAILED",
        )


class LNGProcessingError(LNGTerminalError):
    """Raised when LNG terminal data processing fails."""

    default_code = "LNG_PROCESSING_ERROR"

    def __init__(
        self,
        message: str,
        operation: str,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        context = context or {}
        context["operation"] = operation
        super().__init__(message, code, context, cause)
        self.operation = operation

    @classmethod
    def failed(
        cls, operation: str, reason: str, cause: Optional[Exception] = None
    ) -> "LNGProcessingError":
        """Create error for a failed processing operation."""
        return cls(
            message=f"LNG processing '{operation}' failed: {reason}",
            operation=operation,
            code="LNG_PROCESSING_FAILED",
            cause=cause,
        )


class LNGExportError(LNGTerminalError):
    """Raised when LNG terminal data export fails."""

    default_code = "LNG_EXPORT_ERROR"

    @classmethod
    def write_failed(cls, path: str, reason: str) -> "LNGExportError":
        """Create error for a failed export write."""
        return cls(
            message=f"Failed to export LNG data to '{path}': {reason}",
            code="LNG_EXPORT_WRITE_FAILED",
            context={"path": path, "reason": reason},
        )

    @classmethod
    def unsupported_format(
        cls, fmt: str, supported: Optional[List[str]] = None
    ) -> "LNGExportError":
        """Create error for an unsupported export format."""
        msg = f"Unsupported LNG export format: {fmt}"
        if supported:
            msg += f". Supported: {', '.join(supported)}"
        return cls(
            message=msg,
            code="LNG_EXPORT_FORMAT",
            context={"format": fmt, "supported": supported},
        )
