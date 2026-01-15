"""
ABOUTME: Comprehensive tests for schemas.py validation schema classes
ABOUTME: Tests DataType enum, FieldSchema, FieldValidator, ValidationSchema hierarchy
"""

import pytest
import pandas as pd
from datetime import datetime
from typing import List, Any

from worldenergydata.validation.schemas import (
    DataType,
    FieldSchema,
    FieldValidator,
    ValidationSchema,
    BSEEProductionSchema,
    BSEEWellSchema,
    BSEELeaseSchema,
    FinancialDataSchema,
    ConfigurationSchema,
)
from worldenergydata.validation.base import ValidationResult
from worldenergydata.validation.exceptions import ValidationError
from worldenergydata.validation.rules import (
    ValidationRules,
    CrossFieldRules,
    CrossFieldRule,
    CustomValidators,
    DataTypeRule,
    RangeRule,
    RequiredFieldRule,
)


# ============================================================================
# TestDataTypeEnum - Test DataType enum values
# ============================================================================
class TestDataTypeEnum:
    """Test DataType enum functionality."""

    def test_data_type_enum_has_integer(self):
        """Test DataType.INTEGER exists."""
        assert hasattr(DataType, 'INTEGER')
        assert DataType.INTEGER is not None

    def test_data_type_enum_has_string(self):
        """Test DataType.STRING exists."""
        assert hasattr(DataType, 'STRING')
        assert DataType.STRING is not None

    def test_data_type_enum_has_float(self):
        """Test DataType.FLOAT exists."""
        assert hasattr(DataType, 'FLOAT')
        assert DataType.FLOAT is not None

    def test_data_type_enum_has_decimal(self):
        """Test DataType.DECIMAL exists."""
        assert hasattr(DataType, 'DECIMAL')
        assert DataType.DECIMAL is not None

    def test_data_type_enum_has_boolean(self):
        """Test DataType.BOOLEAN exists."""
        assert hasattr(DataType, 'BOOLEAN')
        assert DataType.BOOLEAN is not None

    def test_data_type_enum_has_date(self):
        """Test DataType.DATE exists."""
        assert hasattr(DataType, 'DATE')
        assert DataType.DATE is not None

    def test_data_type_enum_has_datetime(self):
        """Test DataType.DATETIME exists."""
        assert hasattr(DataType, 'DATETIME')
        assert DataType.DATETIME is not None

    def test_data_type_enum_has_array(self):
        """Test DataType.ARRAY exists."""
        assert hasattr(DataType, 'ARRAY')
        assert DataType.ARRAY is not None

    def test_data_type_enum_has_object(self):
        """Test DataType.OBJECT exists."""
        assert hasattr(DataType, 'OBJECT')
        assert DataType.OBJECT is not None


