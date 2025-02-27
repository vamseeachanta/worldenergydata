import os
from copy import deepcopy

import pandas as pd

from energydata.modules.bsee.data.scrapy_block_data import ScrapyRunnerBlock

from assetutilities.common.utilities import is_dir_valid_func


class BlockDataWebsite:
    
    def __init__(self):
        pass
    
    def get_data(self, cfg):

        cfg = self.get_all_data(cfg)
        well_data_groups = []
        for group in cfg[cfg['basename']]['well_data']['groups']:
            well_data_group = group.copy()
            block_array = group['bottom_block']
            block_array_well_data = []
            for block in block_array:
                block_df = self.get_block_df(group)

            well_data_group.update({'block_df': block_df})

            block_array_well_data.append(well_data_group)

        well_data_groups.append(block_array_well_data)

        return cfg, well_data_groups
    
    def get_block_df(self, group):

        block_data = pd.read_csv(group['file_name'])
        return block_data

    def get_all_data(self, cfg):

        output_data = []

        if "block_data" in cfg and cfg['block_data']['flag']:
            output_data = self.get_block_data_from_website(cfg, output_data)

        well_data = {'type': 'csv', 'groups': output_data}
        cfg[cfg['basename']].update({'well_data': well_data})

        return cfg

    def get_block_data_from_website(self, cfg, output_data):
        input_items = cfg['data']['groups']
        scrapy_runner_block = ScrapyRunnerBlock()

        for input_item in input_items:
            block_data_from_website = scrapy_runner_block.run_spider(cfg, input_item)
            output_data = self.generate_output_item(cfg, output_data, input_item)
        return output_data
    
    def generate_output_item(self, cfg, output_data, input_item):

        label = input_item['bottom_block'][0]
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