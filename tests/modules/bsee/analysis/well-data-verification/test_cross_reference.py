"""
Tests for cross-reference module functionality.

Tests Excel file reading, field mapping, comparison algorithms,
and discrepancy reporting.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import yaml

from worldenergydata.modules.analysis.verification.cross_reference import (
    ExcelBenchmarkReader,
    FieldMapper,
    ComparisonEngine,
    DiscrepancyReporter,
    CrossReferenceModule,
    MappingConfig,
    ComparisonResult,
    Discrepancy
)


class TestExcelBenchmarkReader:
    """Test Excel file reading and parsing functionality."""
    
    def test_read_xlsx_file(self, tmp_path):
        """Test reading XLSX file."""
        # Create test Excel file
        excel_path = tmp_path / "benchmark.xlsx"
        test_data = pd.DataFrame({
            'Well_ID': ['W001', 'W002', 'W003'],
            'Oil_Production': [1000, 2000, 1500],
            'Gas_Production': [5000, 6000, 5500],
            'Date': ['2024-01-01', '2024-01-01', '2024-01-01']
        })
        test_data.to_excel(excel_path, index=False)
        
        reader = ExcelBenchmarkReader()
        data = reader.read_file(excel_path)
        
        assert isinstance(data, pd.DataFrame)
        assert len(data) == 3
        assert 'Well_ID' in data.columns
        assert data['Oil_Production'].sum() == 4500
    
    def test_read_multiple_sheets(self, tmp_path):
        """Test reading Excel file with multiple sheets."""
        excel_path = tmp_path / "multi_sheet.xlsx"
        
        with pd.ExcelWriter(excel_path) as writer:
            pd.DataFrame({'A': [1, 2, 3]}).to_excel(writer, sheet_name='Sheet1', index=False)
            pd.DataFrame({'B': [4, 5, 6]}).to_excel(writer, sheet_name='Sheet2', index=False)
        
        reader = ExcelBenchmarkReader()
        sheets = reader.read_all_sheets(excel_path)
        
        assert len(sheets) == 2
        assert 'Sheet1' in sheets
        assert 'Sheet2' in sheets
        assert len(sheets['Sheet1']) == 3
    
    def test_handle_missing_file(self):
        """Test handling of missing Excel file."""
        reader = ExcelBenchmarkReader()
        
        with pytest.raises(FileNotFoundError):
            reader.read_file(Path("nonexistent.xlsx"))
    
    def test_parse_dates_in_excel(self, tmp_path):
        """Test parsing of date columns in Excel."""
        excel_path = tmp_path / "dates.xlsx"
        test_data = pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=5),
            'Value': [100, 200, 300, 400, 500]
        })
        test_data.to_excel(excel_path, index=False)
        
        reader = ExcelBenchmarkReader()
        data = reader.read_file(excel_path, parse_dates=['Date'])
        
        assert pd.api.types.is_datetime64_any_dtype(data['Date'])
        assert data['Date'].iloc[0].year == 2024
    
    def test_handle_empty_excel(self, tmp_path):
        """Test handling of empty Excel file."""
        excel_path = tmp_path / "empty.xlsx"
        pd.DataFrame().to_excel(excel_path, index=False)
        
        reader = ExcelBenchmarkReader()
        data = reader.read_file(excel_path)
        
        assert isinstance(data, pd.DataFrame)
        assert len(data) == 0


class TestFieldMapper:
    """Test field mapping configuration and functionality."""
    
    def test_create_mapping_from_config(self):
        """Test creating field mapping from configuration."""
        config = MappingConfig({
            'well_id': 'Well_ID',
            'oil_volume': 'Oil_Production_BBL',
            'gas_volume': 'Gas_Production_MCF',
            'date': 'Production_Date'
        })
        
        mapper = FieldMapper(config)
        
        assert mapper.get_excel_column('well_id') == 'Well_ID'
        assert mapper.get_database_field('Oil_Production_BBL') == 'oil_volume'
    
    def test_map_dataframe_columns(self):
        """Test mapping DataFrame columns."""
        config = MappingConfig({
            'well_id': 'Well_ID',
            'oil_volume': 'Oil_Prod'
        })
        mapper = FieldMapper(config)
        
        df = pd.DataFrame({
            'Well_ID': ['W001', 'W002'],
            'Oil_Prod': [100, 200],
            'Other_Col': [1, 2]
        })
        
        mapped_df = mapper.map_dataframe(df)
        
        assert 'well_id' in mapped_df.columns
        assert 'oil_volume' in mapped_df.columns
        assert 'Well_ID' not in mapped_df.columns
        assert mapped_df['well_id'].iloc[0] == 'W001'
    
    def test_fuzzy_column_matching(self):
        """Test fuzzy matching for column names."""
        mapper = FieldMapper()
        
        # Test various column name variations
        assert mapper.fuzzy_match('well_id', 'Well ID')
        assert mapper.fuzzy_match('oil_production', 'Oil Prod')
        assert mapper.fuzzy_match('gas_volume', 'Gas Vol')
        assert not mapper.fuzzy_match('well_id', 'lease_number')
    
    def test_load_mapping_from_yaml(self, tmp_path):
        """Test loading mapping configuration from YAML."""
        yaml_path = tmp_path / "mapping.yaml"
        yaml_content = """
        field_mappings:
          well_id: Well_Identifier
          oil_volume: Oil_Production
          gas_volume: Gas_Production
        
        data_types:
          well_id: str
          oil_volume: float
          gas_volume: float
        """
        yaml_path.write_text(yaml_content)
        
        config = MappingConfig.from_yaml(yaml_path)
        mapper = FieldMapper(config)
        
        assert mapper.get_excel_column('well_id') == 'Well_Identifier'
        assert mapper.config.data_types['oil_volume'] == 'float'
    
    def test_handle_missing_columns(self):
        """Test handling of missing columns during mapping."""
        config = MappingConfig({
            'well_id': 'Well_ID',
            'oil_volume': 'Oil_Prod',
            'missing_field': 'NonExistent'
        })
        mapper = FieldMapper(config)
        
        df = pd.DataFrame({
            'Well_ID': ['W001'],
            'Oil_Prod': [100]
        })
        
        mapped_df = mapper.map_dataframe(df, skip_missing=True)
        
        assert 'well_id' in mapped_df.columns
        assert 'missing_field' not in mapped_df.columns


class TestComparisonEngine:
    """Test data comparison algorithms."""
    
    def test_numeric_comparison_with_tolerance(self):
        """Test numeric comparison with tolerance."""
        engine = ComparisonEngine(numeric_tolerance=0.01)
        
        result = engine.compare_numeric(100.0, 100.5, tolerance=0.01)
        assert result.is_match is False
        assert result.difference == 0.5
        
        result = engine.compare_numeric(100.0, 100.001, tolerance=0.01)
        assert result.is_match is True
        assert result.difference == 0.001
    
    def test_string_comparison(self):
        """Test string comparison with various options."""
        engine = ComparisonEngine()
        
        # Exact match
        result = engine.compare_string('W001', 'W001')
        assert result.is_match is True
        
        # Case insensitive
        result = engine.compare_string('w001', 'W001', case_sensitive=False)
        assert result.is_match is True
        
        # Fuzzy matching
        result = engine.compare_string('Well 001', 'Well_001', fuzzy=True)
        assert result.is_match is True
        assert result.similarity_score > 0.8
    
    def test_date_comparison(self):
        """Test date/datetime comparison."""
        engine = ComparisonEngine()
        
        date1 = datetime(2024, 1, 1, 12, 0, 0)
        date2 = datetime(2024, 1, 1, 12, 0, 5)
        
        # Exact comparison
        result = engine.compare_date(date1, date2)
        assert result.is_match is False
        
        # With tolerance
        result = engine.compare_date(date1, date2, tolerance_seconds=10)
        assert result.is_match is True
    
    def test_compare_dataframes(self):
        """Test comparing two DataFrames."""
        engine = ComparisonEngine()
        
        df1 = pd.DataFrame({
            'well_id': ['W001', 'W002', 'W003'],
            'oil_volume': [100.0, 200.0, 300.0],
            'gas_volume': [1000.0, 2000.0, 3000.0]
        })
        
        df2 = pd.DataFrame({
            'well_id': ['W001', 'W002', 'W003'],
            'oil_volume': [100.5, 200.0, 299.0],
            'gas_volume': [1000.0, 2001.0, 3000.0]
        })
        
        results = engine.compare_dataframes(df1, df2, key_column='well_id')
        
        assert len(results.discrepancies) > 0
        assert results.total_comparisons == 6  # 3 rows × 2 value columns
        assert results.match_rate < 1.0
    
    def test_aggregate_comparison(self):
        """Test aggregate-level comparisons."""
        engine = ComparisonEngine()
        
        df1 = pd.DataFrame({
            'lease': ['L1', 'L1', 'L2'],
            'oil': [100, 150, 200]
        })
        
        df2 = pd.DataFrame({
            'lease': ['L1', 'L2'],
            'oil': [250, 200]
        })
        
        result = engine.compare_aggregates(
            df1, df2, 
            group_by='lease',
            agg_column='oil',
            agg_func='sum'
        )
        
        assert result.is_match is True  # L1: 250, L2: 200 in both


class TestDiscrepancyReporter:
    """Test discrepancy reporting functionality."""
    
    def test_create_discrepancy_record(self):
        """Test creating discrepancy records."""
        discrepancy = Discrepancy(
            record_id='W001',
            field='oil_volume',
            source_value=100.0,
            benchmark_value=105.0,
            difference=5.0,
            percentage_diff=5.0,
            severity='warning'
        )
        
        assert discrepancy.record_id == 'W001'
        assert discrepancy.severity == 'warning'
        assert discrepancy.percentage_diff == 5.0
    
    def test_generate_summary_report(self):
        """Test generating summary report."""
        discrepancies = [
            Discrepancy('W001', 'oil_volume', 100, 105, 5, 5.0, 'warning'),
            Discrepancy('W002', 'gas_volume', 1000, 1100, 100, 10.0, 'error'),
            Discrepancy('W003', 'oil_volume', 200, 201, 1, 0.5, 'info')
        ]
        
        reporter = DiscrepancyReporter()
        summary = reporter.generate_summary(discrepancies)
        
        assert summary['total_discrepancies'] == 3
        assert summary['by_severity']['error'] == 1
        assert summary['by_severity']['warning'] == 1
        assert summary['by_field']['oil_volume'] == 2
    
    def test_export_discrepancies_to_excel(self, tmp_path):
        """Test exporting discrepancies to Excel."""
        discrepancies = [
            Discrepancy('W001', 'oil_volume', 100, 105, 5, 5.0, 'warning'),
            Discrepancy('W002', 'gas_volume', 1000, 1100, 100, 10.0, 'error')
        ]
        
        reporter = DiscrepancyReporter()
        excel_path = tmp_path / 'discrepancies.xlsx'
        
        reporter.export_to_excel(discrepancies, excel_path)
        
        assert excel_path.exists()
        
        # Read back and verify
        df = pd.read_excel(excel_path)
        assert len(df) == 2
        assert 'record_id' in df.columns
        assert 'severity' in df.columns
    
    def test_generate_detailed_report(self):
        """Test generating detailed discrepancy report."""
        comparison_result = ComparisonResult(
            total_comparisons=100,
            matches=85,
            discrepancies=[
                Discrepancy('W001', 'oil_volume', 100, 105, 5, 5.0, 'warning'),
                Discrepancy('W002', 'gas_volume', 1000, 1100, 100, 10.0, 'error')
            ]
        )
        
        reporter = DiscrepancyReporter()
        report = reporter.generate_detailed_report(comparison_result)
        
        assert 'summary' in report
        assert 'match_rate' in report['summary']
        assert report['summary']['match_rate'] == 0.85
        assert 'discrepancies_by_severity' in report
        assert 'recommendations' in report
    
    def test_filter_discrepancies_by_severity(self):
        """Test filtering discrepancies by severity level."""
        discrepancies = [
            Discrepancy('W001', 'oil_volume', 100, 105, 5, 5.0, 'warning'),
            Discrepancy('W002', 'gas_volume', 1000, 1100, 100, 10.0, 'error'),
            Discrepancy('W003', 'oil_volume', 200, 201, 1, 0.5, 'info')
        ]
        
        reporter = DiscrepancyReporter()
        
        errors = reporter.filter_by_severity(discrepancies, 'error')
        assert len(errors) == 1
        assert errors[0].record_id == 'W002'
        
        warnings_and_above = reporter.filter_by_severity(discrepancies, min_severity='warning')
        assert len(warnings_and_above) == 2


class TestCrossReferenceModule:
    """Test integrated cross-reference module."""
    
    def test_full_cross_reference_workflow(self, tmp_path):
        """Test complete cross-reference workflow."""
        # Create benchmark Excel file
        excel_path = tmp_path / "benchmark.xlsx"
        benchmark_data = pd.DataFrame({
            'Well_ID': ['W001', 'W002', 'W003'],
            'Oil_Prod': [1000, 2000, 1500],
            'Gas_Prod': [5000, 6000, 5500]
        })
        benchmark_data.to_excel(excel_path, index=False)
        
        # Create database data
        db_data = pd.DataFrame({
            'well_id': ['W001', 'W002', 'W003'],
            'oil_volume': [1005, 2000, 1480],
            'gas_volume': [5000, 6050, 5500]
        })
        
        # Create mapping configuration
        mapping_config = MappingConfig({
            'well_id': 'Well_ID',
            'oil_volume': 'Oil_Prod',
            'gas_volume': 'Gas_Prod'
        })
        
        # Run cross-reference
        module = CrossReferenceModule(mapping_config)
        result = module.cross_reference(
            db_data, 
            excel_path,
            key_column='well_id',
            numeric_tolerance=0.01
        )
        
        assert result.total_comparisons > 0
        assert len(result.discrepancies) > 0  # Should find some discrepancies
        assert result.match_rate < 1.0  # Not all values match exactly
    
    def test_cross_reference_with_yaml_config(self, tmp_path):
        """Test cross-reference using YAML configuration."""
        # Create YAML config
        yaml_path = tmp_path / "config.yaml"
        yaml_content = """
        field_mappings:
          well_id: Well_Identifier
          oil_volume: Oil_BBL
          
        comparison_settings:
          numeric_tolerance: 0.001
          string_matching: fuzzy
          case_sensitive: false
          
        reporting:
          severity_thresholds:
            error: 10.0  # >10% difference
            warning: 5.0  # >5% difference
            info: 1.0     # >1% difference
        """
        yaml_path.write_text(yaml_content)
        
        # Create test data
        excel_path = tmp_path / "test.xlsx"
        pd.DataFrame({
            'Well_Identifier': ['W001'],
            'Oil_BBL': [1000]
        }).to_excel(excel_path, index=False)
        
        db_data = pd.DataFrame({
            'well_id': ['W001'],
            'oil_volume': [1050]
        })
        
        # Load config and run
        config = MappingConfig.from_yaml(yaml_path)
        module = CrossReferenceModule(config)
        result = module.cross_reference(db_data, excel_path, 'well_id')
        
        assert len(result.discrepancies) == 1
        assert result.discrepancies[0].severity == 'warning'  # 5% difference
    
    def test_batch_cross_reference(self, tmp_path):
        """Test batch processing of multiple Excel files."""
        # Create multiple Excel files
        excel_files = []
        for i in range(3):
            excel_path = tmp_path / f"benchmark_{i}.xlsx"
            pd.DataFrame({
                'Well_ID': [f'W00{i}'],
                'Oil': [1000 * (i + 1)]
            }).to_excel(excel_path, index=False)
            excel_files.append(excel_path)
        
        db_data = pd.DataFrame({
            'well_id': ['W000', 'W001', 'W002'],
            'oil_volume': [1000, 2010, 3000]
        })
        
        mapping = MappingConfig({'well_id': 'Well_ID', 'oil_volume': 'Oil'})
        module = CrossReferenceModule(mapping)
        
        results = module.batch_cross_reference(db_data, excel_files, 'well_id')
        
        assert len(results) == 3
        assert any(len(r.discrepancies) > 0 for r in results)
    
    def test_generate_consolidated_report(self, tmp_path):
        """Test generating consolidated report from multiple comparisons."""
        module = CrossReferenceModule()
        
        # Create multiple comparison results
        results = [
            ComparisonResult(100, 90, [
                Discrepancy('W001', 'oil', 100, 110, 10, 10.0, 'error')
            ]),
            ComparisonResult(50, 48, [
                Discrepancy('W002', 'gas', 1000, 1005, 5, 0.5, 'info')
            ])
        ]
        
        report_path = tmp_path / 'consolidated_report.xlsx'
        module.generate_consolidated_report(results, report_path)
        
        assert report_path.exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])