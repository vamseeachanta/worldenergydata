import logging
import pandas as pd
from worldenergydata.modules.bsee.data._by_block.data_from_url import DataFromURL

block_data = DataFromURL()

class Block:
       
    def __init__(self):
            pass
    
    def router(self, cfg):

        if 'analysis' in cfg and cfg['analysis']['bottom_blocks'] or 'by' in cfg['data'] and cfg['data']['by'] == 'block':
            cfg = self.add_api12_array_by_block_to_cfg(cfg)

        return cfg
    
    def add_api12_array_by_block_to_cfg(self, cfg):
        cfg, block_data_groups = block_data.router(cfg)
        
        return cfg
    

    