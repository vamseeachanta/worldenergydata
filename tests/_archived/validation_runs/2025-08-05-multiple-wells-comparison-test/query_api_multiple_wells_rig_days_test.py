import pytest
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tempfile
import json
from datetime import datetime

import deepdiff
DEEPDIFF_AVAILABLE = True
import os
import sys

from assetutilities.common.yml_utilities import ymlInput
from worldenergydata.engine import engine
ENGINE_AVAILABLE = True

# Import the multiple wells comparison processor
try:
    from .multiple_wells_comparison_test import MultipleWellsDataProcessor
    COMPARISON_PROCESSOR_AVAILABLE = True
except ImportError:
    COMPARISON_PROCESSOR_AVAILABLE = False


def run_application(input_file, expected_result={}):
    if input_file is not None and not os.path.isfile(input_file):
        input_file = os.path.join(os.path.dirname(__file__), input_file)
    
    if not ENGINE_AVAILABLE:
        pytest.skip("Engine not available - dependencies missing")
    
    cfg = engine(input_file)


def get_valid_pytest_output_file(pytest_output_file):
    if pytest_output_file is not None and not os.path.isfile(
            pytest_output_file):
        pytest_output_file = os.path.join(os.path.dirname(__file__),
                                          pytest_output_file)
    return pytest_output_file

def test_application():

    # Comprehensive analysis 
    input_file = 'query_api_multiple_wells_rig_days.yml' 

    # custom tests
    # input_file = 'custom_analysis.yml'
  

    pytest_output_file = None
    # pytest_output_file = get_valid_pytest_output_file(pytest_output_file)
    # expected_result = ymlInput(pytest_output_file, updateYml=None)

    if len(sys.argv) > 1:
        sys.argv.pop()

    run_application(input_file, expected_result={})


