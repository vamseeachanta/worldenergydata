import os
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
        output_data = [] 
        if "well_data" in cfg and cfg['well_data']['flag']:
            input_items = cfg['input']
            scrapy_runner = ScrapyRunnerAPI()

            for input_item in input_items:
                scrapy_runner.run_spider(cfg, input_item)

                label = input_item['label']
                output_path = input_item['output_dir']
                file_path = os.path.join(output_path, f"{label}.csv")
                input_item_csv_cfg = input_item.update({'label': label, 'file_name': file_path})
                output_data.append(input_item_csv_cfg)

            scrapy_runner.start()
        elif "block_data" in cfg and cfg['block_data']['flag']:
            input_items = cfg['input']
            scrapy_runner = ScrapyRunner()

            for input_item in input_items:
                scrapy_runner.run_spider(cfg, input_item)

                label = input_item['label']
                output_path = input_item['output_dir']
                file_path = os.path.join(output_path, f"{label}.csv")
                input_item_csv_cfg = input_item.update({'label': label, 'file_name': file_path})
                output_data.append(input_item_csv_cfg)
                
            scrapy_runner.start()

        well_data = {'type': 'csv', 'data': output_data}
        cfg[cfg['basename']].update({'well_data': well_data})
        
        return cfg