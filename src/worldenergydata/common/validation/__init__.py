"""
Validation Schemas and Utilities for WorldEnergyData

This module provides reusable validation schemas and utilities for
validating energy data across all modules.

Available Schemas:
    - APINumberSchema: Validates API well numbers
    - ProductionSchema: Validates production data records
    - CoordinateSchema: Validates geographic coordinates
    - DateRangeSchema: Validates date ranges

Example usage:
    from worldenergydata.common.validation import APINumberSchema, validate_data

    # Validate a single value
    result = APINumberSchema.validate("608114123400")

    # Validate a DataFrame
    errors = validate_data(df, ProductionSchema)
"""

from worldenergydata.common.validation.schemas import (
    APINumberSchema,
    ProductionSchema,
    CoordinateSchema,
    DateRangeSchema,
    LeaseSchema,
    WellSchema,
    FinancialSchema,
)
from worldenergydata.common.validation.validators import (
    validate_api_number,
    validate_coordinates,
    validate_date_format,
    validate_production_record,
    validate_data,
    ValidationResult,
)
from worldenergydata.common.validation.rules import (
    ValidationRule,
    RequiredRule,
    RangeRule,
    PatternRule,
    EnumRule,
    CrossFieldRule,
)

__all__ = [
    # Schemas
    "APINumberSchema",
    "ProductionSchema",
    "CoordinateSchema",
    "DateRangeSchema",
    "LeaseSchema",
    "WellSchema",
    "FinancialSchema",
    # Validators
    "validate_api_number",
    "validate_coordinates",
    "validate_date_format",
    "validate_production_record",
    "validate_data",
    "ValidationResult",
    # Rules
    "ValidationRule",
    "RequiredRule",
    "RangeRule",
    "PatternRule",
    "EnumRule",
    "CrossFieldRule",
]
