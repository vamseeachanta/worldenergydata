
# Third party imports
from assetutilities.common.update_deep import update_deep_dictionary
from energydata.custom.scrapy_production_data import SpiderBsee

# Reader imports
from energydata.base_configs.modules.bsee.well_data import WellData

bsee_production = SpiderBsee()
well_data = WellData()

class bsee:
    
    def __init__(self):
        pass


    def router(self, cfg):

        cfg = self.get_cfg_with_master_data(cfg)

        if 'well_data' in cfg and cfg['well_data']['flag']:
            data= well_data.get_well_data(cfg)
        elif "block_data" in cfg and cfg["block_data"]["flag"]:
            data = well_data.get_well_data(cfg)

        if 'production' in cfg and cfg['production']['flag']:
            bsee_production.router(cfg)

        if 'borehole' in cfg and cfg['borehole']['flag']:
            pass

        return cfg

    def get_cfg_with_master_data(self, cfg):
        items_key = 'input'
        if 'settings' in cfg:
            settings_master = cfg['settings'].copy()
            items = cfg[items_key]

            for item_idx in range(0, len(items)):
                group = items[item_idx].copy()
                group = update_deep_dictionary(settings_master, group)
                items[item_idx] = group.copy()

        return cfg
