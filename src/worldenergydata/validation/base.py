"""
Base classes for the validation framework.

This module provides the foundation classes that all validators inherit from,
including result handling, field validation, and schema validation capabilities.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .schemas import FieldSchema


@dataclass
class ValidationError:
    """Represents a single validation error."""

    field: str
    message: str
    value: Any = None
    rule: str = None
    severity: str = "error"  # 'error', 'warning', 'info'
    row_index: Optional[int] = None

    def __str__(self) -> str:
        location = f" at row {self.row_index}" if self.row_index is not None else ""
        return f"{self.severity.upper()}: {self.field}{location}: {self.message}"


@dataclass
class ValidationResult:
    """
    Container for validation results with detailed error reporting.

    This class aggregates all validation errors and provides methods
    for analyzing and reporting validation outcomes.
    """

    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    info: List[ValidationError] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """Returns True if there are no errors (warnings are allowed)."""
        return len(self.errors) == 0

    @property
    def has_warnings(self) -> bool:
        """Returns True if there are warnings."""
        return len(self.warnings) > 0

    @property
    def total_issues(self) -> int:
        """Returns total count of all issues (errors + warnings + info)."""
        return len(self.errors) + len(self.warnings) + len(self.info)

    def add_error(
        self,
        field: str,
        message: str,
        value: Any = None,
        rule: str = None,
        row_index: Optional[int] = None,
    ):
        """Add a validation error."""
        self.errors.append(
            ValidationError(
                field=field,
                message=message,
                value=value,
                rule=rule,
                severity="error",
                row_index=row_index,
            )
        )

    def add_warning(
        self,
        field: str,
        message: str,
        value: Any = None,
        rule: str = None,
        row_index: Optional[int] = None,
    ):
        """Add a validation warning."""
        self.warnings.append(
            ValidationError(
                field=field,
                message=message,
                value=value,
                rule=rule,
                severity="warning",
                row_index=row_index,
            )
        )

    def add_info(
        self,
        field: str,
        message: str,
        value: Any = None,
        rule: str = None,
        row_index: Optional[int] = None,
    ):
        """Add validation info."""
        self.info.append(
            ValidationError(
                field=field,
                message=message,
                value=value,
                rule=rule,
                severity="info",
                row_index=row_index,
            )
        )

    def get_errors_by_field(self, field: str) -> List[ValidationError]:
        """Get all errors for a specific field."""
        return [e for e in self.errors if e.field == field]

    def get_errors_by_severity(self, severity: str) -> List[ValidationError]:
        """Get all issues of a specific severity level."""
        return {
            "error": self.errors,
            "warning": self.warnings,
            "info": self.info,
        }.get(severity, [])

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Merge another validation result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.info.extend(other.info)
        self.metadata.update(other.metadata)
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary format."""
        return {
            "is_valid": self.is_valid,
            "total_errors": len(self.errors),
            "total_warnings": len(self.warnings),
            "total_info": len(self.info),
            "errors": [
                {
                    "field": e.field,
                    "message": e.message,
                    "value": str(e.value) if e.value is not None else None,
                    "rule": e.rule,
                    "row_index": e.row_index,
                }
                for e in self.errors
            ],
            "warnings": [
                {
                    "field": w.field,
                    "message": w.message,
                    "value": str(w.value) if w.value is not None else None,
                    "rule": w.rule,
                    "row_index": w.row_index,
                }
                for w in self.warnings
            ],
            "metadata": self.metadata,
        }

    def get_summary(self) -> str:
        """Get a human-readable summary of validation results."""
        if self.is_valid:
            summary = "✅ Validation PASSED"
        else:
            summary = "❌ Validation FAILED"

        summary += f"\n  Errors: {len(self.errors)}"
        summary += f"\n  Warnings: {len(self.warnings)}"
        summary += f"\n  Info: {len(self.info)}"

        if self.metadata:
            summary += f"\n  Metadata: {self.metadata}"

        return summary


class BaseValidator(ABC):
    """
    Abstract base class for all validators.

    This class provides the common interface and functionality
    that all validators must implement.
    """

    def __init__(self, name: Optional[str] = None):
        self.name = name or self.__class__.__name__
        self.rules = []

    @abstractmethod
    def validate(self, data: Any) -> ValidationResult:
        """
        Validate the provided data.

        Args:
            data: The data to validate (DataFrame, dict, etc.)

        Returns:
            ValidationResult containing validation outcome
        """
        pass

    def add_rule(self, rule: "ValidationRule") -> "BaseValidator":
        """Add a validation rule to this validator."""
        self.rules.append(rule)
        return self

    def _create_result(self) -> ValidationResult:
        """Create a new validation result with metadata."""
        result = ValidationResult()
        result.metadata["validator"] = self.name
        result.metadata["timestamp"] = datetime.now().isoformat()
        return result


