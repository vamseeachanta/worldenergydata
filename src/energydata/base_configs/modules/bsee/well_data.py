import os
import pandas as pd
from energydata.custom.scrapy_for_API import BSEEDataSpider
from energydata.custom.scrapy_for_block import BSEESpider

bsee_wellAPI = BSEEDataSpider()
bsee_block = BSEESpider()

class WellData:
    
    def __init__(self):
        pass
    
    def get_well_data(self, cfg):
        if "well_data" in cfg and cfg['well_data']['flag']:
            for input_item in cfg['input']:
                continue 
            well_data = bsee_wellAPI.router(cfg, input_item)
        elif "block_data" in cfg and cfg['block_data']['flag']:
            for input_item in cfg['input']:
                continue
            block_data = bsee_block.router(cfg, input_item)

        # for input_item in cfg['input']:
        #     pass
            


