import os
import pickle
import zipfile
from loguru import logger

from worldenergydata.modules.bsee.data._by_block.data_from_local_files import DataFromLocalFiles

from assetutilities.common.yml_utilities import WorkingWithYAML  # noqa
from assetutilities.modules.zip_utilities.zip_files_to_dataframe import ZipFilestoDf

wwy = WorkingWithYAML()
zip_files_to_df = ZipFilestoDf()

block_data = DataFromLocalFiles()

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
        
        columns = ['MMS_COMPANY_NUM',
                    'API_WELL_NUMBER',
                    'WATER_DEPTH',
                    'WELL_NM_BP_SFIX',
                    'WELL_NM_ST_SFIX',
                    'SURF_AREA_CODE',
                    'SURF_BLOCK_NUM',
                    'SURF_LEASE_NUM',
                    'BOTM_AREA_CODE',
                    'BOTM_BLOCK_NUM',
                    'BOTM_LEASE_NUM',
                    'RIG_ID_NUM',
                    'BOREHOLE_STAT_CD',
                    'WELL_TYPE_CODE',
                    'BUS_ASC_NAME']

        #TODO 

    def save_eWellAPMRawData_to_binary(self, cfg):
        folder_path_zip = cfg['parameters']['filepath']['apm']['zip']
        library_name = 'worldenergydata'
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
            if file_name == "dsptsdelimit.ZIP":
                # Special case for dsptsdelimit.ZIP file
                column_names = self._get_column_names_for_dsptsdelimit_file(file_name_with_path)
            else:
                column_names = None
            cfg_zip_utilities = {'zip_utilities': {}}
            cfg_zip_utilities['zip_utilities'] = {
                'technique': 'zip_files_to_df',
                'folder_path_zip': folder_path_zip,
                'column_names': column_names,
                'file_name': file_name_with_path,
                'nrows': None
            }

            dfs = zip_files_to_df.zip_file_to_dataframe(cfg_zip_utilities)

            for key, df in dfs.items():
                if len(df) > 0:
                    file_label = key
                    file_name = file_label + '.bin'
                    file_name_with_path = os.path.join(folder_path_bin, file_name)
                    with open(file_name_with_path, "wb") as f:
                        pickle.dump(df, f)

    def _get_column_names_for_dsptsdelimit_file(self, file_path):
        """
        Check if the zip file contains column headers and return appropriate column names.
        If the file has headers, return None to let pandas infer them.
        If the file doesn't have headers, return target column names.
        """
        
        target_columns = [
            'API_WELL_NUMBER', 'INCL_ANG_DEG_VAL', 'INCL_ANG_MIN_VAL',
            'SURVEY_POINT_MD', 'WELL_N_S_CODE', 'DIR_DEG_VAL', 'DIR_MINS_VAL',
            'WELL_E_W_CODE', 'SURVEY_POINT_TVD', 'DELTA_X', 'DELTA_Y',
            'SURF_LONGITUDE', 'SURF_LATITUDE'
        ]
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                # Get the first file in the zip
                file_names = [f for f in zip_file.namelist() if not f.endswith('/')]
                if not file_names:
                    logger.warning(f"No files found in zip: {file_path}")
                    return None
                
                first_file = file_names[0]
                
                # Read the first few lines to check for headers
                with zip_file.open(first_file) as csv_file:
                    # Read first line as string
                    first_line = csv_file.readline().decode('utf-8', errors='ignore').strip()
                    
                    if not first_line:
                        logger.warning(f"Empty file in zip: {file_path}")
                        return None
                    
                    # Check if first line contains typical header patterns
                    # Headers usually contain alphabetic characters and underscores
                    first_line_values = first_line.split(',')
                    
                    # If most values in first line are non-numeric and contain letters, likely headers
                    header_indicators = 0
                    for value in first_line_values[:5]:  # Check first 5 columns
                        value = value.strip().strip('"\'')
                        if value and any(c.isalpha() or c == '_' for c in value):
                            header_indicators += 1
                    
                    # If more than half of the first values look like headers, assume file has headers
                    if header_indicators > len(first_line_values) :
                        logger.debug(f"Headers detected in zip file: {file_path}")
                        return None  # Let pandas infer headers
                    else:
                        logger.debug(f"No headers detected in zip file: {file_path}, using target columns")
                        return target_columns
                        
        except Exception as e:
            logger.error(f"Error checking headers in zip file {file_path}: {e}")
            # In case of error, return target columns as fallback
            return target_columns

