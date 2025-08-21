"""
Validation schema definitions for energy data.
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import re


class DataType(Enum):
    """Supported data types for validation."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    DECIMAL = "decimal"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class DateFormat(Enum):
    """Common date formats in energy data."""
    YYYYMM = "YYYYMM"  # BSEE format: 202301
    YYYY_MM_DD = "YYYY-MM-DD"  # ISO format
    MM_DD_YYYY = "MM/DD/YYYY"  # US format
    DD_MM_YYYY = "DD/MM/YYYY"  # EU format
    YYYYMMDD = "YYYYMMDD"  # Compact format
    ISO8601 = "ISO8601"  # Full ISO format with time


@dataclass
class FieldSchema:
    """Schema definition for a single field."""
    
    name: str
    data_type: DataType
    required: bool = True
    nullable: bool = False
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    date_format: Optional[DateFormat] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    default_value: Optional[Any] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    
    def __post_init__(self):
        """Validate field schema configuration."""
        if self.pattern:
            try:
                re.compile(self.pattern)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern for field {self.name}: {e}")
        
        if self.min_value is not None and self.max_value is not None:
            if self.min_value > self.max_value:
                raise ValueError(f"min_value cannot be greater than max_value for field {self.name}")
        
        if self.min_length is not None and self.max_length is not None:
            if self.min_length > self.max_length:
                raise ValueError(f"min_length cannot be greater than max_length for field {self.name}")


@dataclass
class ValidationSchema:
    """Complete validation schema for a dataset."""
    
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None
    fields: List[FieldSchema] = field(default_factory=list)
    cross_field_rules: List[Dict[str, Any]] = field(default_factory=list)
    custom_validators: List[str] = field(default_factory=list)
    
    def add_field(self, field_schema: FieldSchema):
        """Add a field to the schema."""
        self.fields.append(field_schema)
    
    def get_field(self, field_name: str) -> Optional[FieldSchema]:
        """Get field schema by name."""
        for field_schema in self.fields:
            if field_schema.name == field_name:
                return field_schema
        return None
    
    def get_required_fields(self) -> List[str]:
        """Get list of required field names."""
        return [f.name for f in self.fields if f.required]
    
    def add_cross_field_rule(self, rule: Dict[str, Any]):
        """Add a cross-field validation rule."""
        self.cross_field_rules.append(rule)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert schema to dictionary format."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "fields": [
                {
                    "name": f.name,
                    "data_type": f.data_type.value,
                    "required": f.required,
                    "nullable": f.nullable,
                    "min_value": f.min_value,
                    "max_value": f.max_value,
                    "min_length": f.min_length,
                    "max_length": f.max_length,
                    "pattern": f.pattern,
                    "allowed_values": f.allowed_values,
                    "date_format": f.date_format.value if f.date_format else None,
                    "precision": f.precision,
                    "scale": f.scale,
                    "default_value": f.default_value,
                    "description": f.description,
                    "unit": f.unit,
                }
                for f in self.fields
            ],
            "cross_field_rules": self.cross_field_rules,
            "custom_validators": self.custom_validators,
        }


