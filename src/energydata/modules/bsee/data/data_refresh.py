import logging

from energydata.modules.bsee.data.production_data_from_zip import GetProdDataFromZip
from energydata.modules.bsee.data.well_from_zip import WellDataFromZip

from assetutilities.common.utilities import is_dir_valid_func

prod_zip = GetProdDataFromZip()
well_zip = WellDataFromZip()


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
        data_refresh_flag = cfg['data'].get('refresh', False)

        if data_refresh_flag:
            self.refresh_well_data(cfg)
            self.refresh_production_data(cfg)
            logging.info('Data refresh completed.')

        return cfg, None

    def refresh_well_data(self, cfg):
        """
        Refresh well data
        """
        data_refresh_apm_flag = cfg['data'].get('apm', False)
        if data_refresh_apm_flag:
            well_zip.save_eWellAPMRawData_to_binary(cfg)

    def refresh_production_data(self, cfg):
        """
        Refresh production data
        """
        data_refresh_prod_flag = cfg['data'].get('production', False)
        if data_refresh_prod_flag:
            prod_zip.save_zip_data_to_binary(cfg)