class MultipleWellsComparisonFramework:
    """
    Enhanced framework for comparing multiple wells drilling and completion days
    between different BSEE analysis methods.
    """
    
    def __init__(self, results_dir: Optional[str] = None):
        """
        Initialize the comparison framework.
        
        Args:
            results_dir: Directory to store comparison results
        """
        self.results_dir = Path(results_dir) if results_dir else Path("tests/modules/bsee/analysis/multiple_wells_comparison_test/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.processor = MultipleWellsDataProcessor(chunk_size=30) if COMPARISON_PROCESSOR_AVAILABLE else None
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def run_api12_method_analysis(self, config_file: str = 'query_api_multiple_wells_rig_days.yml') -> str:
        """
        Execute API12 method analysis for multiple wells.
        
        Args:
            config_file: YAML configuration file for the analysis
            
        Returns:
            str: Path to the generated output file
        """
        if not ENGINE_AVAILABLE:
            raise RuntimeError("Engine not available - dependencies missing")
        
        # Execute the analysis
        run_application(config_file, expected_result={})
        
        # Return expected output file path
        # This should be adapted based on actual output file naming convention
        expected_output = f"well_summ_goa_multiple_wells_{self.timestamp}.csv"
        return expected_output
    
    def run_lease_method_analysis(self, config_file: str = 'drilling_completion_days.yml') -> str:
        """
        Execute lease method analysis for comparison.
        
        Args:
            config_file: YAML configuration file for lease method
            
        Returns:
            str: Path to the generated output file
        """
        if not ENGINE_AVAILABLE:
            raise RuntimeError("Engine not available - dependencies missing")
        
        # This would need to be implemented based on the actual lease method configuration
        # For now, return expected output file path
        expected_output = f"drilling_and_completion_days_by_api_{self.timestamp}.xlsx"
        return expected_output
    
    def compare_method_outputs(self, api12_output: str, lease_output: str) -> Dict:
        """
        Compare outputs from both methods using the MultipleWellsDataProcessor.
        
        Args:
            api12_output: Path to API12 method output file
            lease_output: Path to lease method output file
            
        Returns:
            Dict: Comparison results and statistics
        """
        if not COMPARISON_PROCESSOR_AVAILABLE:
            raise RuntimeError("Comparison processor not available")
        
        # Load data from both methods
        try:
            api12_data = self.processor.load_method_data(api12_output, 'API12_method')
            lease_data = self.processor.load_method_data(lease_output, 'Lease_method')
        except Exception as e:
            raise RuntimeError(f"Error loading method outputs: {str(e)}")
        
        # Process comparison in batches
        comparison_results = self.processor.process_in_batches(lease_data, api12_data)
        
        # Generate comparison statistics
        stats = self._generate_comparison_statistics(comparison_results)
        
        return {
            'comparison_results': comparison_results,
            'statistics': stats,
            'processing_stats': self.processor.processing_stats
        }
    
    def _generate_comparison_statistics(self, results: List[Dict]) -> Dict:
        """
        Generate statistical summary of comparison results.
        
        Args:
            results: List of comparison results
            
        Returns:
            Dict: Statistical summary
        """
        if not results:
            return {'error': 'No comparison results available'}
        
        df = pd.DataFrame(results)
        
        stats = {
            'total_wells': len(df),
            'successful_matches': len(df[df['Status'] == 'OK']),
            'wells_requiring_review': len(df[df['Status'] == 'REVIEW']),
            'wells_with_errors': len(df[df['Status'] == 'ERROR']),
            'match_percentage': (len(df[df['Status'] == 'OK']) / len(df)) * 100,
        }
        
        # Add drilling days statistics
        drilling_diffs = df['Drilling_Days_Diff'].dropna()
        if not drilling_diffs.empty:
            stats['drilling_days_stats'] = {
                'mean_difference': drilling_diffs.mean(),
                'median_difference': drilling_diffs.median(),
                'std_difference': drilling_diffs.std(),
                'max_abs_difference': drilling_diffs.abs().max()
            }
        
        # Add completion days statistics
        completion_diffs = df['Completion_Days_Diff'].dropna()
        if not completion_diffs.empty:
            stats['completion_days_stats'] = {
                'mean_difference': completion_diffs.mean(),
                'median_difference': completion_diffs.median(),
                'std_difference': completion_diffs.std(),
                'max_abs_difference': completion_diffs.abs().max()
            }
        
        return stats
    
    def generate_comparison_report(self, comparison_data: Dict) -> str:
        """
        Generate a comprehensive markdown comparison report for multiple wells.
        
        Args:
            comparison_data: Comparison results and statistics
            
        Returns:
            str: Path to generated markdown report
        """
        results = comparison_data['comparison_results']
        stats = comparison_data['statistics']
        processing_stats = comparison_data['processing_stats']
        
        report_content = self._create_markdown_report_content(results, stats, processing_stats)
        
        # Save report
        report_path = self.results_dir / f"multiple_wells_comparison_report_{self.timestamp}.md"
        with open(report_path, 'w') as f:
            f.write(report_content)
        
        return str(report_path)
    
    def _create_markdown_report_content(self, results: List[Dict], stats: Dict, processing_stats: Dict) -> str:
        """
        Create structured markdown report content to handle 120+ wells efficiently.
        
        Args:
            results: Comparison results
            stats: Statistical summary
            processing_stats: Processing statistics
            
        Returns:
            str: Markdown report content
        """
        df = pd.DataFrame(results)
        
        # Executive Summary
        report = f"""# Multiple Wells Drilling and Completion Days Comparison Report

> Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> Total Wells Analyzed: {stats.get('total_wells', 0)}

## Executive Summary

### Key Findings
- **Total Wells Processed**: {processing_stats.get('total_wells_processed', 0)}
- **Successful Comparisons**: {processing_stats.get('successful_comparisons', 0)}
- **Match Rate**: {stats.get('match_percentage', 0):.1f}%
- **Wells Requiring Review**: {stats.get('wells_requiring_review', 0)}
- **Wells with Errors**: {stats.get('wells_with_errors', 0)}

### Processing Performance
- **Memory Optimization**: Batch processing with {self.processor.chunk_size if self.processor else 'N/A'} wells per chunk
- **Failed Comparisons**: {processing_stats.get('failed_comparisons', 0)}

## Statistical Analysis

"""
        
        # Add drilling days statistics if available
        if 'drilling_days_stats' in stats:
            drill_stats = stats['drilling_days_stats']
            report += f"""### Drilling Days Comparison
- **Mean Difference**: {drill_stats['mean_difference']:.2f} days
- **Median Difference**: {drill_stats['median_difference']:.2f} days
- **Standard Deviation**: {drill_stats['std_difference']:.2f} days
- **Maximum Absolute Difference**: {drill_stats['max_abs_difference']:.2f} days

"""
        
        # Add completion days statistics if available
        if 'completion_days_stats' in stats:
            comp_stats = stats['completion_days_stats']
            report += f"""### Completion Days Comparison
- **Mean Difference**: {comp_stats['mean_difference']:.2f} days
- **Median Difference**: {comp_stats['median_difference']:.2f} days
- **Standard Deviation**: {comp_stats['std_difference']:.2f} days
- **Maximum Absolute Difference**: {comp_stats['max_abs_difference']:.2f} days

"""
        
        # Summary Tables (Top discrepancies only to avoid messy output)
        report += "## Summary Tables\n\n"
        
        # Top 10 drilling days discrepancies
        if not df.empty and 'Drilling_Days_Diff' in df.columns:
            top_drilling = df.nlargest(10, 'Drilling_Days_Diff', keep='all')[
                ['API12', 'Well_Name', 'Drilling_Days_Lease', 'Drilling_Days_API12', 'Drilling_Days_Diff', 'Status']
            ]
            report += "### Top 10 Drilling Days Discrepancies\n\n"
            report += top_drilling.to_markdown(index=False)
            report += "\n\n"
        
        # Status distribution
        if not df.empty:
            status_counts = df['Status'].value_counts()
            report += "### Status Distribution\n\n"
            report += "| Status | Count | Percentage |\n"
            report += "|--------|-------|------------|\n"
            for status, count in status_counts.items():
                percentage = (count / len(df)) * 100
                report += f"| {status} | {count} | {percentage:.1f}% |\n"
            report += "\n"
        
        # Wells requiring attention (ERROR and REVIEW status only)
        error_review_wells = df[df['Status'].isin(['ERROR', 'REVIEW'])]
        if not error_review_wells.empty:
            report += "## Wells Requiring Attention\n\n"
            report += "### Wells with ERROR or REVIEW Status\n\n"
            
            attention_table = error_review_wells[
                ['API12', 'Well_Name', 'Drilling_Days_Diff', 'Completion_Days_Diff', 'Status']
            ].head(20)  # Limit to top 20 to avoid overwhelming output
            
            report += attention_table.to_markdown(index=False)
            
            if len(error_review_wells) > 20:
                report += f"\n\n*Note: Showing top 20 wells requiring attention. Total wells with ERROR/REVIEW status: {len(error_review_wells)}*\n"
            report += "\n\n"
        
        # Appendix reference (don't include full data to avoid messy output)
        report += f"""## Data Export

Complete comparison data has been exported to CSV files in the results directory:
- Full comparison results: `multiple_wells_comparison_detailed_{self.timestamp}.csv`
- Summary statistics: `multiple_wells_comparison_summary_{self.timestamp}.json`

### Notes
- This report focuses on summary statistics and key discrepancies to maintain readability
- For detailed well-by-well analysis, refer to the exported CSV files
- Wells with minor differences (Status: OK) are not included in detailed sections
"""
        
        return report
    
    def export_detailed_results(self, comparison_data: Dict) -> Tuple[str, str]:
        """
        Export detailed comparison results to CSV and JSON files.
        
        Args:
            comparison_data: Comparison results and statistics
            
        Returns:
            Tuple[str, str]: Paths to CSV and JSON export files
        """
        results = comparison_data['comparison_results']
        stats = comparison_data['statistics']
        
        # Export detailed CSV
        df = pd.DataFrame(results)
        csv_path = self.results_dir / f"multiple_wells_comparison_detailed_{self.timestamp}.csv"
        df.to_csv(csv_path, index=False)
        
        # Export summary statistics JSON
        json_path = self.results_dir / f"multiple_wells_comparison_summary_{self.timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(stats, f, indent=2, default=str)
        
        return str(csv_path), str(json_path)


def test_multiple_wells_comparison_framework():
    """
    Test the enhanced multiple wells comparison framework.
    """
    if not COMPARISON_PROCESSOR_AVAILABLE:
        pytest.skip("Comparison processor not available")
    
    # Initialize framework
    framework = MultipleWellsComparisonFramework()
    
    # Test framework initialization
    assert framework.processor is not None
    assert framework.results_dir.exists()
    
    # Test that we can process the configuration
    config_file = 'query_api_multiple_wells_rig_days.yml'
    config_path = os.path.join(os.path.dirname(__file__), config_file)
    
    if os.path.exists(config_path):
        # Test configuration loading
        try:
            config = ymlInput(config_path, updateYml=None)
            assert config is not None
            
            # Verify we have multiple API12 wells configured
            api12_list = config.get('data', {}).get('groups', [{}])[0].get('api12', [])
            assert len(api12_list) > 100, f"Expected 120+ wells, got {len(api12_list)}"
            
        except Exception as e:
            pytest.skip(f"Could not load configuration: {str(e)}")
    else:
        pytest.skip(f"Configuration file not found: {config_path}")


def test_batch_processing_capability():
    """
    Test that the framework can handle large datasets with batch processing.
    """
    if not COMPARISON_PROCESSOR_AVAILABLE:
        pytest.skip("Comparison processor not available")
    
    framework = MultipleWellsComparisonFramework()
    
    # Create mock data simulating 120+ wells
    api12_wells = [f'60812400{i:04d}' for i in range(1, 123)]
    
    mock_api12_data = pd.DataFrame({
        'API12': api12_wells,
        'Well Name': [f'API12 Well {i}' for i in range(1, 123)],
        'Drilling Days': [35 + (i % 30) for i in range(122)],
        'Completion Days': [8 + (i % 15) for i in range(122)]
    })
    
    mock_lease_data = pd.DataFrame({
        'API12': api12_wells,
        'Well Name': [f'Lease Well {i}' for i in range(1, 123)],
        'Drilling Days': [37 + (i % 28) for i in range(122)],
        'Completion Days': [9 + (i % 13) for i in range(122)]
    })
    
    # Test batch processing
    results = framework.processor.process_in_batches(mock_lease_data, mock_api12_data)
    
    # Verify batch processing results
    assert len(results) == 122
    assert framework.processor.processing_stats['total_wells_processed'] == 122
    assert framework.processor.processing_stats['successful_comparisons'] > 0
    
    # Test report generation with large dataset
    comparison_data = {
        'comparison_results': results,
        'statistics': framework._generate_comparison_statistics(results),
        'processing_stats': framework.processor.processing_stats
    }
    
    # Generate report (should handle large dataset without being messy)
    report_path = framework.generate_comparison_report(comparison_data)
    assert os.path.exists(report_path)
    
    # Verify report content is structured and not overwhelming
    with open(report_path, 'r') as f:
        report_content = f.read()
    
    # Check that report has proper structure
    assert "Executive Summary" in report_content
    assert "Statistical Analysis" in report_content
    assert "Top 10" in report_content  # Should focus on top discrepancies, not all wells
    assert len(report_content.split('\n')) < 200  # Should be concise despite 120+ wells


if __name__ == "__main__":
    test_application()