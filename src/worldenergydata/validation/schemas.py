"""
Validation schemas for different types of energy data.

This module contains schema definitions that specify the validation
requirements for BSEE data, financial data, and configuration data.
"""

from typing import Dict, Any, List
from datetime import datetime
import pandas as pd
from loguru import logger

from .base import ValidationSchema, ValidationResult, FieldValidator
from .rules import (
    DataTypeRule, RequiredFieldRule, RangeRule, DateFormatRule,
    APINumberRule, BSEEDateRule, CrossFieldRule, PatternRule, UniqueRule
)


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
        api_validator = FieldValidator("API_WELL_NUMBER")
        api_validator.add_rule(APINumberRule())
        api_validator.add_rule(DataTypeRule([str, int], allow_null=False))
        self.add_field_validator("API_WELL_NUMBER", api_validator)
        
        # Production Date - can be YYYY-MM-DD or YYYYMM format
        prod_date_validator = FieldValidator("PRODUCTION_DATE")
        prod_date_validator.add_rule(DateFormatRule([
            '%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y%m'
        ], min_date=datetime(1970, 1, 1), max_date=datetime.now()))
        self.add_field_validator("PRODUCTION_DATE", prod_date_validator)
        
        # Oil Volume - numeric, non-negative
        oil_volume_validator = FieldValidator("OIL_VOLUME")
        oil_volume_validator.add_rule(DataTypeRule([int, float], allow_null=True))
        oil_volume_validator.add_rule(RangeRule(min_value=0))
        self.add_field_validator("OIL_VOLUME", oil_volume_validator)
        
        # Gas Volume - numeric, non-negative  
        gas_volume_validator = FieldValidator("GAS_VOLUME")
        gas_volume_validator.add_rule(DataTypeRule([int, float], allow_null=True))
        gas_volume_validator.add_rule(RangeRule(min_value=0))
        self.add_field_validator("GAS_VOLUME", gas_volume_validator)
        
        # Water Volume - numeric, non-negative
        water_volume_validator = FieldValidator("WATER_VOLUME")
        water_volume_validator.add_rule(DataTypeRule([int, float], allow_null=True))
        water_volume_validator.add_rule(RangeRule(min_value=0))
        self.add_field_validator("WATER_VOLUME", water_volume_validator)
        
        # Lease Number - required pattern
        lease_validator = FieldValidator("LEASE_NUMBER")
        lease_validator.add_rule(PatternRule(
            r'^OCS-[A-Z]-\d+$',
            "Lease number must follow OCS-X-##### format"
        ))
        self.add_field_validator("LEASE_NUMBER", lease_validator)
        
        # Field Name - required string
        field_name_validator = FieldValidator("FIELD_NAME")
        field_name_validator.add_rule(DataTypeRule(str, allow_null=False))
        self.add_field_validator("FIELD_NAME", field_name_validator)
        
        # Days on Production - numeric, valid range
        days_prod_validator = FieldValidator("DAYS_ON_PRODUCTION")
        days_prod_validator.add_rule(DataTypeRule([int, float], allow_null=True))
        days_prod_validator.add_rule(RangeRule(min_value=0, max_value=31))
        self.add_field_validator("DAYS_ON_PRODUCTION", days_prod_validator)
        
        # Well Status - controlled vocabulary
        well_status_validator = FieldValidator("WELL_STATUS")
        well_status_validator.add_rule(PatternRule(
            r'^(ACTIVE|INACTIVE|SHUT-IN|ABANDONED|SUSPENDED)$',
            "Well status must be one of: ACTIVE, INACTIVE, SHUT-IN, ABANDONED, SUSPENDED"
        ))
        self.add_field_validator("WELL_STATUS", well_status_validator)
    
    def _setup_cross_field_rules(self):
        """Set up cross-field validation rules."""
        
        # Production consistency rule
        def validate_production_consistency(df: pd.DataFrame) -> List[str]:
            errors = []
            
            # Check for records with zero production in all categories
            zero_production = (
                (df['OIL_VOLUME'].fillna(0) == 0) &
                (df['GAS_VOLUME'].fillna(0) == 0) &
                (df['WATER_VOLUME'].fillna(0) == 0)
            )
            
            if zero_production.any():
                zero_count = zero_production.sum()
                errors.append(f"Found {zero_count} records with zero production in all categories")
            
            # Check for unrealistic production rates
            if 'DAYS_ON_PRODUCTION' in df.columns:
                high_oil_rate = (df['OIL_VOLUME'] / df['DAYS_ON_PRODUCTION'].fillna(1)) > 10000
                if high_oil_rate.any():
                    high_count = high_oil_rate.sum()
                    errors.append(f"Found {high_count} records with unrealistically high oil production rates (>10,000 bbl/day)")
            
            return errors
        
        production_consistency_rule = CrossFieldRule(
            validate_production_consistency,
            ['OIL_VOLUME', 'GAS_VOLUME', 'WATER_VOLUME', 'DAYS_ON_PRODUCTION']
        )
        self.add_cross_field_rule(production_consistency_rule)
    
    def validate(self, data: Any) -> ValidationResult:
        """Validate BSEE production data."""
        result = ValidationResult()
        result.metadata['schema_type'] = 'bsee_production'
        
        if not isinstance(data, pd.DataFrame):
            result.add_error(
                "dataset",
                "BSEE production data must be provided as a pandas DataFrame",
                rule="data_type_check"
            )
            return result
        
        # Check required fields
        required_fields = [
            'API_WELL_NUMBER', 'PRODUCTION_DATE', 'LEASE_NUMBER', 'FIELD_NAME'
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
        
        # Well Name
        well_name_validator = FieldValidator("WELL_NAME")
        well_name_validator.add_rule(DataTypeRule(str, allow_null=False))
        self.add_field_validator("WELL_NAME", well_name_validator)
        
        # Lease Number
        lease_validator = FieldValidator("LEASE_NUMBER")
        lease_validator.add_rule(PatternRule(
            r'^OCS-[A-Z]-\d+$',
            "Lease number must follow OCS-X-##### format"
        ))
        self.add_field_validator("LEASE_NUMBER", lease_validator)
        
        # Water Depth - numeric, reasonable range
        water_depth_validator = FieldValidator("WATER_DEPTH")
        water_depth_validator.add_rule(DataTypeRule([int, float], allow_null=True))
        water_depth_validator.add_rule(RangeRule(min_value=0, max_value=15000))  # feet
        self.add_field_validator("WATER_DEPTH", water_depth_validator)
        
        # Total Depth - numeric, reasonable range
        total_depth_validator = FieldValidator("TOTAL_DEPTH")
        total_depth_validator.add_rule(DataTypeRule([int, float], allow_null=True))
        total_depth_validator.add_rule(RangeRule(min_value=0, max_value=50000))  # feet
        self.add_field_validator("TOTAL_DEPTH", total_depth_validator)
        
        # Spud Date
        spud_date_validator = FieldValidator("SPUD_DATE")
        spud_date_validator.add_rule(DateFormatRule([
            '%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y'
        ], min_date=datetime(1950, 1, 1), max_date=datetime.now()))
        self.add_field_validator("SPUD_DATE", spud_date_validator)
        
        # Completion Date
        completion_date_validator = FieldValidator("COMPLETION_DATE")
        completion_date_validator.add_rule(DateFormatRule([
            '%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y'
        ], min_date=datetime(1950, 1, 1), max_date=datetime.now()))
        self.add_field_validator("COMPLETION_DATE", completion_date_validator)
        
        # Longitude - valid range
        longitude_validator = FieldValidator("LONGITUDE")
        longitude_validator.add_rule(DataTypeRule([int, float], allow_null=True))
        longitude_validator.add_rule(RangeRule(min_value=-180, max_value=180))
        self.add_field_validator("LONGITUDE", longitude_validator)
        
        # Latitude - valid range
        latitude_validator = FieldValidator("LATITUDE")
        latitude_validator.add_rule(DataTypeRule([int, float], allow_null=True))
        latitude_validator.add_rule(RangeRule(min_value=-90, max_value=90))
        self.add_field_validator("LATITUDE", latitude_validator)
        
        # Well Type
        well_type_validator = FieldValidator("WELL_TYPE")
        well_type_validator.add_rule(PatternRule(
            r'^(OIL|GAS|INJECTION|WATER|DRY|EXPLORATION)$',
            "Well type must be one of: OIL, GAS, INJECTION, WATER, DRY, EXPLORATION"
        ))
        self.add_field_validator("WELL_TYPE", well_type_validator)
    
    def _setup_cross_field_rules(self):
        """Set up cross-field validation rules."""
        
        def validate_well_consistency(df: pd.DataFrame) -> List[str]:
            errors = []
            
            # Spud date should be before or equal to completion date
            if 'SPUD_DATE' in df.columns and 'COMPLETION_DATE' in df.columns:
                spud_after_completion = pd.to_datetime(df['SPUD_DATE']) > pd.to_datetime(df['COMPLETION_DATE'])
                if spud_after_completion.any():
                    error_count = spud_after_completion.sum()
                    errors.append(f"Found {error_count} wells where spud date is after completion date")
            
            # Total depth should be greater than water depth
            if 'TOTAL_DEPTH' in df.columns and 'WATER_DEPTH' in df.columns:
                invalid_depths = df['TOTAL_DEPTH'] <= df['WATER_DEPTH']
                if invalid_depths.any():
                    error_count = invalid_depths.sum()
                    errors.append(f"Found {error_count} wells where total depth <= water depth")
            
            return errors
        
        well_consistency_rule = CrossFieldRule(
            validate_well_consistency,
            ['SPUD_DATE', 'COMPLETION_DATE', 'TOTAL_DEPTH', 'WATER_DEPTH']
        )
        self.add_cross_field_rule(well_consistency_rule)
    
    def validate(self, data: Any) -> ValidationResult:
        """Validate BSEE well data."""
        result = ValidationResult()
        result.metadata['schema_type'] = 'bsee_well'
        
        if not isinstance(data, pd.DataFrame):
            result.add_error(
                "dataset",
                "BSEE well data must be provided as a pandas DataFrame",
                rule="data_type_check"
            )
            return result
        
        # Check required fields
        required_fields = ['API_WELL_NUMBER', 'WELL_NAME', 'LEASE_NUMBER']
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
        lease_validator.add_rule(PatternRule(
            r'^OCS-[A-Z]-\d+$',
            "Lease number must follow OCS-X-##### format"
        ))
        lease_validator.add_rule(UniqueRule())
        self.add_field_validator("LEASE_NUMBER", lease_validator)
        
        # Area Code
        area_validator = FieldValidator("AREA_CODE")
        area_validator.add_rule(DataTypeRule(str, allow_null=False))
        self.add_field_validator("AREA_CODE", area_validator)
        
        # Block Number
        block_validator = FieldValidator("BLOCK_NUMBER")
        block_validator.add_rule(DataTypeRule([str, int], allow_null=False))
        self.add_field_validator("BLOCK_NUMBER", block_validator)
    
    def validate(self, data: Any) -> ValidationResult:
        """Validate BSEE lease data."""
        result = ValidationResult()
        result.metadata['schema_type'] = 'bsee_lease'
        
        if not isinstance(data, pd.DataFrame):
            result.add_error(
                "dataset",
                "BSEE lease data must be provided as a pandas DataFrame",
                rule="data_type_check"
            )
            return result
        
        # Check required fields
        required_fields = ['LEASE_NUMBER', 'AREA_CODE', 'BLOCK_NUMBER']
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
        
        # Discount Rate - percentage
        discount_rate_validator = FieldValidator("DISCOUNT_RATE")
        discount_rate_validator.add_rule(DataTypeRule([int, float], allow_null=False))
        discount_rate_validator.add_rule(RangeRule(min_value=0, max_value=100))
        self.add_field_validator("DISCOUNT_RATE", discount_rate_validator)
        
        # Cash Flow - can be negative
        cash_flow_validator = FieldValidator("CASH_FLOW")
        cash_flow_validator.add_rule(DataTypeRule([int, float], allow_null=True))
        self.add_field_validator("CASH_FLOW", cash_flow_validator)
        
        # Investment - should be positive
        investment_validator = FieldValidator("INVESTMENT")
        investment_validator.add_rule(DataTypeRule([int, float], allow_null=True))
        investment_validator.add_rule(RangeRule(min_value=0))
        self.add_field_validator("INVESTMENT", investment_validator)
        
        # Project Year - positive integer
        project_year_validator = FieldValidator("PROJECT_YEAR")
        project_year_validator.add_rule(DataTypeRule(int, allow_null=False))
        project_year_validator.add_rule(RangeRule(min_value=1, max_value=50))
        self.add_field_validator("PROJECT_YEAR", project_year_validator)
    
    def _setup_cross_field_rules(self):
        """Set up cross-field validation rules."""
        
        def validate_financial_consistency(df: pd.DataFrame) -> List[str]:
            errors = []
            
            # Check for unrealistic discount rates
            if 'DISCOUNT_RATE' in df.columns:
                high_rates = df['DISCOUNT_RATE'] > 30
                if high_rates.any():
                    errors.append("Found discount rates >30%, please verify these values")
            
            return errors
        
        financial_consistency_rule = CrossFieldRule(
            validate_financial_consistency,
            ['DISCOUNT_RATE']
        )
        self.add_cross_field_rule(financial_consistency_rule)
    
    def validate(self, data: Any) -> ValidationResult:
        """Validate financial data."""
        result = ValidationResult()
        result.metadata['schema_type'] = 'financial'
        
        if not isinstance(data, pd.DataFrame):
            result.add_error(
                "dataset",
                "Financial data must be provided as a pandas DataFrame",
                rule="data_type_check"
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
        result.metadata['schema_type'] = 'configuration'
        
        if not isinstance(data, dict):
            result.add_error(
                "configuration",
                "Configuration data must be provided as a dictionary",
                rule="data_type_check"
            )
            return result
        
        # Check for required configuration sections
        required_sections = ['basename', 'data']
        for section in required_sections:
            if section not in data:
                result.add_error(
                    section,
                    f"Required configuration section '{section}' is missing",
                    rule="required_section"
                )
        
        # Validate basename
        if 'basename' in data:
            valid_basenames = ['bsee', 'dwnld_from_zipurl', 'bsee_custom']
            if data['basename'] not in valid_basenames:
                result.add_warning(
                    'basename',
                    f"Basename '{data['basename']}' is not in recognized list: {valid_basenames}",
                    value=data['basename']
                )
        
        return result