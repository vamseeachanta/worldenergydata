import logging
import pandas as pd
from energydata.modules.bsee.data.block_data import BlockData

block_data = BlockData()

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

        cfg = self.add_api12_array_by_block_to_cfg(cfg)


        #TODO DELETE
        # cfg = self.update_cfg_to_wells_api12(cfg, api12_array)
        # from energydata.engine import engine 
        # engine(inputfile=None, cfg=cfg, config_flag=False)

        return cfg
    
    def add_api12_array_by_block_to_cfg(self, cfg):
        cfg, block_data_groups = block_data.router(cfg)
        
        # api12_array = []
        # if cfg[cfg['basename']]['well_data']['type'] == 'csv':
        #     csv_groups = cfg[cfg['basename']]['well_data']['groups']
        #     for csv_group in csv_groups:
        #         df = pd.read_csv(csv_group['file_name'])
        #         api12_csv_group = df['API Well Number'].unique().tolist()
        #         api12_array = api12_array + api12_csv_group

        return cfg
    
    def update_cfg_to_wells_api12(self, cfg, api12_array):
        '''
        function which transforms cfg into desired cfg
        '''

        updated_cfg = cfg.copy()
    
        # Update 'data' section
        updated_cfg['data']['by'] = 'API12'
        updated_cfg['data']['well_data'] = True
        updated_cfg['data']['production_data'] = False
        
        # Replace 'groups' with 'api12' array
        updated_cfg['data']['groups'] = [{'api12': api12_array}]
        
        return updated_cfg



    