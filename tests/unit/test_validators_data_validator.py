"""
ABOUTME: Tests for DataValidator class with quality scoring and interactive reporting
ABOUTME: Comprehensive unit test coverage for all validation methods and edge cases
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import yaml

from validators.data_validator import DataValidator


class TestDataValidatorInit:
    """Test DataValidator initialization."""

    def test_init_without_config(self):
        """Test initialization without configuration file."""
        validator = DataValidator()
        assert validator.config == {}
        assert validator.logger is not None

    def test_init_with_valid_config(self):
        """Test initialization with valid YAML configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                'validation': {
                    'numeric_fields': ['amount', 'count', 'value']
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            validator = DataValidator(config_path=config_path)
            assert 'validation' in validator.config
            assert validator.config['validation']['numeric_fields'] == ['amount', 'count', 'value']
        finally:
            config_path.unlink()

    def test_init_with_missing_config(self):
        """Test initialization with non-existent configuration file."""
        validator = DataValidator(config_path=Path('/nonexistent/config.yaml'))
        assert validator.config == {}


class TestValidateDataframe:
    """Test validate_dataframe method."""

    def test_validate_empty_dataframe(self):
        """Test validation of empty DataFrame."""
        validator = DataValidator()
        df = pd.DataFrame()

        results = validator.validate_dataframe(df)

        assert results['valid'] is False
        assert results['total_rows'] == 0
        assert results['total_columns'] == 0
        assert results['quality_score'] == 0.0
        assert 'DataFrame is empty' in results['issues']

    def test_validate_valid_dataframe(self):
        """Test validation of valid DataFrame."""
        validator = DataValidator()
        df = pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'name': ['A', 'B', 'C', 'D', 'E'],
            'value': [10.5, 20.3, 15.7, 25.2, 30.1]
        })

        results = validator.validate_dataframe(df)

        assert results['valid'] is True
        assert results['total_rows'] == 5
        assert results['total_columns'] == 3
        assert results['quality_score'] == 100.0
        assert len(results['issues']) == 0

    def test_validate_with_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        validator = DataValidator()
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['A', 'B', 'C']
        })

        results = validator.validate_dataframe(
            df,
            required_fields=['id', 'name', 'email', 'phone']
        )

        assert results['valid'] is False
        assert results['quality_score'] < 100.0
        assert any('Missing required fields' in issue for issue in results['issues'])

    def test_validate_with_unique_field_duplicates(self):
        """Test validation detects duplicate unique field values."""
        validator = DataValidator()
        df = pd.DataFrame({
            'id': [1, 2, 2, 4, 5],
            'name': ['A', 'B', 'C', 'D', 'E']
        })

        results = validator.validate_dataframe(df, unique_field='id')

        assert 'duplicate' in str(results['issues']).lower()
        assert results['quality_score'] < 100.0

    def test_validate_with_high_missing_data(self):
        """Test validation detects high missing data percentage (>50%)."""
        validator = DataValidator()
        df = pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'value': [np.nan, np.nan, np.nan, 4.0, 5.0]
        })

        results = validator.validate_dataframe(df)

        assert results['valid'] is False
        assert results['quality_score'] < 70.0
        assert 'High missing data' in str(results['issues'])
        assert 'missing_data' in results

    def test_validate_with_moderate_missing_data(self):
        """Test validation detects moderate missing data (20-50%)."""
        validator = DataValidator()
        df = pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'value': [np.nan, 2.0, 3.0, 4.0, 5.0]
        })

        results = validator.validate_dataframe(df)

        assert results['valid'] is True
        assert results['quality_score'] < 100.0
        assert 'Moderate missing data' in str(results['issues'])

    def test_validate_quality_score_bounds(self):
        """Test quality score never goes below 0 or above 100."""
        validator = DataValidator()

        # Empty dataframe should give 0
        df_empty = pd.DataFrame()
        results_empty = validator.validate_dataframe(df_empty)
        assert results_empty['quality_score'] == 0.0

        # Valid dataframe should give 100
        df_valid = pd.DataFrame({'col': [1, 2, 3]})
        results_valid = validator.validate_dataframe(df_valid)
        assert results_valid['quality_score'] == 100.0


