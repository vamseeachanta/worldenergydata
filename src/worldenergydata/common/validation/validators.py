"""
Validation Functions and Utilities for WorldEnergyData

This module provides standalone validation functions that can be
used independently or in conjunction with the schema classes.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from worldenergydata.common.types import DataFrameLike

# Conditional pandas import
try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


@dataclass
class ValidationResult:
    """
    Container for validation results.

    Attributes:
        is_valid: Whether validation passed
        errors: List of validation error details
        warnings: List of validation warnings
        validated_count: Number of records validated
        failed_count: Number of records that failed validation
    """

    is_valid: bool = True
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    validated_count: int = 0
    failed_count: int = 0

    def add_error(
        self,
        field: str,
        error_type: str,
        message: str,
        value: Any = None,
        row: Optional[int] = None,
    ) -> None:
        """Add a validation error."""
        self.is_valid = False
        error = {
            "field": field,
            "type": error_type,
            "message": message,
        }
        if value is not None:
            error["value"] = str(value)[:100]  # Truncate long values
        if row is not None:
            error["row"] = row
        self.errors.append(error)

    def add_warning(
        self,
        field: str,
        message: str,
        value: Any = None,
        row: Optional[int] = None,
    ) -> None:
        """Add a validation warning."""
        warning = {
            "field": field,
            "message": message,
        }
        if value is not None:
            warning["value"] = str(value)[:100]
        if row is not None:
            warning["row"] = row
        self.warnings.append(warning)

    def merge(self, other: "ValidationResult") -> None:
        """Merge another validation result into this one."""
        if not other.is_valid:
            self.is_valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.validated_count += other.validated_count
        self.failed_count += other.failed_count

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "validated_count": self.validated_count,
            "failed_count": self.failed_count,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors[:50],  # Limit error details
            "warnings": self.warnings[:50],
        }


def validate_api_number(
    api_number: str,
    required_length: Optional[int] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Validate an API well number.

    Args:
        api_number: The API number to validate
        required_length: Expected length (10, 12, or 14). If None, any valid length is accepted.

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        is_valid, error = validate_api_number("608114123400")
        if not is_valid:
            print(f"Invalid API: {error}")
    """
    if not api_number:
        return False, "API number is required"

    # Remove non-digit characters
    cleaned = re.sub(r"\D", "", api_number)

    valid_lengths = {10, 12, 14}
    if len(cleaned) not in valid_lengths:
        return False, f"API number must be 10, 12, or 14 digits, got {len(cleaned)}"

    if required_length and len(cleaned) != required_length:
        return False, f"API number must be {required_length} digits, got {len(cleaned)}"

    # Validate state code (01-90)
    state_code = int(cleaned[:2])
    if state_code < 1 or state_code > 90:
        return False, f"Invalid state code: {state_code}"

    return True, None


def validate_coordinates(
    latitude: float,
    longitude: float,
    strict_ocean: bool = False,
) -> Tuple[bool, Optional[str]]:
    """
    Validate geographic coordinates.

    Args:
        latitude: Latitude in degrees
        longitude: Longitude in degrees
        strict_ocean: If True, validate coordinates are in valid offshore regions

    Returns:
        Tuple of (is_valid, error_message)
    """
    if latitude < -90 or latitude > 90:
        return False, f"Latitude must be between -90 and 90, got {latitude}"

    if longitude < -180 or longitude > 180:
        return False, f"Longitude must be between -180 and 180, got {longitude}"

    if strict_ocean:
        # Basic check for Gulf of Mexico region
        if latitude < 18 or latitude > 32:
            return False, f"Latitude {latitude} is outside expected offshore region"
        if longitude < -98 or longitude > -80:
            return False, f"Longitude {longitude} is outside expected offshore region"

    return True, None


