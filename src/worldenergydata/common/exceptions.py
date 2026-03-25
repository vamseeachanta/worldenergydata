"""
Exception Hierarchy for WorldEnergyData

This module defines a structured exception hierarchy for consistent error
handling across all modules. Each exception includes context and optional
cause tracking for debugging.

Exception Hierarchy:
    WorldEnergyDataError (base)
    |-- ConfigError (configuration issues)
    |-- DataError (data-related issues)
    |   |-- DataSourceError (source unavailable)
    |   |-- ValidationError (validation failures)
    |   |-- ProcessingError (processing failures)
    |-- APIError (external API issues)
    |-- ModuleError (module-specific base)
        |-- BSEEError
        |-- SODIRError
        |-- EIAError

Example usage:
    from worldenergydata.common.exceptions import DataError, ValidationError

    try:
        process_data(records)
    except ValidationError as e:
        logger.error(f"Validation failed: {e}", extra=e.context)
    except DataError as e:
        logger.error(f"Data error: {e}")
"""

from typing import Any, Dict, List, Optional


class WorldEnergyDataError(Exception):
    """
    Base exception for all WorldEnergyData errors.

    All custom exceptions in the package inherit from this class,
    enabling consistent error handling and logging.

    Attributes:
        message: Human-readable error message
        code: Error code for programmatic handling
        context: Additional context about the error
        cause: Original exception that caused this error
    """

    default_code: str = "WED_ERROR"

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Human-readable error description
            code: Error code (defaults to class default_code)
            context: Additional context dictionary
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.context = context or {}
        self.cause = cause

        # Chain the cause if provided
        if cause:
            self.__cause__ = cause

    def __str__(self) -> str:
        """Return string representation of the error."""
        parts = [f"[{self.code}] {self.message}"]
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")
        return " | ".join(parts)

    def __repr__(self) -> str:
        """Return detailed representation of the error."""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"code={self.code!r}, "
            f"context={self.context!r})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for serialization."""
        result = {
            "error": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
        }
        if self.context:
            result["context"] = self.context
        if self.cause:
            result["cause"] = str(self.cause)
        return result


class ConfigError(WorldEnergyDataError):
    """
    Configuration-related errors.

    Raised when there are issues with application configuration,
    missing required settings, or invalid configuration values.
    """

    default_code = "CONFIG_ERROR"

    @classmethod
    def missing_setting(cls, setting_name: str) -> "ConfigError":
        """Create error for missing required setting."""
        return cls(
            message=f"Required setting '{setting_name}' is missing",
            code="CONFIG_MISSING",
            context={"setting": setting_name},
        )

    @classmethod
    def invalid_value(cls, setting_name: str, value: Any, reason: str) -> "ConfigError":
        """Create error for invalid setting value."""
        return cls(
            message=f"Invalid value for '{setting_name}': {reason}",
            code="CONFIG_INVALID",
            context={"setting": setting_name, "value": str(value), "reason": reason},
        )


class DataError(WorldEnergyDataError):
    """
    Base class for data-related errors.

    Parent class for all errors related to data handling,
    including loading, processing, and validation.
    """

    default_code = "DATA_ERROR"


