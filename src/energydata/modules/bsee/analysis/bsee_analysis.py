# Standard library imports
import json
import logging

# # # Third party imports
import pandas as pd
from energydata.modules.bsee.data.bsee_data import BSEEData
from energydata.modules.bsee.analysis.well_api12 import WellAPI12
from energydata.modules.bsee.analysis.production import ProductionAnalysis

# from energydata.common.bsee_data_manager import BSEEData

# from energydata.common.data import AttributeDict, transform_df_datetime_to_str

bsee_data = BSEEData()
well_data_analysis = WellAPI12()
prod_analysis = ProductionAnalysis()

class BSEEAnalysis():

    def __init__(self):
        pass
        # self.bsee_data = BSEEData(self.cfg)

    def router(self, cfg, data):

        if 'analysis' in cfg and cfg['analysis']['flag']:
            if cfg['data']['by'] == 'API12':
                cfg = self.run_analysis_for_all_wells(cfg, data)

        return cfg

    def assign_cfg(self, cfg):
        self.cfg = cfg

    def run_analysis_for_all_wells(self, cfg, data):

        well_data_groups = data['well_data']
        production_data_groups = data['production_data']

        if well_data_groups is not None:
            for group in well_data_groups:

                api12_df = group[0]['api12_df']
                cfg = well_data_analysis.router(cfg, api12_df)

        if production_data_groups is not None:
            for group in production_data_groups:

                api12_df = group[0]['api12_df']
                cfg = prod_analysis.router(cfg, api12_df)

        return cfg

