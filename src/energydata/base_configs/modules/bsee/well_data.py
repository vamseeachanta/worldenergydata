import os
import pandas as pd
from energydata.custom.scrapy_for_API import BSEEDataSpider
from energydata.custom.scrapy_for_API import run_spiders
from energydata.custom.scrapy_for_block import run_spider
from energydata.custom.scrapy_for_block import BSEESpider

bsee_wellAPI = BSEEDataSpider()
bsee_block = BSEESpider()

class WellData:
    
    def __init__(self):
        pass
    
    def get_well_data(self, cfg):
        if "well_data" in cfg and cfg['well_data']['flag']:
             input_items = cfg['input']
             run_spiders(cfg, input_items)
        elif "block_data" in cfg and cfg['block_data']['flag']:
             input_items = cfg['input']
             run_spider(cfg, input_items)

        


