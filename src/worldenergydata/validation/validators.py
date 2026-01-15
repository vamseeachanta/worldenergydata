"""
Main data validator implementation.
"""

from typing import Any, Dict, List, Optional, Union, Tuple
import pandas as pd
from pathlib import Path
import json
import yaml
import logging

from .schemas import ValidationSchema, FieldSchema, DataType
from .rules import ValidationRules, CrossFieldRules, CustomValidators
from .exceptions import (
    ValidationError,
    SchemaValidationError,
    RequiredFieldError,
    DataTypeError,
    RangeValidationError,
    DateFormatError,
    ConsistencyError,
    CrossFieldValidationError
)

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
        
    def validate(self, data: Union[Dict, pd.DataFrame, List[Dict]]) -> Tuple[bool, List[ValidationError]]:
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
            records = data.to_dict('records')
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
                    row_index=row_idx
                )
                if self.strict:
                    raise error
                self.errors.append(error)
                continue

        # Validate each field
        for field_schema in self.schema.fields.values():
            field_name = field_schema.name
            value = record.get(field_name)
            print(f"[DEBUG] Validating field: {field_name}, value: {value} (type: {type(value).__name__})")

            try:
                self._validate_field(value, field_schema, row_idx)
                print(f"[DEBUG] Field {field_name} validation passed")
            except ValidationError as e:
                print(f"[DEBUG] Field {field_name} validation FAILED: {type(e).__name__}: {e.message}")
                e.message = f"Row {row_idx}: {e.message}"
                e.row_index = row_idx
                if self.strict:
                    raise
                print(f"[DEBUG] Non-strict mode: appending error to self.errors")
                self.errors.append(e)
                print(f"[DEBUG] self.errors now has {len(self.errors)} errors")
    
    def _validate_field(self, value: Any, field_schema: FieldSchema, row_idx: int):
        """Validate a single field value."""
        field_name = field_schema.name

        print(f"[DEBUG] _validate_field() called: field={field_name}, value={value} (type: {type(value).__name__}), expected_type={field_schema.data_type}")

        # Required validation
        try:
            ValidationRules.validate_required(value, field_name, field_schema.required)
            print(f"[DEBUG] Required validation passed for {field_name}")
        except ValidationError as e:
            print(f"[DEBUG] Required validation FAILED for {field_name}: {e}")
            raise

        # Skip further validation if null and nullable
        if value is None and field_schema.nullable:
            print(f"[DEBUG] Skipping validation for {field_name} - null and nullable")
            return

        # Data type validation
        print(f"[DEBUG] About to call ValidationRules.validate_data_type() for {field_name}")
        try:
            ValidationRules.validate_data_type(value, field_name, field_schema.data_type)
            print(f"[DEBUG] Type validation PASSED for {field_name}")
        except ValidationError as e:
            print(f"[DEBUG] Type validation FAILED for {field_name}: {type(e).__name__}: {e.message}")
            raise
        
        # Range validation for numeric types
        if field_schema.data_type in [DataType.INTEGER, DataType.FLOAT, DataType.DECIMAL]:
            ValidationRules.validate_range(
                value, field_name, 
                field_schema.min_value, 
                field_schema.max_value
            )
        
        # Length validation for strings
        if field_schema.data_type == DataType.STRING:
            ValidationRules.validate_length(
                value, field_name,
                field_schema.min_length,
                field_schema.max_length
            )
        
        # Pattern validation
        if field_schema.pattern:
            ValidationRules.validate_pattern(value, field_name, field_schema.pattern)
        
        # Allowed values validation
        if field_schema.allowed_values:
            ValidationRules.validate_allowed_values(
                value, field_name, 
                field_schema.allowed_values
            )
        
        # Date format validation
        if field_schema.date_format:
            ValidationRules.validate_date_format(
                value, field_name, 
                field_schema.date_format
            )
        
        # Custom validators (only for BSEE schemas)
        if self.schema.name.startswith("BSEE"):
            if field_name == "API_WELL_NUMBER":
                CustomValidators.validate_api_well_number(str(value) if value else "")
            elif field_name == "LEASE_NUMBER":
                CustomValidators.validate_lease_number(str(value) if value else "")
            elif field_name == "PRODUCTION_DATE":
                CustomValidators.validate_production_date(str(value) if value else "")
    
    def _validate_cross_fields(self, record: Dict[str, Any], row_idx: int):
        """Validate cross-field rules."""
        for rule in self.schema.cross_field_rules:
            rule_type = rule.get("type")
            
            try:
                if rule_type == "date_consistency":
                    fields = rule.get("fields", [])
                    if len(fields) >= 2:
                        CrossFieldRules.validate_date_consistency(
                            record, fields[0], fields[1]
                        )
                
                elif rule_type == "production_consistency":
                    CrossFieldRules.validate_production_consistency(record)
                
                elif rule_type == "sum_consistency":
                    component_fields = rule.get("component_fields", [])
                    total_field = rule.get("total_field")
                    tolerance = rule.get("tolerance", 0.01)
                    if component_fields and total_field:
                        CrossFieldRules.validate_sum_consistency(
                            record, component_fields, total_field, tolerance
                        )
                
                elif rule_type == "percentage_sum":
                    percentage_fields = rule.get("fields", [])
                    tolerance = rule.get("tolerance", 0.01)
                    if percentage_fields:
                        CrossFieldRules.validate_percentage_sum(
                            record, percentage_fields, tolerance
                        )
                        
            except ValidationError as e:
                e.message = f"Row {row_idx}: {e.message}"
                e.row_index = row_idx
                raise
    
    def validate_file(self, file_path: Union[str, Path]) -> Tuple[bool, List[ValidationError]]:
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
        
        if extension == '.csv':
            data = pd.read_csv(file_path)
        elif extension in ['.xlsx', '.xls']:
            data = pd.read_excel(file_path)
        elif extension == '.json':
            with open(file_path, 'r') as f:
                data = json.load(f)
        elif extension in ['.yaml', '.yml']:
            with open(file_path, 'r') as f:
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
    
    def validate_with_schema(self, schema_name: str, data: Any) -> Tuple[bool, List[ValidationError]]:
        """Validate data with named schema."""
        validator = self.get_validator(schema_name)
        if not validator:
            raise ValueError(f"Schema not found: {schema_name}")
        return validator.validate(data)
    
    def load_schema_from_file(self, file_path: Union[str, Path]):
        """Load schema from JSON or YAML file."""
        file_path = Path(file_path)
        
        with open(file_path, 'r') as f:
            if file_path.suffix in ['.yaml', '.yml']:
                schema_dict = yaml.safe_load(f)
            else:
                schema_dict = json.load(f)
        
        # Convert dict to ValidationSchema
        schema = ValidationSchema(
            name=schema_dict['name'],
            version=schema_dict.get('version', '1.0.0'),
            description=schema_dict.get('description')
        )
        
        # Add fields
        for field_dict in schema_dict.get('fields', []):
            field_schema = FieldSchema(
                name=field_dict['name'],
                data_type=DataType(field_dict['data_type']),
                required=field_dict.get('required', True),
                nullable=field_dict.get('nullable', False),
                min_value=field_dict.get('min_value'),
                max_value=field_dict.get('max_value'),
                min_length=field_dict.get('min_length'),
                max_length=field_dict.get('max_length'),
                pattern=field_dict.get('pattern'),
                allowed_values=field_dict.get('allowed_values'),
                precision=field_dict.get('precision'),
                scale=field_dict.get('scale'),
                default_value=field_dict.get('default_value'),
                description=field_dict.get('description'),
                unit=field_dict.get('unit')
            )
            schema.add_field(field_schema)
        
        # Add cross-field rules
        for rule in schema_dict.get('cross_field_rules', []):
            schema.add_cross_field_rule(rule)
        
        # Add custom validators
        for validator_name in schema_dict.get('custom_validators', []):
            schema.custom_validators.append(validator_name)
        
        self.register_schema(schema)
        return schema


# Import required field error for convenience
from .exceptions import RequiredFieldError