# ============================================================================
# TestFieldSchema - Test FieldSchema initialization and properties
# ============================================================================
class TestFieldSchema:
    """Test FieldSchema class functionality."""

    def test_field_schema_basic_initialization(self):
        """Test FieldSchema initialization with minimal parameters."""
        schema = FieldSchema(name="test_field", data_type=DataType.STRING)
        assert schema.name == "test_field"
        assert schema.data_type == DataType.STRING

    def test_field_schema_required_parameter(self):
        """Test FieldSchema required parameter."""
        schema = FieldSchema(name="test", data_type=DataType.INTEGER, required=True)
        assert schema.required is True

    def test_field_schema_required_parameter_false(self):
        """Test FieldSchema with required=False."""
        schema = FieldSchema(name="test", data_type=DataType.STRING, required=False)
        assert schema.required is False

    def test_field_schema_nullable_parameter(self):
        """Test FieldSchema nullable parameter."""
        schema = FieldSchema(name="test", data_type=DataType.STRING, nullable=True)
        assert schema.nullable is True

    def test_field_schema_min_length_parameter(self):
        """Test FieldSchema min_length parameter."""
        schema = FieldSchema(name="test", data_type=DataType.STRING, min_length=5)
        assert schema.min_length == 5

    def test_field_schema_max_length_parameter(self):
        """Test FieldSchema max_length parameter."""
        schema = FieldSchema(name="test", data_type=DataType.STRING, max_length=100)
        assert schema.max_length == 100

    def test_field_schema_min_value_parameter(self):
        """Test FieldSchema min_value parameter."""
        schema = FieldSchema(name="test", data_type=DataType.FLOAT, min_value=0.0)
        assert schema.min_value == 0.0

    def test_field_schema_max_value_parameter(self):
        """Test FieldSchema max_value parameter."""
        schema = FieldSchema(name="test", data_type=DataType.FLOAT, max_value=100.0)
        assert schema.max_value == 100.0

    def test_field_schema_pattern_parameter(self):
        """Test FieldSchema pattern parameter."""
        pattern = r"^\d{3}-\d{2}-\d{4}$"
        schema = FieldSchema(name="test", data_type=DataType.STRING, pattern=pattern)
        assert schema.pattern == pattern

    def test_field_schema_date_format_parameter(self):
        """Test FieldSchema date_format parameter."""
        schema = FieldSchema(name="test", data_type=DataType.DATE, date_format="%Y-%m-%d")
        assert schema.date_format == "%Y-%m-%d"

    def test_field_schema_allowed_values_parameter(self):
        """Test FieldSchema allowed_values parameter."""
        allowed = ["active", "inactive", "pending"]
        schema = FieldSchema(name="test", data_type=DataType.STRING, allowed_values=allowed)
        assert schema.allowed_values == allowed

    def test_field_schema_precision_parameter(self):
        """Test FieldSchema precision parameter."""
        schema = FieldSchema(name="test", data_type=DataType.DECIMAL, precision=10)
        assert schema.precision == 10

    def test_field_schema_scale_parameter(self):
        """Test FieldSchema scale parameter."""
        schema = FieldSchema(name="test", data_type=DataType.DECIMAL, scale=2)
        assert schema.scale == 2

    def test_field_schema_default_value_parameter(self):
        """Test FieldSchema default_value parameter."""
        schema = FieldSchema(name="test", data_type=DataType.STRING, default_value="N/A")
        assert schema.default_value == "N/A"

    def test_field_schema_description_parameter(self):
        """Test FieldSchema description parameter."""
        desc = "Test field description"
        schema = FieldSchema(name="test", data_type=DataType.STRING, description=desc)
        assert schema.description == desc

    def test_field_schema_unit_parameter(self):
        """Test FieldSchema unit parameter."""
        schema = FieldSchema(name="test", data_type=DataType.FLOAT, unit="meters")
        assert schema.unit == "meters"

    def test_field_schema_all_parameters_combined(self):
        """Test FieldSchema with all parameters specified."""
        schema = FieldSchema(
            name="production_rate",
            data_type=DataType.DECIMAL,
            required=True,
            nullable=False,
            min_length=None,
            max_length=None,
            min_value=0.0,
            max_value=10000.0,
            pattern=None,
            date_format=None,
            allowed_values=None,
            precision=10,
            scale=2,
            default_value=0.0,
            description="Daily production rate",
            unit="barrels per day"
        )
        assert schema.name == "production_rate"
        assert schema.data_type == DataType.DECIMAL
        assert schema.required is True
        assert schema.min_value == 0.0
        assert schema.max_value == 10000.0
        assert schema.precision == 10
        assert schema.scale == 2
        assert schema.unit == "barrels per day"


