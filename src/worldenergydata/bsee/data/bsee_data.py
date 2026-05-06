from worldenergydata.bsee.data.loaders.api.well import WellData
from worldenergydata.bsee.data.loaders.block.router import BlockRouter
from worldenergydata.bsee.data.loaders.lease.router import LeaseRouter
from worldenergydata.bsee.data.production.router import ProductionRouter
from worldenergydata.bsee.data.refresh.data_refresh import DataRefresh


class BSEEData:

    def __init__(self):
        self._production = ProductionRouter()
        self._block = BlockRouter()
        self._lease = LeaseRouter()
        self._well = WellData()
        self._data_refresh = DataRefresh()

    def router(self, cfg):

        cfg, _ = self._data_refresh.router(cfg)

        cfg = self._block.router(cfg)

        cfg, well_data = self._well.router(cfg)
        cfg, production_data = self._production.router(cfg)
        cfg = self._lease.router(cfg)

        data = {"well_data": well_data, "production_data": production_data}

        return cfg, data
