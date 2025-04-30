import os
import pickle
import pandas as pd
from copy import deepcopy
import logging
from loguru import logger

from energydata.modules.bsee.data.scrapy_well_data import ScrapyRunnerAPI
from energydata.modules.bsee.data.block_data import BlockData

from assetutilities.common.utilities import is_dir_valid_func
from assetutilities.common.yml_utilities import WorkingWithYAML  # noqa
from assetutilities.common.utilities import get_repository_filename, get_repository_filepath
from assetutilities.modules.zip_utilities.zip_files_to_dataframe import ZipFilestoDf

wwy = WorkingWithYAML()
zip_files_to_df = ZipFilestoDf()

block_data = BlockData()

class WellDataFromZip:

    def __init__(self):
        pass

    def router(self, cfg):
        
        cfg, well_data  = self.get_well_data_all_wells(cfg)

        #TODO Other data sources
        # directional_surveys = self.bsee_data.get_directional_surveys_by_api10(api10)
        # well_tubulars_data = self.bsee_data.get_well_tubulars_data_by_api10(api10)
        # completion_data = self.bsee_data.get_completion_data_by_api10(api10)

        return cfg, well_data
        
    def get_eWellAPMRawData_from_zip(self, cfg):
        
        columns = [MMS_COMPANY_NUM,
                    API_WELL_NUMBER,
                    WATER_DEPTH,
                    WELL_NM_BP_SFIX,
                    WELL_NM_ST_SFIX,
                    SURF_AREA_CODE,
                    SURF_BLOCK_NUM,
                    SURF_LEASE_NUM,
                    BOTM_AREA_CODE,
                    BOTM_BLOCK_NUM,
                    BOTM_LEASE_NUM,
                    RIG_ID_NUM,
                    BOREHOLE_STAT_CD,
                    WELL_TYPE_CODE,
                    BUS_ASC_NAME]

        #TODO 

    def save_eWellAPMRawData_to_binary(self, cfg):
        folder_path_zip = cfg['parameters']['filepath']['apm']['zip']
        library_name = 'energydata'
        library_file_cfg = {
            'filepath': folder_path_zip,
            'library_name': library_name
        }
        folder_path_zip = wwy.get_library_filepath(library_file_cfg, src_relative_location_flag=False)
        if not os.path.exists(folder_path_zip):
            raise FileNotFoundError(f"The folder '{folder_path_zip}' does not exist.")

        folder_path_bin = cfg['parameters']['filepath']['apm']['bin']
        library_file_cfg = {
            'filepath': folder_path_bin,
            'library_name': library_name
        }
        folder_path_bin = wwy.get_library_filepath(library_file_cfg, src_relative_location_flag=False)
        if not os.path.exists(folder_path_zip):
            raise FileNotFoundError(f"The folder '{folder_path_zip}' does not exist.")

        for file_name in os.listdir(folder_path_zip):

            file_name_with_path = os.path.join(folder_path_zip, file_name)
            column_names = None
            cfg_zip_utilities = {'zip_utilities': {}}
            cfg_zip_utilities['zip_utilities'] = {
                'technique': 'zip_files_to_df',
                'input_directory': folder_path_zip,
                'column_names': column_names,
                'file_name': file_name_with_path
            }

            dfs = zip_files_to_df.router(cfg_zip_utilities)

            for key, df in dfs.items():
                if len(df) > 0:
                    file_label = key
                    file_name = file_label + '.bin'
                    file_name_with_path = os.path.join(folder_path_bin, file_name)
                    with open(file_name_with_path, "wb") as f:
                        pickle.dump(df, f)

