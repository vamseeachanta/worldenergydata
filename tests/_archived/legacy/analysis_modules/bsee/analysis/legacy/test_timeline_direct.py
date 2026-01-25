#!/usr/bin/env python3
"""
Direct test to add production dates to well summary and regenerate timeline
"""
import pandas as pd
import sys
from pathlib import Path

# Add the src directory to the Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

from worldenergydata.modules.bsee.analysis.well_api12 import WellAPI12

def test_timeline_with_production_dates():
    """Test timeline generation with production dates"""
    
    # Load existing well summary
    well_summary_file = current_dir / "results" / "well_summ_goa_anchor.csv"
    
    if not well_summary_file.exists():
        print(f"Well summary file not found: {well_summary_file}")
        return
    
    # Read the well summary
    well_summary_df = pd.read_csv(well_summary_file)
    print(f"Original well summary shape: {well_summary_df.shape}")
    print(f"Columns: {list(well_summary_df.columns)}")
    
    # Add some test production dates
    if 'START_PRODUCTION_DATE' in well_summary_df.columns:
        # Add production dates to first few wells
        well_summary_df.loc[0, 'START_PRODUCTION_DATE'] = '2024-01-15'
        well_summary_df.loc[0, 'LAST_PRODUCTION_DATE'] = '2024-12-31'
        
        if len(well_summary_df) > 1:
            well_summary_df.loc[1, 'START_PRODUCTION_DATE'] = '2024-03-01'
            well_summary_df.loc[1, 'LAST_PRODUCTION_DATE'] = '2024-11-30'
        
        if len(well_summary_df) > 2:
            well_summary_df.loc[2, 'START_PRODUCTION_DATE'] = '2024-06-01'
            well_summary_df.loc[2, 'LAST_PRODUCTION_DATE'] = ''  # Still producing
        
        print("Added test production dates")
        
        # Save the updated well summary
        well_summary_df.to_csv(well_summary_file, index=False)
        print(f"Updated well summary saved to: {well_summary_file}")
        
        # Generate timeline
        well_api12_analysis = WellAPI12()
        
        # Create a mock config
        cfg = {
            'meta': {'label': 'goa_anchor'},
            'Analysis': {
                'result_folder': str(current_dir / "results"),
                'file_name_for_overwrite': 'goa_anchor'
            }
        }
        
        # Generate timeline
        print("Generating timeline...")
        well_timeline_df = well_api12_analysis.well_timeline_analysis(cfg, well_summary_df)
        print(f"Timeline shape: {well_timeline_df.shape}")
        print(f"Timeline columns: {list(well_timeline_df.columns)}")
        
        # Check if production columns exist
        expected_columns = ['PRODUCTION_START_COUNT', 'PRODUCTION_END_COUNT', 'PRODUCING_CURRENTLY_COUNT']
        for col in expected_columns:
            if col in well_timeline_df.columns:
                print(f"✓ {col} found in timeline")
            else:
                print(f"✗ {col} missing from timeline")
        
        # Save timeline
        groups_dict = {
            'well_summary_df_groups': well_summary_df,
            'well_timeline_df': well_timeline_df
        }
        
        well_api12_analysis.save_result_groups(cfg, groups_dict)
        print("Timeline saved")
        
        # Generate plot
        try:
            well_api12_analysis.plot_well_timeline_df(cfg, groups_dict)
            print("✓ Plot generated successfully")
        except Exception as e:
            print(f"✗ Plot generation failed: {e}")
        
        # Show sample timeline data
        print("\nSample timeline data:")
        print(well_timeline_df.head(10))
        
    else:
        print("START_PRODUCTION_DATE column not found in well summary")

if __name__ == "__main__":
    test_timeline_with_production_dates()
