# Standard library imports
import json
import logging

# # # Third party imports
import pandas as pd
from energydata.modules.bsee.data.bsee_data import BSEEData
from energydata.modules.bsee.analysis.well_basic import WellAnalysis

# from energydata.common.bsee_data_manager import BSEEData

# from energydata.common.data import AttributeDict, transform_df_datetime_to_str

bsee_data = BSEEData()
well_data_analysis = WellAnalysis()

class BSEEAnalysis():

    def __init__(self):
        pass
        # self.bsee_data = BSEEData(self.cfg)

    def router(self, cfg):

        #TODO Reroute to data via bsee_data.router
        cfg = bsee_data.router(cfg)
        if cfg['data']['by'] == 'API12':
            cfg = self.run_analysis_for_all_wells(cfg)

        return cfg

    def assign_cfg(self, cfg):
        self.cfg = cfg

    def run_analysis_for_all_wells(self, cfg):
        api12_list = cfg[cfg['basename']]['api12']
        
        groups = cfg[cfg['basename']]['well_data']['groups']
        for group in groups:
            well_data_by_api = pd.read_csv(group['file_name'])
            bore_hole_apd_df = cfg[cfg['basename']]['Borehole_apd_df']
            well_data_analysis.router(cfg, well_data_by_api, bore_hole_apd_df)