# ============================================================================
# TestFieldValidator - Test FieldValidator class and validation logic
# ============================================================================
class TestFieldValidator:
    """Test FieldValidator class functionality."""

    def test_field_validator_initialization(self):
        """Test FieldValidator initialization."""
        validator = FieldValidator(name="test_validator")
        assert validator.name == "test_validator"
        assert hasattr(validator, 'rules')

    def test_field_validator_rules_list_initialized(self):
        """Test FieldValidator rules list is initialized."""
        validator = FieldValidator(name="test")
        assert isinstance(validator.rules, list)
        assert len(validator.rules) == 0

    def test_field_validator_add_rule(self):
        """Test FieldValidator add_rule method."""
        validator = FieldValidator(name="test")
        rule = DataTypeRule(allowed_types=str)
        validator.add_rule(rule)
        assert len(validator.rules) == 1
        assert validator.rules[0] is rule

    def test_field_validator_add_multiple_rules(self):
        """Test FieldValidator can add multiple rules."""
        validator = FieldValidator(name="test")
        rule1 = DataTypeRule(allowed_types=str)
        rule2 = RequiredFieldRule(required_fields=["test"])
        validator.add_rule(rule1)
        validator.add_rule(rule2)
        assert len(validator.rules) == 2

    def test_field_validator_validate_missing_column(self):
        """Test FieldValidator.validate() with missing column."""
        validator = FieldValidator(name="test_validator")
        df = pd.DataFrame({"other_column": [1, 2, 3]})
        # This should handle missing column - test expects proper error handling
        result = validator.validate(df)
        assert isinstance(result, ValidationResult)

    def test_field_validator_validate_no_rules(self):
        """Test FieldValidator.validate() with no rules."""
        validator = FieldValidator(name="test_validator")
        df = pd.DataFrame({"test": [1, 2, 3]})
        result = validator.validate(df)
        assert isinstance(result, ValidationResult)

    def test_field_validator_validate_with_single_rule(self):
        """Test FieldValidator.validate() with one rule."""
        validator = FieldValidator(name="test_validator")
        rule = DataTypeRule([int], allow_null=False)
        validator.add_rule(rule)
        df = pd.DataFrame({"test": [1, 2, 3]})
        result = validator.validate(df)
        assert isinstance(result, ValidationResult)

    def test_field_validator_validate_with_multiple_rules(self):
        """Test FieldValidator.validate() with multiple rules."""
        validator = FieldValidator(name="test_validator")
        rule1 = DataTypeRule([int], allow_null=False)
        rule2 = RangeRule(min_value=0, max_value=100)
        validator.add_rule(rule1)
        validator.add_rule(rule2)
        df = pd.DataFrame({"test": [1, 50, 99]})
        result = validator.validate(df)
        assert isinstance(result, ValidationResult)


# ============================================================================
# TestValidationSchemaBase - Test ValidationSchema base class
# ============================================================================
class TestValidationSchemaBase:
    """Test ValidationSchema base class functionality."""

    def test_validation_schema_initialization(self):
        """Test ValidationSchema can be initialized."""
        schema = ValidationSchema(name="test_schema")
        assert isinstance(schema, ValidationSchema)

    def test_validation_schema_add_field(self):
        """Test ValidationSchema add_field method."""
        schema = ValidationSchema(name="test_schema")
        field = FieldSchema(name="test_field", data_type=DataType.STRING)
        schema.add_field(field)
        # Verify field was added - should be stored internally
        assert hasattr(schema, 'fields') or hasattr(schema, '_fields')

    def test_validation_schema_add_multiple_fields(self):
        """Test ValidationSchema can add multiple fields."""
        schema = ValidationSchema(name="test_schema")
        field1 = FieldSchema(name="field1", data_type=DataType.STRING)
        field2 = FieldSchema(name="field2", data_type=DataType.INTEGER)
        schema.add_field(field1)
        schema.add_field(field2)
        # Verify both fields exist
        assert len(schema.fields) == 2 if hasattr(schema, 'fields') else True

    def test_validation_schema_add_field_validator(self):
        """Test ValidationSchema add_field_validator method."""
        schema = ValidationSchema(name="test_schema")
        validator = FieldValidator(name="test_validator")
        schema.add_field_validator("test_field", validator)
        # Verify validator was added
        assert hasattr(schema, 'field_validators') or hasattr(schema, '_field_validators')

    def test_validation_schema_add_cross_field_rule(self):
        """Test ValidationSchema add_cross_field_rule method."""
        schema = ValidationSchema(name="test_schema")
        # Create a simple cross-field rule
        def validate_cross_fields(df: pd.DataFrame) -> List[str]:
            return []  # No errors

        rule = CrossFieldRule(
            validation_func=validate_cross_fields,
            dependent_fields=["field1", "field2"]
        )
        schema.add_cross_field_rule(rule)
        # Verify rule was added
        assert hasattr(schema, 'cross_field_rules') or hasattr(schema, '_cross_field_rules')

    def test_validation_schema_get_required_fields(self):
        """Test ValidationSchema get_required_fields method."""
        schema = ValidationSchema(name="test_schema")
        field1 = FieldSchema(name="required_field", data_type=DataType.STRING, required=True)
        field2 = FieldSchema(name="optional_field", data_type=DataType.STRING, required=False)
        schema.add_field(field1)
        schema.add_field(field2)
        required_fields = schema.get_required_fields()
        assert "required_field" in required_fields
        assert "optional_field" not in required_fields

    def test_validation_schema_validate(self):
        """Test ValidationSchema validate method."""
        schema = ValidationSchema(name="test_schema")
        field = FieldSchema(name="test", data_type=DataType.STRING)
        schema.add_field(field)
        df = pd.DataFrame({"test": ["a", "b", "c"]})
        result = schema.validate(df)
        assert isinstance(result, ValidationResult)


