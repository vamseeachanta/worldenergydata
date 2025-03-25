import pandas as pd
from energydata.modules.bsee.data.block_data import BlockData

block_data = BlockData()

class Block:
       
    def __init__(self):
            pass
    
    def router(self, cfg):
       
        api12_array = self.get_api12_array_by_block(cfg)
        cfg = self.update_cfg_to_wells_api12(cfg, api12_array)
        from energydata.engine import engine 
        engine(inputfile=None, cfg=cfg, config_flag=False)
        return cfg           
    
    def get_api12_array_by_block(self, cfg):
        cfg, block_data_groups = block_data.router(cfg)
        
        api12_array = []
        if cfg[cfg['basename']]['well_data']['type'] == 'csv':
            csv_groups = cfg[cfg['basename']]['well_data']['groups']
            for csv_group in csv_groups:
                df = pd.read_csv(csv_group['file_name'])
                api12_csv_group = df['API Well Number'].unique().tolist()
                api12_array = api12_array + api12_csv_group

        return api12_array
    
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



    