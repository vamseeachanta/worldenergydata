# ABOUTME: Custom exception classes for ATSB marine investigation scraper.
# ABOUTME: Provides specialized error types for validation and connection failures.

"""
ATSB Scraper Exception Classes

Custom exceptions for the Australian Transport Safety Bureau scraper.
"""

from typing import Any, Optional

from worldenergydata.modules.marine_safety.exceptions import (
    ScraperError,
    ValidationError,
)


class ATSBDataValidationError(ValidationError):
    """Raised when ATSB data fails validation."""

    def __init__(
        self,
        field: str,
        value: Any,
        reason: str,
        atsb_id: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        """
        Initialize ATSB data validation error.

        Args:
            field: Name of the field that failed validation
            value: The invalid value
            reason: Reason for validation failure
            atsb_id: Optional ATSB investigation ID
            message: Optional custom message
        """
        if message is None:
            id_info = f" (ATSB ID: {atsb_id})" if atsb_id else ""
            message = f"Invalid ATSB data for '{field}'{id_info}: {reason}"
        super().__init__(
            message=message,
            error_code="ATSB_VALIDATION_ERROR",
            details={
                "field": field,
                "value": value,
                "reason": reason,
                "atsb_id": atsb_id,
            },
        )


class ATSBConnectionError(ScraperError):
    """Raised when connection to ATSB website fails."""

    def __init__(
        self,
        message: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize ATSB connection error.

        Args:
            message: Optional custom message
            cause: Optional original exception
        """
        if message is None:
            message = "Failed to connect to ATSB website"
        super().__init__(
            message=message,
            error_code="ATSB_CONNECTION_ERROR",
            details={"cause": str(cause) if cause else None},
            cause=cause,
        )
