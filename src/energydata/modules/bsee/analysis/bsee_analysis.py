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
from energydata.modules.bsee.analysis.production_api10 import ProductionAPI10Analysis

# from energydata.common.bsee_data_manager import BSEEData

# from energydata.common.data import AttributeDict, transform_df_datetime_to_str

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

        cfg = self.run_well_data_analysis(cfg, data)
        cfg = self.run_production_data_analysis(cfg, data)

        return cfg

    def run_production_data_analysis(self, cfg, data):
        production_data_groups = data.get('production_data', None)
        if production_data_groups is not None:
            production_group_api12_summary_df = pd.DataFrame()
            for group in production_data_groups:
                for production_data in group:
                    cfg, api12_summary = prod_api12_analysis.router(cfg, production_data)
                    production_group_api12_summary_df = pd.concat([production_group_api12_summary_df, api12_summary], ignore_index=True)

            cfg, production_group_api10_summary_df = prod_api10_analysis.router(cfg, production_group_api12_summary_df)

            block_number = cfg['data']['groups'][group_idx].get('bottom_block', [None])[0]
            if block_number is None:
                label = str(group_idx)
            else:
                label = str(block_number)
            file_label = 'block_' + label + '_api12'
            file_name = os.path.join(cfg['Analysis']['result_folder'], file_label + '.csv')
            production_group_api12_summary_df.to_csv(file_name, index=False)

            # file_name = os.path.join(cfg['Analysis']['result_folder'], 'api10_summary_' + cfg['Analysis']['file_name_for_overwrite'] + '.csv')
            # production_group_api10_summary_df.to_csv(file_name)

        return cfg

    def run_well_data_analysis(self, cfg, data):
        well_data_groups = data['well_data']

        if well_data_groups is not None:
            well_group_api12_summary_df = pd.DataFrame()
            for group_idx in range(0, len(well_data_groups)):
                group = well_data_groups[group_idx]
                for well_idx in range(0, len(group)):
                    well_data = group[well_idx]
                    cfg, api12_analysis = well_api12_analysis.router(cfg, well_data)
                    well_group_api12_summary_df = pd.concat([well_group_api12_summary_df, api12_analysis], ignore_index=True)
                    well_api12 = well_group_api12_summary_df.API12.iloc[0]
                    # api12_label = str(well_api12)
                    # file_name = 'api12_' + api12_label + '_data.csv'
                    # file_name = os.path.join(cfg['Analysis']['result_folder'], file_name)
                    # well_group_api12_summary_df.to_csv(file_name, index=False)
                    logging.info("Well data is prepared for well: " + str(well_api12))

                block_number = cfg['data']['groups'][group_idx].get('bottom_block', [None])[0]
                if block_number is None:
                    label = str(group_idx)
                else:
                    label = str(block_number)
                file_label = 'block_' + label + '_api12'
                file_name = os.path.join(cfg['Analysis']['result_folder'], file_label + '.csv')
                well_group_api12_summary_df.to_csv(file_name, index=False)

                # cfg, well_group_api10_summary_df = well_api10_analysis.router(cfg, well_group_api12_summary_df)
                # file_label = 'api10_' + cfg['Analysis']['file_name_for_overwrite'] + '_' + label
                # file_name = os.path.join(cfg['Analysis']['result_folder'], file_label + '.csv')
                # well_group_api10_summary_df.to_csv(file_name)

        return cfg
