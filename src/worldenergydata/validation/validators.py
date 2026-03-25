"""
Main data validator implementation.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
import yaml

from .exceptions import RequiredFieldError, ValidationError
from .rules import CrossFieldRules, CustomValidators, ValidationRules
from .schemas import DataType, FieldSchema, ValidationSchema

logger = logging.getLogger(__name__)


class DataValidator:
    """Main data validator for energy data."""

    def __init__(self, schema: ValidationSchema, strict: bool = True):
        """
        Initialize data validator.

        Args:
            schema: Validation schema to use
            strict: If True, raise exceptions on validation errors
        """
        self.schema = schema
        self.strict = strict
        self.errors: List[ValidationError] = []
        self.warnings: List[str] = []

    def validate(
        self, data: Union[Dict, pd.DataFrame, List[Dict]]
    ) -> Tuple[bool, List[ValidationError]]:
        """
        Validate data against schema.

        Args:
            data: Data to validate (dict, DataFrame, or list of dicts)

        Returns:
            Tuple of (is_valid, errors)
        """
        self.errors = []
        self.warnings = []

        print(f"\n[DEBUG] validate() called with data type: {type(data).__name__}")
        print(f"[DEBUG] Schema name: {self.schema.name}, strict mode: {self.strict}")

        # Convert data to consistent format
        if isinstance(data, pd.DataFrame):
            records = data.to_dict("records")
        elif isinstance(data, dict):
            records = [data]
            print(f"[DEBUG] Dict input wrapped in list. Input: {data}")
        elif isinstance(data, list):
            records = data
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

        # Validate each record
        for idx, record in enumerate(records):
            try:
                self._validate_record(record, idx)
            except ValidationError as e:
                if self.strict:
                    raise
                self.errors.append(e)

        # Validate cross-field rules if no errors
        if not self.errors and len(records) > 0:
            for idx, record in enumerate(records):
                try:
                    self._validate_cross_fields(record, idx)
                except ValidationError as e:
                    if self.strict:
                        raise
                    self.errors.append(e)

        return len(self.errors) == 0, self.errors

    def _validate_record(self, record: Dict[str, Any], row_idx: int):
        """Validate a single record."""
        print(f"\n[DEBUG] _validate_record() called for row {row_idx}")
        print(f"[DEBUG] Record keys: {list(record.keys())}")

        # Check for required fields
        required_fields = self.schema.get_required_fields()
        for field_name in required_fields:
            if field_name not in record:
                error = RequiredFieldError(
                    f"Required field missing in row {row_idx}",
                    field=field_name,
                    row_index=row_idx,
                )
                if self.strict:
                    raise error
                self.errors.append(error)
                continue

        # Validate each field
        # Support both list and dict for schema.fields
        if isinstance(self.schema.fields, dict):
            field_schemas = self.schema.fields.values()
        else:
            field_schemas = self.schema.fields
        for field_schema in field_schemas:
            field_name = field_schema.name
            value = record.get(field_name)
            print(
                f"[DEBUG] Validating field: {field_name}, value: {value} (type: {type(value).__name__})"
            )

            try:
                self._validate_field(value, field_schema, row_idx)
                print(f"[DEBUG] Field {field_name} validation passed")
            except ValidationError as e:
                print(
                    f"[DEBUG] Field {field_name} validation FAILED: {type(e).__name__}: {e.message}"
                )
                e.message = f"Row {row_idx}: {e.message}"
                e.row_index = row_idx
                if self.strict:
                    raise
                print("[DEBUG] Non-strict mode: appending error to self.errors")
                self.errors.append(e)
                print(f"[DEBUG] self.errors now has {len(self.errors)} errors")

    def _validate_field(self, value: Any, field_schema: FieldSchema, row_idx: int):
        """Validate a single field value against schema constraints."""
        field_name = field_schema.name
        logger.debug(
            "Validating field=%s, value=%s (type=%s), expected=%s",
            field_name, value, type(value).__name__, field_schema.data_type
        )

        # Guard: Required field validation (early return on failure)
        self._validate_required_field(value, field_name, field_schema.required)

        # Guard: Skip further validation for null values in nullable fields
        if value is None and field_schema.nullable:
            logger.debug("Skipping validation for %s - null and nullable", field_name)
            return

        # Core validation: data type
        self._validate_field_type(value, field_name, field_schema.data_type)

        # Type-specific validations via dispatch
        self._validate_type_specific(value, field_name, field_schema)

        # Optional constraint validations
        self._validate_field_constraints(value, field_name, field_schema)

        # Custom BSEE validators
        self._validate_bsee_custom(value, field_name)

    def _validate_required_field(
        self, value: Any, field_name: str, is_required: bool
    ) -> None:
        """Validate required field constraint."""
        ValidationRules.validate_required(value, field_name, is_required)
        logger.debug("Required validation passed for %s", field_name)

    def _validate_field_type(
        self, value: Any, field_name: str, data_type: DataType
    ) -> None:
        """Validate field data type."""
        ValidationRules.validate_data_type(value, field_name, data_type)
        logger.debug("Type validation passed for %s", field_name)

    def _validate_type_specific(
        self, value: Any, field_name: str, field_schema: FieldSchema
    ) -> None:
        """Apply type-specific validations using dispatch pattern."""
        # Dispatch table for type-specific validations
        type_validators = {
            DataType.INTEGER: self._validate_numeric_range,
            DataType.FLOAT: self._validate_numeric_range,
            DataType.DECIMAL: self._validate_numeric_range,
            DataType.STRING: self._validate_string_length,
        }
        validator = type_validators.get(field_schema.data_type)
        if validator:
            validator(value, field_name, field_schema)

    def _validate_numeric_range(
        self, value: Any, field_name: str, field_schema: FieldSchema
    ) -> None:
        """Validate numeric field range constraints."""
        ValidationRules.validate_range(
            value, field_name, field_schema.min_value, field_schema.max_value
        )

    def _validate_string_length(
        self, value: Any, field_name: str, field_schema: FieldSchema
    ) -> None:
        """Validate string field length constraints."""
        ValidationRules.validate_length(
            value, field_name, field_schema.min_length, field_schema.max_length
        )

    def _validate_field_constraints(
        self, value: Any, field_name: str, field_schema: FieldSchema
    ) -> None:
        """Validate optional field constraints (pattern, allowed values, date format)."""
        if field_schema.pattern:
            ValidationRules.validate_pattern(value, field_name, field_schema.pattern)

        if field_schema.allowed_values:
            ValidationRules.validate_allowed_values(
                value, field_name, field_schema.allowed_values
            )

        if field_schema.date_format:
            ValidationRules.validate_date_format(
                value, field_name, field_schema.date_format
            )

    def _validate_bsee_custom(self, value: Any, field_name: str) -> None:
        """Apply BSEE-specific custom validators."""
        if not self.schema.name.startswith("BSEE"):
            return

        # Dispatch table for BSEE custom validators
        bsee_validators = {
            "API_WELL_NUMBER": lambda v: CustomValidators.validate_api_well_number(
                str(v) if v else ""
            ),
            "LEASE_NUMBER": lambda v: CustomValidators.validate_lease_number(
                str(v) if v else ""
            ),
            "PRODUCTION_DATE": lambda v: CustomValidators.validate_production_date(
                str(v) if v else ""
            ),
        }
        validator = bsee_validators.get(field_name)
        if validator:
            validator(value)

    def _validate_cross_fields(self, record: Dict[str, Any], row_idx: int):
        """Validate cross-field rules."""
        for rule in self.schema.cross_field_rules:
            self._apply_cross_field_rule(record, rule, row_idx)

    def _apply_cross_field_rule(self, record: Dict[str, Any], rule: Dict, row_idx: int):
        """Apply a single cross-field validation rule."""
        rule_type = rule.get("type")
        if not rule_type:
            return

        validator = self._get_cross_field_validator(rule_type)
        if not validator:
            return

        try:
            validator(record, rule)
        except ValidationError as e:
            e.message = f"Row {row_idx}: {e.message}"
            e.row_index = row_idx
            raise

    def _get_cross_field_validator(self, rule_type: str):
        """Get the validator function for a cross-field rule type."""
        validators = {
            "date_consistency": self._validate_date_consistency_rule,
            "production_consistency": self._validate_production_consistency_rule,
            "sum_consistency": self._validate_sum_consistency_rule,
            "percentage_sum": self._validate_percentage_sum_rule,
        }
        return validators.get(rule_type)

    def _validate_date_consistency_rule(self, record: Dict[str, Any], rule: Dict):
        """Validate date consistency between two date fields."""
        fields = rule.get("fields", [])
        if len(fields) < 2:
            return
        CrossFieldRules.validate_date_consistency(record, fields[0], fields[1])

    def _validate_production_consistency_rule(self, record: Dict[str, Any], rule: Dict):
        """Validate production data consistency."""
        CrossFieldRules.validate_production_consistency(record)

    def _validate_sum_consistency_rule(self, record: Dict[str, Any], rule: Dict):
        """Validate that component fields sum to total field."""
        component_fields = rule.get("component_fields", [])
        total_field = rule.get("total_field")
        if not component_fields or not total_field:
            return
        tolerance = rule.get("tolerance", 0.01)
        CrossFieldRules.validate_sum_consistency(
            record, component_fields, total_field, tolerance
        )

    def _validate_percentage_sum_rule(self, record: Dict[str, Any], rule: Dict):
        """Validate that percentage fields sum to 100%."""
        percentage_fields = rule.get("fields", [])
        if not percentage_fields:
            return
        tolerance = rule.get("tolerance", 0.01)
        CrossFieldRules.validate_percentage_sum(record, percentage_fields, tolerance)

    def validate_file(
        self, file_path: Union[str, Path]
    ) -> Tuple[bool, List[ValidationError]]:
        """
        Validate data from a file.

        Args:
            file_path: Path to data file (CSV, Excel, JSON, or YAML)

        Returns:
            Tuple of (is_valid, errors)
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Load data based on file extension
        extension = file_path.suffix.lower()

        if extension == ".csv":
            data = pd.read_csv(file_path)
        elif extension in [".xlsx", ".xls"]:
            data = pd.read_excel(file_path)
        elif extension == ".json":
            with open(file_path, "r") as f:
                data = json.load(f)
        elif extension in [".yaml", ".yml"]:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported file type: {extension}")

        return self.validate(data)

    def get_validation_report(self) -> str:
        """Get formatted validation report."""
        report = []
        report.append(f"Validation Report for Schema: {self.schema.name}")
        report.append("=" * 50)

        if not self.errors:
            report.append("✅ All validations passed!")
        else:
            report.append(f"❌ Found {len(self.errors)} validation errors:")
            report.append("")
            for idx, error in enumerate(self.errors, 1):
                report.append(f"{idx}. {error.format_message()}")

        if self.warnings:
            report.append("")
            report.append(f"⚠️ Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                report.append(f"   - {warning}")

        return "\n".join(report)


class ValidationManager:
    """Manager for multiple validation schemas."""

    def __init__(self):
        """Initialize validation manager."""
        self.schemas: Dict[str, ValidationSchema] = {}
        self.validators: Dict[str, DataValidator] = {}

    def register_schema(self, schema: ValidationSchema):
        """Register a validation schema."""
        self.schemas[schema.name] = schema
        self.validators[schema.name] = DataValidator(schema)

    def get_validator(self, schema_name: str) -> Optional[DataValidator]:
        """Get validator by schema name."""
        return self.validators.get(schema_name)

    def validate_with_schema(
        self, schema_name: str, data: Any
    ) -> Tuple[bool, List[ValidationError]]:
        """Validate data with named schema."""
        validator = self.get_validator(schema_name)
        if not validator:
            raise ValueError(f"Schema not found: {schema_name}")
        return validator.validate(data)

    def load_schema_from_file(self, file_path: Union[str, Path]):
        """Load schema from JSON or YAML file."""
        file_path = Path(file_path)

        with open(file_path, "r") as f:
            if file_path.suffix in [".yaml", ".yml"]:
                schema_dict = yaml.safe_load(f)
            else:
                schema_dict = json.load(f)

        # Convert dict to ValidationSchema
        schema = ValidationSchema(
            name=schema_dict["name"],
            version=schema_dict.get("version", "1.0.0"),
            description=schema_dict.get("description"),
        )

        # Add fields
        for field_dict in schema_dict.get("fields", []):
            field_schema = FieldSchema(
                name=field_dict["name"],
                data_type=DataType(field_dict["data_type"]),
                required=field_dict.get("required", True),
                nullable=field_dict.get("nullable", False),
                min_value=field_dict.get("min_value"),
                max_value=field_dict.get("max_value"),
                min_length=field_dict.get("min_length"),
                max_length=field_dict.get("max_length"),
                pattern=field_dict.get("pattern"),
                allowed_values=field_dict.get("allowed_values"),
                precision=field_dict.get("precision"),
                scale=field_dict.get("scale"),
                default_value=field_dict.get("default_value"),
                description=field_dict.get("description"),
                unit=field_dict.get("unit"),
            )
            schema.add_field(field_schema)

        # Add cross-field rules
        for rule in schema_dict.get("cross_field_rules", []):
            schema.add_cross_field_rule(rule)

        # Add custom validators
        for validator_name in schema_dict.get("custom_validators", []):
            schema.custom_validators.append(validator_name)

        self.register_schema(schema)
        return schema


# Import required field error for convenience
