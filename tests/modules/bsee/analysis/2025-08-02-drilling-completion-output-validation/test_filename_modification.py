"""Test to verify filename modification doesn't break functionality"""
import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../src')))

from worldenergydata.modules.bsee.analysis.custom_scripts.Roy.july.drilling_and_completion_days import DrillingCompletionDays


class TestFilenameModification:
    """Test suite for verifying filename modification functionality"""
    
    def test_original_filename_pattern(self):
        """Test that the validation filename is as expected"""
        # Create instance
        dcd = DrillingCompletionDays()
        
        # Find the actual file path
        import inspect
        module_file = inspect.getfile(dcd.__class__)
        
        # Check the modified filename in the file
        with open(module_file, 'r') as f:
            content = f.read()
            # The filename should now be the validation version
            assert 'drilling_and_completion_days_by_api_validation.xlsx' in content
    
    def test_import_module_successful(self):
        """Test that the module can be imported successfully"""
        try:
            from worldenergydata.modules.bsee.analysis.custom_scripts.Roy.july.drilling_and_completion_days import DrillingCompletionDays
            assert True
        except ImportError:
            pytest.fail("Failed to import DrillingCompletionDays module")
    
    def test_class_instantiation(self):
        """Test that the class can be instantiated"""
        dcd = DrillingCompletionDays()
        assert dcd is not None
        assert hasattr(dcd, 'router')
        assert hasattr(dcd, '_process_analysis')
    
    @patch('pandas.DataFrame.to_excel')
    @patch('os.path.join')
    def test_filename_usage_in_process_analysis(self, mock_join, mock_to_excel):
        """Test that the filename is used correctly in the process"""
        # Create instance
        dcd = DrillingCompletionDays()
        
        # Mock the configuration
        dcd.cfg = {
            'Analysis': {
                'result_folder': '/test/results'
            }
        }
        
        # Mock other required attributes
        dcd.lease_df = MagicMock()
        dcd.leases = []
        dcd.main_war = MagicMock()
        dcd.main_war_filtered = MagicMock()
        dcd.boreholes = MagicMock()
        dcd.main_prop = MagicMock()
        
        # Set up mock return value
        mock_join.return_value = '/test/results/drilling_and_completion_days_by_api.xlsx'
        
        # We'll test this after modification to ensure it still works
        # This is a placeholder that will be updated when we modify the filename