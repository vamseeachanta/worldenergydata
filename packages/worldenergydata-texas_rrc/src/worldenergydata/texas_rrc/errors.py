# ABOUTME: Texas RRC module-specific exception classes inheriting from framework base
# ABOUTME: Provides structured error handling for Texas Railroad Commission data operations

"""
Texas RRC Module Exception Hierarchy

This module defines exception classes for the Texas Railroad Commission (RRC)
data module. All exceptions inherit from the common exceptions framework to ensure
consistent error handling across the codebase.

Exception Hierarchy:
    TexasRRCError (from common.exceptions)
    |-- TexasRRCAPIError (API-related errors)
    |   |-- TexasRRCRateLimitError (rate limiting)
    |-- TexasRRCConfigurationError (configuration issues)
    |-- TexasRRCDataError (data processing issues)
    |-- TexasRRCValidationError (validation failures)

Example usage:
    from worldenergydata.texas_rrc.errors import TexasRRCAPIError

    try:
        download_pdq_data()
    except TexasRRCAPIError as e:
        logger.error(f"API call failed: {e}", extra=e.context)
"""

from typing import Any, Dict, List, Optional

from worldenergydata.common.exceptions import ModuleError


class TexasRRCError(ModuleError):
    """
    Base exception for Texas RRC module operations.

    Attributes:
        message: Human-readable error message
        code: Error code for programmatic handling
        context: Additional context about the error
        cause: Original exception that caused this error
    """

    default_code = "TEXAS_RRC_ERROR"
    module_name = "texas_rrc"


class TexasRRCAPIError(TexasRRCError):
    """
    API-related errors for Texas RRC data fetching.

    Raised when API calls to Texas RRC endpoints fail, return unexpected
    responses, or encounter network issues.

    Attributes:
        status_code: HTTP status code if applicable
        response_data: Response data from API if available
        endpoint: API endpoint that was called
    """

    default_code = "TEXAS_RRC_API_ERROR"

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
    ) -> "TexasRRCAPIError":
        """Create error for failed API request."""
        return cls(
            message=f"Texas RRC API request to '{endpoint}' failed with status {status_code}",
            status_code=status_code,
            endpoint=endpoint,
            code="TEXAS_RRC_API_REQUEST_FAILED",
            context={"response": response_body[:500] if response_body else None},
        )

    @classmethod
    def connection_failed(
        cls,
        endpoint: str,
        reason: str = "",
        cause: Optional[Exception] = None,
    ) -> "TexasRRCAPIError":
        """Create error for connection failure."""
        msg = f"Failed to connect to Texas RRC endpoint '{endpoint}'"
        if reason:
            msg += f": {reason}"
        return cls(
            message=msg,
            endpoint=endpoint,
            code="TEXAS_RRC_API_CONNECTION_FAILED",
            cause=cause,
        )

    @classmethod
    def timeout(
        cls,
        endpoint: str,
        timeout_seconds: int,
    ) -> "TexasRRCAPIError":
        """Create error for API timeout."""
        return cls(
            message=f"Texas RRC API request to '{endpoint}' timed out after {timeout_seconds}s",
            endpoint=endpoint,
            code="TEXAS_RRC_API_TIMEOUT",
            context={"timeout": timeout_seconds},
        )

    @classmethod
    def download_failed(
        cls,
        file_type: str,
        reason: str = "",
        cause: Optional[Exception] = None,
    ) -> "TexasRRCAPIError":
        """Create error for failed file download."""
        msg = f"Failed to download Texas RRC {file_type} data"
        if reason:
            msg += f": {reason}"
        return cls(
            message=msg,
            code="TEXAS_RRC_DOWNLOAD_FAILED",
            context={"file_type": file_type},
            cause=cause,
        )


class TexasRRCRateLimitError(TexasRRCAPIError):
    """
    Exception raised when Texas RRC API rate limit is exceeded.

    Attributes:
        retry_after: Seconds to wait before retrying
    """

    default_code = "TEXAS_RRC_RATE_LIMITED"

    def __init__(
        self,
        message: str = "Texas RRC API rate limit exceeded",
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
    ) -> "TexasRRCRateLimitError":
        """Create error for rate limit exceeded."""
        msg = "Texas RRC API rate limit exceeded"
        if retry_after:
            msg += f", retry after {retry_after} seconds"
        return cls(
            message=msg,
            retry_after=retry_after,
            endpoint=endpoint,
        )