def validate_date_format(
    date_str: str,
    expected_format: str = "%Y%m",
) -> Tuple[bool, Optional[str]]:
    """
    Validate a date string matches the expected format.

    Args:
        date_str: Date string to validate
        expected_format: Expected strptime format

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        parsed = datetime.strptime(date_str, expected_format)

        # Additional sanity checks
        if parsed.year < 1900 or parsed.year > 2100:
            return False, f"Year {parsed.year} is out of reasonable range"

        return True, None
    except ValueError as e:
        return False, f"Invalid date format: {str(e)}"


def validate_production_record(
    record: Dict[str, Any],
    strict: bool = False,
) -> ValidationResult:
    """
    Validate a single production record.

    Args:
        record: Production data record
        strict: If True, apply stricter validation rules

    Returns:
        ValidationResult with any errors
    """
    result = ValidationResult(validated_count=1)

    # Required fields
    required_fields = ["api_well_number", "production_date", "oil_volume", "gas_volume"]
    for field_name in required_fields:
        if field_name not in record or record[field_name] is None:
            result.add_error(
                field_name, "required", f"Field '{field_name}' is required"
            )

    if not result.is_valid:
        result.failed_count = 1
        return result

    # Validate API number
    api = record.get("api_well_number", "")
    is_valid, error = validate_api_number(api, required_length=12)
    if not is_valid:
        result.add_error(
            "api_well_number", "format", error or "Invalid API number", api
        )

    # Validate date
    prod_date = record.get("production_date", "")
    is_valid, error = validate_date_format(str(prod_date), "%Y%m")
    if not is_valid:
        result.add_error(
            "production_date", "format", error or "Invalid date", prod_date
        )

    # Validate volumes
    for vol_field in ["oil_volume", "gas_volume", "water_volume"]:
        if vol_field in record and record[vol_field] is not None:
            try:
                value = float(record[vol_field])
                if value < 0:
                    result.add_error(
                        vol_field, "range", "Volume cannot be negative", value
                    )
                elif strict and value > 10000000:
                    result.add_warning(
                        vol_field, f"Volume {value} seems unusually high", value
                    )
            except (ValueError, TypeError):
                result.add_error(
                    vol_field, "type", "Volume must be numeric", record[vol_field]
                )

    # Validate days on production
    days = record.get("days_on_production")
    if days is not None:
        try:
            days_val = int(days)
            if days_val < 0 or days_val > 31:
                result.add_error(
                    "days_on_production",
                    "range",
                    "Days on production must be 0-31",
                    days,
                )
        except (ValueError, TypeError):
            result.add_error(
                "days_on_production",
                "type",
                "Days on production must be an integer",
                days,
            )

    if not result.is_valid:
        result.failed_count = 1

    return result


def validate_data(
    data: DataFrameLike,
    schema: Type[BaseModel],
    sample_size: Optional[int] = None,
    stop_on_first_error: bool = False,
) -> ValidationResult:
    """
    Validate a DataFrame or list of records against a schema.

    Args:
        data: Data to validate (DataFrame or list of dicts)
        schema: Pydantic schema class to validate against
        sample_size: If provided, only validate a sample of records
        stop_on_first_error: If True, stop after first error

    Returns:
        ValidationResult with all errors

    Example:
        from worldenergydata.common.validation.schemas import ProductionSchema

        result = validate_data(df, ProductionSchema)
        if not result.is_valid:
            print(f"Found {len(result.errors)} errors")
    """
    result = ValidationResult()

    # Convert to list of dicts if DataFrame
    if HAS_PANDAS and isinstance(data, pd.DataFrame):
        records = data.to_dict(orient="records")
    elif isinstance(data, list):
        records = data
    else:
        result.add_error(
            "_data", "type", "Data must be a DataFrame or list of dictionaries"
        )
        return result

    # Sample if requested
    if sample_size and len(records) > sample_size:
        import random

        records = random.sample(records, sample_size)

    # Validate each record
    for i, record in enumerate(records):
        result.validated_count += 1

        try:
            schema.model_validate(record)
        except PydanticValidationError as e:
            result.failed_count += 1

            for error in e.errors():
                field_path = ".".join(str(loc) for loc in error.get("loc", []))
                result.add_error(
                    field=field_path,
                    error_type=error.get("type", "validation"),
                    message=error.get("msg", "Validation failed"),
                    value=record.get(field_path),
                    row=i,
                )

            if stop_on_first_error:
                break

    return result
