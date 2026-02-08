#!/usr/bin/env python3
"""
Simple test to generate actual 3D plots from directional surveys data
"""

import os
import sys
import pandas as pd
import numpy as np

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

from worldenergydata.bsee.analysis.well_api12 import WellAPI12

def test_actual_3d_plotting():
    """Generate actual 3D plots to verify visualization works"""
    
    print("Testing actual 3D plot generation...")
    
    # Create realistic test data
    directional_surveys = pd.DataFrame({
        'API12': [608124000400] * 6,
        'API_WELL_NUMBER': [608124000400] * 6,
        'SURVEY_POINT_MD': [0, 1000, 2000, 3000, 4000, 5000],
        'INCL_ANG_DEG_VAL': [0, 5, 15, 25, 35, 45],
        'INCL_ANG_MIN_VAL': [0, 0, 0, 0, 0, 0],
        'DIR_DEG_VAL': [0, 45, 90, 135, 180, 225],
        'DIR_MINS_VAL': [0, 0, 0, 0, 0, 0],
        'WELL_N_S_CODE': ['N'] * 6,
        'WELL_E_W_CODE': ['E'] * 6,
        'SURVEY_POINT_TVD': [0, 999, 1980, 2920, 3800, 4600]
    })
    
    well_data = {
        'merged_api12_df': pd.DataFrame({
            'API12': [608124000400],
            'API10': [6081240004],
            'Well Name': ['TEST WELL'],
            'Sidetrack and Bypass': ['ST01'],
            'SURF_x_rel': [1000.0],
            'SURF_y_rel': [2000.0],
            'Water Depth (feet)': [4000],
            'Total Measured Depth': [12000],
            'Total Depth Date': ['2023-06-15'],
            'Spud Date': ['2023-04-10']
        })
    }
    
    # Create output directory
    output_dir = "test_output"
    os.makedirs(output_dir, exist_ok=True)
    
    cfg = {
        'Analysis': {
            'result_folder': f'./{output_dir}/',
            'file_name_for_overwrite': 'test_directional_surveys'
        },
        'custom_parameters': {
            'field_nickname': 'TestField'
        }
    }
    
    # Initialize WellAPI12
    well_api12 = WellAPI12()
    well_api12.cfg = cfg
    well_api12.output_data_api12_df = well_data['merged_api12_df'].copy()
    well_api12.output_data_api12_df['xyz'] = None
    
    try:
        # Process the directional surveys
        print("1. Running prepare_well_paths...")
        well_api12.prepare_well_paths(directional_surveys, well_data)
        
        # Verify data was created
        if len(well_api12.output_data_well_path) > 0:
            print(f"   ✓ Well path data created for {len(well_api12.output_data_well_path)} wells")
            
            well_path = well_api12.output_data_well_path[608124000400]
            print(f"   ✓ Survey points: {len(well_path)}")
            print(f"   ✓ X range: {well_path['x_coor'].min():.1f} to {well_path['x_coor'].max():.1f} ft")
            print(f"   ✓ Y range: {well_path['y_coor'].min():.1f} to {well_path['y_coor'].max():.1f} ft")
            print(f"   ✓ Z range: {well_path['z_coor'].min():.1f} to {well_path['z_coor'].max():.1f} ft")
        
        # Generate actual 3D plot
        print("\n2. Generating 3D plot...")
        well_api12.plot_field_wells()
        
        # Check if plot file was created
        plot_file = f"{output_dir}/test_directional_surveys_well_paths.png"
        if os.path.exists(plot_file):
            print(f"   ✓ 3D plot saved successfully: {plot_file}")
            print(f"   ✓ File size: {os.path.getsize(plot_file)} bytes")
            return True
        else:
            print(f"   ✗ Plot file not found: {plot_file}")
            return False
            
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_actual_3d_plotting()
    if success:
        print("\n🎉 SUCCESS: All directional surveys methods working!")
        print("Check the test_output/ directory for the generated 3D plot.")
    else:
        print("\n❌ FAILED: Issues with directional surveys methods.")
    
    sys.exit(0 if success else 1)