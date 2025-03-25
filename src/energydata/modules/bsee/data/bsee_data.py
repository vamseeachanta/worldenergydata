from energydata.modules.bsee.data.well import WellData
from energydata.modules.bsee.data.production import Production
from energydata.modules.bsee.data.block import Block

well = WellData()
production = Production()
block = Block()

class BSEEData:

    def __init__(self):
        pass

    def router(self, cfg):
        
        if cfg['data']['by'] == 'block':
            block.router(cfg)
   
        else:
            cfg, well_data_groups = well.router(cfg)
            cfg, production_data_groups = production.router(cfg)

        data = {'well_data': well_data_groups, 'production_data': production_data_groups}

        return cfg, data
