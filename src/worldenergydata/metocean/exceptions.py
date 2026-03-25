"""
ABOUTME: Custom exceptions for the Metocean module.
ABOUTME: Defines a hierarchy of exceptions for API clients, caching, and data operations.
"""

from typing import Any, Dict, Optional

from worldenergydata.common.exceptions import ModuleError


class MetoceanError(ModuleError):
    """Base exception for all Metocean module errors."""

    default_code = "METOCEAN_ERROR"
    module_name = "metocean"

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
        # Backward compatibility aliases
        self.error_code = self.code
        self.details = self.context


# Configuration Errors
class ConfigurationError(MetoceanError):
    """Raised when there's a configuration error."""

    default_code = "METOCEAN_CONFIG_ERROR"


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration values are invalid."""

    default_code = "METOCEAN_INVALID_CONFIG"


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""

    default_code = "METOCEAN_MISSING_CONFIG"


# Database Errors
class DatabaseError(MetoceanError):
    """Base exception for database-related errors."""

    default_code = "METOCEAN_DB_ERROR"


class ConnectionError(DatabaseError):
    """Raised when database connection fails."""

    default_code = "METOCEAN_DB_CONNECTION"


class QueryError(DatabaseError):
    """Raised when a database query fails."""

    default_code = "METOCEAN_DB_QUERY"


# Validation Errors
class ValidationError(MetoceanError):
    """Base exception for validation errors."""

    default_code = "METOCEAN_VALIDATION_ERROR"


class InvalidDataError(ValidationError):
    """Raised when data fails validation."""

    def __init__(
        self,
        field: str,
        value: Any,
        reason: str,
        message: Optional[str] = None,
    ) -> None:
        """
        Initialize invalid data error.

        Args:
            field: Name of the field that failed validation
            value: The invalid value
            reason: Reason for validation failure
            message: Optional custom message
        """
        if message is None:
            message = f"Invalid value for '{field}': {reason}"
        super().__init__(
            message=message,
            error_code="METOCEAN_INVALID_DATA",
            details={"field": field, "value": value, "reason": reason},
        )


# Client Errors (base for API client errors)
class ClientError(MetoceanError):
    """Base exception for API client errors."""

    default_code = "METOCEAN_CLIENT_ERROR"


class HTTPError(ClientError):
    """Raised when HTTP request fails."""

    def __init__(
        self,
        url: str,
        status_code: int,
        message: Optional[str] = None,
    ) -> None:
        """
        Initialize HTTP error.

        Args:
            url: URL that failed
            status_code: HTTP status code
            message: Optional custom message
        """
        if message is None:
            message = f"HTTP request failed for {url} with status {status_code}"
        super().__init__(
            message=message,
            error_code="METOCEAN_HTTP_ERROR",
            details={"url": url, "status_code": status_code},
        )
        self.url = url
        self.status_code = status_code


class RateLimitError(ClientError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        source: str,
        retry_after: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        """
        Initialize rate limit error.

        Args:
            source: Source that rate-limited the request
            retry_after: Seconds to wait before retrying
            message: Optional custom message
        """
        if message is None:
            message = f"Rate limit exceeded for {source}"
            if retry_after:
                message += f". Retry after {retry_after} seconds"
        super().__init__(
            message=message,
            error_code="METOCEAN_RATE_LIMIT",
            details={"source": source, "retry_after": retry_after},
        )
        self.retry_after = retry_after


class TimeoutError(ClientError):
    """Raised when request times out."""

    def __init__(
        self,
        url: str,
        timeout: int,
        message: Optional[str] = None,
    ) -> None:
        """
        Initialize timeout error.

        Args:
            url: URL that timed out
            timeout: Timeout duration in seconds
            message: Optional custom message
        """
        if message is None:
            message = f"Request to {url} timed out after {timeout} seconds"
        super().__init__(
            message=message,
            error_code="METOCEAN_TIMEOUT",
            details={"url": url, "timeout": timeout},
        )
        self.url = url
        self.timeout = timeout


class ParsingError(ClientError):
    """Raised when content parsing fails."""

    def __init__(
        self,
        source: str,
        reason: str,
        message: Optional[str] = None,
    ) -> None:
        """
        Initialize parsing error.

        Args:
            source: Source being parsed
            reason: Reason for parsing failure
            message: Optional custom message
        """
        if message is None:
            message = f"Failed to parse content from {source}: {reason}"
        super().__init__(
            message=message,
            error_code="METOCEAN_PARSING_ERROR",
            details={"source": source, "reason": reason},
        )
        self.source = source
        self.reason = reason


class DataNotFoundError(ClientError):
    """Raised when requested data is not available."""

    def __init__(
        self,
        source: str,
        message: Optional[str] = None,
    ) -> None:
        """
        Initialize data not found error.

        Args:
            source: Data source queried
            message: Optional custom message
        """
        if message is None:
            message = f"Requested data not found from {source}"
        super().__init__(
            message=message,
            error_code="METOCEAN_DATA_NOT_FOUND",
            details={"source": source},
        )
        self.source = source


# Cache Errors
class CacheError(MetoceanError):
    """Base exception for cache-related errors."""

    default_code = "METOCEAN_CACHE_ERROR"


class CacheReadError(CacheError):
    """Raised when reading from cache fails."""

    default_code = "METOCEAN_CACHE_READ"


class CacheWriteError(CacheError):
    """Raised when writing to cache fails."""

    default_code = "METOCEAN_CACHE_WRITE"


# Export Errors
class ExportError(MetoceanError):
    """Base exception for data export errors."""

    default_code = "METOCEAN_EXPORT_ERROR"


class ExportFormatError(ExportError):
    """Raised when export format is unsupported or invalid."""

    def __init__(
        self,
        format_name: str,
        supported_formats: Optional[list] = None,
        message: Optional[str] = None,
    ) -> None:
        """
        Initialize export format error.

        Args:
            format_name: The unsupported format
            supported_formats: List of supported formats
            message: Optional custom message
        """
        if message is None:
            message = f"Unsupported export format: {format_name}"
            if supported_formats:
                message += f". Supported formats: {', '.join(supported_formats)}"
        super().__init__(
            message=message,
            error_code="METOCEAN_EXPORT_FORMAT",
            details={"format": format_name, "supported": supported_formats},
        )


class ExportWriteError(ExportError):
    """Raised when writing exported data fails."""

    def __init__(
        self,
        path: str,
        reason: str,
        message: Optional[str] = None,
    ) -> None:
        """
        Initialize export write error.

        Args:
            path: Path where write failed
            reason: Reason for failure
            message: Optional custom message
        """
        if message is None:
            message = f"Failed to write export to {path}: {reason}"
        super().__init__(
            message=message,
            error_code="METOCEAN_EXPORT_WRITE",
            details={"path": path, "reason": reason},
        )
