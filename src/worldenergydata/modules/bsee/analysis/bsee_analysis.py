# Standard library imports
import os
import json
import logging

# # # Third party imports
import pandas as pd
import numpy as np
from worldenergydata.modules.bsee.data.bsee_data import BSEEData
from worldenergydata.modules.bsee.analysis.well_api12 import WellAPI12
from worldenergydata.modules.bsee.analysis.well_api10 import WellAPI10
from worldenergydata.modules.bsee.analysis.production_api12 import ProductionAPI12Analysis
from worldenergydata.modules.bsee.analysis.production_api10 import ProductionAPI10Analysis


bsee_data = BSEEData()
well_api12_analysis = WellAPI12()
well_api10_analysis = WellAPI10()

prod_api12_analysis = ProductionAPI12Analysis()
prod_api10_analysis = ProductionAPI10Analysis()

class BSEEAnalysis():

    def __init__(self):
        pass

    def router(self, cfg, data):

        if "analysis" in cfg and cfg['analysis'].get('flag', False):
            cfg = self.run_analysis_for_all_wells(cfg, data)

        return cfg

    def run_analysis_for_all_wells(self, cfg, data):

        cfg, well_data_analysis_groups = well_api12_analysis.run_well_analysis(cfg, data)
        cfg, production_data_analysis_groups = prod_api12_analysis.run_production_analysis(cfg, data)
        
        # Merge production summary data into well summary data
        if 'production_summary_df_groups' in production_data_analysis_groups and 'well_summary_df_groups' in well_data_analysis_groups:
            production_summary_df = production_data_analysis_groups['production_summary_df_groups']
            well_summary_df = well_data_analysis_groups['well_summary_df_groups']
            
            # Add production start and last dates to well summary
            well_summary_enhanced = self.merge_production_dates_to_well_summary(well_summary_df, production_summary_df)
            well_data_analysis_groups['well_summary_df_groups'] = well_summary_enhanced
            
            # Save the enhanced well summary
            well_api12_analysis.save_result_groups(cfg, well_data_analysis_groups)
            
            # Enhance timeline with production data
            if 'prod_rate_bopd_groups' in production_data_analysis_groups:
                prod_timeline_df = self.create_production_timeline(production_data_analysis_groups['prod_rate_bopd_groups'])
                enhanced_timeline_df = self.merge_production_timeline_to_well_timeline(
                    well_data_analysis_groups['well_timeline_df'], 
                    prod_timeline_df
                )
                well_data_analysis_groups['well_timeline_df'] = enhanced_timeline_df
                
                # Save enhanced timeline and re-plot
                well_api12_analysis.save_result_groups(cfg, well_data_analysis_groups)
                well_api12_analysis.plot_well_timeline_df(cfg, well_data_analysis_groups)

        return cfg

    def merge_production_dates_to_well_summary(self, well_summary_df, production_summary_df):
        """
        Merge production start and last dates into well summary DataFrame
        """
        if production_summary_df.empty:
            # Add empty production date columns if no production data
            well_summary_df['PRODUCTION_START_DATE'] = pd.NaT
            well_summary_df['PRODUCTION_LAST_DATE'] = pd.NaT
            return well_summary_df
            
        # Group production data by API12 to get earliest start and latest end dates
        production_dates = production_summary_df.groupby('API12').agg({
            'PRODUCTION_START_DATE': 'min',
            'PRODUCTION_LAST_DATE': 'max'
        }).reset_index()
        
        # Merge with well summary
        well_summary_enhanced = well_summary_df.merge(
            production_dates[['API12', 'PRODUCTION_START_DATE', 'PRODUCTION_LAST_DATE']], 
            on='API12', 
            how='left'
        )
        
        return well_summary_enhanced
    
    def create_production_timeline(self, prod_rate_df):
        """
        Create production timeline data from production rate DataFrame
        """
        if prod_rate_df.empty or 'PRODUCTION_DATETIME' not in prod_rate_df.columns:
            return pd.DataFrame(columns=['date_time', 'PRODUCTION_START_COUNT', 'PRODUCTION_ACTIVE_COUNT'])
            
        # Get all wells that have production data
        prod_columns = [col for col in prod_rate_df.columns if col != 'PRODUCTION_DATETIME']
        
        timeline_data = []
        active_wells = set()
        
        for _, row in prod_rate_df.iterrows():
            date_time = row['PRODUCTION_DATETIME']
            if pd.isna(date_time):
                continue
                
            # Count wells starting production (first non-null/non-zero value)
            new_producers = 0
            for col in prod_columns:
                if pd.notna(row[col]) and row[col] > 0:
                    if col not in active_wells:
                        new_producers += 1
                        active_wells.add(col)
            
            # Count currently active wells  
            currently_active = sum(1 for col in prod_columns 
                                 if pd.notna(row[col]) and row[col] > 0)
            
            timeline_data.append({
                'date_time': date_time,
                'PRODUCTION_START_COUNT': len(active_wells),  # Cumulative count of wells that started
                'PRODUCTION_ACTIVE_COUNT': currently_active   # Current active producers
            })
        
        return pd.DataFrame(timeline_data)
    
    def merge_production_timeline_to_well_timeline(self, well_timeline_df, prod_timeline_df):
        """
        Merge production timeline data into well timeline DataFrame
        """
        if prod_timeline_df.empty:
            # Add empty production timeline columns
            well_timeline_df['PRODUCTION_START_COUNT'] = None
            well_timeline_df['PRODUCTION_ACTIVE_COUNT'] = None
            return well_timeline_df
            
        # Merge production timeline data
        enhanced_timeline = well_timeline_df.merge(
            prod_timeline_df,
            on='date_time',
            how='outer'
        )
        
        # Sort by date and clean up
        enhanced_timeline = enhanced_timeline.replace({np.nan: None})
        enhanced_timeline.sort_values(by=['date_time'], inplace=True)
        enhanced_timeline.reset_index(drop=True, inplace=True)
        
        return enhanced_timeline


