# Standard library imports


# Third party imports
import pandas as pd
import datetime


@dataclass
class BSEEData:
    """Class for handling BSEE data"""
    
    def __init__(self):
        pass
    
    def get_api12_data_by_block(self, cfg):
        #TODO refactor to BSEEDATA class
        api12_array = []
        if cfg[cfg['basename']]['well_data']['type'] == 'csv':
            csv_groups = cfg[cfg['basename']]['well_data']['groups']
            for csv_group in csv_groups:
                df = pd.read_csv(csv_group['file_name'])
                api12_csv_group = df['API Well Number'].unique().tolist()
                api12_array = api12_array + api12_csv_group

        return api12_array

    def get_production_data_by_bottom_lease(self, bottom_lease):
        #TODO refactor to BSEEDATA class
        # wire up scrapy_production_data.py?
        # Output files are: LNG15110.csv & LNG25251.csv
        # Add these output csv files path to cfg[cfg'basename']['production']['block']
        
        # Detailed workflow
        # 1. Load production_data_by_lease.yml template
        # 2. Update with input settings (e.g. bottom_lease, output folder)
        # 3. Run the application as individual process to save the data
        # 4. Add output csv files to cfg[cfg'basename']['production']['block']
        
        pass
    
    def get_production_data_for_api12_array(self, api12):
        api12_array = cfg[cfg['basename']]['api12']
        for api12 in api12_array:
            production_data = self.bsee_data.get_production_data_by_api12(api12)
            self.prepare_production_data(production_data)
            # Add these output csv files path to cfg[cfg'basename']['production']['api12']

    def get_production_data_for_api12(self, cfg):
        # Load each yearly zip file
        # For each zip file, filter the API12 (or) API12array data needed.
        pass        


    def get_production_data_by_block_array(self, cfg):
        
        bottom_lease_array = cfg[cfg['basename']]['production']['bottom_lease']
        for bottom_lease in bottom_lease_array:
            production_data = self.get_production_data_by_bottom_lease(bottom_lease)
            self.prepare_production_data(production_data)
            # Add these output csv files path to cfg[cfg'basename']['production']['block']  

    def get_api12_data(self, cfg):
        if cfg['data']['by'] == 'block':
            api12_array = self.bsee_data.get_api12_data_by_block(cfg)

        cfg[cfg['basename']].update({'api12': api12_array})

        return cfg

    def get_production_data(self, cfg):
        if cfg['analysis']['production']['block']:
            cfg = self.get_block_bottom_leases(cfg)
            production_data = self.get_production_data_by_block_array(cfg)
            cfg[cfg['basename']].update({'production': {'block':production_data}})

        if cfg['analysis']['production']['api12']:
            production_data = self.get_production_data_for_api12_array(cfg)
            cfg[cfg['basename']].update({'production': {'api12':production_data}})

        return cfg

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