# Predefined schemas for common BSEE data types
class BSEESchemas:
    """Collection of predefined BSEE data schemas."""
    
    @staticmethod
    def production_schema() -> ValidationSchema:
        """Schema for BSEE production data."""
        schema = ValidationSchema(
            name="BSEE_Production",
            version="1.0.0",
            description="Validation schema for BSEE oil and gas production data"
        )
        
        # Production date field
        schema.add_field(FieldSchema(
            name="PRODUCTION_DATE",
            data_type=DataType.STRING,
            required=True,
            pattern=r"^\d{6}$",  # YYYYMM format
            date_format=DateFormat.YYYYMM,
            description="Production month in YYYYMM format"
        ))
        
        # API well number
        schema.add_field(FieldSchema(
            name="API_WELL_NUMBER",
            data_type=DataType.STRING,
            required=True,
            pattern=r"^\d{12}$",  # 12-digit API number
            description="12-digit API well identifier"
        ))
        
        # Oil production volume
        schema.add_field(FieldSchema(
            name="MON_O_PROD_VOL",
            data_type=DataType.FLOAT,
            required=True,
            min_value=0,
            max_value=10000000,  # Max 10 million barrels/month
            unit="barrels",
            description="Monthly oil production volume"
        ))
        
        # Gas production volume
        schema.add_field(FieldSchema(
            name="MON_G_PROD_VOL",
            data_type=DataType.FLOAT,
            required=True,
            min_value=0,
            max_value=100000000,  # Max 100 million MCF/month
            unit="MCF",
            description="Monthly gas production volume"
        ))
        
        # Water production volume
        schema.add_field(FieldSchema(
            name="MON_W_PROD_VOL",
            data_type=DataType.FLOAT,
            required=False,
            nullable=True,
            min_value=0,
            max_value=10000000,
            unit="barrels",
            description="Monthly water production volume"
        ))
        
        # Days on production
        schema.add_field(FieldSchema(
            name="DAYS_ON_PROD",
            data_type=DataType.INTEGER,
            required=True,
            min_value=0,
            max_value=31,
            description="Number of days on production in the month"
        ))
        
        # Lease number
        schema.add_field(FieldSchema(
            name="LEASE_NUMBER",
            data_type=DataType.STRING,
            required=True,
            pattern=r"^[A-Z0-9]+$",
            max_length=10,
            description="BSEE lease identifier"
        ))
        
        # Add cross-field rules
        schema.add_cross_field_rule({
            "type": "production_consistency",
            "description": "If DAYS_ON_PROD is 0, all production volumes should be 0",
            "fields": ["DAYS_ON_PROD", "MON_O_PROD_VOL", "MON_G_PROD_VOL"],
        })
        
        return schema
    
    @staticmethod
    def well_schema() -> ValidationSchema:
        """Schema for BSEE well data."""
        schema = ValidationSchema(
            name="BSEE_Well",
            version="1.0.0",
            description="Validation schema for BSEE well master data"
        )
        
        # API well number
        schema.add_field(FieldSchema(
            name="API_WELL_NUMBER",
            data_type=DataType.STRING,
            required=True,
            pattern=r"^\d{12}$",
            description="12-digit API well identifier"
        ))
        
        # Well name
        schema.add_field(FieldSchema(
            name="WELL_NAME",
            data_type=DataType.STRING,
            required=True,
            max_length=100,
            description="Well name"
        ))
        
        # Spud date
        schema.add_field(FieldSchema(
            name="SPUD_DATE",
            data_type=DataType.DATE,
            required=False,
            nullable=True,
            date_format=DateFormat.YYYY_MM_DD,
            description="Well spud date"
        ))
        
        # Total depth
        schema.add_field(FieldSchema(
            name="TOTAL_DEPTH",
            data_type=DataType.FLOAT,
            required=False,
            nullable=True,
            min_value=0,
            max_value=50000,  # Max 50,000 feet
            unit="feet",
            description="Total well depth"
        ))
        
        # Water depth
        schema.add_field(FieldSchema(
            name="WATER_DEPTH",
            data_type=DataType.FLOAT,
            required=False,
            nullable=True,
            min_value=0,
            max_value=12000,  # Max 12,000 feet water depth
            unit="feet",
            description="Water depth at well location"
        ))
        
        # Well status
        schema.add_field(FieldSchema(
            name="WELL_STATUS",
            data_type=DataType.STRING,
            required=True,
            allowed_values=["ACTIVE", "INACTIVE", "PLUGGED", "ABANDONED", "SUSPENDED"],
            description="Current well status"
        ))
        
        # Surface latitude
        schema.add_field(FieldSchema(
            name="SURFACE_LATITUDE",
            data_type=DataType.FLOAT,
            required=False,
            nullable=True,
            min_value=-90,
            max_value=90,
            precision=6,
            description="Surface location latitude"
        ))
        
        # Surface longitude
        schema.add_field(FieldSchema(
            name="SURFACE_LONGITUDE",
            data_type=DataType.FLOAT,
            required=False,
            nullable=True,
            min_value=-180,
            max_value=180,
            precision=6,
            description="Surface location longitude"
        ))
        
        return schema
    
    @staticmethod
    def lease_schema() -> ValidationSchema:
        """Schema for BSEE lease data."""
        schema = ValidationSchema(
            name="BSEE_Lease",
            version="1.0.0",
            description="Validation schema for BSEE lease data"
        )
        
        # Lease number
        schema.add_field(FieldSchema(
            name="LEASE_NUMBER",
            data_type=DataType.STRING,
            required=True,
            pattern=r"^[A-Z0-9]+$",
            max_length=10,
            description="BSEE lease identifier"
        ))
        
        # Lease area
        schema.add_field(FieldSchema(
            name="AREA_CODE",
            data_type=DataType.STRING,
            required=True,
            allowed_values=["GOM", "PAC", "ATL", "ALA"],
            description="Lease area code"
        ))
        
        # Block number
        schema.add_field(FieldSchema(
            name="BLOCK_NUMBER",
            data_type=DataType.STRING,
            required=True,
            max_length=20,
            description="Block number"
        ))
        
        # Lease effective date
        schema.add_field(FieldSchema(
            name="LEASE_EFF_DATE",
            data_type=DataType.DATE,
            required=True,
            date_format=DateFormat.YYYY_MM_DD,
            description="Lease effective date"
        ))
        
        # Lease expiration date
        schema.add_field(FieldSchema(
            name="LEASE_EXPIR_DATE",
            data_type=DataType.DATE,
            required=False,
            nullable=True,
            date_format=DateFormat.YYYY_MM_DD,
            description="Lease expiration date"
        ))
        
        # Add cross-field rule for dates
        schema.add_cross_field_rule({
            "type": "date_consistency",
            "description": "Lease expiration date must be after effective date",
            "fields": ["LEASE_EFF_DATE", "LEASE_EXPIR_DATE"],
        })
        
        return schema


