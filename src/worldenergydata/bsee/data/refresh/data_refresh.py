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

class DataRefresh:
    """
    This class is responsible for refreshing data in the BSEE module.
    It handles the logic for updating and reloading data as needed.
    """

    def __init__(self):
        self._prod_zip = GetProdDataFromZip()
        self._well_zip = WellDataFromZip()
        self._data_refresh_enhanced = None  # Will be initialized only when needed
        self._config_router = ConfigRouter()

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
            if self._data_refresh_enhanced is None:
                self._data_refresh_enhanced = DataRefreshEnhanced()
            return self._data_refresh_enhanced.router(cfg)

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
            self._well_zip.save_eWellAPMRawData_to_binary(cfg)

    def refresh_production_data(self, cfg):
        """
        Refresh production data
        """
        data_refresh_prod_flag = cfg.get("data", {}).get("production", False)
        if data_refresh_prod_flag:
            self._prod_zip.save_zip_data_to_binary(cfg)
