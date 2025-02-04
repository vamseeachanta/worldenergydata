from energydata.modules.bsee.data.scrapy_for_API import BSEEDataSpider
from energydata.modules.bsee.data.scrapy_for_API import ScrapyRunnerAPI

from energydata.modules.bsee.analysis.scrapy_for_block import BSEESpider
from energydata.modules.bsee.analysis.scrapy_for_block import ScrapyRunner

bsee_wellAPI = BSEEDataSpider()
bsee_block = BSEESpider()

class WellData:
    
    def __init__(self):
        pass
    
    def get_well_data(self, cfg):
        if "well_data" in cfg and cfg['well_data']['flag']:
            input_items = cfg['input']
            scrapy_runner = ScrapyRunnerAPI()

            for input_item in input_items:
                scrapy_runner.run_spider(cfg, input_item)
            scrapy_runner.start()
        elif "block_data" in cfg and cfg['block_data']['flag']:
            input_items = cfg['input']
            scrapy_runner = ScrapyRunner()

            for input_item in input_items:
                scrapy_runner.run_spider(cfg, input_item)
            scrapy_runner.start()

        


