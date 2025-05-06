import os
import pickle
import pandas as pd
from copy import deepcopy
import logging
from loguru import logger

from worldenergydata.modules.bsee.data.scrapy_well_data import ScrapyRunnerAPI
from worldenergydata.modules.bsee.data.block_data import BlockData

from assetutilities.common.utilities import is_dir_valid_func
from assetutilities.common.yml_utilities import WorkingWithYAML  # noqa
from assetutilities.common.utilities import get_repository_filename, get_repository_filepath
from assetutilities.modules.zip_utilities.zip_files_to_dataframe import ZipFilestoDf

wwy = WorkingWithYAML()
zip_files_to_df = ZipFilestoDf()

block_data = BlockData()

class APMData:

    def __init__(self, cfg):
        self.load_bin_data(cfg)

    def load_bin_data(self, cfg):
        folder_path_bin = cfg['parameters']['filepath']['apm']['bin']
        library_name = 'worldenergydata'
        library_file_cfg = {
            'filepath': folder_path_bin,
            'library_name': library_name
        }
        folder_path_bin = wwy.get_library_filepath(library_file_cfg, src_relative_location_flag=False)

        self.apm_data = {}
        for file_name in os.listdir(folder_path_bin):

            file_name_with_path = os.path.join(folder_path_bin, file_name)
            file_name_without_extension, extension = os.path.splitext(file_name)
            with open(file_name_with_path, 'rb') as file:
                # Load the data from the pickle file
                df = pickle.load(file)
                self.apm_data[file_name_without_extension] = df

    def get_apm_data(self, cfg, api12_metadata):
        api12 = api12_metadata['api12'][0]
