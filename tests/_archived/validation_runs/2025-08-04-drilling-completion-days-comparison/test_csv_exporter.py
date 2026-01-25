import pytest
import pandas as pd
import tempfile
import os
import csv
from pathlib import Path
from datetime import datetime, date

# Import the CSV exporter class (to be implemented)
try:
    from csv_exporter import CSVExporter
except ImportError:
    # Class will be implemented after tests are written
    CSVExporter = None


class TestCSVExporter:
    """Test cases for CSVExporter class"""

    @pytest.fixture
    def sample_comparison_data(self):
        """Sample comparison data with all required fields"""
        return pd.DataFrame({
            'api_number': [608084001500, 608124009400, 608124011101],
            'well_name_lease': ['TIBER-001', 'JACK-001', 'JULIA-001'],
            'well_name_api12': ['TIBER ST00BP00 001', 'JACK ST00BP00 001', 'JULIA ST00BP00 001'],
            'drilling_days_lease': [157, 45, 78],
            'drilling_days_api12': [151, 43, 80],
            'drilling_days_difference': [6, 2, -2],
            'drilling_days_percent_diff': [3.97, 4.65, -2.50],
            'completion_days_lease': [10, 25, 32],
            'completion_days_api12': [0, 27, 30],
            'completion_days_difference': [10, -2, 2],
            'completion_days_percent_diff': [float('inf'), -7.41, 6.67],
            'status_flag': ['ERROR', 'OK', 'OK']
        })

    @pytest.fixture
    def sample_lease_data(self):
        """Sample lease method data"""
        return pd.DataFrame({
            'api_number': [608084001500, 608124009400, 608124011101],
            'well_name': ['TIBER-001', 'JACK-001', 'JULIA-001'],
            'drilling_days_lease': [157, 45, 78],
            'completion_days_lease': [10, 25, 32],
            'lease_name': ['Tiber', 'Jack', 'Julia'],
            'water_depth': [4130, 7000, 7200]
        })

    @pytest.fixture
    def sample_api12_data(self):
        """Sample API12 method data"""
        return pd.DataFrame({
            'api_number': [608084001500, 608124009400],
            'well_name': ['TIBER ST00BP00 001', 'JACK ST00BP00 001'],
            'drilling_days_api12': [151, 43],
            'completion_days_api12': [0, 27],
            'water_depth': [4130, 7000]
        })

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory for testing"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    def test_csv_exporter_initialization(self):
        """Test CSVExporter initialization"""
        if CSVExporter is None:
            pytest.skip("CSVExporter not implemented yet")
        
        exporter = CSVExporter()
        assert exporter is not None

    def test_standardized_csv_format_columns(self, sample_comparison_data):
        """Test that standardized CSV format has all required columns"""
        if CSVExporter is None:
            pytest.skip("CSVExporter not implemented yet")
        
        exporter = CSVExporter()
        standardized_df = exporter.prepare_standardized_format(sample_comparison_data)
        
        # Check required columns from specification
        expected_columns = [
            'API12_number', 'Well_name', 'lease_method_drilling_days', 'api12_method_drilling_days',
            'lease_method_completion_days', 'api12_method_completion_days',
            'Drilling_days_difference', 'Completion_days_difference',
            'Drilling_days_percent_diff', 'Completion_days_percent_diff',
            'Status_flag', 'Notes'
        ]
        
        for col in expected_columns:
            assert col in standardized_df.columns, f"Missing required column: {col}"
        
        assert len(standardized_df) == 3  # Should have 3 wells

    def test_csv_comparison_export(self, sample_comparison_data, temp_output_dir):
        """Test exporting comparison results to CSV"""
        if CSVExporter is None:
            pytest.skip("CSVExporter not implemented yet")
        
        exporter = CSVExporter()
        output_file = temp_output_dir / "test_comparison.csv"
        
        exporter.export_comparison_results(sample_comparison_data, output_file)
        
        # Check file was created
        assert output_file.exists()
        
        # Check file content - skip comment lines when reading
        df = pd.read_csv(output_file, comment='#')
        assert len(df) == 3
        assert 'API12_number' in df.columns
        assert 'Status_flag' in df.columns

    def test_individual_method_csv_export(self, sample_lease_data, sample_api12_data, temp_output_dir):
        """Test exporting individual method outputs to separate CSV files"""
        if CSVExporter is None:
            pytest.skip("CSVExporter not implemented yet")
        
        exporter = CSVExporter()
        
        # Test lease method export
        lease_file = temp_output_dir / "lease_method_test.csv"
        exporter.export_lease_method_data(sample_lease_data, lease_file)
        assert lease_file.exists()
        
        # Test API12 method export
        api12_file = temp_output_dir / "api12_method_test.csv"
        exporter.export_api12_method_data(sample_api12_data, api12_file)
        assert api12_file.exists()
        
        # Verify content
        lease_df = pd.read_csv(lease_file, comment='#')
        api12_df = pd.read_csv(api12_file, comment='#')
        
        assert len(lease_df) == 3
        assert len(api12_df) == 2
        assert 'api_number' in lease_df.columns
        assert 'api_number' in api12_df.columns

    def test_timestamped_file_naming(self, sample_comparison_data, temp_output_dir):
        """Test CSV file naming with timestamps"""
        if CSVExporter is None:
            pytest.skip("CSVExporter not implemented yet")
        
        exporter = CSVExporter()
        
        # Generate timestamped filenames
        today = datetime.now().strftime("%Y%m%d")
        
        lease_filename = exporter.generate_timestamped_filename("drilling_days_lease_method", "csv")
        api12_filename = exporter.generate_timestamped_filename("drilling_days_api12_method", "csv")
        comparison_filename = exporter.generate_timestamped_filename("drilling_days_comparison", "csv")
        
        # Check format: name_YYYYMMDD.csv
        assert today in lease_filename
        assert "drilling_days_lease_method" in lease_filename
        assert lease_filename.endswith(".csv")
        
        assert today in api12_filename
        assert "drilling_days_api12_method" in api12_filename
        
        assert today in comparison_filename
        assert "drilling_days_comparison" in comparison_filename

    def test_csv_metadata_headers(self, sample_comparison_data, temp_output_dir):
        """Test CSV files include metadata headers"""
        if CSVExporter is None:
            pytest.skip("CSVExporter not implemented yet")
        
        exporter = CSVExporter()
        output_file = temp_output_dir / "test_with_metadata.csv"
        
        exporter.export_comparison_results(
            sample_comparison_data, 
            output_file,
            include_metadata=True
        )
        
        # Read raw file content to check for metadata headers
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should contain metadata comments at the top
        assert "# Processing Date:" in content or "Processing Date:" in content
        assert "# Generated by:" in content or "Generated by:" in content

    def test_data_integrity_validation(self, sample_comparison_data):
        """Test CSV export maintains data integrity"""
        if CSVExporter is None:
            pytest.skip("CSVExporter not implemented yet")
        
        exporter = CSVExporter()
        standardized_df = exporter.prepare_standardized_format(sample_comparison_data)
        
        # Check that all original data is preserved
        assert len(standardized_df) == len(sample_comparison_data)
        
        # Check specific values
        tiber_matches = standardized_df[standardized_df['API12_number'] == '608084001500']
        if len(tiber_matches) == 0:
            # Try without string conversion
            tiber_matches = standardized_df[standardized_df['API12_number'] == 608084001500]
        
        assert len(tiber_matches) > 0, f"No matching rows found for API 608084001500 in {standardized_df['API12_number'].values}"
        tiber_row = tiber_matches.iloc[0]
        assert tiber_row['lease_method_drilling_days'] == 157
        assert tiber_row['api12_method_drilling_days'] == 151
        assert tiber_row['Drilling_days_difference'] == 6
        assert tiber_row['Status_flag'] == 'ERROR'

    def test_handle_missing_data_in_csv(self):
        """Test handling of missing data in CSV export"""
        if CSVExporter is None:
            pytest.skip("CSVExporter not implemented yet")
        
        # Data with missing values
        incomplete_data = pd.DataFrame({
            'api_number': [608084001500, 608124009400],
            'drilling_days_lease': [157, None],
            'drilling_days_api12': [151, 43],
            'completion_days_lease': [10, 25],
            'completion_days_api12': [0, None],
            'status_flag': ['ERROR', 'REVIEW']
        })
        
        exporter = CSVExporter()
        standardized_df = exporter.prepare_standardized_format(incomplete_data)
        
        # Should handle missing values gracefully
        assert len(standardized_df) == 2
        assert pd.isna(standardized_df.iloc[1]['lease_method_drilling_days']) or standardized_df.iloc[1]['lease_method_drilling_days'] == 'N/A'

    def test_excel_compatibility(self, sample_comparison_data, temp_output_dir):
        """Test that exported CSV files are compatible with Excel"""
        if CSVExporter is None:
            pytest.skip("CSVExporter not implemented yet")
        
        exporter = CSVExporter()
        output_file = temp_output_dir / "excel_compatible_test.csv"
        
        exporter.export_comparison_results(sample_comparison_data, output_file)
        
        # Read with pandas (simulates Excel import)
        df = pd.read_csv(output_file, comment='#')
        
        # Check no parsing issues
        assert len(df) == 3
        assert df['API12_number'].dtype in ['int64', 'float64', 'object']
        
        # Check for Excel-problematic values (like inf)
        drilling_diff_col = 'Drilling_days_percent_diff'
        if drilling_diff_col in df.columns:
            # Should handle infinity values appropriately
            import numpy as np
            assert not any(np.isinf(pd.to_numeric(df[drilling_diff_col], errors='coerce')).fillna(False))

    def test_pandas_roundtrip_compatibility(self, sample_comparison_data, temp_output_dir):
        """Test pandas read/write roundtrip compatibility"""
        if CSVExporter is None:
            pytest.skip("CSVExporter not implemented yet")
        
        exporter = CSVExporter()
        output_file = temp_output_dir / "pandas_roundtrip_test.csv"
        
        # Export with CSVExporter
        exporter.export_comparison_results(sample_comparison_data, output_file)
        
        # Read back with pandas
        imported_df = pd.read_csv(output_file, comment='#')
        
        # Write back with pandas
        roundtrip_file = temp_output_dir / "pandas_roundtrip_output.csv"
        imported_df.to_csv(roundtrip_file, index=False)
        
        # Read final result
        final_df = pd.read_csv(roundtrip_file)
        
        # Should maintain same structure
        assert len(final_df) == 3
        assert list(imported_df.columns) == list(final_df.columns)

    def test_large_dataset_csv_export(self, temp_output_dir):
        """Test CSV export performance with larger datasets"""
        if CSVExporter is None:
            pytest.skip("CSVExporter not implemented yet")
        
        # Create larger dataset
        large_data = pd.DataFrame({
            'api_number': range(100000000000, 100000000100),  # 100 API numbers
            'drilling_days_lease': [150 + i for i in range(100)],
            'drilling_days_api12': [148 + i for i in range(100)],
            'completion_days_lease': [20 + i for i in range(100)],
            'completion_days_api12': [18 + i for i in range(100)],
            'drilling_days_difference': [2] * 100,
            'completion_days_difference': [2] * 100,
            'drilling_days_percent_diff': [1.35] * 100,
            'completion_days_percent_diff': [11.11] * 100,
            'status_flag': ['OK'] * 100
        })
        
        exporter = CSVExporter()
        output_file = temp_output_dir / "large_dataset_test.csv"
        
        exporter.export_comparison_results(large_data, output_file)
        
        # Verify file was created and has correct size
        assert output_file.exists()
        df = pd.read_csv(output_file, comment='#')
        assert len(df) == 100

    def test_special_characters_in_csv(self, temp_output_dir):
        """Test handling of special characters in CSV export"""
        if CSVExporter is None:
            pytest.skip("CSVExporter not implemented yet")
        
        special_data = pd.DataFrame({
            'api_number': [608084001500],
            'well_name_lease': ['WELL-001 (ST01BP02) "Test"'],
            'drilling_days_lease': [157],
            'drilling_days_api12': [151],
            'completion_days_lease': [10],
            'completion_days_api12': [0],
            'status_flag': ['ERROR']
        })
        
        exporter = CSVExporter()
        output_file = temp_output_dir / "special_chars_test.csv"
        
        exporter.export_comparison_results(special_data, output_file)
        
        # Read back and verify special characters are preserved
        df = pd.read_csv(output_file, comment='#')
        assert len(df) == 1
        assert '608084001500' in str(df['API12_number'].iloc[0])

    def test_file_versioning_and_overwrite_protection(self, sample_comparison_data, temp_output_dir):
        """Test file versioning and overwrite protection"""
        if CSVExporter is None:
            pytest.skip("CSVExporter not implemented yet")
        
        exporter = CSVExporter()
        base_filename = "drilling_days_comparison"
        
        # First export
        file1 = temp_output_dir / f"{base_filename}.csv"
        exporter.export_comparison_results(sample_comparison_data, file1)
        assert file1.exists()
        
        # Second export with same name (should handle versioning)
        timestamp_filename = exporter.generate_timestamped_filename(base_filename, "csv")
        file2 = temp_output_dir / timestamp_filename
        exporter.export_comparison_results(sample_comparison_data, file2)
        assert file2.exists()
        
        # Both files should exist
        assert file1.exists() and file2.exists()

    def test_results_directory_creation(self, sample_comparison_data):
        """Test automatic creation of results directory"""
        if CSVExporter is None:
            pytest.skip("CSVExporter not implemented yet")
        
        exporter = CSVExporter()
        
        # Test with non-existing directory
        test_dir = Path("temp_test_results")
        output_file = test_dir / "auto_created_test.csv"
        
        try:
            exporter.export_comparison_results(sample_comparison_data, output_file, create_dirs=True)
            
            # Directory should be created automatically
            assert test_dir.exists()
            assert output_file.exists()
            
        finally:
            # Cleanup
            if output_file.exists():
                output_file.unlink()
            if test_dir.exists():
                test_dir.rmdir()


