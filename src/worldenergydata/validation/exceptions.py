"""
Validation exceptions for data quality checks.
"""

class ValidationError(Exception):
    """Base exception for validation errors."""
    
    def __init__(self, message, field=None, value=None, rule=None):
        self.message = message
        self.field = field
        self.value = value
        self.rule = rule
        super().__init__(self.format_message())
    
    def format_message(self):
        """Format error message with context."""
        parts = [self.message]
        if self.field:
            parts.append(f"Field: {self.field}")
        if self.value is not None:
            parts.append(f"Value: {self.value}")
        if self.rule:
            parts.append(f"Rule: {self.rule}")
        return " | ".join(parts)


class SchemaValidationError(ValidationError):
    """Exception for schema validation failures."""
    pass


class DataTypeError(ValidationError):
    """Exception for data type validation failures."""
    pass


class RangeValidationError(ValidationError):
    """Exception for value range validation failures."""
    pass


class RequiredFieldError(ValidationError):
    """Exception for missing required fields."""
    pass


class DateFormatError(ValidationError):
    """Exception for date format validation failures."""
    pass


class ConsistencyError(ValidationError):
    """Exception for data consistency validation failures."""
    pass


class CrossFieldValidationError(ValidationError):
    """Exception for cross-field dependency failures."""
    
    def __init__(self, message, fields=None, **kwargs):
        self.fields = fields or []
        super().__init__(message, **kwargs)
    
    def format_message(self):
        """Format error message with multiple fields."""
        parts = [self.message]
        if self.fields:
            parts.append(f"Fields: {', '.join(self.fields)}")
        if self.rule:
            parts.append(f"Rule: {self.rule}")
        return " | ".join(parts)