class TestCheckMissingData:
    """Test _check_missing_data method."""

    def test_check_missing_data_no_missing_values(self):
        """Test when there are no missing values."""
        validator = DataValidator()
        df = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': ['a', 'b', 'c']
        })

        missing = validator._check_missing_data(df)

        assert missing == {}

    def test_check_missing_data_with_missing_values(self):
        """Test detection of missing values per column."""
        validator = DataValidator()
        df = pd.DataFrame({
            'col1': [1, np.nan, 3],
            'col2': ['a', 'b', np.nan],
            'col3': [10.5, 20.3, 30.1]
        })

        missing = validator._check_missing_data(df)

        assert 'col1' in missing
        assert 'col2' in missing
        assert 'col3' not in missing
        assert missing['col1'] == pytest.approx(1/3, abs=0.01)
        assert missing['col2'] == pytest.approx(1/3, abs=0.01)

    def test_check_missing_data_single_row(self):
        """Test missing data calculation with single row."""
        validator = DataValidator()
        df = pd.DataFrame({
            'col1': [np.nan],
            'col2': [5]
        })

        missing = validator._check_missing_data(df)

        assert missing['col1'] == 1.0
        assert 'col2' not in missing

    def test_check_missing_data_all_missing(self):
        """Test when entire column is missing."""
        validator = DataValidator()
        df = pd.DataFrame({
            'col1': [np.nan, np.nan, np.nan],
            'col2': [1, 2, 3]
        })

        missing = validator._check_missing_data(df)

        assert missing['col1'] == 1.0
        assert 'col2' not in missing


class TestCheckDataTypes:
    """Test _check_data_types method."""

    def test_check_data_types_no_issues(self):
        """Test when all data types are valid."""
        validator = DataValidator()
        df = pd.DataFrame({
            'year': [2020, 2021, 2022],
            'value': [100, 200, 300],
            'name': ['a', 'b', 'c']
        })

        issues = validator._check_data_types(df)

        assert issues == []

    def test_check_data_types_with_numeric_field_issues(self):
        """Test detection of non-numeric values in numeric fields."""
        validator = DataValidator()
        df = pd.DataFrame({
            'year': [2020, 'not_a_year', 2022],
            'value': [100, 200, 300]
        })

        issues = validator._check_data_types(df)

        assert any('year' in issue for issue in issues)

    def test_check_data_types_custom_numeric_fields_from_config(self):
        """Test data type checking with custom numeric fields from config."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                'validation': {
                    'numeric_fields': ['amount', 'quantity']
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            validator = DataValidator(config_path=config_path)
            df = pd.DataFrame({
                'amount': [100, 'invalid', 300],
                'quantity': [1, 2, 3]
            })

            issues = validator._check_data_types(df)

            assert any('amount' in issue for issue in issues)
        finally:
            config_path.unlink()

    def test_check_data_types_all_null_numeric_field(self):
        """Test that all-null numeric fields don't trigger type issues."""
        validator = DataValidator()
        df = pd.DataFrame({
            'year': [np.nan, np.nan, np.nan],
            'value': [1, 2, 3]
        })

        issues = validator._check_data_types(df)

        # Should not report issues for all-null columns
        assert not any('year' in issue for issue in issues)


class TestGenerateReport:
    """Test generate_report method."""

    def test_generate_report_valid_data(self):
        """Test report generation for valid data."""
        validator = DataValidator()
        results = {
            'valid': True,
            'total_rows': 100,
            'total_columns': 5,
            'quality_score': 95.0,
            'issues': [],
            'missing_data': {}
        }

        report = validator.generate_report(results)

        assert '✓ PASS' in report
        assert '95.0/100.0' in report
        assert '100' in report
        assert '5' in report

    def test_generate_report_invalid_data(self):
        """Test report generation for invalid data."""
        validator = DataValidator()
        results = {
            'valid': False,
            'total_rows': 10,
            'total_columns': 3,
            'quality_score': 45.0,
            'issues': ['Issue 1', 'Issue 2'],
            'missing_data': {'col1': 0.5, 'col2': 0.3}
        }

        report = validator.generate_report(results)

        assert '✗ FAIL' in report
        assert '45.0/100.0' in report
        assert 'Issue 1' in report
        assert 'Issue 2' in report
        assert 'col1' in report

    def test_generate_report_structure(self):
        """Test report has expected structure."""
        validator = DataValidator()
        results = {
            'valid': True,
            'total_rows': 50,
            'total_columns': 4,
            'quality_score': 80.0,
            'issues': [],
            'missing_data': {}
        }

        report = validator.generate_report(results)

        assert '=' * 60 in report
        assert 'DATA VALIDATION REPORT' in report
        assert 'Overall Status' in report
        assert 'Quality Score' in report
        assert 'Dataset Size' in report


