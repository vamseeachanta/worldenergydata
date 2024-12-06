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
            well_data = bsee_wellAPI.router(cfg)
        elif "block_data" in cfg and cfg['block_data']['flag']:
            block_data = bsee_block.router(cfg)

        for input_item in cfg['input']:
            label = input_item['label']
            output_path = input_item['output_dir']
            file_path = os.path.join(output_path, f"{label}.csv")
            df = pd.read_csv(file_path)


