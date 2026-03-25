"""
Validation schemas for different types of energy data.

This module contains schema definitions that specify the validation
requirements for BSEE data, financial data, and configuration data.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd

from .base import ValidationResult
from .rules import (
    APINumberRule,
    CrossFieldRule,
    DataTypeRule,
    DateFormatRule,
    PatternRule,
    RangeRule,
    RequiredFieldRule,
    UniqueRule,
)


class DataType(Enum):
    """Enum for field data types."""

    INTEGER = "integer"
    STRING = "string"
    FLOAT = "float"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    ARRAY = "array"
    OBJECT = "object"


class DateFormat(Enum):
    """Enum for date format specifications."""

    YYYYMM = "YYYYMM"
    YYYY_MM_DD = "YYYY_MM_DD"
    MM_DD_YYYY = "MM_DD_YYYY"
    DD_MM_YYYY = "DD_MM_YYYY"
    YYYYMMDD = "YYYYMMDD"
    ISO8601 = "ISO8601"


class FieldSchema:
    """Defines validation requirements for a single field."""

    def __init__(
        self,
        name: str,
        data_type: DataType,
        required: bool = True,
        nullable: bool = False,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        pattern: Optional[str] = None,
        date_format: Optional[str] = None,
        allowed_values: Optional[List[Any]] = None,
        precision: Optional[int] = None,
        scale: Optional[int] = None,
        default_value: Optional[Any] = None,
        description: Optional[str] = None,
        unit: Optional[str] = None,
    ):
        self.name = name
        self.data_type = data_type
        self.required = required
        self.nullable = nullable
        self.min_length = min_length
        self.max_length = max_length
        self.min_value = min_value
        self.max_value = max_value
        self.pattern = pattern
        self.date_format = date_format
        self.allowed_values = allowed_values
        self.precision = precision
        self.scale = scale
        self.default_value = default_value
        self.description = description
        self.unit = unit


class FieldValidator:
    """Validates individual fields against schema requirements."""

    def __init__(self, name: str):
        self.name = name
        self.rules: List[Any] = []

    def add_rule(self, rule: Any):
        """Add a validation rule to this field."""
        self.rules.append(rule)

    def validate(self, data: pd.DataFrame) -> ValidationResult:
        """Validate field in dataframe."""
        result = ValidationResult()
        if self.name not in data.columns:
            result.add_warning(self.name, f"Field '{self.name}' not found in data")
            return result

        # Apply each rule
        for rule in self.rules:
            if hasattr(rule, "validate"):
                rule_result = rule.validate(data[self.name])
                result.merge(rule_result)

        return result


class ValidationSchema:
    """Container for field validation schemas and rules."""

    def __init__(
        self,
        name: str,
        version: Optional[str] = None,
        description: Optional[str] = None,
    ):
        self.name = name
        self.version = version
        self.description = description
        self.fields: Dict[str, FieldSchema] = {}
        self.field_validators: Dict[str, FieldValidator] = {}
        self.cross_field_rules: List[Any] = []
        self.custom_validators: List[str] = []

    def add_field(self, field: FieldSchema):
        """Add a field schema."""
        self.fields[field.name] = field

    def add_field_validator(self, field_name: str, validator: FieldValidator):
        """Add a field validator."""
        self.field_validators[field_name] = validator

    def add_cross_field_rule(self, rule: Any):
        """Add a cross-field validation rule."""
        self.cross_field_rules.append(rule)

    def get_required_fields(self) -> List[str]:
        """Return list of field names marked as required."""
        return [field.name for field in self.fields.values() if field.required]

    def validate(self, data: Any) -> ValidationResult:
        """Validate data against schema. Subclasses override for specific implementations."""
        result = ValidationResult()
        return result


class BSEEProductionSchema(ValidationSchema):
    """
    Validation schema for BSEE production data.

    This schema validates production data files including required fields,
    data types, value ranges, and BSEE-specific formatting requirements.
    """

    def __init__(self):
        super().__init__("BSEE Production Data")
        self._setup_field_validators()
        self._setup_cross_field_rules()

    def _setup_field_validators(self):
        """Set up field validators for production data."""

        # API Well Number - required, 12 digits
        self.add_field(
            FieldSchema(
                name="api_well_number",
                data_type=DataType.STRING,
                required=True,
                nullable=False,
                pattern=r"^\d{12}$",
                description="API Well Number - 12 digit identifier",
            )
        )

        # Production Date - can be YYYY-MM-DD or YYYYMM format
        self.add_field(
            FieldSchema(
                name="production_date",
                data_type=DataType.DATE,
                required=True,
                nullable=False,
                date_format=DateFormat.YYYY_MM_DD,
                description="Production date in YYYY-MM-DD format",
            )
        )

        # Oil Volume - numeric, non-negative
        self.add_field(
            FieldSchema(
                name="oil_volume",
                data_type=DataType.FLOAT,
                required=False,
                nullable=True,
                min_value=0,
                description="Oil volume produced in barrels per day",
            )
        )

        # Gas Volume - numeric, non-negative
        self.add_field(
            FieldSchema(
                name="gas_volume",
                data_type=DataType.FLOAT,
                required=False,
                nullable=True,
                min_value=0,
                description="Gas volume produced in million cubic feet per day",
            )
        )

        # Water Volume - numeric, non-negative
        self.add_field(
            FieldSchema(
                name="water_volume",
                data_type=DataType.FLOAT,
                required=False,
                nullable=True,
                min_value=0,
                description="Water volume produced in barrels per day",
            )
        )

        # Lease Number - required pattern
        self.add_field(
            FieldSchema(
                name="lease_number",
                data_type=DataType.STRING,
                required=True,
                nullable=False,
                pattern=r"^OCS-[A-Z]-\d+$",
                description="Lease number in OCS-X-##### format",
            )
        )

        # Field Name - required string
        self.add_field(
            FieldSchema(
                name="field_name",
                data_type=DataType.STRING,
                required=True,
                nullable=False,
                description="Name of the production field",
            )
        )

        # Days on Production - numeric, valid range
        self.add_field(
            FieldSchema(
                name="days_on_production",
                data_type=DataType.INTEGER,
                required=False,
                nullable=True,
                min_value=0,
                max_value=31,
                description="Number of days well was in production this month",
            )
        )

        # Well Status - controlled vocabulary
        self.add_field(
            FieldSchema(
                name="well_status",
                data_type=DataType.STRING,
                required=True,
                nullable=False,
                allowed_values=[
                    "ACTIVE",
                    "INACTIVE",
                    "SHUT-IN",
                    "ABANDONED",
                    "SUSPENDED",
                ],
                description="Current well status",
            )
        )

    def _setup_cross_field_rules(self):
        """Set up cross-field validation rules."""

        # Production consistency rule
        def validate_production_consistency(df: pd.DataFrame) -> List[str]:
            errors = []

            # Check for records with zero production in all categories
            zero_production = (
                (df["OIL_VOLUME"].fillna(0) == 0)
                & (df["GAS_VOLUME"].fillna(0) == 0)
                & (df["WATER_VOLUME"].fillna(0) == 0)
            )

            if zero_production.any():
                zero_count = zero_production.sum()
                errors.append(
                    f"Found {zero_count} records with zero production in all categories"
                )

            # Check for unrealistic production rates
            if "DAYS_ON_PRODUCTION" in df.columns:
                high_oil_rate = (
                    df["OIL_VOLUME"] / df["DAYS_ON_PRODUCTION"].fillna(1)
                ) > 10000
                if high_oil_rate.any():
                    high_count = high_oil_rate.sum()
                    errors.append(
                        f"Found {high_count} records with unrealistically high oil production rates (>10,000 bbl/day)"
                    )

            return errors

        production_consistency_rule = CrossFieldRule(
            validate_production_consistency,
            ["OIL_VOLUME", "GAS_VOLUME", "WATER_VOLUME", "DAYS_ON_PRODUCTION"],
        )
        self.add_cross_field_rule(production_consistency_rule)

    def validate(self, data: Any) -> ValidationResult:
        """Validate BSEE production data."""
        result = ValidationResult()
        result.metadata["schema_type"] = "bsee_production"

        if not isinstance(data, pd.DataFrame):
            result.add_error(
                "dataset",
                "BSEE production data must be provided as a pandas DataFrame",
                rule="data_type_check",
            )
            return result

        # Check required fields
        required_fields = [
            "API_WELL_NUMBER",
            "PRODUCTION_DATE",
            "LEASE_NUMBER",
            "FIELD_NAME",
        ]
        required_rule = RequiredFieldRule(required_fields)
        required_result = required_rule.validate(data)
        result.merge(required_result)

        # Apply field validators
        for field_name, validator in self.field_validators.items():
            if field_name in data.columns:
                field_result = validator.validate(data)
                result.merge(field_result)

        # Apply cross-field rules
        for rule in self.cross_field_rules:
            cross_result = rule.validate(data)
            result.merge(cross_result)

        return result


class BSEEWellSchema(ValidationSchema):
    """Validation schema for BSEE well data."""

    def __init__(self):
        super().__init__("BSEE Well Data")
        self._setup_field_validators()
        self._setup_cross_field_rules()

    def _setup_field_validators(self):
        """Set up field validators for well data."""

        # API Well Number
        api_validator = FieldValidator("API_WELL_NUMBER")
        api_validator.add_rule(APINumberRule())
        api_validator.add_rule(UniqueRule())  # Well numbers should be unique
        self.add_field_validator("API_WELL_NUMBER", api_validator)
        self.add_field(
            FieldSchema(
                name="api_number",
                data_type=DataType.STRING,
                required=True,
                pattern=r"^OCS-[A-Z]{2}-\d+$",
                description="API well number in OCS format",
            )
        )

        # Well Name
        well_name_validator = FieldValidator("WELL_NAME")
        well_name_validator.add_rule(DataTypeRule(str, allow_null=False))
        self.add_field_validator("WELL_NAME", well_name_validator)
        self.add_field(
            FieldSchema(
                name="well_name",
                data_type=DataType.STRING,
                required=True,
                nullable=False,
                description="Name of the well",
            )
        )

        # Lease Number
        lease_validator = FieldValidator("LEASE_NUMBER")
        lease_validator.add_rule(
            PatternRule(
                r"^OCS-[A-Z]-\d+$", "Lease number must follow OCS-X-##### format"
            )
        )
        self.add_field_validator("LEASE_NUMBER", lease_validator)
        self.add_field(
            FieldSchema(
                name="lease_number",
                data_type=DataType.STRING,
                pattern=r"^OCS-[A-Z]-\d+$",
                description="Lease number in OCS format",
            )
        )

        # Water Depth - numeric, reasonable range
        water_depth_validator = FieldValidator("WATER_DEPTH")
        water_depth_validator.add_rule(DataTypeRule([int, float], allow_null=True))
        water_depth_validator.add_rule(RangeRule(min_value=0, max_value=15000))  # feet
        self.add_field_validator("WATER_DEPTH", water_depth_validator)
        self.add_field(
            FieldSchema(
                name="water_depth",
                data_type=DataType.FLOAT,
                nullable=True,
                min_value=0,
                max_value=15000,
                unit="feet",
                description="Water depth at the well location",
            )
        )

        # Total Depth - numeric, reasonable range
        total_depth_validator = FieldValidator("TOTAL_DEPTH")
        total_depth_validator.add_rule(DataTypeRule([int, float], allow_null=True))
        total_depth_validator.add_rule(RangeRule(min_value=0, max_value=50000))  # feet
        self.add_field_validator("TOTAL_DEPTH", total_depth_validator)
        self.add_field(
            FieldSchema(
                name="tvd",
                data_type=DataType.FLOAT,
                nullable=True,
                min_value=0,
                max_value=50000,
                unit="feet",
                description="Total vertical depth of the well",
            )
        )

        # Spud Date
        spud_date_validator = FieldValidator("SPUD_DATE")
        spud_date_validator.add_rule(
            DateFormatRule(
                ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"],
                min_date=datetime(1950, 1, 1),
                max_date=datetime.now(),
            )
        )
        self.add_field_validator("SPUD_DATE", spud_date_validator)
        self.add_field(
            FieldSchema(
                name="spud",
                data_type=DataType.DATE,
                nullable=True,
                date_format=DateFormat.YYYY_MM_DD,
                description="Well spud date (start of drilling)",
            )
        )

        # Completion Date
        completion_date_validator = FieldValidator("COMPLETION_DATE")
        completion_date_validator.add_rule(
            DateFormatRule(
                ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"],
                min_date=datetime(1950, 1, 1),
                max_date=datetime.now(),
            )
        )
        self.add_field_validator("COMPLETION_DATE", completion_date_validator)
        self.add_field(
            FieldSchema(
                name="completion_date",
                data_type=DataType.DATE,
                nullable=True,
                date_format=DateFormat.YYYY_MM_DD,
                description="Well completion date (end of drilling)",
            )
        )

        # Longitude - valid range
        longitude_validator = FieldValidator("LONGITUDE")
        longitude_validator.add_rule(DataTypeRule([int, float], allow_null=True))
        longitude_validator.add_rule(RangeRule(min_value=-180, max_value=180))
        self.add_field_validator("LONGITUDE", longitude_validator)
        self.add_field(
            FieldSchema(
                name="longitude",
                data_type=DataType.FLOAT,
                nullable=True,
                min_value=-180,
                max_value=180,
                unit="degrees",
                description="Well location longitude coordinate",
            )
        )

        # Latitude - valid range
        latitude_validator = FieldValidator("LATITUDE")
        latitude_validator.add_rule(DataTypeRule([int, float], allow_null=True))
        latitude_validator.add_rule(RangeRule(min_value=-90, max_value=90))
        self.add_field_validator("LATITUDE", latitude_validator)
        self.add_field(
            FieldSchema(
                name="latitude",
                data_type=DataType.FLOAT,
                nullable=True,
                min_value=-90,
                max_value=90,
                unit="degrees",
                description="Well location latitude coordinate",
            )
        )

        # Well Type
        well_type_validator = FieldValidator("WELL_TYPE")
        well_type_validator.add_rule(
            PatternRule(
                r"^(OIL|GAS|INJECTION|WATER|DRY|EXPLORATION)$",
                "Well type must be one of: OIL, GAS, INJECTION, WATER, DRY, EXPLORATION",
            )
        )
        self.add_field_validator("WELL_TYPE", well_type_validator)

    def _setup_cross_field_rules(self):
        """Set up cross-field validation rules."""

        def validate_well_consistency(df: pd.DataFrame) -> List[str]:
            errors = []

            # Spud date should be before or equal to completion date
            if "SPUD_DATE" in df.columns and "COMPLETION_DATE" in df.columns:
                spud_after_completion = pd.to_datetime(
                    df["SPUD_DATE"]
                ) > pd.to_datetime(df["COMPLETION_DATE"])
                if spud_after_completion.any():
                    error_count = spud_after_completion.sum()
                    errors.append(
                        f"Found {error_count} wells where spud date is after completion date"
                    )

            # Total depth should be greater than water depth
            if "TOTAL_DEPTH" in df.columns and "WATER_DEPTH" in df.columns:
                invalid_depths = df["TOTAL_DEPTH"] <= df["WATER_DEPTH"]
                if invalid_depths.any():
                    error_count = invalid_depths.sum()
                    errors.append(
                        f"Found {error_count} wells where total depth <= water depth"
                    )

            return errors

        well_consistency_rule = CrossFieldRule(
            validate_well_consistency,
            ["SPUD_DATE", "COMPLETION_DATE", "TOTAL_DEPTH", "WATER_DEPTH"],
        )
        self.add_cross_field_rule(well_consistency_rule)

    def validate(self, data: Any) -> ValidationResult:
        """Validate BSEE well data."""
        result = ValidationResult()
        result.metadata["schema_type"] = "bsee_well"

        if not isinstance(data, pd.DataFrame):
            result.add_error(
                "dataset",
                "BSEE well data must be provided as a pandas DataFrame",
                rule="data_type_check",
            )
            return result

        # Check required fields
        required_fields = ["API_WELL_NUMBER", "WELL_NAME", "LEASE_NUMBER"]
        required_rule = RequiredFieldRule(required_fields)
        required_result = required_rule.validate(data)
        result.merge(required_result)

        # Apply field validators
        for field_name, validator in self.field_validators.items():
            if field_name in data.columns:
                field_result = validator.validate(data)
                result.merge(field_result)

        # Apply cross-field rules
        for rule in self.cross_field_rules:
            cross_result = rule.validate(data)
            result.merge(cross_result)

        return result


class BSEELeaseSchema(ValidationSchema):
    """Validation schema for BSEE lease data."""

    def __init__(self):
        super().__init__("BSEE Lease Data")
        self._setup_field_validators()

    def _setup_field_validators(self):
        """Set up field validators for lease data."""

        # Lease Number
        lease_validator = FieldValidator("LEASE_NUMBER")
        lease_validator.add_rule(
            PatternRule(
                r"^OCS-[A-Z]-\d+$", "Lease number must follow OCS-X-##### format"
            )
        )
        lease_validator.add_rule(UniqueRule())
        self.add_field_validator("LEASE_NUMBER", lease_validator)
        self.add_field(
            FieldSchema(
                name="lease_number",
                data_type=DataType.STRING,
                required=True,
                pattern=r"^OCS-[A-Z]-\d+$",
                description="BSEE lease number in OCS-X-##### format",
            )
        )

        # Area Code
        area_validator = FieldValidator("AREA_CODE")
        area_validator.add_rule(DataTypeRule(str, allow_null=False))
        self.add_field_validator("AREA_CODE", area_validator)
        self.add_field(
            FieldSchema(
                name="area_code",
                data_type=DataType.STRING,
                required=True,
                nullable=False,
                description="Gulf of Mexico area code",
            )
        )

        # Block Number
        block_validator = FieldValidator("BLOCK_NUMBER")
        block_validator.add_rule(DataTypeRule([str, int], allow_null=False))
        self.add_field_validator("BLOCK_NUMBER", block_validator)
        self.add_field(
            FieldSchema(
                name="block_number",
                data_type=DataType.STRING,
                required=True,
                nullable=False,
                description="Block number within area",
            )
        )

    def validate(self, data: Any) -> ValidationResult:
        """Validate BSEE lease data."""
        result = ValidationResult()
        result.metadata["schema_type"] = "bsee_lease"

        if not isinstance(data, pd.DataFrame):
            result.add_error(
                "dataset",
                "BSEE lease data must be provided as a pandas DataFrame",
                rule="data_type_check",
            )
            return result

        # Check required fields
        required_fields = ["LEASE_NUMBER", "AREA_CODE", "BLOCK_NUMBER"]
        required_rule = RequiredFieldRule(required_fields)
        required_result = required_rule.validate(data)
        result.merge(required_result)

        # Apply field validators
        for field_name, validator in self.field_validators.items():
            if field_name in data.columns:
                field_result = validator.validate(data)
                result.merge(field_result)

        return result


class FinancialDataSchema(ValidationSchema):
    """Validation schema for financial analysis data."""

    def __init__(self):
        super().__init__("Financial Data")
        self._setup_field_validators()
        self._setup_cross_field_rules()

    def _setup_field_validators(self):
        """Set up field validators for financial data."""

        # NPV - can be negative
        npv_validator = FieldValidator("NPV")
        npv_validator.add_rule(DataTypeRule([int, float], allow_null=True))
        self.add_field_validator("NPV", npv_validator)
        self.add_field(
            FieldSchema(
                name="npv",
                data_type=DataType.DECIMAL,
                required=False,
                nullable=True,
                unit="USD",
                description="Net Present Value of the project (can be negative)",
            )
        )

        # Discount Rate - percentage
        discount_rate_validator = FieldValidator("DISCOUNT_RATE")
        discount_rate_validator.add_rule(DataTypeRule([int, float], allow_null=False))
        discount_rate_validator.add_rule(RangeRule(min_value=0, max_value=100))
        self.add_field_validator("DISCOUNT_RATE", discount_rate_validator)
        self.add_field(
            FieldSchema(
                name="discount_rate",
                data_type=DataType.DECIMAL,
                required=True,
                nullable=False,
                min_value=0,
                max_value=100,
                unit="percent",
                description="Annual discount rate for NPV calculation",
            )
        )

        # Cash Flow - can be negative
        cash_flow_validator = FieldValidator("CASH_FLOW")
        cash_flow_validator.add_rule(DataTypeRule([int, float], allow_null=True))
        self.add_field_validator("CASH_FLOW", cash_flow_validator)
        self.add_field(
            FieldSchema(
                name="cash_flow",
                data_type=DataType.DECIMAL,
                required=False,
                nullable=True,
                unit="USD",
                description="Annual cash flow (can be negative for costs)",
            )
        )

        # Investment - should be positive
        investment_validator = FieldValidator("INVESTMENT")
        investment_validator.add_rule(DataTypeRule([int, float], allow_null=True))
        investment_validator.add_rule(RangeRule(min_value=0))
        self.add_field_validator("INVESTMENT", investment_validator)
        self.add_field(
            FieldSchema(
                name="investment",
                data_type=DataType.DECIMAL,
                required=False,
                nullable=True,
                min_value=0,
                unit="USD",
                description="Initial capital investment required",
            )
        )

        # Project Year - positive integer
        project_year_validator = FieldValidator("PROJECT_YEAR")
        project_year_validator.add_rule(DataTypeRule(int, allow_null=False))
        project_year_validator.add_rule(RangeRule(min_value=1, max_value=50))
        self.add_field_validator("PROJECT_YEAR", project_year_validator)
        self.add_field(
            FieldSchema(
                name="project_year",
                data_type=DataType.INTEGER,
                required=True,
                nullable=False,
                min_value=1,
                max_value=50,
                description="Project year for analysis (1-50 year horizon)",
            )
        )

    def _setup_cross_field_rules(self):
        """Set up cross-field validation rules."""

        def validate_financial_consistency(df: pd.DataFrame) -> List[str]:
            errors = []

            # Check for unrealistic discount rates
            if "DISCOUNT_RATE" in df.columns:
                high_rates = df["DISCOUNT_RATE"] > 30
                if high_rates.any():
                    errors.append(
                        "Found discount rates >30%, please verify these values"
                    )

            return errors

        financial_consistency_rule = CrossFieldRule(
            validate_financial_consistency, ["DISCOUNT_RATE"]
        )
        self.add_cross_field_rule(financial_consistency_rule)

    def validate(self, data: Any) -> ValidationResult:
        """Validate financial data."""
        result = ValidationResult()
        result.metadata["schema_type"] = "financial"

        if not isinstance(data, pd.DataFrame):
            result.add_error(
                "dataset",
                "Financial data must be provided as a pandas DataFrame",
                rule="data_type_check",
            )
            return result

        # Apply field validators
        for field_name, validator in self.field_validators.items():
            if field_name in data.columns:
                field_result = validator.validate(data)
                result.merge(field_result)

        # Apply cross-field rules
        for rule in self.cross_field_rules:
            cross_result = rule.validate(data)
            result.merge(cross_result)

        return result


class ConfigurationSchema(ValidationSchema):
    """Validation schema for configuration files."""

    def __init__(self):
        super().__init__("Configuration")
        self._setup_validators()

    def _setup_validators(self):
        """Set up configuration validation rules."""
        pass  # Will be implemented based on specific config requirements

    def validate(self, data: Any) -> ValidationResult:
        """Validate configuration data."""
        result = ValidationResult()
        result.metadata["schema_type"] = "configuration"

        if not isinstance(data, dict):
            result.add_error(
                "configuration",
                "Configuration data must be provided as a dictionary",
                rule="data_type_check",
            )
            return result

        # Check for required configuration sections
        required_sections = ["basename", "data"]
        for section in required_sections:
            if section not in data:
                result.add_error(
                    section,
                    f"Required configuration section '{section}' is missing",
                    rule="required_section",
                )

        # Validate basename
        if "basename" in data:
            valid_basenames = ["bsee", "dwnld_from_zipurl", "bsee_custom"]
            if data["basename"] not in valid_basenames:
                result.add_warning(
                    "basename",
                    f"Basename '{data['basename']}' is not in recognized list: {valid_basenames}",
                    value=data["basename"],
                )

        return result
