"""
Comprehensive tests for the data validation framework.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
import yaml

from worldenergydata.validation import (
    DataValidator,
    ValidationError,
    ValidationRules,
    ValidationSchema,
)
from worldenergydata.validation.exceptions import (
    ConsistencyError,
    CrossFieldValidationError,
    DataTypeError,
    DateFormatError,
    RangeValidationError,
    RequiredFieldError,
)
from worldenergydata.validation.schema import (
    BSEESchemas,
    DataType,
    DateFormat,
    FieldSchema,
    FinancialSchemas,
)
from worldenergydata.validation.validators import ValidationManager


class TestValidationSchema:
    """Test validation schema creation and management."""

    def test_create_basic_schema(self):
        """Test creating a basic validation schema."""
        schema = ValidationSchema(
            name="TestSchema", version="1.0.0", description="Test schema"
        )

        assert schema.name == "TestSchema"
        assert schema.version == "1.0.0"
        assert schema.description == "Test schema"
        assert len(schema.fields) == 0

    def test_add_field_to_schema(self):
        """Test adding fields to schema."""
        schema = ValidationSchema(name="TestSchema")

        field = FieldSchema(
            name="test_field", data_type=DataType.STRING, required=True, max_length=100
        )

        schema.add_field(field)
        assert len(schema.fields) == 1
        assert schema.get_field("test_field") == field

    def test_get_required_fields(self):
        """Test getting required fields from schema."""
        schema = ValidationSchema(name="TestSchema")

        schema.add_field(
            FieldSchema(name="required_field", data_type=DataType.STRING, required=True)
        )

        schema.add_field(
            FieldSchema(
                name="optional_field", data_type=DataType.STRING, required=False
            )
        )

        required = schema.get_required_fields()
        assert len(required) == 1
        assert "required_field" in required
        assert "optional_field" not in required

    def test_bsee_production_schema(self):
        """Test predefined BSEE production schema."""
        schema = BSEESchemas.production_schema()

        assert schema.name == "BSEE_Production"
        assert len(schema.fields) > 0

        # Check for key fields
        api_field = schema.get_field("API_WELL_NUMBER")
        assert api_field is not None
        assert api_field.data_type == DataType.STRING
        assert api_field.pattern == r"^\d{12}$"

        prod_date_field = schema.get_field("PRODUCTION_DATE")
        assert prod_date_field is not None
        assert prod_date_field.date_format == DateFormat.YYYYMM

    def test_financial_npv_schema(self):
        """Test predefined financial NPV schema."""
        schema = FinancialSchemas.npv_schema()

        assert schema.name == "NPV_Analysis"

        discount_field = schema.get_field("DISCOUNT_RATE")
        assert discount_field is not None
        assert discount_field.min_value == 0
        assert discount_field.max_value == 1


class TestDataValidator:
    """Test data validation functionality."""

    def test_validate_simple_record(self):
        """Test validating a simple record."""
        schema = ValidationSchema(name="TestSchema")
        schema.add_field(
            FieldSchema(name="name", data_type=DataType.STRING, required=True)
        )
        schema.add_field(
            FieldSchema(
                name="age",
                data_type=DataType.INTEGER,
                required=True,
                min_value=0,
                max_value=150,
            )
        )

        validator = DataValidator(schema)

        # Valid record
        valid_data = {"name": "John", "age": 30}
        is_valid, errors = validator.validate(valid_data)
        assert is_valid
        assert len(errors) == 0

        # Invalid record - missing required field
        invalid_data = {"name": "John"}
        validator_strict = DataValidator(schema, strict=False)
        is_valid, errors = validator_strict.validate(invalid_data)
        assert not is_valid
        assert len(errors) > 0

    def test_validate_dataframe(self):
        """Test validating a pandas DataFrame."""
        schema = ValidationSchema(name="TestSchema")
        schema.add_field(
            FieldSchema(
                name="value",
                data_type=DataType.FLOAT,
                required=True,
                min_value=0,
                max_value=100,
            )
        )

        df = pd.DataFrame({"value": [10, 20, 30, 40, 50]})

        validator = DataValidator(schema)
        is_valid, errors = validator.validate(df)
        assert is_valid
        assert len(errors) == 0

    def test_validate_bsee_production_data(self):
        """Test validating BSEE production data."""
        schema = BSEESchemas.production_schema()
        validator = DataValidator(schema, strict=False)

        # Valid BSEE production record
        valid_record = {
            "PRODUCTION_DATE": "202301",
            "API_WELL_NUMBER": "177154098200",
            "MON_O_PROD_VOL": 15000.5,
            "MON_G_PROD_VOL": 25000.0,
            "MON_W_PROD_VOL": 5000.0,
            "DAYS_ON_PROD": 28,
            "LEASE_NUMBER": "G12345",
        }

        is_valid, errors = validator.validate(valid_record)
        assert is_valid
        assert len(errors) == 0

        # Invalid production date format
        invalid_record = valid_record.copy()
        invalid_record["PRODUCTION_DATE"] = "2023-01"

        is_valid, errors = validator.validate(invalid_record)
        assert not is_valid
        assert any("date format" in str(e).lower() for e in errors)

    def test_validate_cross_field_rules(self):
        """Test cross-field validation rules."""
        schema = BSEESchemas.production_schema()
        validator = DataValidator(schema, strict=False)

        # Invalid: production with zero days
        invalid_record = {
            "PRODUCTION_DATE": "202301",
            "API_WELL_NUMBER": "177154098200",
            "MON_O_PROD_VOL": 15000.5,  # Should be 0 if DAYS_ON_PROD is 0
            "MON_G_PROD_VOL": 25000.0,  # Should be 0 if DAYS_ON_PROD is 0
            "DAYS_ON_PROD": 0,
            "LEASE_NUMBER": "G12345",
        }

        is_valid, errors = validator.validate(invalid_record)
        assert not is_valid
        assert any("production" in str(e).lower() for e in errors)


class TestValidationRules:
    """Test individual validation rules."""

    def test_validate_required(self):
        """Test required field validation."""
        # Valid: required field present
        assert ValidationRules.validate_required("value", "field", True)

        # Invalid: required field missing
        with pytest.raises(RequiredFieldError):
            ValidationRules.validate_required(None, "field", True)

        with pytest.raises(RequiredFieldError):
            ValidationRules.validate_required("", "field", True)

    def test_validate_data_type(self):
        """Test data type validation."""
        # String type
        assert ValidationRules.validate_data_type("text", "field", DataType.STRING)

        # Integer type
        assert ValidationRules.validate_data_type(42, "field", DataType.INTEGER)
        assert ValidationRules.validate_data_type("42", "field", DataType.INTEGER)

        # Float type
        assert ValidationRules.validate_data_type(3.14, "field", DataType.FLOAT)
        assert ValidationRules.validate_data_type("3.14", "field", DataType.FLOAT)

        # Invalid type
        with pytest.raises(DataTypeError):
            ValidationRules.validate_data_type("text", "field", DataType.INTEGER)

    def test_validate_range(self):
        """Test numeric range validation."""
        # Valid range
        assert ValidationRules.validate_range(50, "field", 0, 100)

        # Below minimum
        with pytest.raises(RangeValidationError):
            ValidationRules.validate_range(-1, "field", 0, 100)

        # Above maximum
        with pytest.raises(RangeValidationError):
            ValidationRules.validate_range(101, "field", 0, 100)

    def test_validate_date_format(self):
        """Test date format validation."""
        # YYYYMM format
        assert ValidationRules.validate_date_format(
            "202301", "field", DateFormat.YYYYMM
        )

        # Invalid YYYYMM
        with pytest.raises(DateFormatError):
            ValidationRules.validate_date_format("2023-01", "field", DateFormat.YYYYMM)

        # Invalid month
        with pytest.raises(DateFormatError):
            ValidationRules.validate_date_format("202313", "field", DateFormat.YYYYMM)


class TestValidationManager:
    """Test validation manager functionality."""

    def test_register_and_get_schema(self):
        """Test registering and retrieving schemas."""
        manager = ValidationManager()

        schema = ValidationSchema(name="TestSchema")
        manager.register_schema(schema)

        validator = manager.get_validator("TestSchema")
        assert validator is not None
        assert validator.schema == schema

    def test_validate_with_named_schema(self):
        """Test validating with a named schema."""
        manager = ValidationManager()

        schema = ValidationSchema(name="TestSchema")
        schema.add_field(
            FieldSchema(name="value", data_type=DataType.INTEGER, required=True)
        )

        manager.register_schema(schema)

        is_valid, errors = manager.validate_with_schema("TestSchema", {"value": 42})
        assert is_valid

    def test_load_schema_from_yaml(self):
        """Test loading schema from YAML file."""
        schema_dict = {
            "name": "TestSchema",
            "version": "1.0.0",
            "fields": [
                {
                    "name": "test_field",
                    "data_type": "string",
                    "required": True,
                    "max_length": 100,
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(schema_dict, f)
            temp_path = f.name

        try:
            manager = ValidationManager()
            schema = manager.load_schema_from_file(temp_path)

            assert schema.name == "TestSchema"
            assert len(schema.fields) == 1
        finally:
            Path(temp_path).unlink()


class TestValidationIntegration:
    """Integration tests for the validation framework."""

    def test_full_validation_workflow(self):
        """Test complete validation workflow."""
        # Create schema
        schema = BSEESchemas.production_schema()

        # Create test data
        test_data = pd.DataFrame(
            [
                {
                    "PRODUCTION_DATE": "202301",
                    "API_WELL_NUMBER": "177154098200",
                    "MON_O_PROD_VOL": 15000,
                    "MON_G_PROD_VOL": 25000,
                    "MON_W_PROD_VOL": 5000,
                    "DAYS_ON_PROD": 28,
                    "LEASE_NUMBER": "G12345",
                },
                {
                    "PRODUCTION_DATE": "202302",
                    "API_WELL_NUMBER": "177154098201",
                    "MON_O_PROD_VOL": 16000,
                    "MON_G_PROD_VOL": 26000,
                    "MON_W_PROD_VOL": 5500,
                    "DAYS_ON_PROD": 28,
                    "LEASE_NUMBER": "G12346",
                },
            ]
        )

        # Validate
        validator = DataValidator(schema)
        is_valid, errors = validator.validate(test_data)

        assert is_valid
        assert len(errors) == 0

        # Get validation report
        report = validator.get_validation_report()
        assert "All validations passed" in report

    def test_validate_csv_file(self):
        """Test validating data from CSV file."""
        # Create test CSV
        test_data = pd.DataFrame(
            {
                "DISCOUNT_RATE": [0.1, 0.15, 0.2],
                "OIL_PRICE": [70, 80, 90],
                "GAS_PRICE": [3.5, 4.0, 4.5],
                "CAPEX": [1000000, 1500000, 2000000],
                "OPEX": [100000, 150000, 200000],
                "PROJECT_LIFE_YEARS": [20, 25, 30],
            }
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            test_data.to_csv(f, index=False)
            temp_path = f.name

        try:
            schema = FinancialSchemas.npv_schema()
            validator = DataValidator(schema)

            is_valid, errors = validator.validate_file(temp_path)
            assert is_valid
            assert len(errors) == 0
        finally:
            Path(temp_path).unlink()
