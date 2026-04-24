# ABOUTME: Landman module exception classes inheriting from framework base
# ABOUTME: Provides structured error handling for mineral ownership and lease data operations

"""
Landman Module Exception Hierarchy

This module defines exception classes for the Landman data module. All exceptions
inherit from the common exceptions framework to ensure consistent error handling.

Exception Hierarchy:
    LandmanError (from ModuleError)
    |-- LandmanProviderError (provider/data source issues)
    |-- LandmanRecordNotFoundError (record lookup failures)
    |-- LandmanValidationError (data validation failures)
    |-- LandmanAuthError (authentication for subscription services)

Example usage:
    from worldenergydata.landman.errors import LandmanRecordNotFoundError

    try:
        record = search_ownership(legal_description)
    except LandmanRecordNotFoundError as e:
        logger.warning(f"No records found: {e}")
"""

from typing import Any, Dict, List, Optional

from worldenergydata.common.exceptions import ModuleError


class LandmanError(ModuleError):
    """
    Base exception for Landman module operations.

    Attributes:
        message: Human-readable error message
        code: Error code for programmatic handling
        context: Additional context about the error
        cause: Original exception that caused this error
    """

    default_code = "LANDMAN_ERROR"
    module_name = "landman"


class LandmanProviderError(LandmanError):
    """
    Provider/data source errors for Landman module.

    Raised when data providers (county records, commercial services) are
    unavailable, return errors, or have connectivity issues.

    Attributes:
        provider_name: Name of the provider that failed
        status_code: HTTP status code if applicable
    """

    default_code = "LANDMAN_PROVIDER_ERROR"

    def __init__(
        self,
        message: str,
        provider_name: Optional[str] = None,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize provider error.

        Args:
            message: Error message
            provider_name: Name of the provider that failed
            status_code: HTTP status code if applicable
            code: Error code
            context: Additional context
            cause: Original exception
        """
        context = context or {}
        if provider_name:
            context["provider"] = provider_name
        if status_code is not None:
            context["status_code"] = status_code

        super().__init__(message, code, context, cause)
        self.provider_name = provider_name
        self.status_code = status_code

    @classmethod
    def unavailable(
        cls,
        provider_name: str,
        reason: str = "",
        cause: Optional[Exception] = None,
    ) -> "LandmanProviderError":
        """Create error for unavailable provider."""
        msg = f"Landman provider '{provider_name}' is unavailable"
        if reason:
            msg += f": {reason}"
        return cls(
            message=msg,
            provider_name=provider_name,
            code="LANDMAN_PROVIDER_UNAVAILABLE",
            cause=cause,
        )

    @classmethod
    def request_failed(
        cls,
        provider_name: str,
        status_code: int,
        response_body: str = "",
    ) -> "LandmanProviderError":
        """Create error for failed provider request."""
        return cls(
            message=f"Request to provider '{provider_name}' failed with status {status_code}",
            provider_name=provider_name,
            status_code=status_code,
            code="LANDMAN_PROVIDER_REQUEST_FAILED",
            context={"response": response_body[:500] if response_body else None},
        )

    @classmethod
    def timeout(
        cls,
        provider_name: str,
        timeout_seconds: int,
    ) -> "LandmanProviderError":
        """Create error for provider timeout."""
        return cls(
            message=f"Request to provider '{provider_name}' timed out after {timeout_seconds}s",
            provider_name=provider_name,
            code="LANDMAN_PROVIDER_TIMEOUT",
            context={"timeout": timeout_seconds},
        )

    @classmethod
    def rate_limited(
        cls,
        provider_name: str,
        retry_after: Optional[int] = None,
    ) -> "LandmanProviderError":
        """Create error for rate limiting."""
        msg = f"Rate limited by provider '{provider_name}'"
        if retry_after:
            msg += f", retry after {retry_after} seconds"
        return cls(
            message=msg,
            provider_name=provider_name,
            status_code=429,
            code="LANDMAN_PROVIDER_RATE_LIMITED",
            context={"retry_after": retry_after} if retry_after else None,
        )


class LandmanRecordNotFoundError(LandmanError):
    """
    Record not found errors for Landman module.

    Raised when a requested record (ownership, lease, title) cannot be found
    in the data source.

    Attributes:
        record_type: Type of record that was not found
        search_criteria: Criteria used to search for the record
    """

    default_code = "LANDMAN_RECORD_NOT_FOUND"

    def __init__(
        self,
        message: str,
        record_type: Optional[str] = None,
        search_criteria: Optional[Dict[str, Any]] = None,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize record not found error.

        Args:
            message: Error message
            record_type: Type of record (ownership, lease, title)
            search_criteria: Dictionary of search criteria used
            code: Error code
            context: Additional context
            cause: Original exception
        """
        context = context or {}
        if record_type:
            context["record_type"] = record_type
        if search_criteria:
            context["search_criteria"] = search_criteria

        super().__init__(message, code, context, cause)
        self.record_type = record_type
        self.search_criteria = search_criteria or {}

    @classmethod
    def ownership_not_found(
        cls,
        legal_description: str,
        state: Optional[str] = None,
        county: Optional[str] = None,
    ) -> "LandmanRecordNotFoundError":
        """Create error for ownership record not found."""
        search = {"legal_description": legal_description}
        if state:
            search["state"] = state
        if county:
            search["county"] = county
        return cls(
            message=f"No ownership records found for legal description: {legal_description}",
            record_type="ownership",
            search_criteria=search,
            code="LANDMAN_OWNERSHIP_NOT_FOUND",
        )

    @classmethod
    def lease_not_found(
        cls,
        lease_id: Optional[str] = None,
        owner_name: Optional[str] = None,
    ) -> "LandmanRecordNotFoundError":
        """Create error for lease record not found."""
        search = {}
        if lease_id:
            search["lease_id"] = lease_id
        if owner_name:
            search["owner_name"] = owner_name
        msg = "No lease records found"
        if lease_id:
            msg += f" for lease ID: {lease_id}"
        elif owner_name:
            msg += f" for owner: {owner_name}"
        return cls(
            message=msg,
            record_type="lease",
            search_criteria=search,
            code="LANDMAN_LEASE_NOT_FOUND",
        )

    @classmethod
    def title_not_found(
        cls,
        document_number: Optional[str] = None,
        grantor: Optional[str] = None,
    ) -> "LandmanRecordNotFoundError":
        """Create error for title record not found."""
        search = {}
        if document_number:
            search["document_number"] = document_number
        if grantor:
            search["grantor"] = grantor
        msg = "No title records found"
        if document_number:
            msg += f" for document: {document_number}"
        elif grantor:
            msg += f" for grantor: {grantor}"
        return cls(
            message=msg,
            record_type="title",
            search_criteria=search,
            code="LANDMAN_TITLE_NOT_FOUND",
        )


class LandmanValidationError(LandmanError):
    """
    Data validation errors for Landman module.

    Raised when landman data fails validation rules, such as invalid
    legal descriptions, owner names, or interest percentages.
    """

    default_code = "LANDMAN_VALIDATION_ERROR"

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
    def from_errors(cls, errors: List[Dict[str, Any]]) -> "LandmanValidationError":
        """Create validation error from list of error details."""
        error_count = len(errors)
        return cls(
            message=f"Landman validation failed with {error_count} error(s)",
            errors=errors,
            code="LANDMAN_VALIDATION_FAILED",
        )

    @classmethod
    def invalid_legal_description(
        cls, legal_description: str, reason: str = ""
    ) -> "LandmanValidationError":
        """Create error for invalid legal description format."""
        msg = f"Invalid legal description: {legal_description}"
        if reason:
            msg += f" - {reason}"
        error = cls(
            message=msg,
            code="LANDMAN_INVALID_LEGAL_DESC",
            context={"legal_description": legal_description},
        )
        error.add_error("legal_description", "format", msg, legal_description)
        return error

    @classmethod
    def invalid_interest_percentage(cls, percentage: float) -> "LandmanValidationError":
        """Create error for invalid mineral interest percentage."""
        msg = f"Invalid mineral interest percentage: {percentage}. Must be between 0 and 100."
        error = cls(
            message=msg,
            code="LANDMAN_INVALID_INTEREST",
            context={"percentage": percentage},
        )
        error.add_error("mineral_interest", "range", msg, percentage)
        return error

    @classmethod
    def invalid_state_code(cls, state_code: str) -> "LandmanValidationError":
        """Create error for invalid state code."""
        msg = (
            f"Invalid state code: {state_code}. Must be a valid 2-letter US state code."
        )
        error = cls(
            message=msg,
            code="LANDMAN_INVALID_STATE",
            context={"state_code": state_code},
        )
        error.add_error("state", "format", msg, state_code)
        return error


class LandmanAuthError(LandmanError):
    """
    Authentication errors for Landman module subscription services.

    Raised when authentication fails for commercial title services or
    subscription-based data providers.

    Attributes:
        provider_name: Name of the provider requiring authentication
    """

    default_code = "LANDMAN_AUTH_ERROR"

    def __init__(
        self,
        message: str,
        provider_name: Optional[str] = None,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize authentication error.

        Args:
            message: Error message
            provider_name: Name of the provider requiring auth
            code: Error code
            context: Additional context
            cause: Original exception
        """
        context = context or {}
        if provider_name:
            context["provider"] = provider_name

        super().__init__(message, code, context, cause)
        self.provider_name = provider_name

    @classmethod
    def invalid_credentials(cls, provider_name: str) -> "LandmanAuthError":
        """Create error for invalid credentials."""
        return cls(
            message=f"Invalid credentials for provider '{provider_name}'",
            provider_name=provider_name,
            code="LANDMAN_AUTH_INVALID_CREDENTIALS",
        )

    @classmethod
    def expired_token(cls, provider_name: str) -> "LandmanAuthError":
        """Create error for expired authentication token."""
        return cls(
            message=f"Authentication token expired for provider '{provider_name}'",
            provider_name=provider_name,
            code="LANDMAN_AUTH_TOKEN_EXPIRED",
        )

    @classmethod
    def subscription_required(cls, provider_name: str) -> "LandmanAuthError":
        """Create error when subscription is required."""
        return cls(
            message=f"Active subscription required for provider '{provider_name}'",
            provider_name=provider_name,
            code="LANDMAN_AUTH_SUBSCRIPTION_REQUIRED",
        )

    @classmethod
    def insufficient_permissions(
        cls, provider_name: str, required_permission: str
    ) -> "LandmanAuthError":
        """Create error for insufficient permissions."""
        return cls(
            message=f"Insufficient permissions for '{provider_name}': requires {required_permission}",  # noqa: E501
            provider_name=provider_name,
            code="LANDMAN_AUTH_INSUFFICIENT_PERMISSIONS",
            context={"required_permission": required_permission},
        )


__all__ = [
    "LandmanError",
    "LandmanProviderError",
    "LandmanRecordNotFoundError",
    "LandmanValidationError",
    "LandmanAuthError",
]
