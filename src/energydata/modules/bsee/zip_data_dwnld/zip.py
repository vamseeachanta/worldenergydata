
from energydata.modules.bsee.zip_data_dwnld.dwnld_from_zipurl import DownloadFromZipUrl

# Initialize instances of imported classes
download_from_zip = DownloadFromZipUrl()

class zip:

    def __init__(self):
        pass

    def router(self, cfg):

        if "online_query" in cfg and cfg['online_query']['raw_data']['delimit']:
            download_from_zip.router(cfg)

        return cfg