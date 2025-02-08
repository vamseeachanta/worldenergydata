
from energydata.modules.zip_data_dwnld.dwnld_from_zipurl import DownloadFromZipUrl

# Initialize instances of imported classes
d_f_zu = DownloadFromZipUrl()

class zip_router:

    def __init__(self):
        pass

    def router(self, cfg):

        if "data" in cfg and cfg['data']['flag']:
            d_f_zu.router(cfg)

        return cfg