from worldenergydata.bsee.analysis.bsee_analysis import BSEEAnalysis
from worldenergydata.bsee.data.bsee_data import BSEEData

bsee_data = BSEEData()
bsee_analysis = BSEEAnalysis()


class bsee:

    def __init__(self):
        pass

    def router(self, cfg):
        basename = cfg["basename"]

        cfg[basename] = {}
        cfg[basename].update({"data": cfg.get("data", {}).copy()})
        cfg[basename].update({"analysis": cfg.get("analysis", {}).copy()})

        cfg, data = bsee_data.router(cfg)
        cfg = bsee_analysis.router(cfg, data)

        return cfg
