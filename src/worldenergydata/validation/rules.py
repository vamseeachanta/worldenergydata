"""
Validation rules engine for energy data.
"""

import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

import pandas as pd

from .base import ValidationResult
from .exceptions import (
    ConsistencyError,
    CrossFieldValidationError,
    DataTypeError,
    DateFormatError,
    RangeValidationError,
    RequiredFieldError,
    ValidationError,
)
from .schema import DataType, DateFormat


class ValidationRules:
    """Core validation rules for data quality checks."""

    @staticmethod
    def validate_required(value: Any, field_name: str, required: bool) -> bool:
        """Validate required field."""
        if required and (value is None or value == ""):
            raise RequiredFieldError("Required field is missing", field=field_name)
        return True

    @staticmethod
    def validate_data_type(value: Any, field_name: str, data_type: DataType) -> bool:
        """Validate data type."""
        if value is None:
            return True  # Null handling is done separately

        type_validators = {
            DataType.STRING.value: lambda v: isinstance(v, str),
            DataType.INTEGER.value: lambda v: isinstance(v, int)
            or (isinstance(v, str) and v.isdigit()),
            DataType.FLOAT.value: lambda v: isinstance(v, (int, float))
            or ValidationRules._is_numeric_string(v),
            DataType.DECIMAL.value: lambda v: isinstance(v, (int, float))
            or ValidationRules._is_numeric_string(v),
            DataType.BOOLEAN.value: lambda v: isinstance(v, bool)
            or v in ["true", "false", "True", "False", "0", "1"],
            DataType.DATE.value: lambda v: ValidationRules._is_date_string(v),
            DataType.DATETIME.value: lambda v: ValidationRules._is_datetime_string(v),
            DataType.ARRAY.value: lambda v: isinstance(v, (list, tuple)),
            DataType.OBJECT.value: lambda v: isinstance(v, dict),
        }

        validator = type_validators.get(data_type.value)

        if validator and not validator(value):
            raise DataTypeError(
                "Invalid data type",
                field=field_name,
                value=value,
                rule=f"Expected {data_type.value}",
            )

        return True

    @staticmethod
    def validate_range(
        value: Any,
        field_name: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> bool:
        """Validate numeric range."""
        if value is None:
            return True

        numeric_value = ValidationRules._to_numeric(value)
        if numeric_value is None:
            return True

        if min_value is not None and numeric_value < min_value:
            raise RangeValidationError(
                "Value below minimum",
                field=field_name,
                value=numeric_value,
                rule=f"Minimum: {min_value}",
            )

        if max_value is not None and numeric_value > max_value:
            raise RangeValidationError(
                "Value above maximum",
                field=field_name,
                value=numeric_value,
                rule=f"Maximum: {max_value}",
            )

        return True

    @staticmethod
    def validate_length(
        value: Any,
        field_name: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
    ) -> bool:
        """Validate string length."""
        if value is None:
            return True

        if not isinstance(value, str):
            value = str(value)

        length = len(value)

        if min_length is not None and length < min_length:
            raise ValidationError(
                "String too short",
                field=field_name,
                value=value,
                rule=f"Minimum length: {min_length}",
            )

        if max_length is not None and length > max_length:
            raise ValidationError(
                "String too long",
                field=field_name,
                value=value,
                rule=f"Maximum length: {max_length}",
            )

        return True

    @staticmethod
    def validate_pattern(value: Any, field_name: str, pattern: Optional[str]) -> bool:
        """Validate against regex pattern."""
        if pattern is None or value is None:
            return True

        if not isinstance(value, str):
            value = str(value)

        if not re.match(pattern, value):
            raise ValidationError(
                "Pattern mismatch",
                field=field_name,
                value=value,
                rule=f"Pattern: {pattern}",
            )

        return True

    @staticmethod
    def validate_allowed_values(
        value: Any, field_name: str, allowed_values: Optional[List[Any]]
    ) -> bool:
        """Validate against allowed values list."""
        if allowed_values is None or value is None:
            return True

        if value not in allowed_values:
            raise ValidationError(
                "Value not in allowed list",
                field=field_name,
                value=value,
                rule=f"Allowed: {allowed_values}",
            )

        return True

    @staticmethod
    def validate_date_format(
        value: Any, field_name: str, date_format: Optional[DateFormat]
    ) -> bool:
        """Validate date format."""
        if date_format is None or value is None:
            return True

        if not isinstance(value, str):
            value = str(value)

        format_patterns = {
            DateFormat.YYYYMM: r"^\d{6}$",
            DateFormat.YYYY_MM_DD: r"^\d{4}-\d{2}-\d{2}$",
            DateFormat.MM_DD_YYYY: r"^\d{2}/\d{2}/\d{4}$",
            DateFormat.DD_MM_YYYY: r"^\d{2}/\d{2}/\d{4}$",
            DateFormat.YYYYMMDD: r"^\d{8}$",
            DateFormat.ISO8601: r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
        }

        pattern = format_patterns.get(date_format)
        if pattern and not re.match(pattern, value):
            raise DateFormatError(
                "Invalid date format",
                field=field_name,
                value=value,
                rule=f"Expected format: {date_format.value}",
            )

        # Additional validation for actual date values
        if date_format == DateFormat.YYYYMM:
            year = int(value[:4])
            month = int(value[4:6])
            if not (1900 <= year <= 2100) or not (1 <= month <= 12):
                raise DateFormatError(
                    "Invalid date values",
                    field=field_name,
                    value=value,
                    rule="Valid year (1900-2100) and month (1-12)",
                )

        return True

    @staticmethod
    def _is_numeric_string(value: str) -> bool:
        """Check if string represents a number."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _to_numeric(value: Any) -> Optional[float]:
        """Convert value to numeric."""
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _is_date_string(value: Any) -> bool:
        """Check if value is a valid date string."""
        if not isinstance(value, str):
            return False

        # Try common date patterns
        patterns = [
            r"^\d{4}-\d{2}-\d{2}$",  # YYYY-MM-DD
            r"^\d{2}/\d{2}/\d{4}$",  # MM/DD/YYYY or DD/MM/YYYY
            r"^\d{6}$",  # YYYYMM
            r"^\d{8}$",  # YYYYMMDD
        ]

        return any(re.match(pattern, value) for pattern in patterns)

    @staticmethod
    def _is_datetime_string(value: Any) -> bool:
        """Check if value is a valid datetime string."""
        if not isinstance(value, str):
            return False

        # Try common datetime patterns
        patterns = [
            r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$",  # YYYY-MM-DD HH:MM:SS
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",  # ISO 8601
        ]

        return any(re.match(pattern, value) for pattern in patterns)


class CrossFieldRules:
    """Cross-field validation rules."""

    @staticmethod
    def validate_date_consistency(
        data: Dict[str, Any], start_field: str, end_field: str
    ) -> bool:
        """Validate that end date is after start date."""
        start_date = data.get(start_field)
        end_date = data.get(end_field)

        if start_date is None or end_date is None:
            return True  # Skip if either is missing

        # Convert to comparable format
        try:
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date.replace("/", "-"))
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date.replace("/", "-"))

            if end_date < start_date:
                raise CrossFieldValidationError(
                    "End date must be after start date",
                    fields=[start_field, end_field],
                    rule="date_consistency",
                )
        except (ValueError, TypeError):
            # Skip validation if dates can't be parsed
            pass

        return True

    @staticmethod
    def validate_production_consistency(data: Dict[str, Any]) -> bool:
        """Validate production data consistency."""
        days_on_prod = data.get("DAYS_ON_PROD", 0)
        oil_prod = data.get("MON_O_PROD_VOL", 0)
        gas_prod = data.get("MON_G_PROD_VOL", 0)

        # Convert to numeric
        try:
            days_on_prod = float(days_on_prod) if days_on_prod is not None else 0
            oil_prod = float(oil_prod) if oil_prod is not None else 0
            gas_prod = float(gas_prod) if gas_prod is not None else 0
        except (ValueError, TypeError):
            return True  # Skip validation if conversion fails

        # If no production days, volumes should be zero
        if days_on_prod == 0 and (oil_prod > 0 or gas_prod > 0):
            raise ConsistencyError(
                "Production volumes should be zero when days on production is zero",
                field="DAYS_ON_PROD",
                rule="production_consistency",
            )

        # If there are production days, at least one volume should be non-zero
        if days_on_prod > 0 and oil_prod == 0 and gas_prod == 0:
            # This is a warning, not necessarily an error
            pass  # Could log warning here

        return True

    @staticmethod
    def validate_sum_consistency(
        data: Dict[str, Any],
        component_fields: List[str],
        total_field: str,
        tolerance: float = 0.01,
    ) -> bool:
        """Validate that component fields sum to total field."""
        components = []
        for field in component_fields:
            value = data.get(field, 0)
            try:
                components.append(float(value) if value is not None else 0)
            except (ValueError, TypeError):
                return True  # Skip validation if conversion fails

        total = data.get(total_field, 0)
        try:
            total = float(total) if total is not None else 0
        except (ValueError, TypeError):
            return True

        calculated_total = sum(components)

        if abs(calculated_total - total) > tolerance:
            raise ConsistencyError(
                f"Sum of components ({calculated_total}) does not match total ({total})",
                field=total_field,
                rule="sum_consistency",
            )

        return True

    @staticmethod
    def validate_percentage_sum(
        data: Dict[str, Any], percentage_fields: List[str], tolerance: float = 0.01
    ) -> bool:
        """Validate that percentage fields sum to 100."""
        percentages = []
        for field in percentage_fields:
            value = data.get(field, 0)
            try:
                percentages.append(float(value) if value is not None else 0)
            except (ValueError, TypeError):
                return True  # Skip validation if conversion fails

        total_percentage = sum(percentages)

        if abs(total_percentage - 100.0) > tolerance:
            raise ConsistencyError(
                f"Percentages sum to {total_percentage}, expected 100",
                rule="percentage_sum",
            )

        return True


class CustomValidators:
    """Custom validators for specific business rules."""

    @staticmethod
    def validate_api_well_number(value: str) -> bool:
        """Validate API well number format."""
        if not value:
            return True

        # API well number should be 12 digits
        if not re.match(r"^\d{12}$", value):
            raise ValidationError(
                "Invalid API well number format",
                value=value,
                rule="12-digit API number",
            )

        # Additional checks could include state/county codes
        state_code = value[:2]
        if state_code not in [
            "17",
            "22",
            "48",
        ]:  # Example: Louisiana, Texas offshore codes
            # This could be a warning rather than error
            pass

        return True

    @staticmethod
    def validate_lease_number(value: str) -> bool:
        """Validate BSEE lease number format."""
        if not value:
            return True

        # Lease numbers are typically alphanumeric
        if not re.match(r"^[A-Z0-9]+$", value):
            raise ValidationError(
                "Invalid lease number format",
                value=value,
                rule="Alphanumeric lease number",
            )

        return True

    @staticmethod
    def validate_production_date(value: str) -> bool:
        """Validate BSEE production date format (YYYYMM)."""
        if not value:
            return True

        if not re.match(r"^\d{6}$", value):
            raise DateFormatError(
                "Invalid production date format",
                value=value,
                rule="YYYYMM format required",
            )

        year = int(value[:4])
        month = int(value[4:6])

        current_year = datetime.now().year
        if not (1900 <= year <= current_year + 1):
            raise DateFormatError(
                "Invalid year in production date",
                value=value,
                rule=f"Year must be between 1900 and {current_year + 1}",
            )

        if not (1 <= month <= 12):
            raise DateFormatError(
                "Invalid month in production date",
                value=value,
                rule="Month must be between 1 and 12",
            )

        return True


# ============================================================================
# WRAPPER RULE CLASSES - TDD Step 3 Implementation
# These classes wrap the static validation methods to provide instantiable
# rule objects that can be added to field validators.
# ============================================================================


class APINumberRule:
    """Wrapper for API well number validation."""

    def validate(self, data: pd.Series) -> ValidationResult:
        """Validate API well numbers in a pandas Series."""
        result = ValidationResult()
        for idx, value in data.items():
            try:
                CustomValidators.validate_api_well_number(
                    str(value) if pd.notna(value) else ""
                )
            except ValidationError as e:
                result.add_error(str(idx), str(e), rule="api_number")
        return result


class DataTypeRule:
    """Wrapper for data type validation."""

    def __init__(self, allowed_types: Union[type, List[type]], allow_null: bool = True):
        """Initialize with allowed type(s)."""
        self.allowed_types = (
            allowed_types
            if isinstance(allowed_types, (list, tuple))
            else [allowed_types]
        )
        self.allow_null = allow_null

    def validate(self, data: pd.Series) -> ValidationResult:
        """Validate data types in a pandas Series."""
        result = ValidationResult()
        for idx, value in data.items():
            if pd.isna(value):
                if not self.allow_null:
                    result.add_error(
                        str(idx), "Null value not allowed", rule="data_type"
                    )
            elif not isinstance(value, tuple(self.allowed_types)):
                result.add_error(
                    str(idx), f"Invalid type: {type(value)}", rule="data_type"
                )
        return result


class DateFormatRule:
    """Wrapper for date format validation."""

    def __init__(
        self,
        formats: List[str],
        min_date: Optional[datetime] = None,
        max_date: Optional[datetime] = None,
    ):
        """Initialize with allowed date formats and optional bounds."""
        self.formats = formats
        self.min_date = min_date
        self.max_date = max_date

    def validate(self, data: pd.Series) -> ValidationResult:
        """Validate date formats in a pandas Series."""
        result = ValidationResult()
        for idx, value in data.items():
            self._validate_single_value(idx, value, result)
        return result

    def _validate_single_value(
        self, idx: Any, value: Any, result: ValidationResult
    ) -> None:
        """Validate a single date value and add errors to result."""
        if self._is_empty_value(value):
            return

        parsed_date = self._try_parse_date(value)
        if parsed_date is None:
            result.add_error(
                str(idx),
                self._format_parse_error(value),
                rule="date_format",
            )
            return

        self._validate_date_bounds(idx, parsed_date, result)

    def _is_empty_value(self, value: Any) -> bool:
        """Check if value is empty or null."""
        return pd.isna(value)

    def _try_parse_date(self, value: Any) -> Optional[datetime]:
        """Attempt to parse value with configured formats."""
        str_value = str(value)
        for fmt in self.formats:
            parsed = self._try_single_format(str_value, fmt)
            if parsed is not None:
                return parsed
        return None

    def _try_single_format(self, value: str, fmt: str) -> Optional[datetime]:
        """Try to parse a date string with a single format."""
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            return None

    def _validate_date_bounds(
        self, idx: Any, parsed_date: datetime, result: ValidationResult
    ) -> None:
        """Check if parsed date is within configured bounds."""
        if self.min_date and parsed_date < self.min_date:
            result.add_error(
                str(idx),
                self._format_min_date_error(),
                rule="date_format",
            )

        if self.max_date and parsed_date > self.max_date:
            result.add_error(
                str(idx),
                self._format_max_date_error(),
                rule="date_format",
            )

    def _format_parse_error(self, value: Any) -> str:
        """Build error message for unparseable date."""
        return f"Could not parse date: {value}"

    def _format_min_date_error(self) -> str:
        """Build error message for date below minimum."""
        return f"Date before minimum: {self.min_date}"

    def _format_max_date_error(self) -> str:
        """Build error message for date above maximum."""
        return f"Date after maximum: {self.max_date}"


class RangeRule:
    """Wrapper for numeric range validation."""

    def __init__(
        self, min_value: Optional[float] = None, max_value: Optional[float] = None
    ):
        """Initialize with optional min and max values."""
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, data: pd.Series) -> ValidationResult:
        """Validate numeric ranges in a pandas Series."""
        result = ValidationResult()
        for idx, value in data.items():
            if pd.isna(value):
                continue

            try:
                numeric_value = float(value)
            except (ValueError, TypeError):
                result.add_error(
                    str(idx), f"Could not convert to number: {value}", rule="range"
                )
                continue

            if self.min_value is not None and numeric_value < self.min_value:
                result.add_error(
                    str(idx), f"Value below minimum: {self.min_value}", rule="range"
                )
            if self.max_value is not None and numeric_value > self.max_value:
                result.add_error(
                    str(idx), f"Value above maximum: {self.max_value}", rule="range"
                )

        return result


class PatternRule:
    """Wrapper for regex pattern validation."""

    def __init__(self, pattern: str, message: str = ""):
        """Initialize with regex pattern and optional error message."""
        self.pattern = pattern
        self.message = message

    def validate(self, data: pd.Series) -> ValidationResult:
        """Validate regex patterns in a pandas Series."""
        result = ValidationResult()
        for idx, value in data.items():
            if pd.isna(value):
                continue

            if not re.match(self.pattern, str(value)):
                error_msg = (
                    self.message or f"Value does not match pattern: {self.pattern}"
                )
                result.add_error(str(idx), error_msg, rule="pattern")

        return result


class UniqueRule:
    """Wrapper for field uniqueness validation."""

    def validate(self, data: pd.Series) -> ValidationResult:
        """Validate that values are unique in a pandas Series."""
        result = ValidationResult()
        duplicates = data[data.duplicated(keep=False)]

        for idx, value in duplicates.items():
            result.add_error(str(idx), f"Duplicate value found: {value}", rule="unique")

        return result


class RequiredFieldRule:
    """Wrapper for required field validation."""

    def __init__(self, required_fields: List[str]):
        """Initialize with list of required field names."""
        self.required_fields = required_fields

    def validate(self, data: pd.DataFrame) -> ValidationResult:
        """Validate that required fields exist in a DataFrame."""
        result = ValidationResult()

        for field in self.required_fields:
            if field not in data.columns:
                result.add_error(
                    field, f"Required field missing: {field}", rule="required_field"
                )
            else:
                # Check for missing values in required field
                missing_count = data[field].isna().sum()
                if missing_count > 0:
                    result.add_error(
                        field,
                        f"Required field has {missing_count} missing values",
                        rule="required_field",
                    )

        return result


class CrossFieldRule:
    """Wrapper for cross-field validation."""

    def __init__(
        self,
        validation_func: Callable[[pd.DataFrame], List[str]],
        dependent_fields: List[str],
    ):
        """Initialize with validation function and list of dependent fields."""
        self.validation_func = validation_func
        self.dependent_fields = dependent_fields

    def validate(self, data: pd.DataFrame) -> ValidationResult:
        """Execute custom cross-field validation function."""
        result = ValidationResult()

        # Call validation function
        errors = self.validation_func(data)

        # Add errors to result
        for error_msg in errors:
            result.add_error("cross_field", error_msg, rule="cross_field")

        return result