class DataSourceError(DataError):
    """
    Data source access errors.

    Raised when a data source is unavailable, unreachable,
    or returns unexpected responses.
    """

    default_code = "DATA_SOURCE_ERROR"

    def __init__(
        self,
        message: str,
        source: str,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize data source error.

        Args:
            message: Error description
            source: Name/identifier of the data source
            code: Error code
            context: Additional context
            cause: Original exception
        """
        context = context or {}
        context["source"] = source
        super().__init__(message, code, context, cause)
        self.source = source

    @classmethod
    def unavailable(cls, source: str, reason: str = "") -> "DataSourceError":
        """Create error for unavailable data source."""
        msg = f"Data source '{source}' is unavailable"
        if reason:
            msg += f": {reason}"
        return cls(message=msg, source=source, code="SOURCE_UNAVAILABLE")

    @classmethod
    def timeout(cls, source: str, timeout_seconds: int) -> "DataSourceError":
        """Create error for data source timeout."""
        return cls(
            message=f"Data source '{source}' timed out after {timeout_seconds}s",
            source=source,
            code="SOURCE_TIMEOUT",
            context={"timeout": timeout_seconds},
        )


class ValidationError(DataError):
    """
    Data validation errors.

    Raised when data fails validation rules or schema checks.
    Can contain multiple validation errors.
    """

    default_code = "VALIDATION_ERROR"

    def __init__(
        self,
        message: str,
        errors: Optional[List[Dict[str, Any]]] = None,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize validation error.

        Args:
            message: Error description
            errors: List of individual validation errors
            code: Error code
            context: Additional context
            cause: Original exception
        """
        super().__init__(message, code, context, cause)
        self.errors = errors or []

    def add_error(
        self,
        field: str,
        error_type: str,
        message: str,
        value: Any = None,
    ) -> None:
        """Add a validation error to the list."""
        self.errors.append(
            {
                "field": field,
                "type": error_type,
                "message": message,
                "value": str(value) if value is not None else None,
            }
        )

    def has_errors(self) -> bool:
        """Check if there are any validation errors."""
        return len(self.errors) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary including all validation errors."""
        result = super().to_dict()
        if self.errors:
            result["validation_errors"] = self.errors
        return result

    @classmethod
    def from_errors(cls, errors: List[Dict[str, Any]]) -> "ValidationError":
        """Create validation error from list of error details."""
        error_count = len(errors)
        return cls(
            message=f"Validation failed with {error_count} error(s)",
            errors=errors,
            code="VALIDATION_FAILED",
        )

    @classmethod
    def required_field(cls, field: str) -> "ValidationError":
        """Create error for missing required field."""
        error = cls(
            message=f"Required field '{field}' is missing",
            code="REQUIRED_FIELD",
            context={"field": field},
        )
        error.add_error(field, "required", f"Field '{field}' is required")
        return error

    @classmethod
    def invalid_type(cls, field: str, expected: str, actual: str) -> "ValidationError":
        """Create error for type mismatch."""
        error = cls(
            message=f"Field '{field}' has invalid type: expected {expected}, got {actual}",
            code="INVALID_TYPE",
            context={"field": field, "expected": expected, "actual": actual},
        )
        error.add_error(field, "type", f"Expected {expected}, got {actual}")
        return error


class ProcessingError(DataError):
    """
    Data processing errors.

    Raised when data processing operations fail, such as
    transformations, aggregations, or calculations.
    """

    default_code = "PROCESSING_ERROR"

    def __init__(
        self,
        message: str,
        operation: str,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize processing error.

        Args:
            message: Error description
            operation: Name of the failed operation
            code: Error code
            context: Additional context
            cause: Original exception
        """
        context = context or {}
        context["operation"] = operation
        super().__init__(message, code, context, cause)
        self.operation = operation

    @classmethod
    def failed(
        cls, operation: str, reason: str, cause: Optional[Exception] = None
    ) -> "ProcessingError":
        """Create error for failed processing operation."""
        return cls(
            message=f"Processing operation '{operation}' failed: {reason}",
            operation=operation,
            code="PROCESSING_FAILED",
            cause=cause,
        )


class APIError(WorldEnergyDataError):
    """
    External API errors.

    Raised when calls to external APIs fail or return errors.
    """

    default_code = "API_ERROR"

    def __init__(
        self,
        message: str,
        api_name: str,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize API error.

        Args:
            message: Error description
            api_name: Name of the API
            status_code: HTTP status code if applicable
            code: Error code
            context: Additional context
            cause: Original exception
        """
        context = context or {}
        context["api"] = api_name
        if status_code:
            context["status_code"] = status_code
        super().__init__(message, code, context, cause)
        self.api_name = api_name
        self.status_code = status_code

    @classmethod
    def request_failed(
        cls,
        api_name: str,
        status_code: int,
        response_body: str = "",
    ) -> "APIError":
        """Create error for failed API request."""
        return cls(
            message=f"API request to '{api_name}' failed with status {status_code}",
            api_name=api_name,
            status_code=status_code,
            code="API_REQUEST_FAILED",
            context={"response": response_body[:500] if response_body else None},
        )

    @classmethod
    def rate_limited(
        cls, api_name: str, retry_after: Optional[int] = None
    ) -> "APIError":
        """Create error for rate limiting."""
        context = {}
        if retry_after:
            context["retry_after"] = retry_after
        return cls(
            message=f"Rate limited by '{api_name}'",
            api_name=api_name,
            status_code=429,
            code="API_RATE_LIMITED",
            context=context,
        )


# Module-specific base exceptions
class ModuleError(WorldEnergyDataError):
    """Base class for module-specific errors."""

    default_code = "MODULE_ERROR"
    module_name: str = "unknown"

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        context = context or {}
        context["module"] = self.module_name
        super().__init__(message, code, context, cause)


class BSEEError(ModuleError):
    """BSEE module-specific errors."""

    default_code = "BSEE_ERROR"
    module_name = "bsee"


class SODIRError(ModuleError):
    """SODIR module-specific errors."""

    default_code = "SODIR_ERROR"
    module_name = "sodir"


class EIAError(ModuleError):
    """EIA module-specific errors."""

    default_code = "EIA_ERROR"
    module_name = "eia"


class TexasRRCError(ModuleError):
    """Texas RRC module-specific errors."""

    default_code = "TEXAS_RRC_ERROR"
    module_name = "texas_rrc"


class CanadaError(ModuleError):
    """Canada module-specific errors (AER/BCER)."""

    default_code = "CANADA_ERROR"
    module_name = "canada"


class MexicoCNHError(ModuleError):
    """Mexico CNH module-specific errors."""

    default_code = "MEXICO_CNH_ERROR"
    module_name = "mexico_cnh"
