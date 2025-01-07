# Standard library imports
import os

import pandas as pd
from common.database import get_db_connection


class BSEEData:

    def __init__(self, cfg=None):
        self.assign_cfg(cfg)
        input_bsee_db_properties = cfg['input_bsee_db']
        self.dbe, self.connection_status = get_db_connection(input_bsee_db_properties)

    def assign_cfg(self, cfg):
        self.cfg = cfg

    def get_api10_list(self):
        api10_list = []
        filename = os.path.join('sql', 'bsee.get_all_wells.sql')
        if os.path.isfile(filename):
            try:
                df = self.dbe.executeScriptsFromFile(filename)
                api10_list = df.API10.to_list()
            except:
                print("Error getting data from Database")
        else:
            print("Not a valid filename")

        return api10_list

    def get_well_data_by_api10(self, api10):
        filename = os.path.join('sql', 'bsee.well_data_by_api10.sql')
        df = self.get_data_by_api12(api10, filename)
        return df

    def get_production_data_by_api10(self, api10):
        filename = os.path.join('sql', 'bsee.production_data_by_api10.sql')
        df = self.get_data_by_api12(api10, filename)
        return df

    def get_WAR_summary_by_api10(self, api10):
        filename = os.path.join('sql', 'bsee.WAR_summary_data_by_api10.sql')
        df = self.get_data_by_api12(api10, filename)
        return df

    def get_directional_surveys_by_api10(self, api10):
        filename = os.path.join('sql', 'bsee.directional_surveys_data_by_api10.sql')
        df = self.get_data_by_api12(api10, filename)
        return df

    def get_ST_BP_and_tree_height_by_api10(self, api10):
        filename = os.path.join('sql', 'bsee.ST_BP_and_tree_height_data_by_api10.sql')
        df = self.get_data_by_api12(api10, filename)
        return df

    def get_well_tubulars_data_by_api10(self, api10):
        filename = os.path.join('sql', 'bsee.well_tubulars_data_by_api10.sql')
        df = self.get_data_by_api12(api10, filename)
        return df

    def get_completion_data_by_api10(self, api10):
        filename = os.path.join('sql', 'bsee.completion_data_by_api10.sql')
        df = self.get_data_by_api12(api10, filename)
        return df

    def get_data_by_api12(self, api10, filename):
        df = pd.DataFrame()
        if os.path.isfile(filename):
            try:
                df = self.dbe.executeScriptsFromFile(filename, [api10])
            except:
                print("Error getting data from Database")
        else:
            print("Not a valid filename: {}".format(filename))
        return df