class FinancialSchemas:
    """Collection of financial data schemas."""
    
    @staticmethod
    def npv_schema() -> ValidationSchema:
        """Schema for NPV analysis data."""
        schema = ValidationSchema(
            name="NPV_Analysis",
            version="1.0.0",
            description="Validation schema for NPV financial analysis"
        )
        
        # Discount rate
        schema.add_field(FieldSchema(
            name="DISCOUNT_RATE",
            data_type=DataType.FLOAT,
            required=True,
            min_value=0,
            max_value=1,  # 0-100%
            precision=4,
            description="Discount rate for NPV calculation"
        ))
        
        # Oil price
        schema.add_field(FieldSchema(
            name="OIL_PRICE",
            data_type=DataType.FLOAT,
            required=True,
            min_value=0,
            max_value=500,  # Max $500/barrel
            unit="USD/barrel",
            description="Oil price assumption"
        ))
        
        # Gas price
        schema.add_field(FieldSchema(
            name="GAS_PRICE",
            data_type=DataType.FLOAT,
            required=True,
            min_value=0,
            max_value=50,  # Max $50/MCF
            unit="USD/MCF",
            description="Gas price assumption"
        ))
        
        # CAPEX
        schema.add_field(FieldSchema(
            name="CAPEX",
            data_type=DataType.FLOAT,
            required=True,
            min_value=0,
            unit="USD",
            description="Capital expenditure"
        ))
        
        # OPEX
        schema.add_field(FieldSchema(
            name="OPEX",
            data_type=DataType.FLOAT,
            required=True,
            min_value=0,
            unit="USD",
            description="Operating expenditure"
        ))
        
        # Project life
        schema.add_field(FieldSchema(
            name="PROJECT_LIFE_YEARS",
            data_type=DataType.INTEGER,
            required=True,
            min_value=1,
            max_value=100,
            description="Project life in years"
        ))
        
        return schema