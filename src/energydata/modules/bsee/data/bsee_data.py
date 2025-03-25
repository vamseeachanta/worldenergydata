import logging
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
        
        cfg = block.router(cfg)
   
        cfg, well_data = well.router(cfg)
        cfg, production_data = production.router(cfg)

        data = {'well_data': well_data, 'production_data': production_data}

        return cfg, data
