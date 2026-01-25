from worldenergydata.modules.bsee.data.loaders.api.well import WellData
from worldenergydata.modules.bsee.data.production.router import ProductionRouter
from worldenergydata.modules.bsee.data.loaders.block.router import BlockRouter
from worldenergydata.modules.bsee.data.loaders.lease.router import LeaseRouter
from worldenergydata.modules.bsee.data.refresh.data_refresh import DataRefresh

production = ProductionRouter()
block = BlockRouter()
lease = LeaseRouter()

well = WellData()
data_refresh = DataRefresh()

class BSEEData:

    def __init__(self):
        pass

    def router(self, cfg):

        cfg, _ = data_refresh.router(cfg)

        cfg = block.router(cfg)

        cfg, well_data = well.router(cfg)
        cfg, production_data = production.router(cfg)
        cfg = lease.router(cfg)

        data = {'well_data': well_data, 'production_data': production_data}

        return cfg, data