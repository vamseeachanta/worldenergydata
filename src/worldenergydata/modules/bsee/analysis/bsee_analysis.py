# Standard library imports
import os
import json
import logging

# # # Third party imports
import pandas as pd
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
        
        logging.info(f"Analysis config: {cfg.get('analysis', {})}")
        
        if "analysis" in cfg and cfg['analysis'].get('flag', False):
            logging.info("Running analysis for all wells...")
            cfg = self.run_analysis_for_all_wells(cfg, data)
        else:
            logging.info("Analysis not enabled or flag is False")

        return cfg

    def run_analysis_for_all_wells(self, cfg, data):

        cfg, well_data_analysis_groups = well_api12_analysis.run_well_analysis(cfg, data)
        cfg, production_data_analysis_groups = prod_api12_analysis.run_production_analysis(cfg, data)

        # Add production dates to well summary
        self.add_production_dates_to_well_summary(cfg, well_data_analysis_groups, production_data_analysis_groups)

        return cfg

    def add_production_dates_to_well_summary(self, cfg, well_data_analysis_groups, production_data_analysis_groups):
        """Add start and last production dates to well summary."""
        import pandas as pd
        
        # Get the production summary data
        production_summary_df = production_data_analysis_groups.get('production_summary_df_groups', pd.DataFrame())
        well_summary_df = well_data_analysis_groups.get('well_summary_df_groups', pd.DataFrame())
        
        if production_summary_df.empty or well_summary_df.empty:
            logging.warning("Production or well summary data is empty - skipping production date integration")
            return
        
        # Add columns for production dates if they don't exist
        if 'START_PRODUCTION_DATE' not in well_summary_df.columns:
            well_summary_df['START_PRODUCTION_DATE'] = ''
        if 'LAST_PRODUCTION_DATE' not in well_summary_df.columns:
            well_summary_df['LAST_PRODUCTION_DATE'] = ''
        
        # Merge production dates into well summary based on API12
        for idx, row in production_summary_df.iterrows():
            api12 = str(row['API12'])
            start_date = row.get('START_PRODUCTION_DATE', '')
            last_date = row.get('LAST_PRODUCTION_DATE', '')
            
            # Update well summary with production dates - convert API12 to string for comparison
            well_mask = well_summary_df['API12'].astype(str) == api12
            if well_mask.any():
                if start_date and start_date != '':
                    well_summary_df.loc[well_mask, 'START_PRODUCTION_DATE'] = start_date
                if last_date and last_date != '':
                    well_summary_df.loc[well_mask, 'LAST_PRODUCTION_DATE'] = last_date
                logging.info(f"Updated production dates for API12 {api12}: start={start_date}, last={last_date}")
        
        # Update the groups dict with the modified well summary dataframe
        well_data_analysis_groups['well_summary_df_groups'] = well_summary_df
        
        # Save the updated well summary
        well_api12_analysis.save_result_groups(cfg, well_data_analysis_groups)


