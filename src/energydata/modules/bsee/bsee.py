# Import necessary modules and classes
from assetutilities.common.update_deep import update_deep_dictionary #noqa
# Reader imports
from energydata.modules.bsee.data.production_data_from_zip import GetWellProdDataFromZip
#from energydata.modules.bsee.data.production_data_from_website import GetWellProdDataFromWebsite
from energydata.modules.bsee.data.well_data import WellData
from energydata.modules.bsee.data.production_data import ProductionDataWebsite
from energydata.modules.bsee.data.block_data import BlockDataWebsite
from energydata.modules.bsee.analysis.prepare_data_for_analysis import PrepareBseeData
from energydata.modules.bsee.data.scrapy_production_data import SpiderBsee
from energydata.modules.bsee.analysis.bsee_analysis import BSEEAnalysis
from energydata.modules.bsee.data.bsee_data import BSEEData

# Initialize instances of imported classes
production_from_website = ProductionDataWebsite()
block_data_website = BlockDataWebsite()
bsee_production = SpiderBsee()
well_data = WellData()
#production_data = GetWellProdDataFromWebsite()
prep_bsee_data = PrepareBseeData()
bsee_analysis = BSEEAnalysis()
production_from_zip = GetWellProdDataFromZip()
bsee_data = BSEEData()

class bsee:

    def __init__(self):
        pass

    def router(self, cfg):
        # Update configuration with master data
        cfg = self.get_cfg_with_master_data(cfg)

        cfg[cfg['basename']] = {}

        cfg, data = bsee_data.router(cfg)

        cfg = bsee_analysis.router(cfg, data)

        return cfg

    # Function to update configuration 
    def get_cfg_with_master_data(self, cfg):
        # items_key = 'settings'
        # Check if 'settings' key is present in the cfg dictionary
        # if items_key not in cfg:
        #     raise KeyError(f"The key {items_key} is not present in the configuration file.")
        
        # if 'master_settings' in cfg:
        #     settings_master = cfg['master_settings'].copy()
        #     items = cfg[items_key]

        #     # combine settings with items
        #     for item_idx in range(0, len(items)):
        #         group = items[item_idx].copy()
        #         group = update_deep_dictionary(settings_master, group)
        #         items[item_idx] = group.copy()

        pass
    
        return cfg
