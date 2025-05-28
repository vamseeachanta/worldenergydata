import logging
import pandas as pd
from worldenergydata.modules.bsee.data._by_block.data_from_url import DataFromURL

block_data = DataFromURL()

class Block:
       
    def __init__(self):
            pass
    
    def router(self, cfg):

        #TODO relocate as necessary
        # groups = cfg['data']['groups']
        # for group in groups:
        #     if 'bottom_block' in group and group['bottom_block'] is not None:
        #         group_block = group['bottom_block']
        #         group_api12 = group['api12']
        #         if group_api12 is not None:
        #             logging.warning('group item running by Block data. API12 input NOT used')
        if 'analysis' in cfg and cfg['analysis']['bottom_blocks']:
            cfg = self.add_api12_array_by_block_to_cfg(cfg)



        return cfg
    
    def add_api12_array_by_block_to_cfg(self, cfg):
        cfg, block_data_groups = block_data.router(cfg)
        
        return cfg
    

    