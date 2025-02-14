# Standard library imports
import os
import logging

# Third party imports
import pandas as pd

from assetutilities.common.utilities import is_dir_valid_func
from assetutilities.common.yml_utilities import WorkingWithYAML  # noqa

wwy = WorkingWithYAML()

class DataFromFiles:
    
    def __init__(self):
        pass

    def router(self, cfg):

        if cfg['data_from_files']['production']:
            self.get_production_data_by_api12(cfg)

        return cfg


    def get_production_data_by_api12(self, cfg):

        folder_path = cfg['settings']['files_folder']

        library_name = 'energydata'
        library_file_cfg = {
            'filepath': folder_path,
            'library_name': library_name
        }

        folder_path = wwy.get_library_filepath(library_file_cfg, src_relative_location_flag=False)


        api12 = cfg['settings']['api12']
        logging.info(f"Getting production data for API12: {api12} ... START")
        output_file = os.path.join(cfg['Analysis']['result_folder'], 'Data', 'production_data_' + str(api12) + '.csv')

        if not hasattr(self, 'all_matching_rows'):
            self.all_matching_rows = []

        for file_name in os.listdir(folder_path):
            if file_name.endswith(".csv"):
                file_path = os.path.join(folder_path, file_name)
                try:
                    df = pd.read_csv(file_path)
                    
                    if 'API_WELL_NUMBER' not in df.columns:
                        print(f"Skipping {file_name}: 'API_WELL_NUMBER' column not found.")
                        continue
                    
                    matching_rows = df[df['API_WELL_NUMBER'] == api12]

                    if not matching_rows.empty:
                        # Move 'API_WELL_NUMBER' column to the first position
                        columns = ['API_WELL_NUMBER'] + [col for col in matching_rows.columns if col != 'API_WELL_NUMBER']
                        matching_rows = matching_rows[columns]

                        self.all_matching_rows.append(matching_rows)

                except FileNotFoundError:
                    print(f"File not found: {file_path}")
                except pd.errors.EmptyDataError:
                    print(f"Empty or corrupt CSV file: {file_path}")
                except Exception as e:
                    print(f"An error occurred while processing {file_name}: {e}")

        # Write all matching rows to the output file 
        if hasattr(self, 'all_matching_rows') and self.all_matching_rows:
            final_df = pd.concat(self.all_matching_rows, ignore_index=True)
            final_df.to_csv(output_file, index=False)
            print(f"All matched rows written to {output_file}.")
        else:
            print(f"No matching rows found for {api12}.")

        logging.info(f"Getting production data for API12: {api12} ... COMPLETE")

        return output_file

        

       