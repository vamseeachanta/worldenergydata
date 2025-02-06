# Import necessary modules and classes
from assetutilities.common.update_deep import update_deep_dictionary #noqa
# Reader imports
from energydata.base_configs.modules.bsee.well_data import WellData
from energydata.modules.bsee.analysis.prepare_bsee_data_for_analysis import (
    PrepareBseeData,
)
from energydata.modules.bsee.data.scrapy_production_data import SpiderBsee

# Initialize instances of imported classes
bsee_production = SpiderBsee()
well_data = WellData()
prep_bsee_data = PrepareBseeData()

class bsee_router:
    def __init__(self):
        pass

    def router(self, cfg):
        # Update configuration with master data
        cfg = self.get_cfg_with_master_data(cfg)
        cfg[cfg['basename']] = {}
        # Route to appropriate data processing based on configuration flags
        if 'well_data' in cfg and cfg['well_data']['flag'] or 'block_data' in cfg and cfg['block_data']['flag']:
            cfg = well_data.get_well_data(cfg)
        elif "data_prep" in cfg and cfg["data_prep"]["flag"]:
            data = prep_bsee_data.router(cfg)

        if 'production' in cfg and cfg['production']['flag']:
            bsee_production.router(cfg)

        if 'borehole' in cfg and cfg['borehole']['flag']:
            pass

        return cfg

    # Function to update configuration 
    def get_cfg_with_master_data(self, cfg):
        items_key = 'input'
        if 'settings' in cfg:
            settings_master = cfg['settings'].copy()
            items = cfg[items_key]

            # combine settings with items
            for item_idx in range(0, len(items)):
                group = items[item_idx].copy()
                group = update_deep_dictionary(settings_master, group)
                items[item_idx] = group.copy()

        return cfg
