"""
Validation rules engine for energy data.
"""

from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import re
from .exceptions import (
    ValidationError,
    DataTypeError,
    RangeValidationError,
    RequiredFieldError,
    DateFormatError,
    ConsistencyError,
    CrossFieldValidationError
)
from .schema import DataType, DateFormat, FieldSchema


class ValidationRules:
    """Core validation rules for data quality checks."""
    
    @staticmethod
    def validate_required(value: Any, field_name: str, required: bool) -> bool:
        """Validate required field."""
        if required and (value is None or value == ""):
            raise RequiredFieldError(f"Required field is missing", field=field_name)
        return True
    
    @staticmethod
    def validate_data_type(value: Any, field_name: str, data_type: DataType) -> bool:
        """Validate data type."""
        if value is None:
            return True  # Null handling is done separately
        
        type_validators = {
            DataType.STRING: lambda v: isinstance(v, str),
            DataType.INTEGER: lambda v: isinstance(v, int) or (isinstance(v, str) and v.isdigit()),
            DataType.FLOAT: lambda v: isinstance(v, (int, float)) or ValidationRules._is_numeric_string(v),
            DataType.DECIMAL: lambda v: isinstance(v, (int, float)) or ValidationRules._is_numeric_string(v),
            DataType.BOOLEAN: lambda v: isinstance(v, bool) or v in ["true", "false", "True", "False", "0", "1"],
            DataType.DATE: lambda v: ValidationRules._is_date_string(v),
            DataType.DATETIME: lambda v: ValidationRules._is_datetime_string(v),
            DataType.ARRAY: lambda v: isinstance(v, (list, tuple)),
            DataType.OBJECT: lambda v: isinstance(v, dict),
        }
        
        validator = type_validators.get(data_type)
        if validator and not validator(value):
            raise DataTypeError(
                f"Invalid data type",
                field=field_name,
                value=value,
                rule=f"Expected {data_type.value}"
            )
        return True
    
    @staticmethod
    def validate_range(value: Any, field_name: str, min_value: Optional[float] = None, 
                      max_value: Optional[float] = None) -> bool:
        """Validate numeric range."""
        if value is None:
            return True
        
        numeric_value = ValidationRules._to_numeric(value)
        if numeric_value is None:
            return True
        
        if min_value is not None and numeric_value < min_value:
            raise RangeValidationError(
                f"Value below minimum",
                field=field_name,
                value=numeric_value,
                rule=f"Minimum: {min_value}"
            )
        
        if max_value is not None and numeric_value > max_value:
            raise RangeValidationError(
                f"Value above maximum",
                field=field_name,
                value=numeric_value,
                rule=f"Maximum: {max_value}"
            )
        
        return True
    
    @staticmethod
    def validate_length(value: Any, field_name: str, min_length: Optional[int] = None,
                       max_length: Optional[int] = None) -> bool:
        """Validate string length."""
        if value is None:
            return True
        
        if not isinstance(value, str):
            value = str(value)
        
        length = len(value)
        
        if min_length is not None and length < min_length:
            raise ValidationError(
                f"String too short",
                field=field_name,
                value=value,
                rule=f"Minimum length: {min_length}"
            )
        
        if max_length is not None and length > max_length:
            raise ValidationError(
                f"String too long",
                field=field_name,
                value=value,
                rule=f"Maximum length: {max_length}"
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
                f"Pattern mismatch",
                field=field_name,
                value=value,
                rule=f"Pattern: {pattern}"
            )
        
        return True
    
    @staticmethod
    def validate_allowed_values(value: Any, field_name: str, allowed_values: Optional[List[Any]]) -> bool:
        """Validate against allowed values list."""
        if allowed_values is None or value is None:
            return True
        
        if value not in allowed_values:
            raise ValidationError(
                f"Value not in allowed list",
                field=field_name,
                value=value,
                rule=f"Allowed: {allowed_values}"
            )
        
        return True
    
    @staticmethod
    def validate_date_format(value: Any, field_name: str, date_format: Optional[DateFormat]) -> bool:
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
                f"Invalid date format",
                field=field_name,
                value=value,
                rule=f"Expected format: {date_format.value}"
            )
        
        # Additional validation for actual date values
        if date_format == DateFormat.YYYYMM:
            year = int(value[:4])
            month = int(value[4:6])
            if not (1900 <= year <= 2100) or not (1 <= month <= 12):
                raise DateFormatError(
                    f"Invalid date values",
                    field=field_name,
                    value=value,
                    rule="Valid year (1900-2100) and month (1-12)"
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
    def validate_date_consistency(data: Dict[str, Any], start_field: str, end_field: str) -> bool:
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
                    f"End date must be after start date",
                    fields=[start_field, end_field],
                    rule="date_consistency"
                )
        except (ValueError, TypeError) as e:
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
                rule="production_consistency"
            )
        
        # If there are production days, at least one volume should be non-zero
        if days_on_prod > 0 and oil_prod == 0 and gas_prod == 0:
            # This is a warning, not necessarily an error
            pass  # Could log warning here
        
        return True
    
    @staticmethod
    def validate_sum_consistency(data: Dict[str, Any], component_fields: List[str], 
                                 total_field: str, tolerance: float = 0.01) -> bool:
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
                rule="sum_consistency"
            )
        
        return True
    
    @staticmethod
    def validate_percentage_sum(data: Dict[str, Any], percentage_fields: List[str], 
                               tolerance: float = 0.01) -> bool:
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
                rule="percentage_sum"
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
                rule="12-digit API number"
            )
        
        # Additional checks could include state/county codes
        state_code = value[:2]
        if state_code not in ["17", "22", "48"]:  # Example: Louisiana, Texas offshore codes
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
                rule="Alphanumeric lease number"
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
                rule="YYYYMM format required"
            )
        
        year = int(value[:4])
        month = int(value[4:6])
        
        current_year = datetime.now().year
        if not (1900 <= year <= current_year + 1):
            raise DateFormatError(
                f"Invalid year in production date",
                value=value,
                rule=f"Year must be between 1900 and {current_year + 1}"
            )
        
        if not (1 <= month <= 12):
            raise DateFormatError(
                "Invalid month in production date",
                value=value,
                rule="Month must be between 1 and 12"
            )
        
        return True