class FieldValidator(BaseValidator):
    """
    Validator for individual fields within a dataset.

    This validator applies rules to specific fields and can handle
    both single values and series of values.
    """

    def __init__(self, field_name: str, name: Optional[str] = None):
        super().__init__(name)
        self.field_name = field_name

    def validate(self, data: Any) -> ValidationResult:
        """
        Validate a specific field in the data.

        Args:
            data: Data containing the field to validate

        Returns:
            ValidationResult for the field
        """
        result = self._create_result()
        result.metadata["field_name"] = self.field_name

        # Extract field data based on input type
        field_data = self._extract_field_data(data)
        if field_data is None:
            result.add_error(
                self.field_name,
                f"Field '{self.field_name}' not found in data",
                rule="field_existence",
            )
            return result

        # Apply all rules to the field
        for rule in self.rules:
            try:
                rule_result = rule.validate(field_data, self.field_name)
                result.merge(rule_result)
            except Exception as e:
                logger.error(
                    f"Error applying rule {rule.__class__.__name__} to field {self.field_name}: {e}"
                )
                result.add_error(
                    self.field_name,
                    f"Rule validation failed: {str(e)}",
                    rule=rule.__class__.__name__,
                )

        return result

    def _extract_field_data(self, data: Any) -> Any:
        """Extract field data from various input formats."""
        if isinstance(data, pd.DataFrame):
            if self.field_name in data.columns:
                return data[self.field_name]
        elif isinstance(data, dict):
            return data.get(self.field_name)
        elif isinstance(data, pd.Series) and data.name == self.field_name:
            return data

        return None


class SchemaValidator(BaseValidator):
    """
    Validator that applies a complete schema to validate datasets.

    This validator coordinates multiple field validators and cross-field
    validations to ensure complete data integrity.
    """

    def __init__(self, schema: "ValidationSchema", name: Optional[str] = None):
        super().__init__(name)
        self.schema = schema

    def validate(self, data: Any) -> ValidationResult:
        """
        Validate data against the complete schema.

        Args:
            data: The dataset to validate

        Returns:
            ValidationResult for the entire dataset
        """
        result = self._create_result()
        result.metadata["schema"] = self.schema.name

        try:
            # Apply schema validation
            schema_result = self.schema.validate(data)
            result.merge(schema_result)

            # Apply any additional rules from this validator
            for rule in self.rules:
                try:
                    rule_result = rule.validate(data, "dataset")
                    result.merge(rule_result)
                except Exception as e:
                    logger.error(
                        f"Error applying schema rule {rule.__class__.__name__}: {e}"
                    )
                    result.add_error(
                        "schema",
                        f"Schema rule validation failed: {str(e)}",
                        rule=rule.__class__.__name__,
                    )

        except Exception as e:
            logger.error(f"Error during schema validation: {e}")
            result.add_error(
                "schema",
                f"Schema validation failed: {str(e)}",
                rule="schema_validation",
            )

        return result


class ValidationRule(ABC):
    """
    Abstract base class for validation rules.

    Rules define specific validation logic that can be applied
    to fields or entire datasets.
    """

    def __init__(self, name: Optional[str] = None):
        self.name = name or self.__class__.__name__

    @abstractmethod
    def validate(self, data: Any, field_name: str = None) -> ValidationResult:
        """
        Apply the validation rule to the data.

        Args:
            data: The data to validate
            field_name: Optional field name for context

        Returns:
            ValidationResult for this rule
        """
        pass


class ValidationSchema(ABC):
    """
    Abstract base class for validation schemas.

    Schemas define the complete structure and validation requirements
    for specific data types (e.g., BSEE production data, well data).
    """

    def __init__(self, name: str):
        self.name = name
        self.field_validators: Dict[str, FieldValidator] = {}
        self.cross_field_rules: List[ValidationRule] = []
        self.metadata_rules: List[ValidationRule] = []
        self.fields: Dict[str, "FieldSchema"] = {}

    @abstractmethod
    def validate(self, data: Any) -> ValidationResult:
        """
        Validate data against this schema.

        Args:
            data: The data to validate

        Returns:
            ValidationResult for the schema
        """
        pass

    def add_field_validator(
        self, field_name: str, validator: FieldValidator
    ) -> "ValidationSchema":
        """Add a field validator to the schema."""
        self.field_validators[field_name] = validator
        return self

    def add_cross_field_rule(self, rule: ValidationRule) -> "ValidationSchema":
        """Add a cross-field validation rule."""
        self.cross_field_rules.append(rule)
        return self

    def add_metadata_rule(self, rule: ValidationRule) -> "ValidationSchema":
        """Add a metadata validation rule."""
        self.metadata_rules.append(rule)
        return self

    def add_field(self, field_schema: "FieldSchema") -> "ValidationSchema":
        """Add a field schema to the validation schema."""
        self.fields[field_schema.name] = field_schema
        return self
