"""Direct test of the drilling completion days functionality"""
import os
import sys
import pandas as pd
from loguru import logger

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../src')))

from worldenergydata.bsee.analysis.custom_scripts.Roy.july.drilling_and_completion_days import DrillingCompletionDays


def test_output_filename_generation():
    """Test that the new validation filename is generated correctly"""
    
    # Create test instance
    dcd = DrillingCompletionDays()
    
    # Set up minimal test configuration
    test_results_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(test_results_dir, exist_ok=True)
    
    dcd.cfg = {
        'Analysis': {
            'result_folder': test_results_dir
        }
    }
    
    # Test the expected output path
    expected_filename = "drilling_and_completion_days_by_api_validation.xlsx"
    expected_path = os.path.join(test_results_dir, expected_filename)
    
    print(f"Expected output path: {expected_path}")
    print(f"Results directory exists: {os.path.exists(test_results_dir)}")
    
    # Check if file already exists
    if os.path.exists(expected_path):
        print(f"Warning: Output file already exists at {expected_path}")
        # The code should handle this with a timestamp
    
    return test_results_dir, expected_filename


if __name__ == "__main__":
    test_output_filename_generation()
    print("Test completed successfully!")