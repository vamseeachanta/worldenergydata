#!/usr/bin/env python
"""
Demo script for the data validation framework.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pandas as pd
from worldenergydata.validation import ValidationSchema, DataValidator
from worldenergydata.validation.schema import BSEESchemas, FinancialSchemas

def demo_bsee_validation():
    """Demonstrate BSEE data validation."""
    print("\n" + "="*60)
    print("DEMO: BSEE Production Data Validation")
    print("="*60)
    
    # Get BSEE production schema
    schema = BSEESchemas.production_schema()
    validator = DataValidator(schema, strict=False)
    
    # Create sample data - some valid, some invalid
    test_data = pd.DataFrame([
        {
            "PRODUCTION_DATE": "202301",  # Valid
            "API_WELL_NUMBER": "177154098200",  # Valid
            "MON_O_PROD_VOL": 15000,
            "MON_G_PROD_VOL": 25000,
            "MON_W_PROD_VOL": 5000,
            "DAYS_ON_PROD": 28,
            "LEASE_NUMBER": "G12345"
        },
        {
            "PRODUCTION_DATE": "2023-02",  # Invalid format!
            "API_WELL_NUMBER": "17715409820",  # Invalid - only 11 digits!
            "MON_O_PROD_VOL": -100,  # Invalid - negative!
            "MON_G_PROD_VOL": 26000,
            "MON_W_PROD_VOL": 5500,
            "DAYS_ON_PROD": 35,  # Invalid - max 31 days!
            "LEASE_NUMBER": "G12346"
        },
        {
            "PRODUCTION_DATE": "202303",
            "API_WELL_NUMBER": "177154098202",
            "MON_O_PROD_VOL": 1000,  # Production with 0 days - inconsistent!
            "MON_G_PROD_VOL": 2000,
            "MON_W_PROD_VOL": 0,
            "DAYS_ON_PROD": 0,
            "LEASE_NUMBER": "G12347"
        }
    ])
    
    print("\nValidating BSEE production data...")
    is_valid, errors = validator.validate(test_data)
    
    print("\nValidation Report:")
    print(validator.get_validation_report())
    
    if errors:
        print("\nDetailed Errors:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error.format_message()}")

def demo_financial_validation():
    """Demonstrate financial data validation."""
    print("\n" + "="*60)
    print("DEMO: Financial NPV Data Validation")
    print("="*60)
    
    # Get NPV schema
    schema = FinancialSchemas.npv_schema()
    validator = DataValidator(schema, strict=False)
    
    # Create sample data
    test_data = {
        "DISCOUNT_RATE": 0.12,  # 12%
        "OIL_PRICE": 75.50,
        "GAS_PRICE": 3.25,
        "CAPEX": 5000000,
        "OPEX": 500000,
        "PROJECT_LIFE_YEARS": 25
    }
    
    print("\nValidating NPV analysis data...")
    is_valid, errors = validator.validate(test_data)
    
    if is_valid:
        print("✅ All financial data validations passed!")
    else:
        print("❌ Validation errors found:")
        for error in errors:
            print(f"  - {error.format_message()}")

def demo_custom_schema():
    """Demonstrate creating a custom validation schema."""
    print("\n" + "="*60)
    print("DEMO: Custom Schema Creation")
    print("="*60)
    
    from worldenergydata.validation.schema import ValidationSchema, FieldSchema, DataType, DateFormat
    
    # Create custom schema for wind energy data
    schema = ValidationSchema(
        name="WindEnergy",
        version="1.0.0",
        description="Schema for wind energy production data"
    )
    
    # Add fields
    schema.add_field(FieldSchema(
        name="TURBINE_ID",
        data_type=DataType.STRING,
        required=True,
        pattern=r"^WT-\d{6}$",
        description="Wind turbine identifier"
    ))
    
    schema.add_field(FieldSchema(
        name="PRODUCTION_DATE",
        data_type=DataType.STRING,
        required=True,
        date_format=DateFormat.YYYY_MM_DD,
        description="Production date"
    ))
    
    schema.add_field(FieldSchema(
        name="POWER_OUTPUT_MW",
        data_type=DataType.FLOAT,
        required=True,
        min_value=0,
        max_value=10,  # Max 10 MW per turbine
        unit="MW",
        description="Power output in megawatts"
    ))
    
    schema.add_field(FieldSchema(
        name="WIND_SPEED_MS",
        data_type=DataType.FLOAT,
        required=True,
        min_value=0,
        max_value=50,  # Max 50 m/s
        unit="m/s",
        description="Average wind speed"
    ))
    
    schema.add_field(FieldSchema(
        name="AVAILABILITY_PERCENT",
        data_type=DataType.FLOAT,
        required=True,
        min_value=0,
        max_value=100,
        description="Turbine availability percentage"
    ))
    
    print(f"Created custom schema: {schema.name}")
    print(f"Fields: {', '.join([f.name for f in schema.fields])}")
    
    # Test with sample data
    validator = DataValidator(schema)
    
    test_data = {
        "TURBINE_ID": "WT-123456",
        "PRODUCTION_DATE": "2023-01-15",
        "POWER_OUTPUT_MW": 2.5,
        "WIND_SPEED_MS": 12.3,
        "AVAILABILITY_PERCENT": 95.5
    }
    
    print("\nValidating wind energy data...")
    is_valid, errors = validator.validate(test_data)
    
    if is_valid:
        print("✅ Wind energy data validation passed!")
    else:
        print("❌ Validation errors:")
        for error in errors:
            print(f"  - {error.format_message()}")

if __name__ == "__main__":
    print("\n" + "*"*60)
    print("DATA VALIDATION FRAMEWORK DEMONSTRATION")
    print("*"*60)
    
    demo_bsee_validation()
    demo_financial_validation()
    demo_custom_schema()
    
    print("\n" + "*"*60)
    print("DEMONSTRATION COMPLETE")
    print("*"*60)