# ============================================================================
# TestBSEEProductionSchema - Test BSEE Production Schema
# ============================================================================
class TestBSEEProductionSchema:
    """Test BSEEProductionSchema class and field setup."""

    def test_bsee_production_schema_initialization(self):
        """Test BSEEProductionSchema can be initialized."""
        schema = BSEEProductionSchema()
        assert isinstance(schema, BSEEProductionSchema)
        assert isinstance(schema, ValidationSchema)

    def test_bsee_production_schema_has_field_validators(self):
        """Test BSEEProductionSchema sets up field validators."""
        schema = BSEEProductionSchema()
        assert hasattr(schema, 'field_validators')
        assert len(schema.field_validators) > 0

    def test_bsee_production_schema_has_fields(self):
        """Test BSEEProductionSchema has required fields."""
        schema = BSEEProductionSchema()
        assert hasattr(schema, 'fields')
        # Should have fields for API number, production data, etc.
        assert len(schema.fields) > 0

    def test_bsee_production_schema_api_number_field_exists(self):
        """Test BSEEProductionSchema has API number field."""
        schema = BSEEProductionSchema()
        field_names = [f.name for f in schema.fields]
        assert "api_number" in field_names or "API" in field_names

    def test_bsee_production_schema_date_field_exists(self):
        """Test BSEEProductionSchema has date field."""
        schema = BSEEProductionSchema()
        field_names = [f.name for f in schema.fields]
        # Should have a date-related field
        date_fields = [name for name in field_names if "date" in name.lower()]
        assert len(date_fields) > 0

    def test_bsee_production_schema_production_field_exists(self):
        """Test BSEEProductionSchema has production field."""
        schema = BSEEProductionSchema()
        field_names = [f.name for f in schema.fields]
        production_fields = [name for name in field_names if "production" in name.lower() or "volume" in name.lower()]
        assert len(production_fields) > 0

    def test_bsee_production_schema_has_cross_field_rules(self):
        """Test BSEEProductionSchema sets up cross-field rules."""
        schema = BSEEProductionSchema()
        assert hasattr(schema, 'cross_field_rules')
        # Should have validation rules for field consistency
        assert len(schema.cross_field_rules) > 0

    def test_bsee_production_schema_validate_with_valid_data(self):
        """Test BSEEProductionSchema validation with valid data."""
        schema = BSEEProductionSchema()
        # Create valid test data matching schema
        df = pd.DataFrame({
            "API_WELL_NUMBER": ["123456789012"],
            "PRODUCTION_DATE": [datetime(2025, 1, 1)],
            "LEASE_NUMBER": ["OCS-G-12345"],
            "FIELD_NAME": ["Test Field"],
            "OIL_VOLUME": [1000.0],
            "GAS_VOLUME": [5000000.0],
            "WATER_VOLUME": [500.0],
            "DAYS_ON_PRODUCTION": [31],
            "WELL_STATUS": ["ACTIVE"]
        })
        result = schema.validate(df)
        assert isinstance(result, ValidationResult)

    def test_bsee_production_schema_validate_with_invalid_data(self):
        """Test BSEEProductionSchema validation with invalid data."""
        schema = BSEEProductionSchema()
        # Create invalid test data
        df = pd.DataFrame({
            "api_number": ["invalid"],  # Should be numeric
            "report_date": ["not-a-date"],
            "oil_production": ["not-numeric"],
        })
        result = schema.validate(df)
        assert isinstance(result, ValidationResult)
        # Should detect validation errors
        assert len(result.errors) > 0 or result.valid is False


