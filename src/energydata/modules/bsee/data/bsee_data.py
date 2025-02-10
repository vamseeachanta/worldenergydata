# Standard library imports
from energydata.common.bsee.fetch_data_templates import FetchDataTemplates

# Third party imports
import pandas as pd
import datetime

import os


class BSEEData:
    
    def __init__(self):
        pass

    def get_api12_data(self, cfg):
        if cfg['data']['by'] == 'block':
            api12_array = self.get_api12_data_by_block(cfg)

        cfg[cfg['basename']].update({'api12': api12_array})

        return cfg

    def get_production_data(self, cfg):
        # if cfg['analysis']['production']['block']:
        #     cfg = self.get_block_bottom_leases(cfg)
        #     production_data = self.get_production_data_by_block_array(cfg)
        #     cfg[cfg['basename']].update({'production': {'block':production_data}})

        if cfg['analysis']['production']['api12']:
            production_data = self.get_api12_array_for_production_data(cfg)
            cfg[cfg['basename']].update({'production': {'api12':production_data}})

        return cfg
    
    def get_api12_data_by_block(self, cfg):
    
        api12_array = []
        if cfg[cfg['basename']]['well_data']['type'] == 'csv':
            csv_groups = cfg[cfg['basename']]['well_data']['groups']
            for csv_group in csv_groups:
                df = pd.read_csv(csv_group['file_name'])
                api12_csv_group = df['API Well Number'].unique().tolist()
                api12_array = api12_array + api12_csv_group

        return api12_array

    def get_production_data_by_bottom_lease(self, bottom_lease):
   
        # wire up scrapy_production_data.py?
        # Output files are: LNG15110.csv & LNG25251.csv
        # Add these output csv files path to cfg[cfg'basename']['production']['block']
        
        # Detailed workflow
        # 1. Load production_data_by_lease.yml template
        # 2. Update with input settings (e.g. bottom_lease, output folder)
        # 3. Run the application as individual process to save the data
        # 4. Add output csv files to cfg[cfg'basename']['production']['block']
        
        pass
    
    def get_api12_array_for_production_data(self, cfg):
        api12_array = cfg[cfg['basename']]['api12']
        for api12 in api12_array:
            production_data = self.get_production_data_for_api12(api12)
            # Add these output csv files path to cfg[cfg'basename']['production']['api12']
        return production_data
    
    def get_production_data_for_api12(self, api12):
        folder_path = "tests/modules/bsee/data/well_production_yearly/csv"  
        output_file = "tests/modules/bsee/data/results/Data/well_production_data/production_data_for_wellAPI.csv" 
        file_exists = os.path.exists(output_file)

        for file_name in os.listdir(folder_path):
            if file_name.endswith(".csv"):
                file_path = os.path.join(folder_path, file_name)
                try:
                    
                    df = pd.read_csv(file_path)
                    
                   
                    if 'API_WELL_NUMBER' not in df.columns:
                        print(f"Skipping {file_name}: 'api12' column not found.")
                        continue

                    
                    matching_rows = df[df['API_WELL_NUMBER'] == api12]
                    
                    if not matching_rows.empty:
                        # Move 'api12' column to the first position
                        columns = ['API_WELL_NUMBER'] + [col for col in matching_rows.columns if col != 'API_WELL_NUMBER']
                        matching_rows = matching_rows[columns]
                        
                        # Append or write to the output file
                        matching_rows.to_csv(output_file, mode='a' if file_exists else 'w', header=not file_exists, index=False)
                        file_exists = True 

                except FileNotFoundError:
                    print(f"File not found: {file_path}")
                except pd.errors.EmptyDataError:
                    print(f"Empty or corrupt CSV file: {file_path}")
                except Exception as e:
                    print(f"An error occurred while processing {file_name}: {e}")

        return output_file

    def get_production_data_by_block_array(self, cfg):
        
        bottom_lease_array = cfg[cfg['basename']]['production']['bottom_lease']
        for bottom_lease in bottom_lease_array:
            production_data = self.get_production_data_by_bottom_lease(bottom_lease)
            self.prepare_production_data(production_data)
            # Add these output csv files path to cfg[cfg'basename']['production']['block']  


    def get_block_bottom_leases(self, cfg):
        
        bottom_lease_array = []
        if cfg[cfg['basename']]['well_data']['type'] == 'csv':
            csv_groups = cfg[cfg['basename']]['well_data']['groups']
            for csv_group in csv_groups:
                df = pd.read_csv(csv_group['file_name'])
                bottom_lease_csv_group = df['Bottom Lease Number'].unique().tolist()
                bottom_lease_array = bottom_lease_array + bottom_lease_csv_group

        cfg[cfg['basename']].update({'production': {'bottom_lease': bottom_lease_array}})

        return cfg

