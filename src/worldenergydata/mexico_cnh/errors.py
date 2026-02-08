# ABOUTME: Mexico CNH module-specific exception classes inheriting from framework base
# ABOUTME: Provides structured error handling for Mexico CNH data operations

"""
Mexico CNH Module Exception Hierarchy

This module defines exception classes for the Mexico CNH (Comision Nacional de
Hidrocarburos) data module. All exceptions inherit from the common exceptions
framework to ensure consistent error handling across the codebase.

Exception Hierarchy:
    MexicoCNHError (from common.exceptions)
    |-- MexicoCNHScraperError (Selenium/scraping errors)
    |   |-- MexicoCNHTimeoutError (page load timeouts)
    |-- MexicoCNHParseError (data parsing errors)
    |-- MexicoCNHValidationError (validation failures)
    |-- MexicoCNHConfigurationError (configuration issues)

Example usage:
    from worldenergydata.mexico_cnh.errors import MexicoCNHScraperError

    try:
        scrape_sih_dashboard()
    except MexicoCNHScraperError as e:
        logger.error(f"Scraping failed: {e}", extra=e.context)
"""

from typing import Any, Dict, List, Optional

from worldenergydata.common.exceptions import ModuleError


class MexicoCNHError(ModuleError):
    """
    Base exception for Mexico CNH module operations.

    Attributes:
        message: Human-readable error message
        code: Error code for programmatic handling
        context: Additional context about the error
        cause: Original exception that caused this error
    """

    default_code = "MEXICO_CNH_ERROR"
    module_name = "mexico_cnh"


class MexicoCNHScraperError(MexicoCNHError):
    """
    Scraper-related errors for Mexico CNH data fetching.

    Raised when Selenium scraping operations fail, including page load
    failures, element not found errors, and browser-related issues.

    Attributes:
        url: URL that was being scraped
        element: Element selector that failed (if applicable)
    """

    default_code = "MEXICO_CNH_SCRAPER_ERROR"

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        element: Optional[str] = None,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize scraper error.

        Args:
            message: Error message
            url: URL being scraped when error occurred
            element: CSS/XPath selector that failed
            code: Error code
            context: Additional context
            cause: Original exception
        """
        context = context or {}
        if url:
            context["url"] = url
        if element:
            context["element"] = element

        super().__init__(message, code, context, cause)
        self.url = url
        self.element = element

    @classmethod
    def page_load_failed(
        cls,
        url: str,
        reason: str = "",
        cause: Optional[Exception] = None,
    ) -> "MexicoCNHScraperError":
        """Create error for failed page load."""
        msg = f"Failed to load Mexico CNH page: {url}"
        if reason:
            msg += f" - {reason}"
        return cls(
            message=msg,
            url=url,
            code="MEXICO_CNH_PAGE_LOAD_FAILED",
            cause=cause,
        )

    @classmethod
    def element_not_found(
        cls,
        element: str,
        url: Optional[str] = None,
    ) -> "MexicoCNHScraperError":
        """Create error for element not found."""
        return cls(
            message=f"Element not found on Mexico CNH page: {element}",
            url=url,
            element=element,
            code="MEXICO_CNH_ELEMENT_NOT_FOUND",
        )

    @classmethod
    def javascript_error(
        cls,
        url: str,
        error_msg: str = "",
        cause: Optional[Exception] = None,
    ) -> "MexicoCNHScraperError":
        """Create error for JavaScript execution failure."""
        msg = f"JavaScript error on Mexico CNH page: {url}"
        if error_msg:
            msg += f" - {error_msg}"
        return cls(
            message=msg,
            url=url,
            code="MEXICO_CNH_JS_ERROR",
            cause=cause,
        )

    @classmethod
    def browser_init_failed(
        cls,
        reason: str = "",
        cause: Optional[Exception] = None,
    ) -> "MexicoCNHScraperError":
        """Create error for browser initialization failure."""
        msg = "Failed to initialize Selenium browser for Mexico CNH scraping"
        if reason:
            msg += f": {reason}"
        return cls(
            message=msg,
            code="MEXICO_CNH_BROWSER_INIT_FAILED",
            cause=cause,
        )


class MexicoCNHTimeoutError(MexicoCNHScraperError):
    """
    Exception raised when Mexico CNH page operations time out.

    Attributes:
        timeout_seconds: Timeout duration in seconds
    """

    default_code = "MEXICO_CNH_TIMEOUT"

    def __init__(
        self,
        message: str = "Mexico CNH operation timed out",
        timeout_seconds: Optional[int] = None,
        url: Optional[str] = None,
        element: Optional[str] = None,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize timeout error.

        Args:
            message: Error message
            timeout_seconds: Timeout duration in seconds
            url: URL being accessed when timeout occurred
            element: Element being waited for (if applicable)
            code: Error code
            context: Additional context
            cause: Original exception
        """
        context = context or {}
        if timeout_seconds is not None:
            context["timeout_seconds"] = timeout_seconds

        super().__init__(
            message=message,
            url=url,
            element=element,
            code=code,
            context=context,
            cause=cause,
        )
        self.timeout_seconds = timeout_seconds

    @classmethod
    def page_timeout(
        cls,
        url: str,
        timeout_seconds: int,
    ) -> "MexicoCNHTimeoutError":
        """Create error for page load timeout."""
        return cls(
            message=f"Mexico CNH page '{url}' timed out after {timeout_seconds}s",
            timeout_seconds=timeout_seconds,
            url=url,
            code="MEXICO_CNH_PAGE_TIMEOUT",
        )

    @classmethod
    def element_timeout(
        cls,
        element: str,
        timeout_seconds: int,
        url: Optional[str] = None,
    ) -> "MexicoCNHTimeoutError":
        """Create error for element wait timeout."""
        return cls(
            message=f"Timeout waiting for element '{element}' after {timeout_seconds}s",
            timeout_seconds=timeout_seconds,
            url=url,
            element=element,
            code="MEXICO_CNH_ELEMENT_TIMEOUT",
        )


