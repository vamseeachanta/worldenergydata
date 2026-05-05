from worldenergydata.bsee.analysis.bsee_analysis import BSEEAnalysis
from worldenergydata.bsee.data.bsee_data import BSEEData


class bsee:

    def __init__(self):
        self._bsee_data = BSEEData()
        self._bsee_analysis = BSEEAnalysis()

    def router(self, cfg):
        basename = cfg["basename"]

        cfg[basename] = {}
        cfg[basename].update({"data": cfg.get("data", {}).copy()})
        cfg[basename].update({"analysis": cfg.get("analysis", {}).copy()})

        cfg, data = self._bsee_data.router(cfg)
        cfg = self._bsee_analysis.router(cfg, data)

        return cfg
