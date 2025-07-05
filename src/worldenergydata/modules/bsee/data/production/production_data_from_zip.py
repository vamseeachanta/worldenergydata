# Standard library imports
import pickle
import os
from loguru import logger

# Third party imports
import pandas as pd
 
from assetutilities.common.utilities import is_dir_valid_func
from assetutilities.common.yml_utilities import WorkingWithYAML  # noqa
from assetutilities.modules.zip_utilities.zip_files_to_dataframe import ZipFilestoDf

wwy = WorkingWithYAML()
zip_files_to_df = ZipFilestoDf()

class GetProdDataFromZip:
    
    def __init__(self):
        pass

    def router(self, cfg):
        pass

    def download_zip_data(self, cfg):
        pass

    def save_zip_data_to_binary(self, cfg):
        folder_path_zip = cfg['parameters']['filepath']['production']['zip']
        library_name = 'worldenergydata'
        library_file_cfg = {
            'filepath': folder_path_zip,
            'library_name': library_name
        }
        folder_path_zip = wwy.get_library_filepath(library_file_cfg, src_relative_location_flag=False)
        if not os.path.exists(folder_path_zip):
            raise FileNotFoundError(f"The folder '{folder_path_zip}' does not exist.")

        folder_path_bin = cfg['parameters']['filepath']['production']['bin']
        library_file_cfg = {
            'filepath': folder_path_bin,
            'library_name': library_name
        }
        folder_path_bin = wwy.get_library_filepath(library_file_cfg, src_relative_location_flag=False)
        if not os.path.exists(folder_path_zip):
            raise FileNotFoundError(f"The folder '{folder_path_zip}' does not exist.")

        for file_name in os.listdir(folder_path_zip):

            file_name_with_path = os.path.join(folder_path_zip, file_name)
            column_names = ['LEASE_NUMBER', 'COMPLETION_NAME', 'PRODUCTION_DATE', 'DAYS_ON_PROD', 'PRODUCT_CODE', 'MON_O_PROD_VOL', 'MON_G_PROD_VOL', 'MON_WTR_PROD_VOL', 'API_WELL_NUMBER', 'WELL_STAT_CD', 'AREA_CODE_BLOCK_NUM', 'OPERATOR_NUM', 'SORT_NAME', 'BOEM_FIELD', 'INJECTION_VOLUME', 'PROD_INTERVAL_CD', 'FIRST_PROD_DATE', 'UNIT_AGT_NUMBER', 'UNIT_ALOC_SUFFIX']
            cfg_zip_utilities = {'zip_utilities': {}}
            cfg_zip_utilities['zip_utilities'] = {
                'technique': 'zip_files_to_df',
                'input_directory': folder_path_zip,
                'column_names': column_names,
                'file_name': file_name_with_path
            }

            df_dict = zip_files_to_df.zip_file_to_dataframe(cfg_zip_utilities)
            _, df = list(df_dict.items())[0]

            file_label = file_name.split('.')[0]
            file_name = file_label + '.bin'
            file_name_with_path = os.path.join(folder_path_bin, file_name)
            with open(file_name_with_path, "wb") as f:
                pickle.dump(df, f)
    
    def get_production_data_by_wellapi12(self, cfg, api12):
        try:
            folder_path = self._resolve_folder_path(cfg)
            api12_dataframes = self._process_zip_files(folder_path, api12)
            
            output_file = os.path.join(cfg['Analysis']['result_folder'], 'Data', f'prod_raw_api12_{api12}.csv')
            for api12, df in api12_dataframes.items():
                try:
                    df.to_csv(output_file, index=False)
                    logger.info(f"API {api12} Matched rows written to {output_file}.")
                except Exception as e:
                    logger.error(f"Error writing to output file {output_file}: {e}")

            dataframe = pd.DataFrame()
            if len(api12_dataframes) == 1:
                dataframe = next(iter(api12_dataframes.values()))
            
            logger.info(f"Getting production data for API12: {api12} ... COMPLETE")
            return dataframe

        except KeyError as ke:
            logger.error(f"Missing key in configuration: {ke}")
            raise
        except FileNotFoundError as fnfe:
            logger.error(f"File not found: {fnfe}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise
    
    def _resolve_folder_path(self, cfg):
        folder_path = cfg['parameters']['filepath']['production']['zip']
        library_name = 'worldenergydata'
        library_file_cfg = {
            'filepath': folder_path,
            'library_name': library_name
        }
        folder_path = wwy.get_library_filepath(library_file_cfg, src_relative_location_flag=False)
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"The folder '{folder_path}' does not exist.")
        return folder_path

    def _process_zip_files(self, folder_path, api12):
        api12_dataframes = {}
        column_names = ['LEASE_NUMBER', 'COMPLETION_NAME', 'PRODUCTION_DATE', 'DAYS_ON_PROD', 'PRODUCT_CODE',
                        'MON_O_PROD_VOL', 'MON_G_PROD_VOL', 'MON_WTR_PROD_VOL', 'API_WELL_NUMBER', 'WELL_STAT_CD',
                        'AREA_CODE_BLOCK_NUM', 'OPERATOR_NUM', 'SORT_NAME', 'BOEM_FIELD', 'INJECTION_VOLUME',
                        'PROD_INTERVAL_CD', 'FIRST_PROD_DATE', 'UNIT_AGT_NUMBER', 'UNIT_ALOC_SUFFIX']
        
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            df = self._load_dataframe_from_zip(file_path, column_names)

            if 'API_WELL_NUMBER' not in df.columns:
                logger.warning(f"Skipping {file_name}: 'API_WELL_NUMBER' column not found.")
                continue

            matching_rows = df[df['API_WELL_NUMBER'] == api12]
            
            if not matching_rows.empty:
                columns = ['API_WELL_NUMBER'] + [col for col in matching_rows.columns if col != 'API_WELL_NUMBER']
                matching_rows = matching_rows[columns]

                if api12 not in api12_dataframes:
                    api12_dataframes[api12] = matching_rows
                else:
                    api12_dataframes[api12] = pd.concat([api12_dataframes[api12], matching_rows], ignore_index=True)

                logger.debug(f"Production data found for API {api12} in file {file_name}.")
            else:
                logger.debug(f"Production data NOT found for API {api12} in file {file_name}.")

        return api12_dataframes

    def _load_dataframe_from_zip(self, file_path, column_names):
        cfg_zip_utilities = {
            'zip_utilities': {
                'technique': 'zip_files_to_df',
                'file_name': file_path,
                'column_names': column_names
            }
        }
        df_dict = zip_files_to_df.zip_file_to_dataframe(cfg_zip_utilities)
        _, df = list(df_dict.items())[0]
        return df

    def get_data_by_api12_array(self, cfg, api12_array):

        folder_path_bin = cfg['parameters']['filepath']['production']['bin']
        column_names = ['LEASE_NUMBER', 'COMPLETION_NAME', 'PRODUCTION_DATE', 'DAYS_ON_PROD', 'PRODUCT_CODE', 'MON_O_PROD_VOL', 'MON_G_PROD_VOL', 'MON_WTR_PROD_VOL', 'API_WELL_NUMBER', 'WELL_STAT_CD', 'AREA_CODE_BLOCK_NUM', 'OPERATOR_NUM', 'SORT_NAME', 'BOEM_FIELD', 'INJECTION_VOLUME', 'PROD_INTERVAL_CD', 'FIRST_PROD_DATE', 'UNIT_AGT_NUMBER', 'UNIT_ALOC_SUFFIX']
        library_name = 'worldenergydata'
        library_file_cfg = {
            'filepath': folder_path_bin,
            'library_name': library_name
        }
        folder_path_bin = wwy.get_library_filepath(library_file_cfg , src_relative_location_flag=False)

        df_api12_array = pd.DataFrame()
        for file_name in os.listdir(folder_path_bin):

            file_name_with_path = os.path.join(folder_path_bin, file_name)
            with open(file_name_with_path, 'rb') as file:
                df = pickle.load(file)

                # if column_names and not all(col.replace(' ', '').isalpha() for col in df.columns):
                if column_names:
                    df.columns = column_names

            df_filtered = df[df['API_WELL_NUMBER'].isin(api12_array)]
            df_api12_array = pd.concat([df_api12_array, df_filtered], ignore_index=True)

        # Filter the DataFrame based on the API12 value
        api12_dataframes = {}
        for api12 in api12_array:
            df_api12 = df_api12_array[df_api12_array['API_WELL_NUMBER'] == api12].copy()
            api12_dataframes[api12] = df_api12

        return api12_dataframes