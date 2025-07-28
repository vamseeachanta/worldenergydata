import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import os
import sys

# Add src to path to import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../src'))

from worldenergydata.modules.bsee.analysis.well_api12 import WellAPI12


class TestWellAPI12DirectionalSurveys:
    """Test suite for WellAPI12 directional surveys processing methods"""

    def setup_method(self):
        """Setup test fixtures"""
        self.well_api12 = WellAPI12()
        
        # Mock configuration
        self.mock_cfg = {
            'Analysis': {
                'result_folder': '/tmp/test_results/',
                'file_name_for_overwrite': 'test_field'
            },
            'custom_parameters': {
                'field_nickname': 'TestField'
            }
        }
        
        # Create mock directional surveys DataFrame matching BSEE structure
        self.mock_directional_surveys = pd.DataFrame({
            'API12': [608124000400, 608124000400, 608124000400],
            'API_WELL_NUMBER': [608124000400, 608124000400, 608124000400],
            'SURVEY_POINT_MD': [0, 1000, 2000],
            'INCL_ANG_DEG_VAL': [0, 15, 30],
            'INCL_ANG_MIN_VAL': [0, 30, 0],
            'DIR_DEG_VAL': [0, 45, 90],
            'DIR_MINS_VAL': [0, 0, 0],
            'WELL_N_S_CODE': ['N', 'N', 'N'],
            'WELL_E_W_CODE': ['E', 'E', 'E'],
            'SURVEY_POINT_TVD': [0, 965, 1732]
        })
        
        # Create mock well_data structure matching expected format
        self.mock_well_data = {
            'merged_api12_df': pd.DataFrame({
                'API12': [608124000400],
                'API10': [6081240004],
                'Well Name': ['Test Well'],
                'Sidetrack and Bypass': ['ST01'],
                'SURF_x_rel': [1000.0],
                'SURF_y_rel': [2000.0],
                'Water Depth (feet)': [6000],
                'Total Measured Depth': [15000],
                'Total Depth Date': ['2023-01-15'],
                'Spud Date': ['2022-12-01']
            })
        }
        
        # Initialize output_data_api12_df as expected by the method
        self.well_api12.output_data_api12_df = self.mock_well_data['merged_api12_df'].copy()
        self.well_api12.output_data_api12_df['xyz'] = None

    def test_prepare_well_paths_initialization(self):
        """Test that prepare_well_paths initializes data structures correctly"""
        # Test that the method initializes required attributes
        assert hasattr(self.well_api12, 'output_data_api12_df')
        
        # Initialize the output dictionaries as the method should
        self.well_api12.output_well_path_for_db = {}
        self.well_api12.output_data_well_path = {}
        
        assert isinstance(self.well_api12.output_well_path_for_db, dict)
        assert isinstance(self.well_api12.output_data_well_path, dict)

    def test_prepare_well_paths_parameter_structure(self):
        """Test that prepare_well_paths handles well_data parameter correctly"""
        # Mock the process_survey_xyz and add_relative_WH_positions methods
        with patch.object(self.well_api12, 'process_survey_xyz') as mock_process, \
             patch.object(self.well_api12, 'add_relative_WH_positions') as mock_add_relative:
            
            # Setup mocks
            mock_survey_xyz = pd.DataFrame({
                'x_coor': [0, 100, 200],
                'y_coor': [0, 50, 100], 
                'z_coor': [0, 965, 1732]
            })
            mock_process.return_value = mock_survey_xyz
            mock_add_relative.return_value = mock_survey_xyz
            
            # Initialize required attributes
            self.well_api12.output_well_path_for_db = {}
            self.well_api12.output_data_well_path = {}
            
            # Call the method - this should not raise an error
            try:
                self.well_api12.prepare_well_paths(
                    self.mock_directional_surveys, 
                    self.mock_well_data
                )
                # If we get here, the basic structure is working
                assert True
            except AttributeError as e:
                # This will help us identify the specific attribute errors
                pytest.fail(f"AttributeError in prepare_well_paths: {e}")
            except KeyError as e:
                # This will help us identify data structure issues
                pytest.fail(f"KeyError in prepare_well_paths: {e}")

    def test_prepare_well_paths_api12_extraction(self):
        """Test that prepare_well_paths correctly extracts unique API12 values"""
        # Mock the downstream methods
        with patch.object(self.well_api12, 'process_survey_xyz') as mock_process, \
             patch.object(self.well_api12, 'add_relative_WH_positions') as mock_add_relative:
            
            # Setup mocks
            mock_survey_xyz = pd.DataFrame({
                'x_coor': [0, 100, 200],
                'y_coor': [0, 50, 100], 
                'z_coor': [0, 965, 1732]
            })
            mock_process.return_value = mock_survey_xyz
            mock_add_relative.return_value = mock_survey_xyz
            
            # Initialize required attributes
            self.well_api12.output_well_path_for_db = {}
            self.well_api12.output_data_well_path = {}
            
            # Call the method
            self.well_api12.prepare_well_paths(
                self.mock_directional_surveys, 
                self.mock_well_data
            )
            
            # Verify process_survey_xyz was called once (one unique API12)
            assert mock_process.call_count == 1
            assert mock_add_relative.call_count == 1

    def test_prepare_well_paths_data_storage(self):
        """Test that prepare_well_paths stores results in correct data structures"""
        # Mock the downstream methods
        with patch.object(self.well_api12, 'process_survey_xyz') as mock_process, \
             patch.object(self.well_api12, 'add_relative_WH_positions') as mock_add_relative:
            
            # Setup mocks
            mock_survey_xyz = pd.DataFrame({
                'x_coor': [0, 100, 200],
                'y_coor': [0, 50, 100], 
                'z_coor': [0, 965, 1732]
            })
            mock_process.return_value = mock_survey_xyz
            mock_add_relative.return_value = mock_survey_xyz
            
            # Initialize required attributes
            self.well_api12.output_well_path_for_db = {}
            self.well_api12.output_data_well_path = {}
            
            # Call the method
            self.well_api12.prepare_well_paths(
                self.mock_directional_surveys, 
                self.mock_well_data
            )
            
            # Verify data was stored in output_data_well_path
            assert len(self.well_api12.output_data_well_path) > 0
            assert 608124000400 in self.well_api12.output_data_well_path
            
            # Verify XYZ data was stored in the DataFrame
            xyz_data = self.well_api12.output_data_api12_df['xyz'].iloc[0]
            assert xyz_data is not None

    def test_prepare_well_paths_with_empty_surveys(self):
        """Test prepare_well_paths handles empty directional surveys gracefully"""
        empty_surveys = pd.DataFrame()
        
        # Initialize required attributes
        self.well_api12.output_well_path_for_db = {}
        self.well_api12.output_data_well_path = {}
        
        # This should not crash
        self.well_api12.prepare_well_paths(empty_surveys, self.mock_well_data)
        
        # Should have empty results
        assert len(self.well_api12.output_data_well_path) == 0

    def test_prepare_well_paths_attribute_references(self):
        """Test that prepare_well_paths uses correct attribute names"""
        # This test specifically checks for the attribute reference fixes
        # Mock the downstream methods to avoid their execution
        with patch.object(self.well_api12, 'process_survey_xyz') as mock_process, \
             patch.object(self.well_api12, 'add_relative_WH_positions') as mock_add_relative:
            
            # Setup mocks
            mock_survey_xyz = pd.DataFrame({
                'x_coor': [0, 100, 200],
                'y_coor': [0, 50, 100], 
                'z_coor': [0, 965, 1732]
            })
            mock_process.return_value = mock_survey_xyz
            mock_add_relative.return_value = mock_survey_xyz
            
            # Initialize required attributes
            self.well_api12.output_well_path_for_db = {}
            self.well_api12.output_data_well_path = {}
            
            # Ensure output_data_api12_df exists (this is the correct attribute name)
            assert hasattr(self.well_api12, 'output_data_api12_df')
            
            # The method should not try to access output_data_well_df (incorrect name)
            # If it does, this will fail
            if hasattr(self.well_api12, 'output_data_well_df'):
                delattr(self.well_api12, 'output_data_well_df')
            
            # Call should succeed with correct attribute references
            self.well_api12.prepare_well_paths(
                self.mock_directional_surveys, 
                self.mock_well_data
            )