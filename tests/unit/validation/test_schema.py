"""Tests for validation schema definitions (schema.py)."""

import pytest

from worldenergydata.validation.schema import (
    BSEESchemas,
    DataType,
    DateFormat,
    FieldSchema,
    FinancialSchemas,
    ValidationSchema,
)


class TestDataType:
    def test_all_members(self):
        expected = {
            "STRING", "INTEGER", "FLOAT", "DECIMAL",
            "DATE", "DATETIME", "BOOLEAN", "ARRAY", "OBJECT",
        }
        assert {m.name for m in DataType} == expected

    def test_values(self):
        assert DataType.STRING.value == "string"
        assert DataType.INTEGER.value == "integer"
        assert DataType.FLOAT.value == "float"


class TestDateFormat:
    def test_all_members(self):
        expected = {
            "YYYYMM", "YYYY_MM_DD", "MM_DD_YYYY",
            "DD_MM_YYYY", "YYYYMMDD", "ISO8601",
        }
        assert {m.name for m in DateFormat} == expected

    def test_yyyymm_value(self):
        assert DateFormat.YYYYMM.value == "YYYYMM"


class TestFieldSchema:
    def test_minimal(self):
        fs = FieldSchema(name="test_field", data_type=DataType.STRING)
        assert fs.name == "test_field"
        assert fs.data_type == DataType.STRING
        assert fs.required is True
        assert fs.nullable is False

    def test_all_defaults(self):
        fs = FieldSchema(name="x", data_type=DataType.INTEGER)
        assert fs.min_value is None
        assert fs.max_value is None
        assert fs.min_length is None
        assert fs.max_length is None
        assert fs.pattern is None
        assert fs.allowed_values is None
        assert fs.date_format is None
        assert fs.precision is None
        assert fs.scale is None
        assert fs.default_value is None
        assert fs.description is None
        assert fs.unit is None

    def test_with_range(self):
        fs = FieldSchema(
            name="depth", data_type=DataType.FLOAT,
            min_value=0, max_value=50000, unit="feet",
        )
        assert fs.min_value == 0
        assert fs.max_value == 50000
        assert fs.unit == "feet"

    def test_with_pattern(self):
        fs = FieldSchema(
            name="api", data_type=DataType.STRING,
            pattern=r"^\d{12}$",
        )
        assert fs.pattern == r"^\d{12}$"

    def test_invalid_pattern_raises(self):
        with pytest.raises(ValueError, match="Invalid regex"):
            FieldSchema(name="bad", data_type=DataType.STRING, pattern="[invalid")

    def test_min_greater_than_max_raises(self):
        with pytest.raises(ValueError, match="min_value cannot be greater"):
            FieldSchema(
                name="bad", data_type=DataType.FLOAT,
                min_value=100, max_value=50,
            )

    def test_min_length_greater_than_max_length_raises(self):
        with pytest.raises(ValueError, match="min_length cannot be greater"):
            FieldSchema(
                name="bad", data_type=DataType.STRING,
                min_length=10, max_length=5,
            )

    def test_with_allowed_values(self):
        fs = FieldSchema(
            name="status", data_type=DataType.STRING,
            allowed_values=["ACTIVE", "INACTIVE"],
        )
        assert fs.allowed_values == ["ACTIVE", "INACTIVE"]


