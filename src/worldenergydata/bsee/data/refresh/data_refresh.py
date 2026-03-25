from loguru import logger

from worldenergydata.bsee.data.config import ConfigRouter

# Import enhanced components for routing
from worldenergydata.bsee.data.refresh.data_refresh_enhanced import (
    DataRefreshEnhanced,
)
from worldenergydata.bsee.data.sources.zip.production_data import (
    GetProdDataFromZip,
)
from worldenergydata.bsee.data.sources.zip.well_data import WellDataFromZip

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
        # Check mode in meta section (primary method)
        mode = cfg.get("meta", {}).get("mode", "legacy").lower()

        if mode == "enhanced":
            # Route to enhanced system (no need to check refresh flag)
            logger.info(
                "Enhanced mode detected - routing to enhanced data refresh system"
            )
            global data_refresh_enhanced
            if data_refresh_enhanced is None:
                data_refresh_enhanced = DataRefreshEnhanced()
            return data_refresh_enhanced.router(cfg)

        # Legacy mode - check for refresh flag
        logger.info("Legacy mode - checking for refresh flag")
        data_refresh_flag = cfg.get("data", {}).get("refresh", False)

        if data_refresh_flag:
            logger.info(
                "Legacy refresh flag detected - using legacy data refresh system"
            )
            self.refresh_well_data(cfg)
            self.refresh_production_data(cfg)
            logger.info("Legacy data refresh completed.")
        else:
            logger.info("Legacy mode but refresh flag is False - skipping data refresh")

        return cfg, None

    def refresh_well_data(self, cfg):
        """
        Refresh well data
        """
        data_refresh_apm_flag = cfg.get("data", {}).get("apm", False)
        if data_refresh_apm_flag:
            well_zip.save_eWellAPMRawData_to_binary(cfg)

    def refresh_production_data(self, cfg):
        """
        Refresh production data
        """
        data_refresh_prod_flag = cfg.get("data", {}).get("production", False)
        if data_refresh_prod_flag:
            prod_zip.save_zip_data_to_binary(cfg)
