import logging
from energydata.modules.bsee.data.well import WellData
from energydata.modules.bsee.data.production import Production
from energydata.modules.bsee.data.block import Block
from energydata.modules.bsee.data.data_refresh import DataRefresh

well = WellData()
production = Production()
block = Block()
data_refresh = DataRefresh()
class BSEEData:

    def __init__(self):
        pass

    def router(self, cfg):
        
        data_refresh_flag = cfg['data'].get('refresh', False)
        if data_refresh_flag:
            cfg = data_refresh.router(cfg)
            logging.info('Data refresh completed.')
            return cfg, None
        else:
            cfg = block.router(cfg)
    
            cfg, well_data = well.router(cfg)
            cfg, production_data = production.router(cfg)

            data = {'well_data': well_data ,'production_data': production_data}
            #data = {'production_data': production_data}

            return cfg, data
