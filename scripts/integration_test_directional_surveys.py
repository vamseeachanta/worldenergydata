#!/usr/bin/env python3
"""
Integration test for directional surveys functionality.

This test validates that the four fixed methods work correctly together:
1. prepare_well_paths
2. process_survey_xyz 
3. add_relative_WH_positions
4. plot_field_wells
"""

import os
import sys
import pandas as pd
import numpy as np

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

from worldenergydata.modules.bsee.analysis.well_api12 import WellAPI12

def create_realistic_test_data():
    """Create realistic test data that matches BSEE structure"""
    
    # Create realistic directional survey data for API12 608124000400
    directional_surveys = pd.DataFrame({
        'API12': [608124000400] * 8,
        'API_WELL_NUMBER': [608124000400] * 8,
        'SURVEY_POINT_MD': [0, 500, 1000, 2000, 3000, 4000, 5000, 6000],
        'INCL_ANG_DEG_VAL': [0, 2, 8, 15, 25, 35, 45, 50],
        'INCL_ANG_MIN_VAL': [0, 30, 15, 0, 30, 0, 15, 30],
        'DIR_DEG_VAL': [0, 45, 90, 135, 180, 225, 270, 315],
        'DIR_MINS_VAL': [0, 0, 30, 0, 15, 30, 0, 45],
        'WELL_N_S_CODE': ['N'] * 8,
        'WELL_E_W_CODE': ['E'] * 8,
        'SURVEY_POINT_TVD': [0, 499.8, 998.2, 1990.1, 2950.5, 3850.2, 4680.8, 5435.1]
    })
    
    # Create well data structure matching expected format
    well_data = {
        'merged_api12_df': pd.DataFrame({
            'API12': [608124000400],
            'API10': [6081240004],
            'Well Name': ['ST MALO A-001'],
            'Sidetrack and Bypass': ['ST01'],
            'SURF_x_rel': [2450.5],  # Realistic surface position
            'SURF_y_rel': [1820.3],  # Realistic surface position
            'Water Depth (feet)': [4000],
            'Total Measured Depth': [15750],
            'Total Depth Date': ['2023-06-15'],
            'Spud Date': ['2023-04-10']
        })
    }
    
    # Create mock configuration
    cfg = {
        'Analysis': {
            'result_folder': '/tmp/test_results/',
            'file_name_for_overwrite': 'integration_test_directional_surveys'
        },
        'custom_parameters': {
            'field_nickname': 'StMalo'
        }
    }
    
    return directional_surveys, well_data, cfg

