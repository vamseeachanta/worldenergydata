from energydata.modules.bsee.data.bsee_data import BSEEData
from energydata.modules.bsee.analysis.bsee_analysis import BSEEAnalysis

bsee_data = BSEEData()
bsee_analysis = BSEEAnalysis()

class bsee:

    def __init__(self):
        pass

    def router(self, cfg):
    
        cfg[cfg['basename']] = {}

        if "data" in cfg and cfg['data'].get('obtain', False):
            cfg, data = bsee_data.router(cfg)

        if "analysis" in cfg and cfg['analysis'].get('flag', False):
            cfg = bsee_analysis.router(cfg, data)

        return cfg
