import os
import sys

from worldenergydata.modules.bsee.data._by_api.well import WellData
# from worldenergydata.modules.bsee.data.prepare_data_for_analysis import PrepareBseeData


well = WellData()
# prep_bsee_data = PrepareBseeData()

class WellRouter:
       
    def __init__(self):
            pass
    
    def router(self, cfg):

        if 'groups' in cfg['data'] and cfg['data']['groups'][0]['api12'] is not None:
            cfg = self.get_well_data_groups(cfg)
            
        return cfg
    
    def get_well_data_groups(self, cfg):
        
        if 'preparation_for_analysis' in cfg['data'] and cfg['data']['preparation_for_analysis']:
            # prep_bsee_data.router(cfg)
            pass
        else:
             cfg, well_data_groups = well.router(cfg)

        return cfg