class TestValidationSchema:
    def test_basic(self):
        schema = ValidationSchema(name="test_schema")
        assert schema.name == "test_schema"
        assert schema.version == "1.0.0"
        assert schema.fields == []

    def test_with_version(self):
        schema = ValidationSchema(name="s", version="2.0.0", description="desc")
        assert schema.version == "2.0.0"
        assert schema.description == "desc"

    def test_add_field(self):
        schema = ValidationSchema(name="s")
        fs = FieldSchema(name="col_a", data_type=DataType.STRING)
        schema.add_field(fs)
        assert len(schema.fields) == 1
        assert schema.fields[0].name == "col_a"

    def test_get_field_found(self):
        schema = ValidationSchema(name="s")
        fs = FieldSchema(name="col_a", data_type=DataType.STRING)
        schema.add_field(fs)
        assert schema.get_field("col_a") is fs

    def test_get_field_not_found(self):
        schema = ValidationSchema(name="s")
        assert schema.get_field("missing") is None

    def test_get_required_fields(self):
        schema = ValidationSchema(name="s")
        schema.add_field(FieldSchema(name="req", data_type=DataType.STRING, required=True))
        schema.add_field(FieldSchema(name="opt", data_type=DataType.STRING, required=False))
        required = schema.get_required_fields()
        assert "req" in required
        assert "opt" not in required

    def test_add_cross_field_rule(self):
        schema = ValidationSchema(name="s")
        rule = {"type": "date_consistency", "fields": ["a", "b"]}
        schema.add_cross_field_rule(rule)
        assert len(schema.cross_field_rules) == 1

    def test_to_dict(self):
        schema = ValidationSchema(name="test", version="1.0.0")
        fs = FieldSchema(
            name="depth", data_type=DataType.FLOAT,
            min_value=0, max_value=50000,
        )
        schema.add_field(fs)
        d = schema.to_dict()
        assert d["name"] == "test"
        assert d["version"] == "1.0.0"
        assert len(d["fields"]) == 1
        assert d["fields"][0]["name"] == "depth"
        assert d["fields"][0]["data_type"] == "float"
        assert d["fields"][0]["min_value"] == 0

    def test_to_dict_with_date_format(self):
        schema = ValidationSchema(name="s")
        fs = FieldSchema(
            name="date", data_type=DataType.DATE,
            date_format=DateFormat.YYYY_MM_DD,
        )
        schema.add_field(fs)
        d = schema.to_dict()
        assert d["fields"][0]["date_format"] == "YYYY-MM-DD"


class TestBSEESchemas:
    def test_production_schema(self):
        schema = BSEESchemas.production_schema()
        assert schema.name == "BSEE_Production"
        required = schema.get_required_fields()
        assert "PRODUCTION_DATE" in required
        assert "API_WELL_NUMBER" in required

    def test_production_schema_field_count(self):
        schema = BSEESchemas.production_schema()
        assert len(schema.fields) >= 6

    def test_production_schema_cross_field_rules(self):
        schema = BSEESchemas.production_schema()
        assert len(schema.cross_field_rules) >= 1

    def test_well_schema(self):
        schema = BSEESchemas.well_schema()
        assert schema.name == "BSEE_Well"
        field = schema.get_field("API_WELL_NUMBER")
        assert field is not None
        assert field.required is True

    def test_well_schema_fields(self):
        schema = BSEESchemas.well_schema()
        field_names = [f.name for f in schema.fields]
        assert "API_WELL_NUMBER" in field_names
        assert "WELL_STATUS" in field_names

    def test_lease_schema(self):
        schema = BSEESchemas.lease_schema()
        assert schema.name == "BSEE_Lease"
        required = schema.get_required_fields()
        assert "LEASE_NUMBER" in required

    def test_lease_schema_cross_field_rules(self):
        schema = BSEESchemas.lease_schema()
        assert len(schema.cross_field_rules) >= 1


class TestFinancialSchemas:
    def test_npv_schema(self):
        schema = FinancialSchemas.npv_schema()
        assert schema.name == "NPV_Analysis"
        required = schema.get_required_fields()
        assert "DISCOUNT_RATE" in required
        assert "OIL_PRICE" in required

    def test_npv_schema_field_count(self):
        schema = FinancialSchemas.npv_schema()
        assert len(schema.fields) >= 5

    def test_npv_discount_rate_range(self):
        schema = FinancialSchemas.npv_schema()
        field = schema.get_field("DISCOUNT_RATE")
        assert field.min_value == 0
        assert field.max_value == 1
