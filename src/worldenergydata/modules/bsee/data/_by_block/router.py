import pandas as pd
from worldenergydata.modules.bsee.data._by_block.data_from_local_files import DataFromLocalFiles
from worldenergydata.modules.bsee.data._by_block.war_data import WARDataFromBin

block_data_from_local_files = DataFromLocalFiles()
WAR_data_from_bin = WARDataFromBin()

class BlockRouter:
       
    def __init__(self):
            pass
    
    def router(self, cfg):

        if 'groups' in cfg['data'] and cfg['data']['groups'][0]['bottom_block'] is not None:
            cfg = self.get_block_data_groups(cfg)

        return cfg
    
    def get_block_data_groups(self, cfg):

        # condition utilized for temporary data retrieval
        if 'by_bin' in cfg['data'] and cfg['data']['by_bin']:
            cfg, block_data_groups = WAR_data_from_bin.router(cfg)
        else:
            cfg, block_data_groups = block_data_from_local_files.router(cfg)

        return cfg
    

    