import os
import pandas as pd
from energydata.custom.scrapy_API_data import BSEEDataSpider

bsee_wellAPI = BSEEDataSpider()

class WellData:
    
    def __init__(self):
        pass
    
    def get_well_data(self, cfg):
        well_data = bsee_wellAPI.router(cfg)

        for input_item in cfg['input']:
            label = input_item['label']
            output_path = input_item['output_dir']
            file_path = os.path.join(output_path, f"{label}.csv")
            df = pd.read_csv(file_path)