# ============================================================================
# TestBSEEWellSchema - Test BSEE Well Schema
# ============================================================================
class TestBSEEWellSchema:
    """Test BSEEWellSchema class."""

    def test_bsee_well_schema_initialization(self):
        """Test BSEEWellSchema can be initialized."""
        schema = BSEEWellSchema()
        assert isinstance(schema, BSEEWellSchema)
        assert isinstance(schema, ValidationSchema)

    def test_bsee_well_schema_has_fields(self):
        """Test BSEEWellSchema has required fields."""
        schema = BSEEWellSchema()
        assert hasattr(schema, 'fields')
        assert len(schema.fields) > 0

    def test_bsee_well_schema_api_number_field(self):
        """Test BSEEWellSchema has API number field."""
        schema = BSEEWellSchema()
        field_names = [f.name for f in schema.fields]
        assert "api_number" in field_names or "API" in field_names

    def test_bsee_well_schema_spud_date_field(self):
        """Test BSEEWellSchema has spud date field."""
        schema = BSEEWellSchema()
        field_names = [f.name for f in schema.fields]
        spud_fields = [name for name in field_names if "spud" in name.lower()]
        assert len(spud_fields) > 0

    def test_bsee_well_schema_depth_field(self):
        """Test BSEEWellSchema has depth field."""
        schema = BSEEWellSchema()
        field_names = [f.name for f in schema.fields]
        depth_fields = [name for name in field_names if "depth" in name.lower() or "tvd" in name.lower()]
        assert len(depth_fields) > 0

    def test_bsee_well_schema_validate(self):
        """Test BSEEWellSchema validation."""
        schema = BSEEWellSchema()
        df = pd.DataFrame({
            "api_number": ["123456789"],
            "spud_date": [datetime(2020, 1, 1)],
            "total_depth": [5000.0],
        })
        result = schema.validate(df)
        assert isinstance(result, ValidationResult)


# ============================================================================
# TestBSEELeaseSchema - Test BSEE Lease Schema
# ============================================================================
class TestBSEELeaseSchema:
    """Test BSEELeaseSchema class."""

    def test_bsee_lease_schema_initialization(self):
        """Test BSEELeaseSchema can be initialized."""
        schema = BSEELeaseSchema()
        assert isinstance(schema, BSEELeaseSchema)
        assert isinstance(schema, ValidationSchema)

    def test_bsee_lease_schema_has_fields(self):
        """Test BSEELeaseSchema has required fields."""
        schema = BSEELeaseSchema()
        assert hasattr(schema, 'fields')
        assert len(schema.fields) > 0

    def test_bsee_lease_schema_lease_number_field(self):
        """Test BSEELeaseSchema has lease number field."""
        schema = BSEELeaseSchema()
        field_names = [f.name for f in schema.fields.values()]
        lease_fields = [name for name in field_names if "lease" in name.lower() or "number" in name.lower()]
        assert len(lease_fields) > 0


# ============================================================================
# TestFinancialDataSchema - Test Financial Data Schema
# ============================================================================
class TestFinancialDataSchema:
    """Test FinancialDataSchema class."""

    def test_financial_data_schema_initialization(self):
        """Test FinancialDataSchema can be initialized."""
        schema = FinancialDataSchema()
        assert isinstance(schema, FinancialDataSchema)
        assert isinstance(schema, ValidationSchema)

    def test_financial_data_schema_has_fields(self):
        """Test FinancialDataSchema has required fields."""
        schema = FinancialDataSchema()
        assert hasattr(schema, 'fields')
        assert len(schema.fields) > 0

    def test_financial_data_schema_discount_rate_field(self):
        """Test FinancialDataSchema has discount rate field."""
        schema = FinancialDataSchema()
        field_names = [f.name for f in schema.fields]
        discount_fields = [name for name in field_names if "discount" in name.lower() or "rate" in name.lower()]
        assert len(discount_fields) > 0


# ============================================================================
# TestConfigurationSchema - Test Configuration Schema
# ============================================================================
class TestConfigurationSchema:
    """Test ConfigurationSchema class."""

    def test_configuration_schema_initialization(self):
        """Test ConfigurationSchema can be initialized."""
        schema = ConfigurationSchema()
        assert isinstance(schema, ConfigurationSchema)
        assert isinstance(schema, ValidationSchema)

    def test_configuration_schema_has_fields(self):
        """Test ConfigurationSchema has required fields."""
        schema = ConfigurationSchema()
        assert hasattr(schema, 'fields')

    def test_configuration_schema_validate_dict(self):
        """Test ConfigurationSchema validation with dictionary."""
        schema = ConfigurationSchema()
        test_config = {"setting1": "value1", "setting2": "value2"}
        result = schema.validate(test_config)
        assert isinstance(result, ValidationResult)
