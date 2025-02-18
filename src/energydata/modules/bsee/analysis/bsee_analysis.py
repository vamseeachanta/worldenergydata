# Standard library imports
import json
import logging

# # # Third party imports
import pandas as pd
from energydata.modules.bsee.data.bsee_data import BSEEData
from energydata.modules.bsee.analysis.well_analysis import WellAnalysis

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

    def assign_cfg(self, cfg):
        self.cfg = cfg

    def run_analysis_for_all_wells(self):
        for api10 in self.api10_list[0:20]:
            well_data_analysis.router(cfg)
    
    def prepare_data_for_api10(self, api10):

