import os
from copy import deepcopy
from energydata.modules.bsee.analysis.scrapy_for_block import ScrapyRunnerBlock
from energydata.modules.bsee.data.scrapy_for_API import  ScrapyRunnerAPI
from energydata.modules.bsee.data.scrapy_production_data import ScrapyRunnerProduction


class WellData:
    
    def __init__(self):
        pass

    def get_well_data(self, cfg):
        cfg = self.get_well_data_csv(cfg)
        
        return cfg
        
    def get_well_data_csv(self, cfg):
        output_data = [] 
        if "well_data" in cfg and cfg['well_data']['flag']:
            input_items = cfg['settings']
            scrapy_runner_api = ScrapyRunnerAPI()

            for input_item in input_items:
                scrapy_runner_api.run_spider(cfg, input_item)

                #output_data = self.generate_output_item(cfg, output_data, input_item)

            scrapy_runner_api.start()
        
        elif "production" in cfg and cfg['production']['flag']:
            input_items = cfg['settings']
            scrapy_runner_production = ScrapyRunnerProduction()

            for input_item in input_items:
                scrapy_runner_production.run_spider(cfg, input_item)
                output_data = self.generate_output_item(output_data, input_item)
                
            scrapy_runner_production.start()

        elif "block_data" in cfg and cfg['block_data']['flag'] or "well_production" in cfg and cfg['well_production']['flag']:
            input_items = cfg['settings']
            scrapy_runner_block = ScrapyRunnerBlock()

            for input_item in input_items:
                # well_data_scrapper_cfg = deepcopy(input_item.copy())
                # well_data_scrapper_cfg.update({'output_dir': output_path})
                scrapy_runner_block.run_spider(cfg, input_item)
                output_data = self.generate_output_item(output_data, input_item)
                
            scrapy_runner_block.start()

        well_data = {'type': 'csv', 'groups': output_data}
        cfg[cfg['basename']].update({'well_data': well_data})
        
        return cfg

    def generate_output_item(self, output_data, input_item):
        label = input_item['label']
        output_path = input_item['output_dir']
        file_path = os.path.join(output_path, f"{label}.csv")
        input_item_csv_cfg = deepcopy(input_item)
        input_item_csv_cfg.update({'label': label, 'file_name': file_path})
        output_data.append(input_item_csv_cfg)
        
        return output_data