# ABOUTME: Custom exceptions for Landman module
# ABOUTME: Defines error hierarchy for county records and land data operations

"""
Custom Exceptions for Landman Module

Defines a hierarchy of custom exceptions for better error handling
and debugging throughout the module.
"""

from typing import Any, Dict, Optional

from worldenergydata.common.exceptions import ModuleError


class LandmanError(ModuleError):
    """Base exception for all Landman module errors."""

    default_code = "LANDMAN_ERROR"
    module_name = "landman"

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize base exception.

        Args:
            message: Human-readable error message
            error_code: Optional error code for categorization
            details: Optional dictionary with additional error details
            cause: Optional original exception that caused this error
        """
        super().__init__(message, code=error_code, context=details, cause=cause)
        self.error_code = self.code
        self.details = self.context


class ProviderError(LandmanError):
    """Base exception for provider-related errors."""

    default_code = "PROVIDER_ERROR"


class StateNotSupportedError(ProviderError):
    """Raised when a state is not supported by the provider."""

    def __init__(
        self,
        state: str,
        provider: str,
        supported_states: Optional[list] = None,
        message: Optional[str] = None,
    ) -> None:
        if message is None:
            message = f"State '{state}' is not supported by {provider}"
            if supported_states:
                message += f". Supported states: {', '.join(supported_states)}"
        super().__init__(
            message=message,
            error_code="STATE_NOT_SUPPORTED",
            details={
                "state": state,
                "provider": provider,
                "supported_states": supported_states,
            },
        )


class CountyNotFoundError(ProviderError):
    """Raised when a county is not found."""

    def __init__(
        self,
        county: str,
        state: str,
        message: Optional[str] = None,
    ) -> None:
        if message is None:
            message = f"County '{county}' not found in state '{state}'"
        super().__init__(
            message=message,
            error_code="COUNTY_NOT_FOUND",
            details={"county": county, "state": state},
        )


class APIError(ProviderError):
    """Raised when an API request fails."""

    def __init__(
        self,
        url: str,
        status_code: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        if message is None:
            message = f"API request failed for {url}"
            if status_code:
                message += f" with status {status_code}"
        super().__init__(
            message=message,
            error_code="API_ERROR",
            details={"url": url, "status_code": status_code},
        )


class RateLimitError(ProviderError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        provider: str,
        retry_after: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        if message is None:
            message = f"Rate limit exceeded for {provider}"
            if retry_after:
                message += f". Retry after {retry_after} seconds"
        super().__init__(
            message=message,
            error_code="RATE_LIMIT",
            details={"provider": provider, "retry_after": retry_after},
        )


class TimeoutError(ProviderError):
    """Raised when request times out."""

    def __init__(
        self,
        url: str,
        timeout: int,
        message: Optional[str] = None,
    ) -> None:
        if message is None:
            message = f"Request to {url} timed out after {timeout} seconds"
        super().__init__(
            message=message,
            error_code="TIMEOUT",
            details={"url": url, "timeout": timeout},
        )


class ParsingError(ProviderError):
    """Raised when content parsing fails."""

    def __init__(
        self,
        source: str,
        reason: str,
        message: Optional[str] = None,
    ) -> None:
        if message is None:
            message = f"Failed to parse content from {source}: {reason}"
        super().__init__(
            message=message,
            error_code="PARSING_ERROR",
            details={"source": source, "reason": reason},
        )


class RecordNotFoundError(ProviderError):
    """Raised when a requested record is not found."""

    def __init__(
        self,
        record_type: str,
        identifier: Any,
        message: Optional[str] = None,
    ) -> None:
        if message is None:
            message = f"{record_type} with identifier '{identifier}' not found"
        super().__init__(
            message=message,
            error_code="RECORD_NOT_FOUND",
            details={"record_type": record_type, "identifier": identifier},
        )


class CacheError(LandmanError):
    """Raised when cache operations fail."""

    default_code = "CACHE_ERROR"


class ConfigurationError(LandmanError):
    """Raised when there's a configuration error."""

    default_code = "CONFIGURATION_ERROR"
