# Standard library imports
import pickle
import os
import logging
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

        if cfg['data']['by']== 'zip':
            api12 = cfg['data']['groups'][0]['api12'][0]
            self.get_production_data_by_wellapi12(cfg,api12)

        return cfg

    def save_zip_data_to_binary(self, cfg):
        folder_path_zip = cfg['parameters']['filepath']['production']['zip']
        library_name = 'energydata'
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

            df = zip_files_to_df.router(cfg_zip_utilities)

            file_label = file_name.split('.')[0]
            file_name = file_label + '.bin'
            file_name_with_path = os.path.join(folder_path_bin, file_name)
            with open(file_name_with_path, "wb") as f:
                pickle.dump(df, f)



    def get_production_data_by_wellapi12(self, cfg, api12):
        try:
            folder_path = cfg['parameters']['filepath']['production']['zip']

            library_name = 'energydata'
            library_file_cfg = {
                'filepath': folder_path,
                'library_name': library_name
            }

            folder_path = wwy.get_library_filepath(library_file_cfg, src_relative_location_flag=False)

            if not os.path.exists(folder_path):
                raise FileNotFoundError(f"The folder '{folder_path}' does not exist.")

            logging.info(f"Getting production data for API12: {api12} ... START")
            output_file_label = 'prod_raw_api12_' + str(api12)
            output_file = os.path.join(cfg['Analysis']['result_folder'], 'Data', output_file_label + '.csv')

            api12_dataframes = {}
            for file_name in os.listdir(folder_path):

                column_names = ['LEASE_NUMBER', 'COMPLETION_NAME', 'PRODUCTION_DATE', 'DAYS_ON_PROD', 'PRODUCT_CODE', 'MON_O_PROD_VOL', 'MON_G_PROD_VOL', 'MON_WTR_PROD_VOL', 'API_WELL_NUMBER', 'WELL_STAT_CD', 'AREA_CODE_BLOCK_NUM', 'OPERATOR_NUM', 'SORT_NAME', 'BOEM_FIELD', 'INJECTION_VOLUME', 'PROD_INTERVAL_CD', 'FIRST_PROD_DATE', 'UNIT_AGT_NUMBER', 'UNIT_ALOC_SUFFIX']
                cfg['zip_utilities'] = {
                    'technique': 'zip_files_to_df',
                    'input_directory': folder_path,
                    'column_names': column_names
                }

                df = zip_files_to_df.router(cfg)

                df_name = file_name.split('.')[0]

                if 'API_WELL_NUMBER' not in df.columns:
                    logger.warning(f"Skipping {df_name}: 'API_WELL_NUMBER' column not found.")
                    continue

                # Find matching rows for the current api12
                matching_rows = df[df['API_WELL_NUMBER'] == api12] 

                if not matching_rows.empty:
                    # Move 'API_WELL_NUMBER' column to the first position
                    columns = ['API_WELL_NUMBER'] + [col for col in matching_rows.columns if col != 'API_WELL_NUMBER']
                    matching_rows = matching_rows[columns]

                    # Append matching rows to the corresponding api12 DataFrame
                    if api12 not in api12_dataframes:
                        api12_dataframes[api12] = matching_rows
                    else:
                        api12_dataframes[api12] = pd.concat([api12_dataframes[api12], matching_rows], ignore_index=True)

                    logger.debug(f"Production data found for API {api12} in file {df_name}.")
                else:
                    logger.debug(f"Production data NOT found for API {api12} in file {df_name}.")

            # Write each api12 DataFrame to a separate output file
            for api12, df in api12_dataframes.items():
                try:
                    output_file = os.path.join(output_file)
                    df.to_csv(output_file, index=False)
                    logger.info(f"API {api12} Matched rows from certain files written to {output_file}.")
                except Exception as e:
                    logger.error(f"Error writing to output file {output_file}: {e}")

            logging.info(f"Getting production data for API12: {api12} ... COMPLETE")

            dataframe = pd.DataFrame()
            if len(api12_dataframes) == 1:
                # Extract the single dataframe from the dictionary
                dataframe = next(iter(api12_dataframes.values()))

        except KeyError as ke:
            logger.error(f"Missing key in configuration: {ke}")
            raise
        except FileNotFoundError as fnfe:
            logger.error(f"File not found: {fnfe}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise
        
        return dataframe

    def get_data_by_api12_array(self, cfg, api12_array):
        folder_path_bin = cfg['parameters']['filepath']['production']['bin']
        library_name = 'energydata'
        library_file_cfg = {
            'filepath': folder_path_bin,
            'library_name': library_name
        }
        folder_path_bin = wwy.get_library_filepath(library_file_cfg, src_relative_location_flag=False)

        df_api12_array = pd.DataFrame()
        for file_name in os.listdir(folder_path_bin):

            file_name_with_path = os.path.join(folder_path_bin, file_name)
            with open(file_name_with_path, 'rb') as file:
                # Load the data from the pickle file
                df = pickle.load(file)
            df_filtered = df[df['API_WELL_NUMBER'].isin(api12_array)]
            df_api12_array = pd.concat([df_api12_array, df_filtered], ignore_index=True)

        # Filter the DataFrame based on the API12 value
        api12_dataframes = {}
        for api12 in api12_array:
            df_api12 = df_api12_array[df_api12_array['API_WELL_NUMBER'] == api12]
            api12_dataframes[api12] = df_api12

        return api12_dataframes