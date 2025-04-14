from energydata.modules.bsee.data.bsee_data import BSEEData
from energydata.modules.bsee.analysis.bsee_analysis import BSEEAnalysis
from energydata.modules.bsee.data.production_data_from_zip import GetProdDataFromZip
prod_data = GetProdDataFromZip()

bsee_data = BSEEData()
bsee_analysis = BSEEAnalysis()

class bsee:

    def __init__(self):
        pass

    def router(self, cfg):
        prod_data.router(cfg)
        # cfg[cfg['basename']] = {}
        # cfg[cfg['basename']].update({'data': cfg['data']})
        # cfg[cfg['basename']].update({'analysis': cfg['analysis']})

        cfg, data = bsee_data.router(cfg)

        cfg = bsee_analysis.router(cfg, data)

        return cfg
