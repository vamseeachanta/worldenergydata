import pytest
import pandas as pd
import tempfile
import os
from pathlib import Path

# Import the markdown generator class from local module
try:
    from markdown_generator import MarkdownReportGenerator
except ImportError:
    # Class will be implemented after tests are written
    MarkdownReportGenerator = None


class TestMarkdownReportGenerator:
    """Test cases for MarkdownReportGenerator class"""

    @pytest.fixture
    def sample_comparison_data(self):
        """Sample comparison data with the 5-column format specified in the spec"""
        return pd.DataFrame({
            'api_number': [608084001500, 608124009400, 608124011101],
            'well_name_lease': ['TIBER-001', 'JACK-001', 'JULIA-001'],
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
    def temp_output_file(self):
        """Create temporary output file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp:
            yield tmp.name
        os.unlink(tmp.name)

    def test_markdown_generator_initialization(self):
        """Test MarkdownReportGenerator initialization"""
        if MarkdownReportGenerator is None:
            pytest.skip("MarkdownReportGenerator not implemented yet")
        
        generator = MarkdownReportGenerator()
        assert generator is not None

    def test_generate_markdown_table_structure(self, sample_comparison_data):
        """Test that markdown table has correct structure with 5 columns"""
        if MarkdownReportGenerator is None:
            pytest.skip("MarkdownReportGenerator not implemented yet")
        
        generator = MarkdownReportGenerator()
        markdown_content = generator.generate_comparison_table(sample_comparison_data)
        
        assert isinstance(markdown_content, str)
        assert len(markdown_content) > 0
        
        # Check for markdown table structure
        lines = markdown_content.strip().split('\n')
        
        # Should have header row, separator row, and data rows
        assert len(lines) >= 5  # header + separator + 3 data rows minimum
        
        # Check header row has 5 columns (API, drilling lease, drilling api12, completion lease, completion api12)
        header_row = lines[0]
        assert header_row.count('|') >= 6  # 5 columns = 6 separators (including start/end)
        
        # Check separator row
        separator_row = lines[1]
        assert '---' in separator_row
        assert separator_row.count('|') >= 6

    def test_column_headers_match_specification(self, sample_comparison_data):
        """Test that column headers match the specification requirements"""
        if MarkdownReportGenerator is None:
            pytest.skip("MarkdownReportGenerator not implemented yet")
        
        generator = MarkdownReportGenerator()
        markdown_content = generator.generate_comparison_table(sample_comparison_data)
        
        # Extract header row
        header_row = markdown_content.strip().split('\n')[0]
        
        # Check for required columns based on spec
        assert 'API' in header_row or 'API12' in header_row
        assert 'Drilling Days' in header_row or 'drilling' in header_row.lower()
        assert 'Completion Days' in header_row or 'completion' in header_row.lower()
        assert 'Lease' in header_row or 'Method 1' in header_row
        assert 'API12' in header_row or 'Method 2' in header_row

    def test_data_formatting_in_table(self, sample_comparison_data):
        """Test that data is properly formatted in the markdown table"""
        if MarkdownReportGenerator is None:
            pytest.skip("MarkdownReportGenerator not implemented yet")
        
        generator = MarkdownReportGenerator()
        markdown_content = generator.generate_comparison_table(sample_comparison_data)
        
        # Check that API numbers are present
        assert '608084001500' in markdown_content
        assert '608124009400' in markdown_content
        assert '608124011101' in markdown_content
        
        # Check that drilling days values are present
        assert '157' in markdown_content  # TIBER lease drilling days
        assert '151' in markdown_content  # TIBER API12 drilling days
        
        # Check that completion days values are present
        assert '10' in markdown_content   # TIBER lease completion days
        assert '0' in markdown_content    # TIBER API12 completion days

    def test_column_alignment_and_spacing(self, sample_comparison_data):
        """Test column alignment and consistent spacing"""
        if MarkdownReportGenerator is None:
            pytest.skip("MarkdownReportGenerator not implemented yet")
        
        generator = MarkdownReportGenerator()
        markdown_content = generator.generate_comparison_table(sample_comparison_data)
        
        lines = markdown_content.strip().split('\n')
        
        if len(lines) >= 3:
            # Check that all rows have consistent number of columns
            header_cols = lines[0].count('|')
            separator_cols = lines[1].count('|')
            data_cols = lines[2].count('|')
            
            assert header_cols == separator_cols == data_cols
            
            # Check that columns are properly spaced (no empty cells)
            for line in lines[2:]:  # Skip header and separator
                if '|' in line:
                    cells = [cell.strip() for cell in line.split('|')[1:-1]]  # Remove empty start/end
                    assert len(cells) == 5  # Should have exactly 5 columns
                    assert all(len(cell) > 0 for cell in cells)  # No empty cells

    def test_status_flag_formatting(self, sample_comparison_data):
        """Test that status flags are properly formatted and included"""
        if MarkdownReportGenerator is None:
            pytest.skip("MarkdownReportGenerator not implemented yet")
        
        # This test will check if status flags are included in the table
        # Based on the spec, status flags should be visible in the comparison
        generator = MarkdownReportGenerator()
        markdown_content = generator.generate_comparison_table(sample_comparison_data)
        
        # Status flags should be visible somewhere in the output
        # Either as part of the table or as additional information
        assert 'ERROR' in markdown_content or 'OK' in markdown_content

    def test_handle_missing_data(self):
        """Test handling of missing or invalid data"""
        if MarkdownReportGenerator is None:
            pytest.skip("MarkdownReportGenerator not implemented yet")
        
        # Test with missing data
        incomplete_data = pd.DataFrame({
            'api_number': [608084001500],
            'drilling_days_lease': [None],
            'drilling_days_api12': [151],
            'completion_days_lease': [10],
            'completion_days_api12': [0]
        })
        
        generator = MarkdownReportGenerator()
        markdown_content = generator.generate_comparison_table(incomplete_data)
        
        assert isinstance(markdown_content, str)
        assert len(markdown_content) > 0
        assert '608084001500' in markdown_content

    def test_handle_empty_dataset(self):
        """Test handling of empty comparison dataset"""
        if MarkdownReportGenerator is None:
            pytest.skip("MarkdownReportGenerator not implemented yet")
        
        empty_data = pd.DataFrame()
        
        generator = MarkdownReportGenerator()
        markdown_content = generator.generate_comparison_table(empty_data)
        
        assert isinstance(markdown_content, str)
        # Should still have headers even with no data
        assert 'API' in markdown_content or 'No data' in markdown_content

    def test_file_output_functionality(self, sample_comparison_data, temp_output_file):
        """Test saving markdown report to file"""
        if MarkdownReportGenerator is None:
            pytest.skip("MarkdownReportGenerator not implemented yet")
        
        generator = MarkdownReportGenerator()
        generator.save_comparison_report(sample_comparison_data, temp_output_file)
        
        # Check that file was created and has content
        assert os.path.exists(temp_output_file)
        
        with open(temp_output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert len(content) > 0
        assert '608084001500' in content  # Sample API number should be present
        assert 'API' in content or 'Drilling' in content  # Some header content

    def test_file_output_with_custom_title(self, sample_comparison_data, temp_output_file):
        """Test saving markdown report with custom title"""
        if MarkdownReportGenerator is None:
            pytest.skip("MarkdownReportGenerator not implemented yet")
        
        custom_title = "Drilling Days Comparison Analysis - Test Report"
        
        generator = MarkdownReportGenerator()
        generator.save_comparison_report(
            sample_comparison_data, 
            temp_output_file,
            title=custom_title
        )
        
        with open(temp_output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert custom_title in content

    def test_markdown_table_format_compliance(self, sample_comparison_data):
        """Test that generated markdown complies with standard markdown table format"""
        if MarkdownReportGenerator is None:
            pytest.skip("MarkdownReportGenerator not implemented yet")
        
        generator = MarkdownReportGenerator()
        markdown_content = generator.generate_comparison_table(sample_comparison_data)
        
        lines = markdown_content.strip().split('\n')
        
        # Check basic markdown table structure
        assert len(lines) >= 2  # At least header and separator
        
        # Header row should start and end with |
        header_row = lines[0].strip()
        assert header_row.startswith('|') and header_row.endswith('|')
        
        # Separator row should contain --- and |
        separator_row = lines[1].strip()
        assert '---' in separator_row
        assert separator_row.startswith('|') and separator_row.endswith('|')
        
        # Find where the table ends (before status summary)
        table_end = 2
        for i, line in enumerate(lines[2:], start=2):
            if line.strip().startswith('##') or not line.strip():
                table_end = i
                break
        
        # Data rows should start and end with |
        for line in lines[2:table_end]:
            if line.strip():  # Skip empty lines
                assert line.strip().startswith('|') and line.strip().endswith('|')

    def test_large_dataset_performance(self):
        """Test performance with larger datasets"""
        if MarkdownReportGenerator is None:
            pytest.skip("MarkdownReportGenerator not implemented yet")
        
        # Create a larger dataset
        large_data = pd.DataFrame({
            'api_number': range(100000000000, 100000000050),  # 50 API numbers
            'drilling_days_lease': [150 + i for i in range(50)],
            'drilling_days_api12': [148 + i for i in range(50)],
            'completion_days_lease': [20 + i for i in range(50)],
            'completion_days_api12': [18 + i for i in range(50)],
            'drilling_days_difference': [2] * 50,
            'completion_days_difference': [2] * 50,
            'status_flag': ['OK'] * 50
        })
        
        generator = MarkdownReportGenerator()
        markdown_content = generator.generate_comparison_table(large_data)
        
        assert isinstance(markdown_content, str)
        assert len(markdown_content) > 0
        
        # Should handle all 50 rows
        lines = markdown_content.strip().split('\n')
        assert len(lines) >= 52  # header + separator + 50 data rows

    def test_special_characters_handling(self):
        """Test handling of special characters in well names and data"""
        if MarkdownReportGenerator is None:
            pytest.skip("MarkdownReportGenerator not implemented yet")
        
        special_data = pd.DataFrame({
            'api_number': [608084001500],
            'well_name_lease': ['WELL-001 (ST01BP02)'],
            'drilling_days_lease': [157],
            'drilling_days_api12': [151],
            'completion_days_lease': [10],
            'completion_days_api12': [0],
            'status_flag': ['ERROR']
        })
        
        generator = MarkdownReportGenerator()
        markdown_content = generator.generate_comparison_table(special_data)
        
        assert isinstance(markdown_content, str)
        assert '608084001500' in markdown_content
        # Note: Well names are not included in the 5-column comparison table format
        # The table focuses on API numbers and drilling/completion days only


class TestMarkdownGeneratorIntegration:
    """Integration tests with comparison logic from Task 2"""

    def test_integration_with_comparison_analyzer(self):
        """Test integration with ComparisonAnalyzer output"""
        if MarkdownReportGenerator is None:
            pytest.skip("MarkdownReportGenerator not implemented yet")
        
        # Import comparison logic from local module
        try:
            from comparison_logic import (
                ComparisonDataLoader, ComparisonAnalyzer
            )
        except ImportError:
            pytest.skip("ComparisonAnalyzer not available")
        
        # Create sample data in the format produced by ComparisonAnalyzer
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
        
        generator = MarkdownReportGenerator()
        markdown_content = generator.generate_comparison_table(comparison_data)
        
        assert isinstance(markdown_content, str)
        assert len(markdown_content) > 0
        assert '608084001500' in markdown_content
        assert '157' in markdown_content  # Lease drilling days
        assert '151' in markdown_content  # API12 drilling days

    def test_end_to_end_workflow_with_actual_files(self):
        """Test complete workflow from actual data files to markdown report"""
        if MarkdownReportGenerator is None:
            pytest.skip("MarkdownReportGenerator not implemented yet")
        
        # This test will be run with actual data files
        from pathlib import Path
        
        results_dir = Path(__file__).parent / "results"
        excel_files = list(results_dir.glob("drilling_and_completion_days_by_api_validation_*.xlsx"))
        csv_file = results_dir / "well_summ_goa_tiber.csv"
        
        if not excel_files or not csv_file.exists():
            pytest.skip("Required actual output files not found")
        
        try:
            from comparison_logic import (
                ComparisonDataLoader, ComparisonAnalyzer
            )
        except ImportError:
            pytest.skip("ComparisonAnalyzer not available")
        
        # Load and compare data
        loader = ComparisonDataLoader()
        lease_data = loader.load_lease_method_data(str(excel_files[0]))
        api12_data = loader.load_api12_method_data(str(csv_file))
        
        analyzer = ComparisonAnalyzer()
        matched_data = analyzer.match_wells_by_api(lease_data, api12_data)
        comparison_result = analyzer.perform_complete_comparison(matched_data)
        
        # Generate markdown report
        generator = MarkdownReportGenerator()
        markdown_content = generator.generate_comparison_table(comparison_result)
        
        assert isinstance(markdown_content, str)
        assert len(markdown_content) > 0
        assert '608084001500' in markdown_content  # Tiber API should be present


if __name__ == "__main__":
    pytest.main([__file__, "-v"])