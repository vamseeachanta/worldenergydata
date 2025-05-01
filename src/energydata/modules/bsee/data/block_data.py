import os
from copy import deepcopy

import pandas as pd

from energydata.modules.bsee.data.scrapy_block_data import ScrapyRunnerBlock

from assetutilities.common.utilities import is_dir_valid_func

class BlockData:

    def __init__(self):
        pass

    def router(self, cfg):
        cfg, block_data_groups = self.get_data(cfg)
        
        return cfg, block_data_groups

    def get_data(self, cfg):

        cfg = self.get_block_data_from_website(cfg)

        block_data_groups = []
        for group in cfg[cfg['basename']]['data']['groups']:
            block_data_group = group.copy()
            block_array = group['bottom_block']
            block_array_well_data = []
            for block in block_array:
                block_df = self.get_block_df(group)

            block_data_group.update({'block_df': block_df})

            block_array_well_data.append(block_data_group)

        block_data_groups.append(block_array_well_data)

        return cfg, block_data_groups
    
    def get_block_df(self, group):

        block_data = pd.read_csv(group['file_name'])
        return block_data

    def get_block_data_from_website(self, cfg):

        groups = cfg[cfg['basename']]['data']['groups']
        scrapy_runner_block = ScrapyRunnerBlock()

        block_group_data = []
        for group_idx in range(len(groups)):
            group = groups[group_idx]
            block_data_from_website = scrapy_runner_block.run_spider(cfg, group)
            block_metadata = self.generate_output_item(cfg, group)

            block_group_data.append(block_metadata)
            block_df = pd.read_csv(block_metadata['file_name'])
            api12_list = block_df['API Well Number'].unique().tolist()
            block_metadata['api12'] = api12_list

            cfg[cfg['basename']]['data']['groups'][group_idx] = block_metadata

        return cfg

    def generate_output_item(self, cfg, input_item):

        if 'bottom_block' in input_item and input_item['bottom_block'] is not None:
            bottom_block_num = str(input_item['bottom_block']['number'])
            area = str(input_item['bottom_block']['area'])
            label = area + '_' + bottom_block_num
        elif 'api12' in input_item:
            label = input_item['api12'][0]
        else:
            label = input_item['label']
        output_path = os.path.join(cfg['Analysis']['result_folder'], 'Data')
        if output_path is None:
            result_folder = cfg['Analysis']['result_folder']
            output_path = os.path.join(result_folder, 'Data')

        analysis_root_folder = cfg['Analysis']['analysis_root_folder']
        is_dir_valid, output_path = is_dir_valid_func(output_path, analysis_root_folder)

        output_file = os.path.join(output_path, str(label) + '.csv')

        input_item_csv_cfg = deepcopy(input_item)
        input_item_csv_cfg.update({'label': label, 'file_name': output_file})
        
        return input_item_csv_cfg