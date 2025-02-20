import os
from copy import deepcopy

from energydata.modules.bsee.analysis.scrapy_for_block import ScrapyRunnerBlock
from energydata.modules.bsee.data.scrapy_production_data import ScrapyRunnerProduction

from assetutilities.common.utilities import is_dir_valid_func


class ProductionData:
    
    def __init__(self):
        pass

    def get_production_data(self, cfg):
        cfg = self.get_production_data_csv(cfg)

        return cfg

    def get_production_data_csv(self, cfg):
        output_data = []

        if "production" in cfg and cfg['production']['flag']:
            input_items = cfg['settings']
            scrapy_runner_production = ScrapyRunnerProduction()

            for input_item in input_items:
                scrapy_runner_production.run_spider(cfg, input_item)
                output_data = self.generate_output_item(cfg, output_data, input_item)

        elif "well_production" in cfg and cfg['well_production']['flag']:
            input_items = cfg['settings']
            scrapy_runner_block = ScrapyRunnerBlock()

            for input_item in input_items:
                # well_data_scrapper_cfg = deepcopy(input_item.copy())
                # well_data_scrapper_cfg.update({'output_dir': output_path})
                scrapy_runner_block.run_spider(cfg, input_item)
                output_data = self.generate_output_item(cfg, output_data, input_item)
        

        well_data = {'type': 'csv', 'groups': output_data}
        cfg[cfg['basename']].update({'well_data': well_data})

        return cfg

    def generate_output_item(self, cfg, output_data, input_item):

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
        output_data.append(input_item_csv_cfg)
        
        return output_data