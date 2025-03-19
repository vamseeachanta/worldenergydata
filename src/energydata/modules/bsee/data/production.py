from energydata.modules.bsee.data.production_data_sources import ProductionDataFromSources
from energydata.modules.bsee.data.production_data_from_zip import GetProdDataFromZip


production_data = ProductionDataFromSources()
production_from_zip = GetProdDataFromZip()

class Production:
    
    def __init__(self):
        pass

    def router(self, cfg):

        production_data_flag = cfg['data'].get('production_data', False)
        production_data_groups = None
        if production_data_flag:
            cfg, production_data_groups = production_data.get_data(cfg)
        
        elif "production_from_website" in cfg and cfg['production_from_website']['flag']:
           production_data.get_production_from_website(cfg)
        
        elif "production_from_zip" in cfg and cfg['production_from_zip']['flag']:
            production_data.get_all_data(cfg)

        return cfg, production_data_groups