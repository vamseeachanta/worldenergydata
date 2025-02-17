# Standard library imports
from energydata.common.bsee.retrieve_data_templates import RetrieveDataTemplates

# Third party imports
import pandas as pd
import datetime

import os

f_d_templates = RetrieveDataTemplates()

class BSEEData:
    
    def __init__(self):
        pass

    def get_api12_data(self, cfg):

        if cfg['data']['by'] == 'block':
            api12_array = self.get_api12_data_by_block(cfg)

        cfg[cfg['basename']].update({'api12': api12_array})

        return cfg

    def get_production_data(self, cfg):

        if "block" in cfg and cfg['analysis']['production']['block']:
            bottom_lease_array = self.get_bottom_leases_by_block(cfg)

            if "prod_by_lease" in cfg and cfg['prod_by_lease']['flag']:
                production_data = self.get_production_data_for_each_lease(cfg)
                cfg[cfg['basename']].update({'production': {'block':production_data}})

        if "api12" in cfg and cfg['analysis']['production']['api12']:
            production_data = self.get_production_data_for_each_api12(cfg)
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
    
    def get_production_data_for_each_api12(self, cfg):

        api12_array = cfg[cfg['basename']]['api12']
        for api12 in api12_array:
            production_data = self.get_production_data_by_api12(api12, cfg)
            
        return production_data
    
    def get_production_data_by_api12(self, api12, cfg):

        from energydata.engine import engine as energy_engine
        production_yml = f_d_templates.get_data_from_existing_files(cfg['Analysis'].copy())

        settings = { 'api12': api12,
                    'files_folder': 'data/modules/bsee/production/csv',
                    }
        production_yml['settings'].update(settings)
        production_data = energy_engine(inputfile=None, cfg=production_yml, config_flag=False)

        return production_data

    def get_bottom_leases_by_block(self, cfg):
        
        bottom_lease_array = []
        if cfg[cfg['basename']]['well_data']['type'] == 'csv':
            csv_groups = cfg[cfg['basename']]['well_data']['groups']
            for csv_group in csv_groups:
                df = pd.read_csv(csv_group['file_name'])
                bottom_lease_csv_group = df['Bottom Lease Number'].unique().tolist()
                bottom_lease_array = bottom_lease_array + bottom_lease_csv_group

        cfg[cfg['basename']].update({'production': {'bottom_leases': bottom_lease_array}})

        return bottom_lease_array
    
    def get_production_data_for_each_lease(self, cfg):
        
        bottom_lease_array = cfg[cfg['basename']]['production']['bottom_leases']
        for bottom_lease in bottom_lease_array:
            production_data = self.get_production_data_by_bottom_lease(bottom_lease, cfg)

        return production_data

    def get_production_data_by_bottom_lease(self, bottom_lease, cfg):
        
        from energydata.engine import engine as energy_engine
        production_yml = f_d_templates.get_production_data_by_lease(cfg['Analysis'].copy())

        settings = { 'lease_number': bottom_lease,
                    'label': 'LN' + str(bottom_lease),
                    'Duration': {
                        'from': '01/1999',
                        'to': '01/2024'
                    }
                    }
        master_settings = { 'output_dir': 'tests/modules/bsee/data/results/Data/well_production_data'
                    }
        production_yml['settings'][0].update(settings)
        production_yml['master_settings'].update(master_settings)
        production_data = energy_engine(inputfile=None, cfg=production_yml, config_flag=False)

        return production_data