class MexicoCNHParseError(MexicoCNHError):
    """
    Data parsing errors for Mexico CNH module.

    Raised when parsing operations fail, such as parsing HTML tables,
    Excel files, PDFs, or JSON responses from the SIH dashboard.
    """

    default_code = "MEXICO_CNH_PARSE_ERROR"

    def __init__(
        self,
        message: str,
        data_type: Optional[str] = None,
        source_file: Optional[str] = None,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize parse error.

        Args:
            message: Error description
            data_type: Type of data being parsed (e.g., 'production', 'wells')
            source_file: Source file path if applicable
            code: Error code
            context: Additional context
            cause: Original exception
        """
        context = context or {}
        if data_type:
            context["data_type"] = data_type
        if source_file:
            context["source_file"] = source_file

        super().__init__(message, code, context, cause)
        self.data_type = data_type
        self.source_file = source_file

    @classmethod
    def html_parse_failed(
        cls,
        reason: str = "",
        cause: Optional[Exception] = None,
    ) -> "MexicoCNHParseError":
        """Create error for HTML parsing failure."""
        msg = "Failed to parse Mexico CNH HTML content"
        if reason:
            msg += f": {reason}"
        return cls(
            message=msg,
            data_type="html",
            code="MEXICO_CNH_HTML_PARSE_FAILED",
            cause=cause,
        )

    @classmethod
    def excel_parse_failed(
        cls,
        source_file: str,
        reason: str = "",
        cause: Optional[Exception] = None,
    ) -> "MexicoCNHParseError":
        """Create error for Excel parsing failure."""
        msg = f"Failed to parse Mexico CNH Excel file: {source_file}"
        if reason:
            msg += f" - {reason}"
        return cls(
            message=msg,
            data_type="excel",
            source_file=source_file,
            code="MEXICO_CNH_EXCEL_PARSE_FAILED",
            cause=cause,
        )

    @classmethod
    def pdf_parse_failed(
        cls,
        source_file: str,
        reason: str = "",
        cause: Optional[Exception] = None,
    ) -> "MexicoCNHParseError":
        """Create error for PDF parsing failure."""
        msg = f"Failed to parse Mexico CNH PDF file: {source_file}"
        if reason:
            msg += f" - {reason}"
        return cls(
            message=msg,
            data_type="pdf",
            source_file=source_file,
            code="MEXICO_CNH_PDF_PARSE_FAILED",
            cause=cause,
        )

    @classmethod
    def json_parse_failed(
        cls,
        reason: str = "",
        cause: Optional[Exception] = None,
    ) -> "MexicoCNHParseError":
        """Create error for JSON parsing failure."""
        msg = "Failed to parse Mexico CNH JSON response"
        if reason:
            msg += f": {reason}"
        return cls(
            message=msg,
            data_type="json",
            code="MEXICO_CNH_JSON_PARSE_FAILED",
            cause=cause,
        )

    @classmethod
    def missing_field(
        cls,
        field: str,
        record_type: str = "record",
    ) -> "MexicoCNHParseError":
        """Create error for missing required field."""
        return cls(
            message=f"Required field '{field}' missing from Mexico CNH {record_type}",
            code="MEXICO_CNH_MISSING_FIELD",
            context={"field": field, "record_type": record_type},
        )


class MexicoCNHValidationError(MexicoCNHError):
    """
    Data validation errors for Mexico CNH module.

    Raised when Mexico CNH data fails validation rules such as
    Clave del Pozo format, coordinate bounds, or field name validation.
    Can contain multiple validation errors.
    """

    default_code = "MEXICO_CNH_VALIDATION_ERROR"

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
    def from_errors(cls, errors: List[Dict[str, Any]]) -> "MexicoCNHValidationError":
        """Create validation error from list of error details."""
        error_count = len(errors)
        return cls(
            message=f"Mexico CNH validation failed with {error_count} error(s)",
            errors=errors,
            code="MEXICO_CNH_VALIDATION_FAILED",
        )

    @classmethod
    def invalid_clave_pozo(
        cls, clave_pozo: str, reason: str = ""
    ) -> "MexicoCNHValidationError":
        """Create error for invalid Clave del Pozo (well key) format."""
        msg = f"Invalid Mexico CNH Clave del Pozo: {clave_pozo}"
        if reason:
            msg += f" - {reason}"
        error = cls(
            message=msg,
            code="MEXICO_CNH_INVALID_CLAVE_POZO",
            context={"clave_pozo": clave_pozo},
        )
        error.add_error("clave_pozo", "format", msg, clave_pozo)
        return error

    @classmethod
    def invalid_coordinates(
        cls,
        latitude: float,
        longitude: float,
        reason: str = "",
    ) -> "MexicoCNHValidationError":
        """Create error for invalid Mexican coordinates."""
        msg = f"Coordinates ({latitude}, {longitude}) are outside Mexico bounds"
        if reason:
            msg += f": {reason}"
        error = cls(
            message=msg,
            code="MEXICO_CNH_INVALID_COORDINATES",
            context={"latitude": latitude, "longitude": longitude},
        )
        error.add_error("coordinates", "bounds", msg, f"({latitude}, {longitude})")
        return error


class MexicoCNHConfigurationError(MexicoCNHError):
    """
    Configuration errors for Mexico CNH module.

    Raised when there are issues with module configuration,
    missing required settings, or invalid configuration values.
    """

    default_code = "MEXICO_CNH_CONFIG_ERROR"

    @classmethod
    def missing_setting(cls, setting_name: str) -> "MexicoCNHConfigurationError":
        """Create error for missing required setting."""
        return cls(
            message=f"Required Mexico CNH setting '{setting_name}' is missing",
            code="MEXICO_CNH_CONFIG_MISSING",
            context={"setting": setting_name},
        )

    @classmethod
    def invalid_value(
        cls,
        setting_name: str,
        value: Any,
        reason: str,
    ) -> "MexicoCNHConfigurationError":
        """Create error for invalid setting value."""
        return cls(
            message=f"Invalid value for Mexico CNH setting '{setting_name}': {reason}",
            code="MEXICO_CNH_CONFIG_INVALID",
            context={"setting": setting_name, "value": str(value), "reason": reason},
        )

    @classmethod
    def selenium_not_configured(cls) -> "MexicoCNHConfigurationError":
        """Create error for missing Selenium configuration."""
        return cls(
            message="Selenium WebDriver is not configured for Mexico CNH scraping",
            code="MEXICO_CNH_SELENIUM_NOT_CONFIGURED",
            context={"requirement": "selenium and webdriver must be installed"},
        )


__all__ = [
    "MexicoCNHError",
    "MexicoCNHScraperError",
    "MexicoCNHTimeoutError",
    "MexicoCNHParseError",
    "MexicoCNHValidationError",
    "MexicoCNHConfigurationError",
]
