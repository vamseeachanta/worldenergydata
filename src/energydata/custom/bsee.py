from assetutilities.common.update_deep import update_deep_dictionary

from energydata.custom.bsee_data import bseedata
bsee_data = bseedata()

class bsee:
    
    def __init__(self):
        pass


    def router(self, cfg):

        cfg = self.get_cfg_with_master_data(cfg)

        if cfg['type']['data']:
            bsee_data.router(cfg)

        if cfg['type']['analysis']:
            pass

        if cfg['type']['results']:
            pass

        return cfg


    def get_cfg_with_master_data(self, cfg):
        pass
        
        return cfg

    def get_cfg_with_master_data(self, cfg):
        items_key = 'input'
        if 'settings_master' in cfg:
            settings_master = cfg['settings_master'].copy()
            items = cfg[items_key]

            for item_idx in range(0, len(items)):
                group = items[item_idx].copy()
                group = update_deep_dictionary(settings_master, group)
                items[item_idx] = group.copy()

        return cfg
    