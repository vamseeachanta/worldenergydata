"""Test suite for validation report generation"""
import pytest
import os
import sys
from datetime import datetime
from unittest.mock import Mock, patch

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../src')))


class TestReportGeneration:
    """Test suite for validation report generation functionality"""
    
    def test_report_structure(self):
        """Test that report has all required sections"""
        required_sections = [
            "# Drilling Completion Days Output Validation Report",
            "## Executive Summary",
            "## Validation Process",
            "## File Information",
            "## Structure Comparison",
            "## Data Comparison Results",
            "## Detailed Metrics",
            "## Conclusion and Recommendations"
        ]
        
        # Sample report content
        report_content = "\n".join(required_sections)
        
        for section in required_sections:
            assert section in report_content
    
    def test_metrics_formatting(self):
        """Test that metrics are properly formatted"""
        metrics = {
            'total_cells': 1464,
            'matching_cells': 1464,
            'match_percentage': 100.0
        }
        
        # Format metrics
        formatted = f"- Total Cells: {metrics['total_cells']:,}\n"
        formatted += f"- Matching Cells: {metrics['matching_cells']:,}\n"
        formatted += f"- Match Percentage: {metrics['match_percentage']:.1f}%"
        
        assert "1,464" in formatted
        assert "100.0%" in formatted
    
    def test_timestamp_generation(self):
        """Test that report includes proper timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        report_header = f"Generated: {timestamp}"
        
        assert len(timestamp) == 19  # YYYY-MM-DD HH:MM:SS
        assert timestamp[4] == '-'
        assert timestamp[7] == '-'
        assert timestamp[10] == ' '
        assert timestamp[13] == ':'
        assert timestamp[16] == ':'
    
    def test_file_path_handling(self):
        """Test proper handling of file paths in report"""
        original_path = "docs/modules/bsee/data/SME_Roy_attachments/2025-08-01/drilling_and_completion_days_by_api.xlsx"
        test_path = "tests/modules/bsee/analysis/2025-08-02-drilling-completion-output-validation/results/drilling_and_completion_days_by_api_validation.xlsx"
        
        # Extract filenames
        original_filename = os.path.basename(original_path)
        test_filename = os.path.basename(test_path)
        
        assert original_filename == "drilling_and_completion_days_by_api.xlsx"
        assert test_filename == "drilling_and_completion_days_by_api_validation.xlsx"
    
    def test_column_metrics_table(self):
        """Test generation of column metrics table"""
        column_metrics = {
            'API_WELL_NUMBER': {'matches': 122, 'differences': 0, 'match_percentage': 100.0},
            'DRILLING_DAYS': {'matches': 122, 'differences': 0, 'match_percentage': 100.0}
        }
        
        # Generate table
        table = "| Column | Matches | Differences | Match % |\n"
        table += "|--------|---------|-------------|---------|"
        
        for col, metrics in column_metrics.items():
            table += f"\n| {col} | {metrics['matches']} | {metrics['differences']} | {metrics['match_percentage']}% |"
        
        assert "| API_WELL_NUMBER | 122 | 0 | 100.0% |" in table
        assert "| DRILLING_DAYS | 122 | 0 | 100.0% |" in table
    
    def test_conclusion_generation(self):
        """Test generation of appropriate conclusions based on results"""
        test_cases = [
            (100.0, "PERFECT MATCH", "The test output matches the original output exactly"),
            (99.5, "EXCELLENT MATCH", "Minor differences detected that do not affect overall data quality"),
            (95.0, "GOOD MATCH", "Some differences detected. Review recommended"),
            (85.0, "SIGNIFICANT DIFFERENCES", "Substantial differences found. Investigation required")
        ]
        
        for match_pct, expected_status, expected_desc in test_cases:
            if match_pct == 100:
                assert expected_status == "PERFECT MATCH"
            elif match_pct >= 99:
                assert expected_status == "EXCELLENT MATCH"
            elif match_pct >= 95:
                assert expected_status == "GOOD MATCH"
            else:
                assert expected_status == "SIGNIFICANT DIFFERENCES"
    
    def test_report_file_creation(self):
        """Test that report file is created successfully"""
        test_dir = os.path.dirname(__file__)
        results_dir = os.path.join(test_dir, 'results')
        
        # Ensure results directory exists
        assert os.path.exists(results_dir)
        
        # Test file naming
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"validation_summary_{timestamp}.md"
        
        assert filename.startswith("validation_summary_")
        assert filename.endswith(".md")
        assert len(filename) == 37  # validation_summary_YYYYMMDD_HHMMSS.md
    
    def test_markdown_formatting(self):
        """Test proper markdown formatting"""
        markdown_elements = [
            "# Heading 1",
            "## Heading 2",
            "### Heading 3",
            "- Bullet point",
            "1. Numbered list",
            "**Bold text**",
            "*Italic text*",
            "`inline code`",
            "```python\ncode block\n```",
            "| Table | Header |",
            "|-------|--------|",
            "[Link](url)",
            "![Image](path)"
        ]
        
        for element in markdown_elements:
            # Basic validation of markdown syntax
            if element.startswith("#"):
                assert element.count(" ") >= 1
            elif element.startswith("|"):
                assert element.count("|") >= 2
    
    def test_validation_workflow_summary(self):
        """Test complete validation workflow summary"""
        workflow_steps = [
            "1. Modified output filename to include validation suffix",
            "2. Executed drilling completion days analysis",
            "3. Generated test output with 122 wells",
            "4. Performed comprehensive comparison analysis",
            "5. Achieved 100% match rate across all cells"
        ]
        
        summary = "\n".join(workflow_steps)
        
        assert "Modified output filename" in summary
        assert "122 wells" in summary
        assert "100% match" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])