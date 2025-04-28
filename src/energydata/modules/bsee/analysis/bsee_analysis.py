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

        #cfg, well_data_analysis_groups = well_api12_analysis.run_well_analysis(cfg, data)
        cfg, production_data_analysis_groups = prod_api12_analysis.run_production_analysis(cfg, data)

        return cfg


