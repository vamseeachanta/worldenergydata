from worldenergydata.bsee.data.production.production_data_sources import ProductionDataFromSources
from worldenergydata.bsee.data.sources.zip.production_data import GetProdDataFromZip

production_data_sources = ProductionDataFromSources()
production_from_zip = GetProdDataFromZip()

class ProductionRouter:
    
    def __init__(self):
        pass

    def router(self, cfg):

        production_data_flag = cfg['data'].get('production_data', False)
        production_data_groups = None
        if production_data_flag:
            cfg, production_data_groups = production_data_sources.get_data(cfg)
        
        # elif "production_from_website" in cfg and cfg['production_from_website']['flag']:
        #     production_data_sources.get_production_from_website(cfg)

        return cfg, production_data_groups