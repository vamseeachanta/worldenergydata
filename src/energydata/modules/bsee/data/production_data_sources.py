import os
from copy import deepcopy

import pandas as pd

from energydata.modules.bsee.data.scrapy_production_data import ScrapyRunnerProduction
from energydata.modules.bsee.data.production_data_from_zip import GetProdDataFromZip

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
            api12_array_production_data = []
            for api12 in api12_array:

                api12_df = production_from_zip.get_production_data_by_wellapi12(cfg, api12)
                if not api12_df:
                    api12_df = pd.DataFrame()

                api12_array_production_data.append(api12_df)

            production_data_groups.append(api12_array_production_data)

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