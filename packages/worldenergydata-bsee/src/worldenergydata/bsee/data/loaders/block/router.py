from worldenergydata.bsee.data.loaders.block.local_files import (
    DataFromLocalFiles,
)
from worldenergydata.bsee.data.loaders.block.war_data import WARDataFromBin


class BlockRouter:

    def __init__(self):
        self._block_data_from_local_files = DataFromLocalFiles()
        self._WAR_data_from_bin = WARDataFromBin()

    def router(self, cfg):

        if (
            "groups" in cfg["data"]
            and cfg["data"]["groups"][0]["bottom_block"] is not None
        ):
            cfg = self.get_block_data_groups(cfg)

        return cfg

    def get_block_data_groups(self, cfg):

        # utilized for temporary data retrieval
        if "by_bin" in cfg["data"] and cfg["data"]["by_bin"]:
            cfg, block_data_groups = self._WAR_data_from_bin.router(cfg)
        else:
            cfg, block_data_groups = self._block_data_from_local_files.router(cfg)

        return cfg
