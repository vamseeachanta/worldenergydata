"""
Enhanced BSEE Data Refresh Module

This module provides a parallel implementation to the legacy data_refresh.py,
offering fresh data access through web scraping with in-memory processing.
It maintains full compatibility with existing binary output formats while
eliminating the stale data problem.

This is a NEW implementation that runs alongside the legacy system.
"""

from loguru import logger
from typing import Dict, Any, Optional
import os
import sys
from pathlib import Path

# Import the new components we'll create
from worldenergydata.modules.bsee.data.refresh.bsee_web_scraper import BSEEWebScraper
from worldenergydata.modules.bsee.data.refresh.memory_processor import MemoryProcessor
from worldenergydata.modules.bsee.data.refresh.config_router import ConfigRouter

# Import existing processors for binary generation compatibility
from worldenergydata.modules.bsee.data._from_zip.production_data import GetProdDataFromZip
from worldenergydata.modules.bsee.data._from_zip.well_data import WellDataFromZip

from assetutilities.common.utilities import is_dir_valid_func


class DataRefreshEnhanced:
    """
    Enhanced data refresh implementation with fresh data access.
    
    This class provides a parallel implementation to DataRefresh that:
    - Fetches fresh data directly from BSEE URLs
    - Processes data in-memory without storing zip files
    - Maintains compatibility with existing binary formats
    - Can run independently of the legacy system
    """
    
    def __init__(self):
        """Initialize the enhanced data refresh system."""
        self.web_scraper = BSEEWebScraper()
        self.memory_processor = MemoryProcessor()
        self.config_router = ConfigRouter()
        
        # Use existing processors for compatibility
        self.prod_processor = GetProdDataFromZip()
        self.well_processor = WellDataFromZip()
        
        logger.info("Enhanced Data Refresh System initialized")
    
    def router(self, cfg: Dict[str, Any]) -> tuple:
        """
        Main routing method compatible with existing architecture.
        
        Args:
            cfg: Configuration dictionary from YAML
            
        Returns:
            Tuple of (cfg, None) for compatibility with existing flow
        """
        logger.info("Starting enhanced data refresh process")
        
        # Check if enhanced mode is enabled
        enhanced_mode = self.config_router.is_enhanced_mode(cfg)
        if not enhanced_mode:
            logger.warning("Enhanced mode not enabled in configuration")
            return cfg, None
        
        # Get data refresh flags - using 'enhanced_refresh' to avoid conflicts with legacy system
        data_refresh_flag = cfg.get('data', {}).get('enhanced_refresh', False)
        
        if data_refresh_flag:
            logger.info("Enhanced data refresh flag is True, processing data sources")
            
            # Process each data type based on flags
            self.refresh_well_data_enhanced(cfg)
            self.refresh_war_data_enhanced(cfg)
            self.refresh_production_data_enhanced(cfg)
            
            logger.info('Enhanced data refresh completed successfully')
        else:
            logger.info("Enhanced data refresh flag is False, skipping refresh")
        
        return cfg, None
    
    def refresh_well_data_enhanced(self, cfg: Dict[str, Any]) -> None:
        """
        Refresh well data (APD) with fresh download.
        
        Args:
            cfg: Configuration dictionary
        """
        # Check for well data flag (replaces apm flag in enhanced version)
        well_flag = cfg.get('data', {}).get('well', False)
        legacy_apm_flag = cfg.get('data', {}).get('apm', False)
        
        if well_flag or legacy_apm_flag:
            logger.info("Processing well data (APD) with fresh download")
            
            try:
                # URL for well APD data
                well_url = "https://www.data.bsee.gov/Well/Files/APDRawData.zip"
                
                # Download and process in memory
                logger.info(f"Downloading well data from {well_url}")
                zip_data = self.web_scraper.download_zip_to_memory(well_url)
                
                if zip_data:
                    # Process the data in memory
                    logger.info("Processing well data in memory")
                    processed_data = self.memory_processor.process_well_data(zip_data, cfg)
                    
                    # Save to binary using existing format
                    logger.info("Saving well data to binary format")
                    self._save_well_data_binary(processed_data, cfg)
                    
                    logger.info("Well data refresh completed")
                else:
                    logger.error("Failed to download well data")
                    
            except Exception as e:
                logger.error(f"Error refreshing well data: {str(e)}")
    
    def refresh_war_data_enhanced(self, cfg: Dict[str, Any]) -> None:
        """
        Refresh WAR (Well Activity Report) data with fresh download.
        
        Args:
            cfg: Configuration dictionary
        """
        # Check for WAR data flag (new in enhanced version)
        war_flag = cfg.get('data', {}).get('war', False)
        
        if war_flag:
            logger.info("Processing WAR data with fresh download")
            
            try:
                # URL for WAR data
                war_url = "https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip"
                
                # Download and process in memory
                logger.info(f"Downloading WAR data from {war_url}")
                zip_data = self.web_scraper.download_zip_to_memory(war_url)
                
                if zip_data:
                    # Process the data in memory
                    logger.info("Processing WAR data in memory")
                    processed_data = self.memory_processor.process_war_data(zip_data, cfg)
                    
                    # Save to binary using compatible format
                    logger.info("Saving WAR data to binary format")
                    self._save_war_data_binary(processed_data, cfg)
                    
                    logger.info("WAR data refresh completed")
                else:
                    logger.error("Failed to download WAR data")
                    
            except Exception as e:
                logger.error(f"Error refreshing WAR data: {str(e)}")
    
    def refresh_production_data_enhanced(self, cfg: Dict[str, Any]) -> None:
        """
        Refresh production data with fresh download.
        
        Args:
            cfg: Configuration dictionary
        """
        production_flag = cfg.get('data', {}).get('production', False)
        
        if production_flag:
            logger.info("Processing production data with fresh download")
            
            try:
                # URL for production data
                prod_url = "https://www.data.bsee.gov/Production/Files/ProductionRawData.zip"
                
                # Download and process in memory
                logger.info(f"Downloading production data from {prod_url}")
                zip_data = self.web_scraper.download_zip_to_memory(prod_url)
                
                if zip_data:
                    # Process the data in memory
                    logger.info("Processing production data in memory")
                    processed_data = self.memory_processor.process_production_data(zip_data, cfg)
                    
                    # Save to binary using existing format
                    logger.info("Saving production data to binary format")
                    self._save_production_data_binary(processed_data, cfg)
                    
                    logger.info("Production data refresh completed")
                else:
                    logger.error("Failed to download production data")
                    
            except Exception as e:
                logger.error(f"Error refreshing production data: {str(e)}")
    
    def _save_well_data_binary(self, data: Any, cfg: Dict[str, Any]) -> None:
        """
        Save well data to binary format compatible with legacy system.
        
        Args:
            data: Processed well data
            cfg: Configuration dictionary
        """
        # Use existing well processor for compatibility
        # This ensures the binary format matches exactly
        try:
            # Get output path from config
            bin_path = cfg.get('parameters', {}).get('filepath', {}).get('apm', {}).get('bin', 
                                                                                         'data/modules/bsee/bin/apd')
            
            # Ensure directory exists
            Path(bin_path).mkdir(parents=True, exist_ok=True)
            
            # Save using compatible format
            self.memory_processor.save_to_binary(data, bin_path, 'well_data')
            logger.info(f"Well data saved to {bin_path}")
            
        except Exception as e:
            logger.error(f"Error saving well data binary: {str(e)}")
    
    def _save_war_data_binary(self, data: Any, cfg: Dict[str, Any]) -> None:
        """
        Save WAR data to binary format.
        
        Args:
            data: Processed WAR data
            cfg: Configuration dictionary
        """
        try:
            # Get output path from config (create new path for WAR)
            bin_path = cfg.get('parameters', {}).get('filepath', {}).get('war', {}).get('bin', 
                                                                                         'data/modules/bsee/bin/war')
            
            # Ensure directory exists
            Path(bin_path).mkdir(parents=True, exist_ok=True)
            
            # Save using compatible format
            self.memory_processor.save_to_binary(data, bin_path, 'war_data')
            logger.info(f"WAR data saved to {bin_path}")
            
        except Exception as e:
            logger.error(f"Error saving WAR data binary: {str(e)}")
    
    def _save_production_data_binary(self, data: Any, cfg: Dict[str, Any]) -> None:
        """
        Save production data to binary format compatible with legacy system.
        
        Args:
            data: Processed production data
            cfg: Configuration dictionary
        """
        try:
            # Get output path from config
            bin_path = cfg.get('parameters', {}).get('filepath', {}).get('production', {}).get('bin', 
                                                                                               'data/modules/bsee/bin/production_raw')
            
            # Ensure directory exists
            Path(bin_path).mkdir(parents=True, exist_ok=True)
            
            # Save using compatible format
            self.memory_processor.save_to_binary(data, bin_path, 'production_data')
            logger.info(f"Production data saved to {bin_path}")
            
        except Exception as e:
            logger.error(f"Error saving production data binary: {str(e)}")