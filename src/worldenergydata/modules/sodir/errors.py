# ABOUTME: SODIR module-specific exception classes inheriting from framework base
# ABOUTME: Provides structured error handling for Norwegian oil/gas data operations

"""
SODIR Module Exception Hierarchy

This module defines exception classes for the SODIR (Norwegian Petroleum Directorate)
data module. All exceptions inherit from the common exceptions framework to ensure
consistent error handling across the codebase.

Exception Hierarchy:
    SODIRError (from common.exceptions)
    |-- SodirError (alias for backward compatibility)
    |-- SodirAPIError (API-related errors)
    |   |-- SodirRateLimitError (rate limiting)
    |-- SodirConfigurationError (configuration issues)
    |-- SodirDataError (data processing issues)
    |-- SodirValidationError (validation failures)

Example usage:
    from worldenergydata.modules.sodir.errors import SodirAPIError, SodirValidationError

    try:
        fetch_wellbore_data(wellbore_id)
    except SodirAPIError as e:
        logger.error(f"API call failed: {e}", extra=e.context)
    except SodirValidationError as e:
        logger.error(f"Validation failed: {e}")
"""

from typing import Any, Dict, List, Optional

from worldenergydata.common.exceptions import SODIRError


class SodirError(SODIRError):
    """
    Base exception for SODIR module operations.

    This class provides backward compatibility with existing code that uses
    SodirError while inheriting from the framework's SODIRError base class.

    Attributes:
        message: Human-readable error message
        code: Error code for programmatic handling
        context: Additional context about the error
        cause: Original exception that caused this error
    """

    default_code = "SODIR_ERROR"
    module_name = "sodir"


class SodirAPIError(SodirError):
    """
    API-related errors for SODIR data fetching.

    Raised when API calls to SODIR/NPD endpoints fail, return unexpected
    responses, or encounter network issues.

    Attributes:
        status_code: HTTP status code if applicable
        response_data: Response data from API if available
        endpoint: API endpoint that was called
    """

    default_code = "SODIR_API_ERROR"

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        endpoint: Optional[str] = None,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize API error.

        Args:
            message: Error message
            status_code: HTTP status code if applicable
            response_data: Response data from API if available
            endpoint: API endpoint that was called
            code: Error code
            context: Additional context
            cause: Original exception
        """
        context = context or {}
        if status_code is not None:
            context["status_code"] = status_code
        if endpoint:
            context["endpoint"] = endpoint
        if response_data:
            context["response_data"] = response_data

        super().__init__(message, code, context, cause)
        self.status_code = status_code
        self.response_data = response_data
        self.endpoint = endpoint

    @classmethod
    def request_failed(
        cls,
        endpoint: str,
        status_code: int,
        response_body: str = "",
    ) -> "SodirAPIError":
        """Create error for failed API request."""
        return cls(
            message=f"SODIR API request to '{endpoint}' failed with status {status_code}",
            status_code=status_code,
            endpoint=endpoint,
            code="SODIR_API_REQUEST_FAILED",
            context={"response": response_body[:500] if response_body else None},
        )

    @classmethod
    def connection_failed(
        cls,
        endpoint: str,
        reason: str = "",
        cause: Optional[Exception] = None,
    ) -> "SodirAPIError":
        """Create error for connection failure."""
        msg = f"Failed to connect to SODIR API endpoint '{endpoint}'"
        if reason:
            msg += f": {reason}"
        return cls(
            message=msg,
            endpoint=endpoint,
            code="SODIR_API_CONNECTION_FAILED",
            cause=cause,
        )

    @classmethod
    def timeout(
        cls,
        endpoint: str,
        timeout_seconds: int,
    ) -> "SodirAPIError":
        """Create error for API timeout."""
        return cls(
            message=f"SODIR API request to '{endpoint}' timed out after {timeout_seconds}s",
            endpoint=endpoint,
            code="SODIR_API_TIMEOUT",
            context={"timeout": timeout_seconds},
        )


class SodirRateLimitError(SodirAPIError):
    """
    Exception raised when SODIR API rate limit is exceeded.

    Attributes:
        retry_after: Seconds to wait before retrying
    """

    default_code = "SODIR_RATE_LIMITED"

    def __init__(
        self,
        message: str = "SODIR API rate limit exceeded",
        retry_after: Optional[int] = None,
        endpoint: Optional[str] = None,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            endpoint: API endpoint that was rate limited
            code: Error code
            context: Additional context
            cause: Original exception
        """
        context = context or {}
        if retry_after is not None:
            context["retry_after"] = retry_after

        super().__init__(
            message=message,
            status_code=429,
            endpoint=endpoint,
            code=code,
            context=context,
            cause=cause,
        )
        self.retry_after = retry_after

    @classmethod
    def exceeded(
        cls,
        endpoint: Optional[str] = None,
        retry_after: Optional[int] = None,
    ) -> "SodirRateLimitError":
        """Create error for rate limit exceeded."""
        msg = "SODIR API rate limit exceeded"
        if retry_after:
            msg += f", retry after {retry_after} seconds"
        return cls(
            message=msg,
            retry_after=retry_after,
            endpoint=endpoint,
        )


