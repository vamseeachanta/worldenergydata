from loguru import logger

from worldenergydata.modules.bsee.data._from_zip.production_data import GetProdDataFromZip
from worldenergydata.modules.bsee.data._from_zip.well_data import WellDataFromZip

# Import enhanced components for routing
from worldenergydata.modules.bsee.data.refresh.data_refresh_enhanced import DataRefreshEnhanced
from worldenergydata.modules.bsee.data.refresh.config_router import ConfigRouter

prod_zip = GetProdDataFromZip()
well_zip = WellDataFromZip()
data_refresh_enhanced = None  # Will be initialized only when needed
config_router = ConfigRouter()


class DataRefresh:
    """
    This class is responsible for refreshing data in the BSEE module.
    It handles the logic for updating and reloading data as needed.
    """

    def __init__(self):
        pass

    def router(self, cfg):
        """
        Refresh all data. Routes to enhanced or legacy system based on configuration.
        """
        # Check for enhanced_refresh flag first (new flag for enhanced system)
        enhanced_refresh_flag = cfg.get('data', {}).get('enhanced_refresh', False)
        
        # Also check if enhanced mode is explicitly enabled
        enhanced_mode = cfg.get('enhanced_mode', False) or cfg.get('data', {}).get('enhanced', False)
        
        if enhanced_refresh_flag or enhanced_mode:
            # Route to enhanced system
            logger.info("Enhanced refresh flag detected - routing to enhanced data refresh system")
            global data_refresh_enhanced
            if data_refresh_enhanced is None:
                data_refresh_enhanced = DataRefreshEnhanced()
            return data_refresh_enhanced.router(cfg)
        
        # Fall back to legacy system using the original 'refresh' flag
        data_refresh_flag = cfg['data'].get('refresh', False)

        if data_refresh_flag:
            logger.info("Legacy refresh flag detected - using legacy data refresh system")
            self.refresh_well_data(cfg)
            self.refresh_production_data(cfg)
            logger.info('Legacy data refresh completed.')

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
