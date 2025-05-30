import logging
import pandas as pd
from worldenergydata.modules.bsee.data._by_block.data_from_url import DataFromURL
from worldenergydata.modules.bsee.data._by_block.data_from_bin import DataFromBin


block_data_from_url = DataFromURL()
block_data_from_bin = DataFromBin()

class Block:
       
    def __init__(self):
            pass
    
    def router(self, cfg):

        if cfg['data']['groups'][0]['bottom_block'] is not None:
            cfg = self.add_api12_array_to_cfg(cfg)

        return cfg
    
    def add_api12_array_to_cfg(self, cfg):

        if 'from_bin' in cfg['data'] and cfg['data']['from_bin']:
            cfg, block_data_groups = block_data_from_bin.router(cfg)
        else:
            cfg, block_data_groups = block_data_from_url.router(cfg)

        return cfg
    

    