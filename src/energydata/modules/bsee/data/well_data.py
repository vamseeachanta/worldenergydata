import os
from copy import deepcopy
from energydata.modules.bsee.analysis.scrapy_for_block import BSEESpider, ScrapyRunner
from energydata.modules.bsee.data.scrapy_for_API import BSEEDataSpider, ScrapyRunnerAPI
bsee_block = BSEESpider()

class WellData:
    
    def __init__(self):
        pass

    def get_well_data(self, cfg):
        cfg = self.get_well_data_csv(cfg)
        
        return cfg
        
    def get_well_data_csv(self, cfg):
        output_path = cfg['settings']['output_dir']
        output_data = [] 
        if "well_data" in cfg and cfg['well_data']['flag']:
            input_items = cfg['input']
            scrapy_runner = ScrapyRunnerAPI()

            for input_item in input_items:
                scrapy_runner.run_spider(cfg, input_item)

                output_data = self.generate_output_item(cfg, output_data, input_item)

            scrapy_runner.start()

        elif "block_data" in cfg and cfg['block_data']['flag'] or "well_production" in cfg and cfg['well_production']['flag']:
            input_items = cfg['input']
            scrapy_runner = ScrapyRunner()

            for input_item in input_items:
                well_data_scrapper_cfg = deepcopy(input_item.copy())
                well_data_scrapper_cfg.update({'output_dir': output_path})
                scrapy_runner.run_spider(cfg, well_data_scrapper_cfg)
                output_data = self.generate_output_item(cfg, output_data, well_data_scrapper_cfg)
                
            scrapy_runner.start()

        well_data = {'type': 'csv', 'groups': output_data}
        cfg[cfg['basename']].update({'well_data': well_data})
        
        return cfg

    def generate_output_item(self, cfg, output_data, well_data_scrapper_cfg):
        label = well_data_scrapper_cfg['label']
        output_path = cfg['settings']['output_dir']
        file_path = os.path.join(output_path, f"{label}.csv")
        input_item_csv_cfg = deepcopy(well_data_scrapper_cfg)
        input_item_csv_cfg.update({'label': label, 'file_name': file_path})
        output_data.append(input_item_csv_cfg)
        
        return output_data