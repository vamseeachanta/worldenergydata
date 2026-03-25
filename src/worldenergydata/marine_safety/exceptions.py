"""
Custom Exceptions for Marine Safety Module

Defines a hierarchy of custom exceptions for better error handling
and debugging throughout the module.

These exceptions extend the common exception hierarchy for consistency.
"""

from typing import Any, Dict, Optional

from worldenergydata.common.exceptions import ModuleError


class MarineSafetyError(ModuleError):
    """Base exception for all Marine Safety module errors"""

    default_code = "MARINE_SAFETY_ERROR"
    module_name = "marine_safety"

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
class ConfigurationError(MarineSafetyError):
    """Raised when there's a configuration error"""

    pass


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration values are invalid"""

    pass


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing"""

    pass


# Database Errors
class DatabaseError(MarineSafetyError):
    """Base exception for database-related errors"""

    pass


class ConnectionError(DatabaseError):
    """Raised when database connection fails"""

    pass


class QueryError(DatabaseError):
    """Raised when a database query fails"""

    pass


class IntegrityError(DatabaseError):
    """Raised when data integrity constraints are violated"""

    pass


class RecordNotFoundError(DatabaseError):
    """Raised when a requested record is not found"""

    def __init__(
        self, model_name: str, identifier: Any, message: Optional[str] = None
    ) -> None:
        """
        Initialize record not found error.

        Args:
            model_name: Name of the model/table
            identifier: Identifier used to search for the record
            message: Optional custom message
        """
        if message is None:
            message = f"{model_name} with identifier '{identifier}' not found"
        super().__init__(
            message=message,
            error_code="RECORD_NOT_FOUND",
            details={"model": model_name, "identifier": identifier},
        )


class DuplicateRecordError(DatabaseError):
    """Raised when attempting to create a duplicate record"""

    def __init__(
        self, model_name: str, identifier: Any, message: Optional[str] = None
    ) -> None:
        """
        Initialize duplicate record error.

        Args:
            model_name: Name of the model/table
            identifier: Identifier of the duplicate record
            message: Optional custom message
        """
        if message is None:
            message = f"{model_name} with identifier '{identifier}' already exists"
        super().__init__(
            message=message,
            error_code="DUPLICATE_RECORD",
            details={"model": model_name, "identifier": identifier},
        )


# Validation Errors
class ValidationError(MarineSafetyError):
    """Base exception for validation errors"""

    pass


class InvalidDataError(ValidationError):
    """Raised when data fails validation"""

    def __init__(
        self, field: str, value: Any, reason: str, message: Optional[str] = None
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
            error_code="INVALID_DATA",
            details={"field": field, "value": value, "reason": reason},
        )


class MissingRequiredFieldError(ValidationError):
    """Raised when a required field is missing"""

    def __init__(self, field: str, message: Optional[str] = None) -> None:
        """
        Initialize missing required field error.

        Args:
            field: Name of the missing field
            message: Optional custom message
        """
        if message is None:
            message = f"Required field '{field}' is missing"
        super().__init__(
            message=message,
            error_code="MISSING_REQUIRED_FIELD",
            details={"field": field},
        )


# Scraping Errors
class ScraperError(MarineSafetyError):
    """Base exception for web scraping errors"""

    pass


class HTTPError(ScraperError):
    """Raised when HTTP request fails"""

    def __init__(
        self, url: str, status_code: int, message: Optional[str] = None
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
            error_code="HTTP_ERROR",
            details={"url": url, "status_code": status_code},
        )


class ParsingError(ScraperError):
    """Raised when content parsing fails"""

    def __init__(self, source: str, reason: str, message: Optional[str] = None) -> None:
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
            error_code="PARSING_ERROR",
            details={"source": source, "reason": reason},
        )


class RateLimitError(ScraperError):
    """Raised when rate limit is exceeded"""

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
            error_code="RATE_LIMIT",
            details={"source": source, "retry_after": retry_after},
        )


class TimeoutError(ScraperError):
    """Raised when request times out"""

    def __init__(self, url: str, timeout: int, message: Optional[str] = None) -> None:
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
            error_code="TIMEOUT",
            details={"url": url, "timeout": timeout},
        )


# Storage Errors
class StorageError(MarineSafetyError):
    """Base exception for storage-related errors"""

    pass


class FileNotFoundError(StorageError):
    """Raised when a file is not found"""

    def __init__(self, path: str, message: Optional[str] = None) -> None:
        """
        Initialize file not found error.

        Args:
            path: Path to the missing file
            message: Optional custom message
        """
        if message is None:
            message = f"File not found: {path}"
        super().__init__(
            message=message, error_code="FILE_NOT_FOUND", details={"path": path}
        )


class FileAccessError(StorageError):
    """Raised when file access is denied"""

    def __init__(self, path: str, reason: str, message: Optional[str] = None) -> None:
        """
        Initialize file access error.

        Args:
            path: Path to the file
            reason: Reason for access denial
            message: Optional custom message
        """
        if message is None:
            message = f"Cannot access file {path}: {reason}"
        super().__init__(
            message=message,
            error_code="FILE_ACCESS_ERROR",
            details={"path": path, "reason": reason},
        )


class FileSizeError(StorageError):
    """Raised when file size exceeds limits"""

    def __init__(
        self, path: str, size: int, max_size: int, message: Optional[str] = None
    ) -> None:
        """
        Initialize file size error.

        Args:
            path: Path to the file
            size: Actual file size in bytes
            max_size: Maximum allowed size in bytes
            message: Optional custom message
        """
        if message is None:
            message = (
                f"File {path} size ({size} bytes) exceeds "
                f"maximum allowed size ({max_size} bytes)"
            )
        super().__init__(
            message=message,
            error_code="FILE_SIZE_ERROR",
            details={"path": path, "size": size, "max_size": max_size},
        )


# Processing Errors
class ProcessingError(MarineSafetyError):
    """Base exception for data processing errors"""

    pass


class DataTransformationError(ProcessingError):
    """Raised when data transformation fails"""

    pass


class EnrichmentError(ProcessingError):
    """Raised when data enrichment fails"""

    pass
