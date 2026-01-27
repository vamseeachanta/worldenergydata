# ABOUTME: Canada module-specific exception classes inheriting from framework base
# ABOUTME: Provides structured error handling for Canadian oil/gas data operations

"""
Canada Module Exception Hierarchy

This module defines exception classes for the Canada (AER/BCER)
data module. All exceptions inherit from the common exceptions framework to ensure
consistent error handling across the codebase.

Exception Hierarchy:
    CanadaError (from ModuleError)
    |-- CanadaAERError (Alberta-specific errors)
    |-- CanadaBCERError (BC-specific errors)
    |-- CanadaUWIError (UWI parsing/validation errors)
    |-- CanadaAPIError (API-related errors)
    |   |-- CanadaRateLimitError (rate limiting)
    |-- CanadaConfigurationError (configuration issues)
    |-- CanadaDataError (data processing issues)
    |-- CanadaValidationError (validation failures)

Example usage:
    from worldenergydata.modules.canada.errors import CanadaAPIError, CanadaUWIError

    try:
        fetch_well_data(uwi)
    except CanadaAPIError as e:
        logger.error(f"API call failed: {e}", extra=e.context)
    except CanadaUWIError as e:
        logger.error(f"Invalid UWI: {e}")
"""

from typing import Any, Dict, List, Optional

from worldenergydata.common.exceptions import ModuleError


class CanadaError(ModuleError):
    """
    Base exception for Canada module operations.

    This class provides the foundation for all Canada-specific errors,
    inheriting from the framework's ModuleError base class.

    Attributes:
        message: Human-readable error message
        code: Error code for programmatic handling
        context: Additional context about the error
        cause: Original exception that caused this error
    """

    default_code = "CANADA_ERROR"
    module_name = "canada"


