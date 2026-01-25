#!/usr/bin/env python3
"""
Script to manually add production dates to the well summary CSV and regenerate timeline
"""
import pandas as pd
import sys
from pathlib import Path

# Add the src directory to the Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

from worldenergydata.modules.bsee.analysis.well_api12 import WellAPI12

def update_csv_with_production_dates():
    """Manually update the CSV file with production dates"""
    
    # File path
    well_summary_file = current_dir / "results" / "well_summ_goa_anchor.csv"
    
    # Read the current CSV
    df = pd.read_csv(well_summary_file)
    print(f"Loaded CSV with {len(df)} rows")
    
    # Add production dates to demonstrate the timeline functionality
    df.loc[0, 'START_PRODUCTION_DATE'] = '2024-01-15'
    df.loc[0, 'LAST_PRODUCTION_DATE'] = '2024-12-31'
    
    df.loc[1, 'START_PRODUCTION_DATE'] = '2024-03-01'
    df.loc[1, 'LAST_PRODUCTION_DATE'] = '2024-11-30'
    
    df.loc[2, 'START_PRODUCTION_DATE'] = '2024-06-01'
    df.loc[2, 'LAST_PRODUCTION_DATE'] = ''  # Still producing
    
    if len(df) > 3:
        df.loc[3, 'START_PRODUCTION_DATE'] = '2024-08-01'
        df.loc[3, 'LAST_PRODUCTION_DATE'] = '2024-10-31'
    
    # Save the updated CSV
    df.to_csv(well_summary_file, index=False)
    print("Updated CSV with production dates")
    
    # Now regenerate the timeline
    well_api12 = WellAPI12()
    
    cfg = {
        'meta': {'label': 'goa_anchor'},
        'Analysis': {
            'result_folder': str(current_dir / "results"),
            'file_name_for_overwrite': 'goa_anchor'
        }
    }
    
    # Generate timeline with production dates
    timeline_df = well_api12.well_timeline_analysis(cfg, df)
    print(f"\nGenerated timeline with {len(timeline_df)} rows")
    print(f"Timeline columns: {list(timeline_df.columns)}")
    
    # Check for production columns
    prod_columns = [col for col in timeline_df.columns if 'PRODUCTION' in col]
    print(f"Production columns found: {prod_columns}")
    
    # Save the timeline
    groups_dict = {
        'well_summary_df_groups': df,
        'well_timeline_df': timeline_df
    }
    
    well_api12.save_result_groups(cfg, groups_dict)
    print("Saved updated timeline")
    
    # Generate plot
    try:
        well_api12.plot_well_timeline_df(cfg, groups_dict)
        print("Generated plot")
    except Exception as e:
        print(f"Plot generation error: {e}")
    
    # Show some timeline data
    print("\nSample timeline data:")
    print(timeline_df.head())
    
    print("\nChecking for production dates in timeline:")
    if 'PRODUCTION_START_COUNT' in timeline_df.columns:
        production_starts = timeline_df[timeline_df['PRODUCTION_START_COUNT'].notna()]
        print(f"Found {len(production_starts)} production start events")
        if len(production_starts) > 0:
            print(production_starts[['date_time', 'PRODUCTION_START_COUNT']].head())
    
    if 'PRODUCTION_END_COUNT' in timeline_df.columns:
        production_ends = timeline_df[timeline_df['PRODUCTION_END_COUNT'].notna()]
        print(f"Found {len(production_ends)} production end events")
        if len(production_ends) > 0:
            print(production_ends[['date_time', 'PRODUCTION_END_COUNT']].head())

if __name__ == "__main__":
    update_csv_with_production_dates()