class TestGenerateInteractiveReport:
    """Test generate_interactive_report method."""

    def test_generate_interactive_report_creates_file(self):
        """Test that interactive report file is created."""
        validator = DataValidator()
        results = {
            'valid': True,
            'total_rows': 100,
            'total_columns': 5,
            'quality_score': 85.0,
            'issues': [],
            'missing_data': {'col1': 0.1},
            'type_issues': []
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.html'
            validator.generate_interactive_report(results, output_path)

            assert output_path.exists()
            assert output_path.suffix == '.html'

    def test_generate_interactive_report_with_missing_data(self):
        """Test interactive report with missing data visualization."""
        validator = DataValidator()
        results = {
            'valid': True,
            'total_rows': 100,
            'total_columns': 3,
            'quality_score': 70.0,
            'issues': [],
            'missing_data': {'col1': 0.2, 'col2': 0.1},
            'type_issues': []
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.html'
            validator.generate_interactive_report(results, output_path)

            content = output_path.read_text()
            # Plotly HTML should contain data
            assert 'Plotly' in content or 'plotly' in content.lower()

    def test_generate_interactive_report_with_type_issues(self):
        """Test interactive report with type issues visualization."""
        validator = DataValidator()
        results = {
            'valid': False,
            'total_rows': 100,
            'total_columns': 3,
            'quality_score': 50.0,
            'issues': ['Type issues detected'],
            'missing_data': {},
            'type_issues': ['year: 5 non-numeric values', 'amount: 3 non-numeric values']
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.html'
            validator.generate_interactive_report(results, output_path)

            assert output_path.exists()
            content = output_path.read_text()
            assert len(content) > 0

    def test_generate_interactive_report_creates_parent_directory(self):
        """Test that parent directories are created if needed."""
        validator = DataValidator()
        results = {
            'valid': True,
            'total_rows': 50,
            'total_columns': 2,
            'quality_score': 90.0,
            'issues': [],
            'missing_data': {},
            'type_issues': []
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'deep' / 'nested' / 'report.html'
            validator.generate_interactive_report(results, output_path)

            assert output_path.exists()
            assert output_path.parent.exists()


class TestGetQualityColor:
    """Test _get_quality_color method."""

    def test_get_quality_color_excellent(self):
        """Test color for excellent quality score."""
        validator = DataValidator()
        color = validator._get_quality_color(90.0)
        assert color == 'green'

    def test_get_quality_color_good(self):
        """Test color for good quality score."""
        validator = DataValidator()
        color = validator._get_quality_color(70.0)
        assert color == 'yellow'

    def test_get_quality_color_poor(self):
        """Test color for poor quality score."""
        validator = DataValidator()
        color = validator._get_quality_color(30.0)
        assert color == 'red'

    def test_get_quality_color_boundaries(self):
        """Test color at exact boundaries."""
        validator = DataValidator()

        # Boundary at 80
        assert validator._get_quality_color(80.0) == 'green'
        assert validator._get_quality_color(79.9) == 'yellow'

        # Boundary at 60
        assert validator._get_quality_color(60.0) == 'yellow'
        assert validator._get_quality_color(59.9) == 'red'


class TestValidateDataframeWithBSEEData:
    """Integration tests with realistic BSEE production data."""

    def test_validate_bsee_production_data(self):
        """Test validation with real BSEE production data format."""
        validator = DataValidator()
        df = pd.DataFrame({
            'api_well_number': ['177015020401', '177015020401', '177015130450'],
            'production_date': ['2020-01-01', '2020-02-01', '2020-01-01'],
            'oil_bbls': [50000, 52000, 75000],
            'gas_mcf': [100000, 102000, 150000],
            'water_bbls': [25000, 24000, 35000],
            'rig_days': [0, 0, 0],
            'days_in_month': [31, 29, 31]
        })

        results = validator.validate_dataframe(
            df,
            required_fields=['api_well_number', 'production_date', 'oil_bbls'],
            unique_field='api_well_number'  # Not actually unique
        )

        assert results['valid'] is True
        assert results['total_rows'] == 3
        assert results['total_columns'] == 7

    def test_validate_bsee_well_data(self):
        """Test validation with BSEE well data format."""
        validator = DataValidator()
        df = pd.DataFrame({
            'api_well_number': ['177015020401', '177015130450', '177015250300'],
            'well_name': ['Anchor-02', 'Julia-01', 'Jack-01'],
            'spud_date': ['2010-06-10', '2015-03-01', '2008-05-20'],
            'completion_date': ['2010-09-15', '2015-08-30', '2008-10-15'],
            'water_depth': [510, 1200, 4500],
            'total_depth': [8520, 12000, 30000],
            'operator_name': ['Shell', 'BP', 'Chevron'],
            'well_status': ['PRODUCING', 'PRODUCING', 'PRODUCING']
        })

        results = validator.validate_dataframe(
            df,
            required_fields=['api_well_number', 'well_name', 'water_depth'],
            unique_field='api_well_number'  # Should be unique
        )

        assert results['valid'] is True
        assert len(results['issues']) == 0
