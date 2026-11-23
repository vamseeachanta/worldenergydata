from worldenergydata.bsee.data.loaders.api.well import WellData

# from worldenergydata.bsee.data.prepare_data_for_analysis import PrepareBseeData


class WellRouter:

    def __init__(self):
        self._well = WellData()
        # self._prep_bsee_data = PrepareBseeData()

    def router(self, cfg):

        if "groups" in cfg["data"] and cfg["data"]["groups"][0]["api12"] is not None:
            cfg = self.get_well_data_groups(cfg)

        return cfg

    def get_well_data_groups(self, cfg):

        if (
            "preparation_for_analysis" in cfg["data"]
            and cfg["data"]["preparation_for_analysis"]
        ):
            # self._prep_bsee_data.router(cfg)
            pass
        else:
            cfg, well_data_groups = self._well.router(cfg)

        return cfg
