# Standard library imports
import os
import json
import logging

# # # Third party imports
import pandas as pd
from energydata.modules.bsee.data.bsee_data import BSEEData
from energydata.modules.bsee.analysis.well_api12 import WellAPI12
from energydata.modules.bsee.analysis.well_api10 import WellAPI10
from energydata.modules.bsee.analysis.production_api12 import ProductionAPI12Analysis

# from energydata.common.bsee_data_manager import BSEEData

# from energydata.common.data import AttributeDict, transform_df_datetime_to_str

bsee_data = BSEEData()
well_api12_analysis = WellAPI12()
well_api10_analysis = WellAPI10()

prod_api12_analysis = ProductionAPI12Analysis()

class BSEEAnalysis():

    def __init__(self):
        pass
        # self.bsee_data = BSEEData(self.cfg)

    def router(self, cfg, data):

        if 'analysis' in cfg and cfg['analysis']['flag']:
            if cfg['data']['by'] == 'API12':
                cfg = self.run_analysis_for_all_wells(cfg, data)

        return cfg

    def run_analysis_for_all_wells(self, cfg, data):

        cfg = self.run_well_data_analysis(cfg, data)
        cfg = self.run_production_data_analysis(cfg, data)

        return cfg

    def run_production_data_analysis(self, cfg, data):
        production_data_groups = data['production_data']
        if production_data_groups is not None:
            for group in production_data_groups:
                for well in group:
                    api12_df = well['api12_df']
                    cfg = prod_api12_analysis.router(cfg, api12_df)

        return cfg

    def run_well_data_analysis(self, cfg, data):
        well_data_groups = data['well_data']
        well_group_api12_summary_df = pd.DataFrame()

        if well_data_groups is not None:
            for group in well_data_groups:
                for well in group:
                    api12_df = well['api12_df']
                    cfg, api12_summary = well_api12_analysis.router(cfg, api12_df)
                    well_group_api12_summary_df = pd.concat([well_group_api12_summary_df, api12_summary], ignore_index=True)

            cfg, well_group_api10_summary_df = well_api10_analysis.router(cfg, well_group_api12_summary_df)

        file_name = os.path.join(cfg['Analysis']['result_folder'], cfg['Analysis']['file_name_for_overwrite'] + 'api12_summary.csv')
        well_group_api12_summary_df.to_csv(file_name)

        file_name = os.path.join(cfg['Analysis']['result_folder'], cfg['Analysis']['file_name_for_overwrite'] + 'api10_summary.csv')
        well_group_api10_summary_df.to_csv(file_name)

        return cfg


