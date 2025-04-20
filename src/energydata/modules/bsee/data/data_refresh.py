from energydata.modules.bsee.data.production_data_from_zip import GetProdDataFromZip

from assetutilities.common.utilities import is_dir_valid_func

prod_zip = GetProdDataFromZip()


class DataRefresh:
    """
    This class is responsible for refreshing data in the BSEE module.
    It handles the logic for updating and reloading data as needed.
    """

    def __init__(self):
        pass

    def router(self, cfg):
        """
        Refresh all data.
        """
        self.refresh_production_data(cfg)
        
        return cfg
        
    def refresh_well_data(self, cfg):
        """
        Refresh well data
        """
        pass

    def refresh_production_data(self, cfg):
        """
        Refresh production data
        """
        prod_zip.save_zip_data_to_binary(cfg)
