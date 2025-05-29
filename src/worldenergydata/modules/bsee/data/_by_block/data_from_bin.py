import os
from copy import deepcopy

import pandas as pd

from assetutilities.common.utilities import is_dir_valid_func

class DataFromBin:

    def __init__(self):
        pass

    def router(self, cfg):
        cfg, block_data_groups = self.get_data(cfg)
        
        return cfg, block_data_groups