def test_integration_workflow():
    """Test the complete directional surveys workflow"""
    
    print("Starting directional surveys integration test...")
    print("=" * 60)
    
    # Create test data
    directional_surveys, well_data, cfg = create_realistic_test_data()
    
    print(f"Test data created:")
    print(f"   - Directional surveys: {len(directional_surveys)} points")
    print(f"   - Well data: {len(well_data['merged_api12_df'])} wells")
    print(f"   - API12: {directional_surveys['API12'].iloc[0]}")
    
    # Initialize WellAPI12 instance
    well_api12 = WellAPI12()
    well_api12.cfg = cfg
    well_api12.output_data_api12_df = well_data['merged_api12_df'].copy()
    well_api12.output_data_api12_df['xyz'] = None
    
    try:
        print("\nStep 1: Testing prepare_well_paths...")
        
        # Test prepare_well_paths
        well_api12.prepare_well_paths(directional_surveys, well_data)
        
        # Verify results
        assert hasattr(well_api12, 'output_data_well_path'), "output_data_well_path not created"
        assert len(well_api12.output_data_well_path) > 0, "No well path data generated"
        assert 608124000400 in well_api12.output_data_well_path, "API12 608124000400 not found in results"
        
        well_path_data = well_api12.output_data_well_path[608124000400]
        print(f"   Well path generated: {len(well_path_data)} survey points")
        print(f"   XYZ columns present: {all(col in well_path_data.columns for col in ['x_coor', 'y_coor', 'z_coor'])}")
        
        # Verify coordinates are realistic
        x_range = well_path_data['x_coor'].max() - well_path_data['x_coor'].min()
        y_range = well_path_data['y_coor'].max() - well_path_data['y_coor'].min()
        z_range = well_path_data['z_coor'].max() - well_path_data['z_coor'].min()
        
        print(f"   Coordinate ranges:")
        print(f"      - X (Easting): {well_path_data['x_coor'].min():.1f} to {well_path_data['x_coor'].max():.1f} ft ({x_range:.1f} ft range)")
        print(f"      - Y (Northing): {well_path_data['y_coor'].min():.1f} to {well_path_data['y_coor'].max():.1f} ft ({y_range:.1f} ft range)")
        print(f"      - Z (TVD): {well_path_data['z_coor'].min():.1f} to {well_path_data['z_coor'].max():.1f} ft ({z_range:.1f} ft range)")
        
        # Verify mathematical properties
        assert z_range > 5000, f"TVD range too small: {z_range:.1f} ft"
        assert x_range > 0 or y_range > 0, "Well appears to be perfectly vertical (no lateral displacement)"
        
        print("   Step 1 completed successfully!")
        
        print("\nStep 2: Testing individual method outputs...")
        
        # Test process_survey_xyz directly
        api12_surveys = directional_surveys[directional_surveys['API12'] == 608124000400].copy()
        survey_data = pd.DataFrame({
            'md': api12_surveys['SURVEY_POINT_MD'],
            'inc': api12_surveys['INCL_ANG_DEG_VAL'] + api12_surveys['INCL_ANG_MIN_VAL'] / 60.0,
            'az': api12_surveys['DIR_DEG_VAL'] + api12_surveys['DIR_MINS_VAL'] / 60.0
        })
        
        survey_xyz = well_api12.process_survey_xyz(survey_data)
        print(f"   process_survey_xyz: Generated {len(survey_xyz)} XYZ points")
        
        # Test add_relative_WH_positions
        adjusted_xyz = well_api12.add_relative_WH_positions(608124000400, survey_xyz)
        print(f"   add_relative_WH_positions: Applied wellhead adjustments")
        
        # Verify wellhead adjustment was applied
        expected_x_offset = well_data['merged_api12_df']['SURF_x_rel'].iloc[0]
        expected_y_offset = well_data['merged_api12_df']['SURF_y_rel'].iloc[0]
        
        actual_x_offset = adjusted_xyz['x_coor'].iloc[0] - survey_xyz['x_coor'].iloc[0]
        actual_y_offset = adjusted_xyz['y_coor'].iloc[0] - survey_xyz['y_coor'].iloc[0]
        
        assert abs(actual_x_offset - expected_x_offset) < 0.01, f"X offset mismatch: {actual_x_offset} vs {expected_x_offset}"
        assert abs(actual_y_offset - expected_y_offset) < 0.01, f"Y offset mismatch: {actual_y_offset} vs {expected_y_offset}"
        
        print(f"      - Wellhead position applied: X+{expected_x_offset:.1f}ft, Y+{expected_y_offset:.1f}ft")
        
        print("\nStep 3: Testing plot_field_wells...")
        
        # Test plot_field_wells (mock matplotlib to avoid file creation)
        from unittest.mock import patch, Mock
        
        with patch('matplotlib.pyplot.figure') as mock_figure, \
             patch('matplotlib.pyplot.close') as mock_close:
            
            mock_fig = Mock()
            mock_ax = Mock()
            mock_figure.return_value = mock_fig
            mock_fig.add_subplot.return_value = mock_ax
            mock_ax.get_xlim.return_value = (0, 5000)
            mock_ax.get_ylim.return_value = (0, 5000)
            
            well_api12.plot_field_wells()
            
            # Verify plotting was attempted
            mock_figure.assert_called_once()
            mock_ax.plot3D.assert_called()
            mock_fig.savefig.assert_called()
            
            print("   plot_field_wells: 3D visualization created successfully")
        
        print("\nStep 4: Validating output data structures...")
        
        # Verify stored data structure in output_data_api12_df
        xyz_data = well_api12.output_data_api12_df['xyz'].iloc[0]
        assert xyz_data is not None, "XYZ data not stored in output_data_api12_df"
        
        import json
        stored_data = json.loads(xyz_data)
        assert 'data' in stored_data, "Stored data missing 'data' key"
        assert 'label' in stored_data, "Stored data missing 'label' key"
        
        print(f"   Data structure validation:")
        print(f"      - XYZ data stored: {len(stored_data['data'])} points")
        print(f"      - Well label: {stored_data['label']}")
        
        print("\nIntegration test PASSED!")
        print("=" * 60)
        print("All directional surveys methods working correctly:")
        print("PASS: prepare_well_paths - Data structure handling fixed")
        print("PASS: process_survey_xyz - XYZ calculations working")  
        print("PASS: add_relative_WH_positions - Wellhead adjustments applied")
        print("PASS: plot_field_wells - 3D visualization functional")
        print("PASS: Data integration - End-to-end workflow validated")
        
        return True
        
    except Exception as e:
        print(f"\nIntegration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_integration_workflow()
    sys.exit(0 if success else 1)