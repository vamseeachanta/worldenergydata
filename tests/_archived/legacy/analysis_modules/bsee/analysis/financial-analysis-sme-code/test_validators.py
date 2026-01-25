"""
Unit tests for data validation functions
Tests input/output validation for SME financial analysis
"""

import unittest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from datetime import datetime, date

from src.worldenergydata.modules.bsee.analysis.financial.validators import (
    DataValidator,
    validate_required_columns,
    validate_date_columns,
    validate_numeric_columns,
    validate_lease_numbers,
    validate_production_data,
    validate_drilling_data,
    validate_financial_assumptions
)


class TestDataValidator(unittest.TestCase):
    """Test suite for data validation functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = DataValidator()
        
        # Sample valid data
        self.valid_leases = pd.DataFrame({
            'LEASE_NUM': ['G12345', 'G23456'],
            'LEASE_NAME': ['Lease A', 'Lease B'],
            'DEV_NAME': ['DEV_1', 'DEV_2'],
            'DEV_TYPE_EFF': ['subsea', 'dry tree']
        })
        
        self.valid_production = pd.DataFrame({
            'YearMonth': pd.date_range('2023-01-01', periods=3, freq='MS'),
            'WELL_A': [100.5, 200.0, 150.75],
            'WELL_B': [50.0, 75.5, 60.25]
        })
        
        self.valid_drilling = pd.DataFrame({
            'WELL_NAME': ['WELL_A', 'WELL_B'],
            'DRILL_DAYS': [30, 45],
            'COMP_DAYS': [15, 20],
            'WELL_SPUD_DATE': pd.to_datetime(['2023-01-01', '2023-02-01']),
            'TOTAL_DEPTH_DATE': pd.to_datetime(['2023-01-31', '2023-03-17'])
        })
        
        self.valid_assumptions = {
            'NPV_Discount_Rate': 0.10,
            'Drilling_Cost_Per_Day_USD': 100000,
            'Completion_Cost_Per_Day_USD': 75000,
            'Oil_Price_Per_Barrel': 80.0,
            'OPEX_Per_Barrel': 25.0,
            'Tax_Rate': 0.35
        }
    
    def test_validate_required_columns(self):
        """Test validation of required columns"""
        # Valid case
        result = validate_required_columns(
            self.valid_leases,
            ['LEASE_NUM', 'LEASE_NAME', 'DEV_NAME']
        )
        self.assertTrue(result)
        
        # Missing column
        with self.assertRaises(ValueError) as context:
            validate_required_columns(
                self.valid_leases,
                ['LEASE_NUM', 'MISSING_COLUMN']
            )
        self.assertIn('Missing required columns', str(context.exception))
        
        # Empty dataframe
        empty_df = pd.DataFrame()
        with self.assertRaises(ValueError):
            validate_required_columns(empty_df, ['ANY_COLUMN'])
    
    def test_validate_date_columns(self):
        """Test date column validation and conversion"""
        # Create mixed date formats
        mixed_dates = pd.DataFrame({
            'DATE1': pd.to_datetime(['2023-01-01', '2023-02-01']),
            'DATE2': ['2023-03-01', '2023-04-01'],  # String dates
            'DATE3': ['01/05/2023', '06/01/2023'],  # Different format
            'DATE4': ['invalid', 'not a date']  # Invalid dates
        })
        
        # Validate and convert
        result = validate_date_columns(
            mixed_dates,
            ['DATE1', 'DATE2', 'DATE3', 'DATE4']
        )
        
        # Check conversions
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result['DATE1']))
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result['DATE2']))
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result['DATE3']))
        
        # Invalid dates should be NaT
        self.assertTrue(result['DATE4'].isna().all())
    
    def test_validate_numeric_columns(self):
        """Test numeric column validation"""
        mixed_numeric = pd.DataFrame({
            'NUM1': [1, 2, 3],
            'NUM2': ['4', '5', '6'],  # String numbers
            'NUM3': [7.5, 8.5, 9.5],
            'NUM4': ['invalid', 'not a number', 'text']
        })
        
        # Validate and convert
        result = validate_numeric_columns(
            mixed_numeric,
            ['NUM1', 'NUM2', 'NUM3', 'NUM4'],
            fill_invalid=0
        )
        
        # Check conversions
        self.assertTrue(pd.api.types.is_numeric_dtype(result['NUM1']))
        self.assertTrue(pd.api.types.is_numeric_dtype(result['NUM2']))
        self.assertEqual(result['NUM2'].iloc[0], 4.0)
        
        # Invalid should be filled with 0
        self.assertTrue((result['NUM4'] == 0).all())
        
        # Test without fill
        result_nan = validate_numeric_columns(
            mixed_numeric,
            ['NUM4'],
            fill_invalid=None
        )
        self.assertTrue(result_nan['NUM4'].isna().all())
    
    def test_validate_lease_numbers(self):
        """Test lease number validation and normalization"""
        mixed_leases = pd.DataFrame({
            'LEASE_NUM': ['12345', 'G23456', ' 34567 ', 'g45678', 'INVALID']
        })
        
        result = self.validator.validate_lease_numbers(mixed_leases)
        
        # All valid numbers should have G prefix
        self.assertEqual(result['LEASE_NUM'].iloc[0], 'G12345')
        self.assertEqual(result['LEASE_NUM'].iloc[1], 'G23456')
        self.assertEqual(result['LEASE_NUM'].iloc[2], 'G34567')
        self.assertEqual(result['LEASE_NUM'].iloc[3], 'G45678')
        
        # Invalid format should be preserved with warning
        self.assertEqual(result['LEASE_NUM'].iloc[4], 'INVALID')
        
        # Check validation report
        report = self.validator.get_validation_report()
        self.assertIn('warnings', report)
    
    def test_validate_production_data(self):
        """Test production data validation"""
        # Valid production data
        is_valid, errors = self.validator.validate_production_data(self.valid_production)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Invalid: negative production
        invalid_prod = self.valid_production.copy()
        invalid_prod['WELL_A'] = [-100, 200, 150]
        
        is_valid, errors = self.validator.validate_production_data(invalid_prod)
        self.assertFalse(is_valid)
        self.assertIn('negative', errors[0].lower())
        
        # Invalid: missing YearMonth
        no_date_prod = self.valid_production.drop('YearMonth', axis=1)
        
        is_valid, errors = self.validator.validate_production_data(no_date_prod)
        self.assertFalse(is_valid)
        self.assertIn('YearMonth', errors[0])
    
    def test_validate_drilling_data(self):
        """Test drilling and completion data validation"""
        # Valid data
        is_valid, errors = self.validator.validate_drilling_data(self.valid_drilling)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Invalid: TD before spud
        invalid_drill = self.valid_drilling.copy()
        invalid_drill.loc[0, 'TOTAL_DEPTH_DATE'] = pd.Timestamp('2022-12-01')
        
        is_valid, errors = self.validator.validate_drilling_data(invalid_drill)
        self.assertFalse(is_valid)
        self.assertIn('before', errors[0].lower())
        
        # Invalid: negative days
        invalid_drill2 = self.valid_drilling.copy()
        invalid_drill2['DRILL_DAYS'] = [-30, 45]
        
        is_valid, errors = self.validator.validate_drilling_data(invalid_drill2)
        self.assertFalse(is_valid)
        self.assertIn('negative', errors[0].lower())
    
    def test_validate_financial_assumptions(self):
        """Test financial assumptions validation"""
        # Valid assumptions
        is_valid, errors = self.validator.validate_financial_assumptions(self.valid_assumptions)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Invalid: negative discount rate
        invalid_assump = self.valid_assumptions.copy()
        invalid_assump['NPV_Discount_Rate'] = -0.10
        
        is_valid, errors = self.validator.validate_financial_assumptions(invalid_assump)
        self.assertFalse(is_valid)
        self.assertIn('discount rate', errors[0].lower())
        
        # Invalid: tax rate > 1
        invalid_assump2 = self.valid_assumptions.copy()
        invalid_assump2['Tax_Rate'] = 1.5
        
        is_valid, errors = self.validator.validate_financial_assumptions(invalid_assump2)
        self.assertFalse(is_valid)
        self.assertIn('tax rate', errors[0].lower())
        
        # Missing required assumption
        incomplete_assump = {'NPV_Discount_Rate': 0.10}
        
        is_valid, errors = self.validator.validate_financial_assumptions(incomplete_assump)
        self.assertFalse(is_valid)
        self.assertIn('missing', errors[0].lower())
    
    def test_validate_data_consistency(self):
        """Test cross-data consistency validation"""
        # Test well consistency between production and drilling
        production = pd.DataFrame({
            'YearMonth': pd.date_range('2023-01-01', periods=3, freq='MS'),
            'WELL_A': [100, 200, 150],
            'WELL_C': [50, 75, 60]  # WELL_C not in drilling data
        })
        
        drilling = pd.DataFrame({
            'WELL_NAME': ['WELL_A', 'WELL_B'],  # WELL_B not in production
            'DRILL_DAYS': [30, 45]
        })
        
        warnings = self.validator.check_data_consistency(production, drilling)
        
        # Should have warnings about mismatched wells
        self.assertGreater(len(warnings), 0)
        self.assertTrue(any('WELL_B' in w for w in warnings))
        self.assertTrue(any('WELL_C' in w for w in warnings))
    
    def test_validate_data_types(self):
        """Test data type validation"""
        df = pd.DataFrame({
            'TEXT_COL': ['a', 'b', 'c'],
            'INT_COL': [1, 2, 3],
            'FLOAT_COL': [1.5, 2.5, 3.5],
            'DATE_COL': pd.date_range('2023-01-01', periods=3)
        })
        
        # Define expected types
        type_map = {
            'TEXT_COL': 'object',
            'INT_COL': 'int64',
            'FLOAT_COL': 'float64',
            'DATE_COL': 'datetime64[ns]'
        }
        
        is_valid, mismatches = self.validator.validate_data_types(df, type_map)
        self.assertTrue(is_valid)
        self.assertEqual(len(mismatches), 0)
        
        # Wrong type expectation
        wrong_type_map = {'TEXT_COL': 'int64'}
        is_valid, mismatches = self.validator.validate_data_types(df, wrong_type_map)
        self.assertFalse(is_valid)
        self.assertIn('TEXT_COL', mismatches)
    
    def test_validate_ranges(self):
        """Test value range validation"""
        df = pd.DataFrame({
            'PERCENTAGE': [0.1, 0.5, 0.9, 1.5],  # Last value out of range
            'DAYS': [30, 45, 60, -10],  # Last value negative
            'PRICE': [50, 80, 120, 200]
        })
        
        range_rules = {
            'PERCENTAGE': (0, 1),
            'DAYS': (0, None),  # Only minimum
            'PRICE': (0, 150)
        }
        
        violations = self.validator.validate_ranges(df, range_rules)
        
        # Should find violations
        self.assertIn('PERCENTAGE', violations)
        self.assertIn('DAYS', violations)
        self.assertIn('PRICE', violations)
        
        self.assertEqual(len(violations['PERCENTAGE']), 1)  # Row 3
        self.assertEqual(len(violations['DAYS']), 1)  # Row 3
        self.assertEqual(len(violations['PRICE']), 1)  # Row 3
    
    def test_comprehensive_validation(self):
        """Test comprehensive validation workflow"""
        # Create a validation pipeline
        validation_results = self.validator.run_comprehensive_validation({
            'leases': self.valid_leases,
            'production': self.valid_production,
            'drilling': self.valid_drilling,
            'assumptions': self.valid_assumptions
        })
        
        # All should pass
        self.assertTrue(validation_results['all_valid'])
        self.assertEqual(len(validation_results['errors']), 0)
        
        # Check individual results
        self.assertTrue(validation_results['leases_valid'])
        self.assertTrue(validation_results['production_valid'])
        self.assertTrue(validation_results['drilling_valid'])
        self.assertTrue(validation_results['assumptions_valid'])
    
    def test_validation_report_generation(self):
        """Test generation of validation report"""
        # Run some validations
        self.validator.validate_lease_numbers(self.valid_leases)
        self.validator.validate_production_data(self.valid_production)
        self.validator.validate_drilling_data(self.valid_drilling)
        
        # Generate report
        report = self.validator.generate_validation_report()
        
        # Check report structure
        self.assertIn('summary', report)
        self.assertIn('details', report)
        self.assertIn('warnings', report)
        self.assertIn('timestamp', report)
        
        # Check summary stats
        self.assertIn('total_validations', report['summary'])
        self.assertIn('passed', report['summary'])
        self.assertIn('failed', report['summary'])


if __name__ == '__main__':
    unittest.main()