class SodirConfigurationError(SodirError):
    """
    Configuration errors for SODIR module.

    Raised when there are issues with SODIR module configuration,
    missing required settings, or invalid configuration values.
    """

    default_code = "SODIR_CONFIG_ERROR"

    @classmethod
    def missing_setting(cls, setting_name: str) -> "SodirConfigurationError":
        """Create error for missing required setting."""
        return cls(
            message=f"Required SODIR setting '{setting_name}' is missing",
            code="SODIR_CONFIG_MISSING",
            context={"setting": setting_name},
        )

    @classmethod
    def invalid_value(
        cls,
        setting_name: str,
        value: Any,
        reason: str,
    ) -> "SodirConfigurationError":
        """Create error for invalid setting value."""
        return cls(
            message=f"Invalid value for SODIR setting '{setting_name}': {reason}",
            code="SODIR_CONFIG_INVALID",
            context={"setting": setting_name, "value": str(value), "reason": reason},
        )

    @classmethod
    def missing_credentials(cls) -> "SodirConfigurationError":
        """Create error for missing API credentials."""
        return cls(
            message="SODIR API credentials not configured",
            code="SODIR_CONFIG_NO_CREDENTIALS",
        )


class SodirDataError(SodirError):
    """
    Data processing errors for SODIR module.

    Raised when data processing operations fail, such as
    parsing responses, transforming data, or handling records.
    """

    default_code = "SODIR_DATA_ERROR"

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize data error.

        Args:
            message: Error description
            operation: Name of the failed operation
            code: Error code
            context: Additional context
            cause: Original exception
        """
        context = context or {}
        if operation:
            context["operation"] = operation

        super().__init__(message, code, context, cause)
        self.operation = operation

    @classmethod
    def parse_failed(
        cls,
        data_type: str,
        reason: str = "",
        cause: Optional[Exception] = None,
    ) -> "SodirDataError":
        """Create error for parse failure."""
        msg = f"Failed to parse SODIR {data_type} data"
        if reason:
            msg += f": {reason}"
        return cls(
            message=msg,
            operation=f"parse_{data_type}",
            code="SODIR_PARSE_FAILED",
            cause=cause,
        )

    @classmethod
    def transform_failed(
        cls,
        operation: str,
        reason: str = "",
        cause: Optional[Exception] = None,
    ) -> "SodirDataError":
        """Create error for transformation failure."""
        msg = f"SODIR data transformation '{operation}' failed"
        if reason:
            msg += f": {reason}"
        return cls(
            message=msg,
            operation=operation,
            code="SODIR_TRANSFORM_FAILED",
            cause=cause,
        )

    @classmethod
    def missing_field(
        cls,
        field: str,
        record_type: str = "record",
    ) -> "SodirDataError":
        """Create error for missing required field."""
        return cls(
            message=f"Required field '{field}' missing from SODIR {record_type}",
            code="SODIR_MISSING_FIELD",
            context={"field": field, "record_type": record_type},
        )


class SodirValidationError(SodirError):
    """
    Data validation errors for SODIR module.

    Raised when SODIR data fails validation rules or schema checks.
    Can contain multiple validation errors.
    """

    default_code = "SODIR_VALIDATION_ERROR"

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
    def from_errors(cls, errors: List[Dict[str, Any]]) -> "SodirValidationError":
        """Create validation error from list of error details."""
        error_count = len(errors)
        return cls(
            message=f"SODIR validation failed with {error_count} error(s)",
            errors=errors,
            code="SODIR_VALIDATION_FAILED",
        )

    @classmethod
    def required_field(cls, field: str) -> "SodirValidationError":
        """Create error for missing required field."""
        error = cls(
            message=f"Required SODIR field '{field}' is missing",
            code="SODIR_REQUIRED_FIELD",
            context={"field": field},
        )
        error.add_error(field, "required", f"Field '{field}' is required")
        return error

    @classmethod
    def invalid_type(
        cls,
        field: str,
        expected: str,
        actual: str,
    ) -> "SodirValidationError":
        """Create error for type mismatch."""
        error = cls(
            message=f"SODIR field '{field}' has invalid type: expected {expected}, got {actual}",
            code="SODIR_INVALID_TYPE",
            context={"field": field, "expected": expected, "actual": actual},
        )
        error.add_error(field, "type", f"Expected {expected}, got {actual}")
        return error

    @classmethod
    def invalid_format(
        cls,
        field: str,
        expected_format: str,
        value: Any,
    ) -> "SodirValidationError":
        """Create error for invalid format."""
        error = cls(
            message=f"SODIR field '{field}' has invalid format: expected {expected_format}",
            code="SODIR_INVALID_FORMAT",
            context={
                "field": field,
                "expected_format": expected_format,
                "value": str(value),
            },
        )
        error.add_error(field, "format", f"Expected format {expected_format}", value)
        return error

    @classmethod
    def out_of_range(
        cls,
        field: str,
        value: Any,
        min_val: Optional[Any] = None,
        max_val: Optional[Any] = None,
    ) -> "SodirValidationError":
        """Create error for value out of range."""
        range_str = ""
        if min_val is not None and max_val is not None:
            range_str = f"between {min_val} and {max_val}"
        elif min_val is not None:
            range_str = f">= {min_val}"
        elif max_val is not None:
            range_str = f"<= {max_val}"

        error = cls(
            message=f"SODIR field '{field}' value {value} is out of range ({range_str})",
            code="SODIR_OUT_OF_RANGE",
            context={
                "field": field,
                "value": str(value),
                "min": min_val,
                "max": max_val,
            },
        )
        error.add_error(field, "range", f"Value must be {range_str}", value)
        return error


__all__ = [
    "SodirError",
    "SodirAPIError",
    "SodirRateLimitError",
    "SodirConfigurationError",
    "SodirDataError",
    "SodirValidationError",
]