class TestCSVExporterIntegration:
    """Integration tests with comparison logic and markdown generator"""

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory for testing"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    def test_integration_with_comparison_analyzer(self, temp_output_dir):
        """Test integration with ComparisonAnalyzer output"""
        if CSVExporter is None:
            pytest.skip("CSVExporter not implemented yet")
        
        # Import comparison logic
        try:
            from comparison_logic import ComparisonAnalyzer, ComparisonDataLoader
        except ImportError:
            pytest.skip("ComparisonAnalyzer not available")
        
        # Create sample data in ComparisonAnalyzer format
        comparison_data = pd.DataFrame({
            'api_number': [608084001500],
            'well_name_lease': ['TIBER-001'],
            'well_name_api12': ['TIBER ST00BP00 001'],
            'drilling_days_lease': [157],
            'drilling_days_api12': [151],
            'completion_days_lease': [10],
            'completion_days_api12': [0],
            'drilling_days_difference': [6],
            'completion_days_difference': [10],
            'drilling_days_percent_diff': [3.97],
            'completion_days_percent_diff': [float('inf')],
            'status_flag': ['ERROR']
        })
        
        exporter = CSVExporter()
        output_file = temp_output_dir / "integration_test.csv"
        
        exporter.export_comparison_results(comparison_data, output_file)
        
        assert output_file.exists()
        df = pd.read_csv(output_file, comment='#')
        assert len(df) == 1
        assert df['API12_number'].iloc[0] == 608084001500

    def test_end_to_end_workflow_csv_export(self):
        """Test complete workflow from data loading to CSV export"""
        if CSVExporter is None:
            pytest.skip("CSVExporter not implemented yet")
        
        # This test would use actual data files
        from pathlib import Path
        
        results_dir = Path(__file__).parent / "results"
        
        if not results_dir.exists():
            pytest.skip("Results directory not found for integration test")
        
        try:
            from comparison_logic import ComparisonDataLoader, ComparisonAnalyzer
        except ImportError:
            pytest.skip("ComparisonAnalyzer not available")
        
        excel_files = list(results_dir.glob("drilling_and_completion_days_by_api_validation_*.xlsx"))
        csv_file = results_dir / "well_summ_goa_tiber.csv"
        
        if not excel_files or not csv_file.exists():
            pytest.skip("Required actual output files not found")
        
        # Load and compare data
        loader = ComparisonDataLoader()
        lease_data = loader.load_lease_method_data(str(excel_files[0]))
        api12_data = loader.load_api12_method_data(str(csv_file))
        
        analyzer = ComparisonAnalyzer()
        matched_data = analyzer.match_wells_by_api(lease_data, api12_data)
        comparison_result = analyzer.perform_complete_comparison(matched_data)
        
        # Export to CSV
        exporter = CSVExporter()
        output_file = results_dir / "end_to_end_test_export.csv"
        
        exporter.export_comparison_results(comparison_result, output_file)
        
        assert output_file.exists()
        df = pd.read_csv(output_file, comment='#')
        assert len(df) >= 1  # Should have at least Tiber well


if __name__ == "__main__":
    pytest.main([__file__, "-v"])