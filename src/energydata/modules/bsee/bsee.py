from energydata.modules.bsee.data.bsee_data import BSEEData
from energydata.modules.bsee.analysis.bsee_analysis import BSEEAnalysis

bsee_data = BSEEData()
bsee_analysis = BSEEAnalysis()

class bsee:

    def __init__(self):
        pass

    def router(self, cfg):
    
        cfg[cfg['basename']] = {}

        data_flag = cfg['data'].get('obtain', False)
        if data_flag:
            cfg, data = bsee_data.router(cfg)

        analysis_flag = cfg['analysis'].get('flag', False)
        if analysis_flag:
            cfg = bsee_analysis.router(cfg, data)

        return cfg