class CanadaAERError(CanadaError):
    """
    Alberta Energy Regulator specific errors.

    Raised when operations related to AER data fail, including
    API calls, data parsing, or Alberta-specific validations.

    Attributes:
        license_number: AER well license number if applicable
    """

    default_code = "CANADA_AER_ERROR"

    def __init__(
        self,
        message: str,
        license_number: Optional[str] = None,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize AER error.

        Args:
            message: Error message
            license_number: AER license number if applicable
            code: Error code
            context: Additional context
            cause: Original exception
        """
        context = context or {}
        context["regulator"] = "AER"
        if license_number:
            context["license_number"] = license_number

        super().__init__(message, code, context, cause)
        self.license_number = license_number

    @classmethod
    def license_not_found(cls, license_number: str) -> "CanadaAERError":
        """Create error for license not found."""
        return cls(
            message=f"AER license '{license_number}' not found",
            license_number=license_number,
            code="AER_LICENSE_NOT_FOUND",
        )

    @classmethod
    def data_unavailable(cls, data_type: str, reason: str = "") -> "CanadaAERError":
        """Create error for unavailable AER data."""
        msg = f"AER {data_type} data is unavailable"
        if reason:
            msg += f": {reason}"
        return cls(
            message=msg,
            code="AER_DATA_UNAVAILABLE",
            context={"data_type": data_type},
        )


class CanadaBCERError(CanadaError):
    """
    BC Energy Regulator specific errors.

    Raised when operations related to BCER data fail, including
    API calls, data parsing, or BC-specific validations.

    Attributes:
        permit_number: BCER well permit number if applicable
    """

    default_code = "CANADA_BCER_ERROR"

    def __init__(
        self,
        message: str,
        permit_number: Optional[str] = None,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize BCER error.

        Args:
            message: Error message
            permit_number: BCER permit number if applicable
            code: Error code
            context: Additional context
            cause: Original exception
        """
        context = context or {}
        context["regulator"] = "BCER"
        if permit_number:
            context["permit_number"] = permit_number

        super().__init__(message, code, context, cause)
        self.permit_number = permit_number

    @classmethod
    def permit_not_found(cls, permit_number: str) -> "CanadaBCERError":
        """Create error for permit not found."""
        return cls(
            message=f"BCER permit '{permit_number}' not found",
            permit_number=permit_number,
            code="BCER_PERMIT_NOT_FOUND",
        )

    @classmethod
    def arcgis_error(cls, endpoint: str, reason: str = "") -> "CanadaBCERError":
        """Create error for ArcGIS REST API failure."""
        msg = f"BCER ArcGIS endpoint '{endpoint}' failed"
        if reason:
            msg += f": {reason}"
        return cls(
            message=msg,
            code="BCER_ARCGIS_ERROR",
            context={"endpoint": endpoint},
        )


class CanadaUWIError(CanadaError):
    """
    Unique Well Identifier (UWI) parsing and validation errors.

    Raised when a UWI cannot be parsed or fails validation rules.
    Canadian UWIs follow specific formats for Alberta and BC wells.

    Attributes:
        uwi: The UWI that caused the error
        field: Specific UWI field that failed validation
    """

    default_code = "CANADA_UWI_ERROR"

    def __init__(
        self,
        message: str,
        uwi: Optional[str] = None,
        field: Optional[str] = None,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize UWI error.

        Args:
            message: Error message
            uwi: The UWI that caused the error
            field: Specific field that failed
            code: Error code
            context: Additional context
            cause: Original exception
        """
        context = context or {}
        if uwi:
            context["uwi"] = uwi
        if field:
            context["field"] = field

        super().__init__(message, code, context, cause)
        self.uwi = uwi
        self.field = field

    @classmethod
    def invalid_format(cls, uwi: str, reason: str = "") -> "CanadaUWIError":
        """Create error for invalid UWI format."""
        msg = f"Invalid UWI format: '{uwi}'"
        if reason:
            msg += f" - {reason}"
        return cls(
            message=msg,
            uwi=uwi,
            code="UWI_INVALID_FORMAT",
        )

    @classmethod
    def invalid_field(
        cls, uwi: str, field: str, value: str, expected: str
    ) -> "CanadaUWIError":
        """Create error for invalid UWI field value."""
        return cls(
            message=f"Invalid UWI field '{field}': got '{value}', expected {expected}",
            uwi=uwi,
            field=field,
            code="UWI_INVALID_FIELD",
            context={"value": value, "expected": expected},
        )

    @classmethod
    def unknown_province(cls, uwi: str, province_code: str) -> "CanadaUWIError":
        """Create error for unknown province code in UWI."""
        return cls(
            message=f"Unknown province code '{province_code}' in UWI: {uwi}",
            uwi=uwi,
            field="province",
            code="UWI_UNKNOWN_PROVINCE",
            context={"province_code": province_code},
        )


class CanadaAPIError(CanadaError):
    """
    API-related errors for Canadian data fetching.

    Raised when API calls to AER, BCER, or Petrinex endpoints fail,
    return unexpected responses, or encounter network issues.

    Attributes:
        status_code: HTTP status code if applicable
        response_data: Response data from API if available
        endpoint: API endpoint that was called
    """

    default_code = "CANADA_API_ERROR"

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
    ) -> "CanadaAPIError":
        """Create error for failed API request."""
        return cls(
            message=f"Canada API request to '{endpoint}' failed with status {status_code}",
            status_code=status_code,
            endpoint=endpoint,
            code="CANADA_API_REQUEST_FAILED",
            context={"response": response_body[:500] if response_body else None},
        )

    @classmethod
    def connection_failed(
        cls,
        endpoint: str,
        reason: str = "",
        cause: Optional[Exception] = None,
    ) -> "CanadaAPIError":
        """Create error for connection failure."""
        msg = f"Failed to connect to Canada API endpoint '{endpoint}'"
        if reason:
            msg += f": {reason}"
        return cls(
            message=msg,
            endpoint=endpoint,
            code="CANADA_API_CONNECTION_FAILED",
            cause=cause,
        )

    @classmethod
    def timeout(
        cls,
        endpoint: str,
        timeout_seconds: int,
    ) -> "CanadaAPIError":
        """Create error for API timeout."""
        return cls(
            message=f"Canada API request to '{endpoint}' timed out after {timeout_seconds}s",
            endpoint=endpoint,
            code="CANADA_API_TIMEOUT",
            context={"timeout": timeout_seconds},
        )


class CanadaRateLimitError(CanadaAPIError):
    """
    Exception raised when Canada API rate limit is exceeded.

    Attributes:
        retry_after: Seconds to wait before retrying
    """

    default_code = "CANADA_RATE_LIMITED"

    def __init__(
        self,
        message: str = "Canada API rate limit exceeded",
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
    ) -> "CanadaRateLimitError":
        """Create error for rate limit exceeded."""
        msg = "Canada API rate limit exceeded"
        if retry_after:
            msg += f", retry after {retry_after} seconds"
        return cls(
            message=msg,
            retry_after=retry_after,
            endpoint=endpoint,
        )


class CanadaConfigurationError(CanadaError):
    """
    Configuration errors for Canada module.

    Raised when there are issues with Canada module configuration,
    missing required settings, or invalid configuration values.
    """

    default_code = "CANADA_CONFIG_ERROR"

    @classmethod
    def missing_setting(cls, setting_name: str) -> "CanadaConfigurationError":
        """Create error for missing required setting."""
        return cls(
            message=f"Required Canada setting '{setting_name}' is missing",
            code="CANADA_CONFIG_MISSING",
            context={"setting": setting_name},
        )

    @classmethod
    def invalid_value(
        cls,
        setting_name: str,
        value: Any,
        reason: str,
    ) -> "CanadaConfigurationError":
        """Create error for invalid setting value."""
        return cls(
            message=f"Invalid value for Canada setting '{setting_name}': {reason}",
            code="CANADA_CONFIG_INVALID",
            context={"setting": setting_name, "value": str(value), "reason": reason},
        )


class CanadaDataError(CanadaError):
    """
    Data processing errors for Canada module.

    Raised when data processing operations fail, such as
    parsing responses, transforming data, or handling records.
    """

    default_code = "CANADA_DATA_ERROR"

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
    ) -> "CanadaDataError":
        """Create error for parse failure."""
        msg = f"Failed to parse Canada {data_type} data"
        if reason:
            msg += f": {reason}"
        return cls(
            message=msg,
            operation=f"parse_{data_type}",
            code="CANADA_PARSE_FAILED",
            cause=cause,
        )

    @classmethod
    def transform_failed(
        cls,
        operation: str,
        reason: str = "",
        cause: Optional[Exception] = None,
    ) -> "CanadaDataError":
        """Create error for transformation failure."""
        msg = f"Canada data transformation '{operation}' failed"
        if reason:
            msg += f": {reason}"
        return cls(
            message=msg,
            operation=operation,
            code="CANADA_TRANSFORM_FAILED",
            cause=cause,
        )


class CanadaValidationError(CanadaError):
    """
    Data validation errors for Canada module.

    Raised when Canada data fails validation rules or schema checks.
    Can contain multiple validation errors.
    """

    default_code = "CANADA_VALIDATION_ERROR"

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
    def from_errors(cls, errors: List[Dict[str, Any]]) -> "CanadaValidationError":
        """Create validation error from list of error details."""
        error_count = len(errors)
        return cls(
            message=f"Canada validation failed with {error_count} error(s)",
            errors=errors,
            code="CANADA_VALIDATION_FAILED",
        )


__all__ = [
    "CanadaError",
    "CanadaAERError",
    "CanadaBCERError",
    "CanadaUWIError",
    "CanadaAPIError",
    "CanadaRateLimitError",
    "CanadaConfigurationError",
    "CanadaDataError",
    "CanadaValidationError",
]
