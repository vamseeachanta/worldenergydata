import logging
from worldenergydata.modules.bsee.data.well import WellData
from worldenergydata.modules.bsee.data.production import Production
from worldenergydata.modules.bsee.data.block import Block
from worldenergydata.modules.bsee.data.data_refresh import DataRefresh

well = WellData()
production = Production()
block = Block()
data_refresh = DataRefresh()
class BSEEData:

    def __init__(self):
        pass

    def router(self, cfg):

        cfg, _ = data_refresh.router(cfg)

        cfg = block.router(cfg)

        cfg, well_data = well.router(cfg)
        cfg, production_data = production.router(cfg)

        data = {'well_data': well_data, 'production_data': production_data}

        return cfg, data
