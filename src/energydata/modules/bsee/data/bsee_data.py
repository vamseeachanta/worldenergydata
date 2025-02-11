# Standard library imports
from energydata.common.bsee.fetch_data_templates import FetchDataTemplates

#from energydata.engine import engine as aus_engine

# Third party imports
import pandas as pd
import datetime

import os

f_d_templates = FetchDataTemplates()

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
            production_data = self.get_production_data_for_api12(api12, cfg)
            # Add these output csv files path to cfg[cfg'basename']['production']['api12']
        return production_data
    
    def get_production_data_for_api12(self, api12, cfg):

        from energydata.engine import engine as energy_engine
        production_yml = f_d_templates.get_data_from_existing_files(cfg['Analysis'].copy())

        settings = { 'api12': api12,
                    'files_folder': 'tests/modules/bsee/data/well_production_yearly/csv',
                    'output_dir': 'tests/modules/bsee/data/results/Data/well_production_data/production_data_for_wellAPI.csv'
                    }
        production_yml['settings'].update(settings)
        production_data = energy_engine(inputfile=None, cfg=production_yml, config_flag=False)

        return production_data
        

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

