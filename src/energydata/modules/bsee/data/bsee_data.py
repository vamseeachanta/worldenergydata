from energydata.modules.bsee.data.well import WellData
from energydata.modules.bsee.data.production import Production

well = WellData()
production = Production()

class BSEEData:

    def __init__(self):
        pass

    def router(self, cfg):

        cfg, well_data_groups = well.router(cfg)
        cfg, production_data_groups = production.router(cfg)

        data = {'well_data': well_data_groups, 'production_data': production_data_groups}

        return cfg, data