class TexasRRCConfigurationError(TexasRRCError):
    """
    Configuration errors for Texas RRC module.

    Raised when there are issues with module configuration,
    missing required settings, or invalid configuration values.
    """

    default_code = "TEXAS_RRC_CONFIG_ERROR"

    @classmethod
    def missing_setting(cls, setting_name: str) -> "TexasRRCConfigurationError":
        """Create error for missing required setting."""
        return cls(
            message=f"Required Texas RRC setting '{setting_name}' is missing",
            code="TEXAS_RRC_CONFIG_MISSING",
            context={"setting": setting_name},
        )

    @classmethod
    def invalid_value(
        cls,
        setting_name: str,
        value: Any,
        reason: str,
    ) -> "TexasRRCConfigurationError":
        """Create error for invalid setting value."""
        return cls(
            message=f"Invalid value for Texas RRC setting '{setting_name}': {reason}",
            code="TEXAS_RRC_CONFIG_INVALID",
            context={"setting": setting_name, "value": str(value), "reason": reason},
        )


class TexasRRCDataError(TexasRRCError):
    """
    Data processing errors for Texas RRC module.

    Raised when data processing operations fail, such as
    parsing responses, transforming data, or handling records.
    """

    default_code = "TEXAS_RRC_DATA_ERROR"

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
    ) -> "TexasRRCDataError":
        """Create error for parse failure."""
        msg = f"Failed to parse Texas RRC {data_type} data"
        if reason:
            msg += f": {reason}"
        return cls(
            message=msg,
            operation=f"parse_{data_type}",
            code="TEXAS_RRC_PARSE_FAILED",
            cause=cause,
        )

    @classmethod
    def transform_failed(
        cls,
        operation: str,
        reason: str = "",
        cause: Optional[Exception] = None,
    ) -> "TexasRRCDataError":
        """Create error for transformation failure."""
        msg = f"Texas RRC data transformation '{operation}' failed"
        if reason:
            msg += f": {reason}"
        return cls(
            message=msg,
            operation=operation,
            code="TEXAS_RRC_TRANSFORM_FAILED",
            cause=cause,
        )

    @classmethod
    def missing_field(
        cls,
        field: str,
        record_type: str = "record",
    ) -> "TexasRRCDataError":
        """Create error for missing required field."""
        return cls(
            message=f"Required field '{field}' missing from Texas RRC {record_type}",
            code="TEXAS_RRC_MISSING_FIELD",
            context={"field": field, "record_type": record_type},
        )


class TexasRRCValidationError(TexasRRCError):
    """
    Data validation errors for Texas RRC module.

    Raised when Texas RRC data fails validation rules or schema checks.
    Can contain multiple validation errors.
    """

    default_code = "TEXAS_RRC_VALIDATION_ERROR"

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
    def from_errors(cls, errors: List[Dict[str, Any]]) -> "TexasRRCValidationError":
        """Create validation error from list of error details."""
        error_count = len(errors)
        return cls(
            message=f"Texas RRC validation failed with {error_count} error(s)",
            errors=errors,
            code="TEXAS_RRC_VALIDATION_FAILED",
        )

    @classmethod
    def invalid_api_number(
        cls, api_number: str, reason: str = ""
    ) -> "TexasRRCValidationError":
        """Create error for invalid API number format."""
        msg = f"Invalid Texas RRC API number: {api_number}"
        if reason:
            msg += f" - {reason}"
        error = cls(
            message=msg,
            code="TEXAS_RRC_INVALID_API",
            context={"api_number": api_number},
        )
        error.add_error("api_number", "format", msg, api_number)
        return error


__all__ = [
    "TexasRRCError",
    "TexasRRCAPIError",
    "TexasRRCRateLimitError",
    "TexasRRCConfigurationError",
    "TexasRRCDataError",
    "TexasRRCValidationError",
]
