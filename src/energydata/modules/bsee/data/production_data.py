import os
from copy import deepcopy

import pandas as pd

from energydata.modules.bsee.data.scrapy_production_data import ScrapyRunnerProduction
from energydata.modules.bsee.data.production_data_from_zip import GetWellProdDataFromZip

from assetutilities.common.utilities import is_dir_valid_func

production_from_zip = GetWellProdDataFromZip()

class ProductionDataWebsite:
    
    def __init__(self):
        pass

    def get_data(self, cfg):

        cfg = self.get_all_data(cfg)
        production_data_groups = []
        for group in cfg[cfg['basename']]['well_data']['groups']:
            production_data_group = group.copy()
            api12_array = group['api12']
            api12_array_production_data = []
            for api12 in api12_array:
                api12_df =  production_from_zip.get_production_data_by_wellapi12(cfg)

            production_data_group.update({'api12_df': api12_df})

            api12_array_production_data.append(production_data_group)

        production_data_groups.append(api12_array_production_data)

        return cfg, production_data_groups

    
    def get_all_data(self, cfg):

        output_data = []
        if "production" in cfg and cfg['production']['flag']:
            output_data = self.get_production_from_website(cfg, output_data)

        elif "block_data" in cfg and cfg['block_data']['flag']:
            output_data = self.get_block_data_from_website(cfg, output_data)

        elif "well_production" in cfg and cfg['well_production']['flag']:
            input_items = cfg['data']['groups']
            for input_item in input_items:
                output_data = self.generate_output_item(cfg, output_data, input_item)

        well_data = {'type': 'csv', 'groups': output_data}
        cfg[cfg['basename']].update({'well_data': well_data})

        return cfg

    def get_production_from_website(self, cfg, output_data):
        input_items = cfg['data']['groups']
        scrapy_runner_production = ScrapyRunnerProduction()

        for input_item in input_items:
            production_from_website = scrapy_runner_production.run_spider(cfg, input_item)
            output_data = self.generate_output_item(cfg, output_data, input_item)
        return output_data

    def generate_output_item(self, cfg, output_data, input_item):

        label = input_item['api12'][0]
        output_path = os.path.join(cfg['Analysis']['result_folder'], 'Data')
        if output_path is None:
            result_folder = cfg['Analysis']['result_folder']
            output_path = os.path.join(result_folder, 'Data')

        analysis_root_folder = cfg['Analysis']['analysis_root_folder']
        is_dir_valid, output_path = is_dir_valid_func(output_path, analysis_root_folder)

        output_file = os.path.join(output_path, str(label) + '.csv')

        input_item_csv_cfg = deepcopy(input_item)
        input_item_csv_cfg.update({'label': label, 'file_name': output_file})
        output_data.append(input_item_csv_cfg)
        
        return output_data