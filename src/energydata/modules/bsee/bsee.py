# Import necessary modules and classes
from assetutilities.common.update_deep import update_deep_dictionary #noqa
# Reader imports
from energydata.modules.bsee.data.get_data_from_production_files import GetDataFromFiles
from energydata.modules.bsee.data.get_zip_well_production_data import GetWellProdData
from energydata.modules.bsee.data.well_data import WellData
from energydata.modules.bsee.analysis.prepare_data_for_analysis import (
    PrepareBseeData,
)
from energydata.modules.bsee.data.scrapy_production_data import SpiderBsee
from energydata.modules.bsee.analysis.bsee_analysis import BSEEAnalysis

# Initialize instances of imported classes
gwp = GetWellProdData()
bsee_production = SpiderBsee()
well_data = WellData()
prep_bsee_data = PrepareBseeData()
bsee_analysis = BSEEAnalysis()
gdff = GetDataFromFiles()

class bsee:

    def __init__(self):
        pass

    def router(self, cfg):
        # Update configuration with master data
        # if 'input' in cfg and 'settings' in cfg or 'settings' in cfg and 'master_settings' in cfg:
        cfg = self.get_cfg_with_master_data(cfg)
        

        cfg[cfg['basename']] = {}
        # Route to appropriate data processing based on configuration flags
        if 'well_data' in cfg and cfg['well_data']['flag']:
            cfg = well_data.get_well_data(cfg)
        if 'block_data' in cfg and cfg['block_data']['flag'] or 'well_production' in cfg and cfg['well_production']['flag']:
            cfg = well_data.get_well_data(cfg)
        elif "data_prep" in cfg and cfg["data_prep"]["flag"]:
            data = prep_bsee_data.router(cfg)

        if 'analysis' in cfg and cfg['analysis']['flag']:
            bsee_analysis.router(cfg)

        if 'production' in cfg and cfg['production']['flag']:
            cfg = well_data.get_well_data(cfg)

        if 'well_prod_data' in cfg and cfg['well_prod_data']['flag']:
            gwp.router(cfg)

        if 'existing_data' in cfg and cfg['existing_data']['flag']:
            cfg = gdff.router(cfg)

        return cfg

    # Function to update configuration 
    def get_cfg_with_master_data(self, cfg):
        items_key = 'settings'
        # Check if 'settings' key is present in the cfg dictionary
        if items_key not in cfg:
            raise KeyError(f"The key '{items_key}' is not present in the configuration file.")
        
        if 'master_settings' in cfg:
            settings_master = cfg['master_settings'].copy()
            items = cfg[items_key]

            # combine settings with items
            for item_idx in range(0, len(items)):
                group = items[item_idx].copy()
                group = update_deep_dictionary(settings_master, group)
                items[item_idx] = group.copy()

        return cfg
