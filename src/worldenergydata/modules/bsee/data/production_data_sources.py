import os
from copy import deepcopy

import pandas as pd

from worldenergydata.modules.bsee.data.scrapy_production_data import ScrapyRunnerProduction
from worldenergydata.modules.bsee.data.production_data_from_zip import GetProdDataFromZip

from assetutilities.common.utilities import is_dir_valid_func

production_from_zip = GetProdDataFromZip()

class ProductionDataFromSources:
    
    def __init__(self):
        pass
    def router(self, cfg):

       pass

    def get_data(self, cfg):

        # cfg = self.get_groups_data(cfg)
        production_data_groups = []
        for group_idx in range(0, len(cfg['data']['groups'])):
            production_data_group = cfg['data']['groups'][group_idx].copy()
            api12_array = production_data_group['api12']

            df_api12_array = production_from_zip.get_data_by_api12_array(cfg, api12_array)
            production_data_groups.append(df_api12_array)

        return cfg, production_data_groups

    
    def get_groups_data(self, cfg):

        production_data_flag = cfg['data'].get('production_data', False)
        
        output_data = []
        if production_data_flag: 
            input_items = cfg['data']['groups']
            for input in input_items:
                api12_array = input.get('api12', []) 
                for api12 in api12_array:
                    input_item = {'api12': [api12], 'label': str(api12)}
                    output_data = self.generate_output_item(cfg, output_data, input_item)

        production_data = {'type': 'csv', 'groups': output_data }
        cfg[cfg['basename']].update({'production_data': production_data})

        return cfg

    def get_production_from_website(self, cfg):
        input_items = cfg['data']['groups']
        scrapy_runner_production = ScrapyRunnerProduction()

        for input_item in input_items:
            production_data = scrapy_runner_production.run_spider(cfg, input_item)
            #output_data = self.generate_output_item(cfg, output_data, input_item)
        return production_data

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