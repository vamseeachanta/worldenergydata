"""
Validation Rules for WorldEnergyData

This module provides composable validation rules that can be
combined to create complex validation logic.

Rules can be used standalone or as part of a validation pipeline.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass
class RuleResult:
    """Result of applying a validation rule."""

    is_valid: bool
    error_message: Optional[str] = None
    error_type: str = "validation"

    @classmethod
    def success(cls) -> "RuleResult":
        """Create a successful result."""
        return cls(is_valid=True)

    @classmethod
    def failure(cls, message: str, error_type: str = "validation") -> "RuleResult":
        """Create a failed result."""
        return cls(is_valid=False, error_message=message, error_type=error_type)


class ValidationRule(ABC):
    """
    Base class for validation rules.

    Subclasses implement specific validation logic through the validate method.
    """

    def __init__(
        self,
        field_name: str,
        error_message: Optional[str] = None,
    ):
        """
        Initialize the rule.

        Args:
            field_name: Name of the field this rule applies to
            error_message: Custom error message (optional)
        """
        self.field_name = field_name
        self.custom_error = error_message

    @abstractmethod
    def validate(
        self, value: Any, record: Optional[Dict[str, Any]] = None
    ) -> RuleResult:
        """
        Validate a value against this rule.

        Args:
            value: The value to validate
            record: The full record (for cross-field validation)

        Returns:
            RuleResult indicating success or failure
        """
        pass

    def get_error_message(self, default: str) -> str:
        """Get the error message, using custom message if set."""
        return self.custom_error or default


class RequiredRule(ValidationRule):
    """Rule that validates a field is present and not None/empty."""

    def __init__(
        self,
        field_name: str,
        allow_empty_string: bool = False,
        error_message: Optional[str] = None,
    ):
        super().__init__(field_name, error_message)
        self.allow_empty_string = allow_empty_string

    def validate(
        self, value: Any, record: Optional[Dict[str, Any]] = None
    ) -> RuleResult:
        """Check that value is present and not empty."""
        if value is None:
            return RuleResult.failure(
                self.get_error_message(f"Field '{self.field_name}' is required"),
                "required",
            )

        if (
            not self.allow_empty_string
            and isinstance(value, str)
            and value.strip() == ""
        ):
            return RuleResult.failure(
                self.get_error_message(f"Field '{self.field_name}' cannot be empty"),
                "required",
            )

        return RuleResult.success()


class RangeRule(ValidationRule):
    """Rule that validates a numeric value is within a range."""

    def __init__(
        self,
        field_name: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        inclusive: bool = True,
        error_message: Optional[str] = None,
    ):
        super().__init__(field_name, error_message)
        self.min_value = min_value
        self.max_value = max_value
        self.inclusive = inclusive

    def validate(
        self, value: Any, record: Optional[Dict[str, Any]] = None
    ) -> RuleResult:
        """Check that value is within range."""
        if value is None:
            return RuleResult.success()  # Use RequiredRule for null checks

        try:
            num_value = float(value)
        except (ValueError, TypeError):
            return RuleResult.failure(
                f"Field '{self.field_name}' must be numeric", "type"
            )

        if self.inclusive:
            if self.min_value is not None and num_value < self.min_value:
                return RuleResult.failure(
                    self.get_error_message(
                        f"Field '{self.field_name}' must be >= {self.min_value}"
                    ),
                    "range",
                )
            if self.max_value is not None and num_value > self.max_value:
                return RuleResult.failure(
                    self.get_error_message(
                        f"Field '{self.field_name}' must be <= {self.max_value}"
                    ),
                    "range",
                )
        else:
            if self.min_value is not None and num_value <= self.min_value:
                return RuleResult.failure(
                    self.get_error_message(
                        f"Field '{self.field_name}' must be > {self.min_value}"
                    ),
                    "range",
                )
            if self.max_value is not None and num_value >= self.max_value:
                return RuleResult.failure(
                    self.get_error_message(
                        f"Field '{self.field_name}' must be < {self.max_value}"
                    ),
                    "range",
                )

        return RuleResult.success()


class PatternRule(ValidationRule):
    """Rule that validates a string matches a regex pattern."""

    def __init__(
        self,
        field_name: str,
        pattern: str,
        description: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        super().__init__(field_name, error_message)
        self.pattern = re.compile(pattern)
        self.description = description or pattern

    def validate(
        self, value: Any, record: Optional[Dict[str, Any]] = None
    ) -> RuleResult:
        """Check that value matches pattern."""
        if value is None:
            return RuleResult.success()

        if not isinstance(value, str):
            value = str(value)

        if not self.pattern.match(value):
            return RuleResult.failure(
                self.get_error_message(
                    f"Field '{self.field_name}' must match pattern: {self.description}"
                ),
                "pattern",
            )

        return RuleResult.success()


class EnumRule(ValidationRule):
    """Rule that validates a value is one of allowed values."""

    def __init__(
        self,
        field_name: str,
        allowed_values: Set[Any],
        case_sensitive: bool = True,
        error_message: Optional[str] = None,
    ):
        super().__init__(field_name, error_message)
        self.allowed_values = allowed_values
        self.case_sensitive = case_sensitive

        # Pre-compute lowercase values for case-insensitive comparison
        if not case_sensitive:
            self._lower_values = {
                str(v).lower() for v in allowed_values if v is not None
            }

    def validate(
        self, value: Any, record: Optional[Dict[str, Any]] = None
    ) -> RuleResult:
        """Check that value is in allowed set."""
        if value is None:
            return RuleResult.success()

        if self.case_sensitive:
            if value not in self.allowed_values:
                return RuleResult.failure(
                    self.get_error_message(
                        f"Field '{self.field_name}' must be one of: {sorted(self.allowed_values)}"
                    ),
                    "enum",
                )
        else:
            if str(value).lower() not in self._lower_values:
                return RuleResult.failure(
                    self.get_error_message(
                        f"Field '{self.field_name}' must be one of: {sorted(self.allowed_values)}"
                    ),
                    "enum",
                )

        return RuleResult.success()


class LengthRule(ValidationRule):
    """Rule that validates string length."""

    def __init__(
        self,
        field_name: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        error_message: Optional[str] = None,
    ):
        super().__init__(field_name, error_message)
        self.min_length = min_length
        self.max_length = max_length

    def validate(
        self, value: Any, record: Optional[Dict[str, Any]] = None
    ) -> RuleResult:
        """Check string length."""
        if value is None:
            return RuleResult.success()

        str_value = str(value)
        length = len(str_value)

        if self.min_length is not None and length < self.min_length:
            return RuleResult.failure(
                self.get_error_message(
                    f"Field '{self.field_name}' must be at least {self.min_length} characters"
                ),
                "length",
            )

        if self.max_length is not None and length > self.max_length:
            return RuleResult.failure(
                self.get_error_message(
                    f"Field '{self.field_name}' must be at most {self.max_length} characters"
                ),
                "length",
            )

        return RuleResult.success()


class CrossFieldRule(ValidationRule):
    """
    Rule that validates relationships between multiple fields.

    Use a custom validation function to implement complex cross-field logic.
    """

    def __init__(
        self,
        field_name: str,
        related_fields: List[str],
        validator: Callable[[Dict[str, Any]], bool],
        error_message: str,
    ):
        """
        Initialize cross-field rule.

        Args:
            field_name: Primary field name
            related_fields: List of other fields involved in the validation
            validator: Function that takes the full record and returns True if valid
            error_message: Error message if validation fails
        """
        super().__init__(field_name, error_message)
        self.related_fields = related_fields
        self.validator = validator

    def validate(
        self, value: Any, record: Optional[Dict[str, Any]] = None
    ) -> RuleResult:
        """Validate cross-field relationship."""
        if record is None:
            return RuleResult.success()

        # Check all related fields are present
        all_fields = [self.field_name] + self.related_fields
        for field in all_fields:
            if field not in record:
                # Skip validation if not all fields are present
                return RuleResult.success()

        try:
            if not self.validator(record):
                return RuleResult.failure(
                    self.custom_error or "Cross-field validation failed", "cross_field"
                )
        except Exception as e:
            return RuleResult.failure(f"Validation error: {str(e)}", "cross_field")

        return RuleResult.success()


class CustomRule(ValidationRule):
    """Rule that uses a custom validation function."""

    def __init__(
        self,
        field_name: str,
        validator: Callable[[Any], bool],
        error_message: str,
    ):
        """
        Initialize custom rule.

        Args:
            field_name: Field name
            validator: Function that takes the value and returns True if valid
            error_message: Error message if validation fails
        """
        super().__init__(field_name, error_message)
        self.validator = validator

    def validate(
        self, value: Any, record: Optional[Dict[str, Any]] = None
    ) -> RuleResult:
        """Validate using custom function."""
        if value is None:
            return RuleResult.success()

        try:
            if not self.validator(value):
                return RuleResult.failure(
                    self.custom_error or "Custom validation failed", "custom"
                )
        except Exception as e:
            return RuleResult.failure(f"Validation error: {str(e)}", "custom")

        return RuleResult.success()


# Pre-built rules for common patterns
class CommonRules:
    """Collection of commonly used validation rules."""

    @staticmethod
    def api_number_10(field_name: str = "api_number") -> PatternRule:
        """Rule for 10-digit API numbers."""
        return PatternRule(
            field_name,
            pattern=r"^\d{10}$",
            description="10-digit API number",
        )

    @staticmethod
    def api_number_12(field_name: str = "api_number") -> PatternRule:
        """Rule for 12-digit API numbers."""
        return PatternRule(
            field_name,
            pattern=r"^\d{12}$",
            description="12-digit API number",
        )

    @staticmethod
    def production_date(field_name: str = "production_date") -> PatternRule:
        """Rule for YYYYMM production date format."""
        return PatternRule(
            field_name,
            pattern=r"^\d{6}$",
            description="YYYYMM format",
        )

    @staticmethod
    def positive_number(field_name: str) -> RangeRule:
        """Rule for positive numbers (>= 0)."""
        return RangeRule(field_name, min_value=0)

    @staticmethod
    def percentage(field_name: str) -> RangeRule:
        """Rule for percentage values (0-1)."""
        return RangeRule(field_name, min_value=0, max_value=1)

    @staticmethod
    def latitude(field_name: str = "latitude") -> RangeRule:
        """Rule for latitude values (-90 to 90)."""
        return RangeRule(field_name, min_value=-90, max_value=90)

    @staticmethod
    def longitude(field_name: str = "longitude") -> RangeRule:
        """Rule for longitude values (-180 to 180)."""
        return RangeRule(field_name, min_value=-180, max_value=180)

    @staticmethod
    def days_in_month(field_name: str = "days_on_production") -> RangeRule:
        """Rule for days in a month (0-31)."""
        return RangeRule(field_name, min_value=0, max_value=31)
