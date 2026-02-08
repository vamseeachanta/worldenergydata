"""
Enhanced BSEE Data Refresh Module

This module provides a parallel implementation to the legacy data_refresh.py,
offering fresh data access through web scraping with in-memory processing.
It maintains full compatibility with existing binary output formats while
eliminating the stale data problem.

Features:
- Chunk-based change detection to avoid re-downloading unchanged data
- Parallel processing of zip file contents
- Optimized chunked DataFrame processing for large files
- In-memory processing without storing zip files

This is a NEW implementation that runs alongside the legacy system.
"""

from pathlib import Path
from typing import Any, Dict

from loguru import logger

from worldenergydata.bsee.data.config import ConfigRouter
from worldenergydata.bsee.data.processors import MemoryProcessor

# Import the new components
from worldenergydata.bsee.data.scrapers import BSEEWebScraper

# Import chunk manager for intelligent downloads
try:
    from worldenergydata.bsee.data.cache import ChunkManager

    CHUNK_MANAGER_AVAILABLE = True
except ImportError:
    logger.warning("ChunkManager not available - will use direct downloads")
    CHUNK_MANAGER_AVAILABLE = False

# Import existing processors for binary generation compatibility
from worldenergydata.bsee.data.sources.zip.production_data import (
    GetProdDataFromZip,
)
from worldenergydata.bsee.data.sources.zip.well_data import WellDataFromZip


class DataRefreshEnhanced:
    """
    Enhanced data refresh implementation with fresh data access.

    This class provides a parallel implementation to DataRefresh that:
    - Fetches fresh data directly from BSEE URLs
    - Processes data in-memory without storing zip files
    - Maintains compatibility with existing binary formats
    - Can run independently of the legacy system
    """

    def __init__(self, use_chunked_downloads=True, use_optimized_processing=True):
        """
        Initialize the enhanced data refresh system with all optimizations.

        Args:
            use_chunked_downloads: Enable chunk-based change detection
            use_optimized_processing: Enable optimized DataFrame processing
        """
        self.web_scraper = BSEEWebScraper()
        self.memory_processor = MemoryProcessor(use_optimized=use_optimized_processing)
        self.config_router = ConfigRouter()

        # Initialize chunk manager if available and enabled
        self.use_chunked_downloads = use_chunked_downloads and CHUNK_MANAGER_AVAILABLE
        if self.use_chunked_downloads:
            self.chunk_manager = ChunkManager()
            logger.info("Chunk-based change detection ENABLED")
        else:
            self.chunk_manager = None
            if use_chunked_downloads and not CHUNK_MANAGER_AVAILABLE:
                logger.warning("Chunk manager requested but not available")

        # Use existing processors for compatibility
        self.prod_processor = GetProdDataFromZip()
        self.well_processor = WellDataFromZip()

        # Statistics tracking
        self.stats = {
            "bytes_downloaded": 0,
            "bytes_cached": 0,
            "processing_time_ms": 0,
            "chunks_reused": 0,
            "parallel_files_processed": 0,
        }

        logger.info("Enhanced Data Refresh System initialized")
        logger.info(
            f"  - Chunked downloads: {'ENABLED' if self.use_chunked_downloads else 'DISABLED'}"
        )
        logger.info(
            f"  - Optimized processing: {'ENABLED' if use_optimized_processing else 'DISABLED'}"
        )
        logger.info("  - Parallel zip processing: ENABLED (built-in)")

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

        # In enhanced mode, check if any data type flags are set
        # We don't use a 'refresh' flag to avoid confusion with legacy system
        well_flag = cfg.get("data", {}).get("well", False)
        war_flag = cfg.get("data", {}).get("war", False)
        production_flag = cfg.get("data", {}).get("production", False)
        platform_flag = cfg.get("data", {}).get("platform", False)
        pipeline_permit_flag = cfg.get("data", {}).get("pipeline_permit", False)
        deepwater_flag = cfg.get("data", {}).get("deepwater_structure", False)
        pipeline_loc_flag = cfg.get("data", {}).get("pipeline_location", False)

        if (
            well_flag
            or war_flag
            or production_flag
            or platform_flag
            or pipeline_permit_flag
            or deepwater_flag
            or pipeline_loc_flag
        ):
            logger.info("Data type flags detected, processing requested data sources")

            # Process each data type based on flags
            self.refresh_well_data_enhanced(cfg)
            self.refresh_war_data_enhanced(cfg)
            self.refresh_production_data_enhanced(cfg)
            self.refresh_platform_data_enhanced(cfg)
            self.refresh_pipeline_permit_data_enhanced(cfg)
            self.refresh_deepwater_structure_data_enhanced(cfg)
            self.refresh_pipeline_location_data_enhanced(cfg)

            # Report statistics
            self._report_statistics()

            logger.info("Enhanced data refresh completed successfully")
        else:
            logger.info("No data type flags set, skipping refresh")

        return cfg, None

    def _report_statistics(self):
        """Report comprehensive statistics for the refresh process."""
        logger.info("=" * 60)
        logger.info("ENHANCED REFRESH STATISTICS")
        logger.info("=" * 60)

        # Download statistics
        downloaded_mb = self.stats["bytes_downloaded"] / (1024 * 1024)
        cached_mb = self.stats["bytes_cached"] / (1024 * 1024)
        total_mb = downloaded_mb + cached_mb

        logger.info("Data Transfer:")
        logger.info(f"  Downloaded: {downloaded_mb:.2f} MB")
        logger.info(f"  From Cache: {cached_mb:.2f} MB")
        if total_mb > 0:
            cache_ratio = (cached_mb / total_mb) * 100
            logger.info(f"  Cache Hit Rate: {cache_ratio:.1f}%")
            logger.info(f"  Bandwidth Saved: {cached_mb:.2f} MB")

        # Processing statistics
        logger.info("Processing:")
        logger.info(
            f"  Parallel Files Processed: {self.stats['parallel_files_processed']}"
        )

        # Optimization status
        logger.info("Optimizations:")
        logger.info(
            f"  Chunked Downloads: {'ENABLED' if self.use_chunked_downloads else 'DISABLED'}"
        )
        logger.info(
            f"  Optimized Processing: "
            f"{'ENABLED' if self.memory_processor.use_optimized else 'DISABLED'}"
        )
        logger.info("  Parallel Zip Processing: ENABLED")

        # Memory processor stats if available
        if hasattr(self.memory_processor, "optimized_processor"):
            proc_stats = (
                self.memory_processor.optimized_processor.get_processing_summary()
            )
            if proc_stats:
                logger.info(
                    f"  Processing Time: {proc_stats.get('total_time_ms', 0):.0f} ms"
                )
                logger.info(
                    f"  Chunks Processed: {proc_stats.get('chunks_processed', 0)}"
                )

        logger.info("=" * 60)

    def refresh_well_data_enhanced(self, cfg: Dict[str, Any]) -> None:
        """
        Refresh well data (APD) with fresh download using all optimizations.

        Args:
            cfg: Configuration dictionary
        """
        # Check for well data flag (replaces apm flag in enhanced version)
        well_flag = cfg.get("data", {}).get("well", False)
        legacy_apm_flag = cfg.get("data", {}).get("apm", False)

        if well_flag or legacy_apm_flag:
            logger.info("Processing well data (APD) with enhanced optimizations")

            try:
                # URL for well APD data
                well_url = "https://www.data.bsee.gov/Well/Files/APDRawData.zip"

                # Use chunked download if available
                if self.use_chunked_downloads:
                    logger.info("Using chunk-based download with change detection")

                    # Check for changes first
                    change_info = self.chunk_manager.check_remote_changes(
                        well_url, "well"
                    )
                    if not change_info["has_changed"]:
                        logger.info("Well data unchanged - checking cache")
                        self.stats["bytes_cached"] += change_info[
                            "remote_metadata"
                        ].get("content_length", 0)

                    # Download with chunk management
                    zip_data = self.chunk_manager.download_with_chunks(
                        well_url, "well", force_refresh=cfg.get("force_refresh", False)
                    )
                else:
                    # Fallback to direct download
                    logger.info(f"Downloading well data from {well_url}")
                    zip_data = self.web_scraper.download_zip_to_memory(
                        well_url, data_type="well"
                    )

                if zip_data:
                    self.stats["bytes_downloaded"] += len(zip_data)

                    # Process the data with optimized processor (parallel + chunked)
                    logger.info("Processing well data with optimized memory processor")
                    processed_data = self.memory_processor.process_well_data(
                        zip_data, cfg
                    )

                    # Track parallel processing
                    if hasattr(self.memory_processor, "optimized_processor"):
                        stats = (
                            self.memory_processor.optimized_processor.get_processing_summary()
                        )
                        self.stats["parallel_files_processed"] += stats.get(
                            "files_processed", 0
                        )

                    # Save to binary using existing format
                    logger.info("Saving well data to binary format")
                    self._save_well_data_binary(processed_data, cfg)

                    logger.info("Well data refresh completed with all optimizations")
                else:
                    logger.error("Failed to download well data")

            except Exception as e:
                logger.error(f"Error refreshing well data: {str(e)}")

    def refresh_war_data_enhanced(self, cfg: Dict[str, Any]) -> None:
        """
        Refresh WAR (Well Activity Report) data with fresh download using all optimizations.
        WAR files are large (120MB+) so optimizations are especially important.

        Args:
            cfg: Configuration dictionary
        """
        # Check for WAR data flag (new in enhanced version)
        war_flag = cfg.get("data", {}).get("war", False)

        if war_flag:
            logger.info("Processing WAR data (120MB+) with enhanced optimizations")

            try:
                # URL for WAR data
                war_url = "https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip"

                # Use chunked download if available (especially important for large files)
                if self.use_chunked_downloads:
                    logger.info("Using chunk-based download for large WAR file")

                    # Check for changes
                    change_info = self.chunk_manager.check_remote_changes(
                        war_url, "war"
                    )
                    if not change_info["has_changed"]:
                        logger.info(
                            "WAR data unchanged - using cache (saving 120MB+ download)"
                        )
                        self.stats["bytes_cached"] += change_info[
                            "remote_metadata"
                        ].get("content_length", 0)
                        # If unchanged and cached, we can skip processing
                        cached_data = self.chunk_manager._load_from_cache("war")
                        if cached_data:
                            logger.info("WAR data loaded from cache successfully")
                            return

                    # Download with chunk management
                    zip_data = self.chunk_manager.download_with_chunks(
                        war_url, "war", force_refresh=cfg.get("force_refresh", False)
                    )
                else:
                    # Fallback to direct download (will be slow for 120MB+)
                    logger.warning(
                        "Downloading large WAR file without chunking - this may be slow"
                    )
                    logger.info(f"Downloading WAR data from {war_url}")
                    zip_data = self.web_scraper.download_zip_to_memory(
                        war_url, data_type="war"
                    )

                if zip_data:
                    self.stats["bytes_downloaded"] += len(zip_data)
                    logger.info(
                        f"Downloaded {len(zip_data) / (1024*1024):.1f} MB of WAR data"
                    )

                    # Process with optimized processor (REQUIRED for large WAR files)
                    logger.info(
                        "Processing large WAR data with optimized memory processor"
                    )
                    processed_data = self.memory_processor.process_war_data(
                        zip_data, cfg
                    )

                    # Track parallel processing
                    if hasattr(self.memory_processor, "optimized_processor"):
                        stats = (
                            self.memory_processor.optimized_processor.get_processing_summary()
                        )
                        self.stats["parallel_files_processed"] += stats.get(
                            "files_processed", 0
                        )

                    # Save to binary using compatible format
                    logger.info("Saving WAR data to binary format")
                    self._save_war_data_binary(processed_data, cfg)

                    logger.info("WAR data refresh completed with all optimizations")
                else:
                    logger.error("Failed to download WAR data")

            except Exception as e:
                logger.error(f"Error refreshing WAR data: {str(e)}")

    def refresh_production_data_enhanced(self, cfg: Dict[str, Any]) -> None:
        """
        Refresh production data with fresh download using all optimizations.

        Args:
            cfg: Configuration dictionary
        """
        production_flag = cfg.get("data", {}).get("production", False)

        if production_flag:
            logger.info("Processing production data with enhanced optimizations")

            try:
                # URL for production data
                prod_url = (
                    "https://www.data.bsee.gov/Production/Files/ProductionRawData.zip"
                )

                # Use chunked download if available
                if self.use_chunked_downloads:
                    logger.info("Using chunk-based download with change detection")

                    # Check for changes
                    change_info = self.chunk_manager.check_remote_changes(
                        prod_url, "production"
                    )
                    if not change_info["has_changed"]:
                        logger.info("Production data unchanged - checking cache")
                        self.stats["bytes_cached"] += change_info[
                            "remote_metadata"
                        ].get("content_length", 0)

                    # Download with chunk management
                    zip_data = self.chunk_manager.download_with_chunks(
                        prod_url,
                        "production",
                        force_refresh=cfg.get("force_refresh", False),
                    )
                else:
                    # Fallback to direct download
                    logger.info(f"Downloading production data from {prod_url}")
                    zip_data = self.web_scraper.download_zip_to_memory(
                        prod_url, data_type="production"
                    )

                if zip_data:
                    self.stats["bytes_downloaded"] += len(zip_data)

                    # Process with optimized processor (parallel + chunked)
                    logger.info(
                        "Processing production data with optimized memory processor"
                    )
                    processed_data = self.memory_processor.process_production_data(
                        zip_data, cfg
                    )

                    # Track parallel processing
                    if hasattr(self.memory_processor, "optimized_processor"):
                        stats = (
                            self.memory_processor.optimized_processor.get_processing_summary()
                        )
                        self.stats["parallel_files_processed"] += stats.get(
                            "files_processed", 0
                        )

                    # Save to binary using existing format
                    logger.info("Saving production data to binary format")
                    self._save_production_data_binary(processed_data, cfg)

                    logger.info(
                        "Production data refresh completed with all optimizations"
                    )
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
            bin_path = (
                cfg.get("parameters", {})
                .get("filepath", {})
                .get("apm", {})
                .get("bin", "data/modules/bsee/bin/apd")
            )

            # Convert to absolute path relative to project root
            # Find project root by looking for pyproject.toml
            current_dir = Path(__file__).parent
            while current_dir != current_dir.parent:
                if (current_dir / "pyproject.toml").exists():
                    project_root = current_dir
                    break
                current_dir = current_dir.parent
            else:
                # Fallback to assuming we're in the standard structure
                project_root = Path(__file__).parent.parent.parent.parent.parent.parent

            # Resolve path relative to project root
            abs_bin_path = project_root / bin_path

            # Ensure directory exists
            abs_bin_path.mkdir(parents=True, exist_ok=True)

            # Save using compatible format
            self.memory_processor.save_to_binary(data, str(abs_bin_path), "well_data")
            logger.info(f"Well data saved to {abs_bin_path}")

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
            bin_path = (
                cfg.get("parameters", {})
                .get("filepath", {})
                .get("war", {})
                .get("bin", "data/modules/bsee/bin/war")
            )

            # Convert to absolute path relative to project root
            # Find project root by looking for pyproject.toml
            current_dir = Path(__file__).parent
            while current_dir != current_dir.parent:
                if (current_dir / "pyproject.toml").exists():
                    project_root = current_dir
                    break
                current_dir = current_dir.parent
            else:
                # Fallback to assuming we're in the standard structure
                project_root = Path(__file__).parent.parent.parent.parent.parent.parent

            # Resolve path relative to project root
            abs_bin_path = project_root / bin_path

            # Ensure directory exists
            abs_bin_path.mkdir(parents=True, exist_ok=True)

            # Save using compatible format
            self.memory_processor.save_to_binary(data, str(abs_bin_path), "war_data")
            logger.info(f"WAR data saved to {abs_bin_path}")

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
            bin_path = (
                cfg.get("parameters", {})
                .get("filepath", {})
                .get("production", {})
                .get("bin", "data/modules/bsee/bin/production_raw")
            )

            # Convert to absolute path relative to project root
            # Find project root by looking for pyproject.toml
            current_dir = Path(__file__).parent
            while current_dir != current_dir.parent:
                if (current_dir / "pyproject.toml").exists():
                    project_root = current_dir
                    break
                current_dir = current_dir.parent
            else:
                # Fallback to assuming we're in the standard structure
                project_root = Path(__file__).parent.parent.parent.parent.parent.parent

            # Resolve path relative to project root
            abs_bin_path = project_root / bin_path

            # Ensure directory exists
            abs_bin_path.mkdir(parents=True, exist_ok=True)

            # Save using compatible format
            self.memory_processor.save_to_binary(
                data, str(abs_bin_path), "production_data"
            )
            logger.info(f"Production data saved to {abs_bin_path}")

        except Exception as e:
            logger.error(f"Error saving production data binary: {str(e)}")

    def refresh_platform_data_enhanced(self, cfg: Dict[str, Any]) -> None:
        """Refresh platform structure data with fresh download."""
        platform_flag = cfg.get("data", {}).get("platform", False)
        if platform_flag:
            logger.info(
                "Processing platform structure data with enhanced optimizations"
            )
            try:
                platform_url = (
                    "https://www.data.bsee.gov/Platform/Files/PlatStrucRawData.zip"
                )
                if self.use_chunked_downloads:
                    logger.info("Using chunk-based download with change detection")
                    change_info = self.chunk_manager.check_remote_changes(
                        platform_url, "platform"
                    )
                    if not change_info["has_changed"]:
                        logger.info("Platform data unchanged - checking cache")
                        self.stats["bytes_cached"] += change_info[
                            "remote_metadata"
                        ].get("content_length", 0)
                    zip_data = self.chunk_manager.download_with_chunks(
                        platform_url,
                        "platform",
                        force_refresh=cfg.get("force_refresh", False),
                    )
                else:
                    logger.info(f"Downloading platform data from {platform_url}")
                    zip_data = self.web_scraper.download_zip_to_memory(
                        platform_url, data_type="platform"
                    )
                if zip_data:
                    self.stats["bytes_downloaded"] += len(zip_data)
                    logger.info("Processing platform data with memory processor")
                    processed_data = self.memory_processor.process_platform_data(
                        zip_data, cfg
                    )
                    logger.info("Saving platform data to binary format")
                    self._save_platform_data_binary(processed_data, cfg)
                    logger.info("Platform data refresh completed")
                else:
                    logger.error("Failed to download platform data")
            except Exception as e:
                logger.error(f"Error refreshing platform data: {str(e)}")

    def refresh_pipeline_permit_data_enhanced(self, cfg: Dict[str, Any]) -> None:
        """Refresh pipeline permit data with fresh download."""
        pipeline_permit_flag = cfg.get("data", {}).get("pipeline_permit", False)
        if pipeline_permit_flag:
            logger.info("Processing pipeline permit data with enhanced optimizations")
            try:
                pipeline_permit_url = (
                    "https://www.data.bsee.gov/Pipeline/Files/PipePermRawData.zip"
                )
                if self.use_chunked_downloads:
                    logger.info("Using chunk-based download with change detection")
                    change_info = self.chunk_manager.check_remote_changes(
                        pipeline_permit_url, "pipeline_permit"
                    )
                    if not change_info["has_changed"]:
                        logger.info("Pipeline permit data unchanged - checking cache")
                        self.stats["bytes_cached"] += change_info[
                            "remote_metadata"
                        ].get("content_length", 0)
                    zip_data = self.chunk_manager.download_with_chunks(
                        pipeline_permit_url,
                        "pipeline_permit",
                        force_refresh=cfg.get("force_refresh", False),
                    )
                else:
                    logger.info(
                        f"Downloading pipeline permit data from {pipeline_permit_url}"
                    )
                    zip_data = self.web_scraper.download_zip_to_memory(
                        pipeline_permit_url, data_type="pipeline_permit"
                    )
                if zip_data:
                    self.stats["bytes_downloaded"] += len(zip_data)
                    logger.info("Processing pipeline permit data with memory processor")
                    processed_data = self.memory_processor.process_pipeline_permit_data(
                        zip_data, cfg
                    )
                    logger.info("Saving pipeline permit data to binary format")
                    self._save_pipeline_permit_data_binary(processed_data, cfg)
                    logger.info("Pipeline permit data refresh completed")
                else:
                    logger.error("Failed to download pipeline permit data")
            except Exception as e:
                logger.error(f"Error refreshing pipeline permit data: {str(e)}")

    def refresh_deepwater_structure_data_enhanced(self, cfg: Dict[str, Any]) -> None:
        """Refresh deepwater (permitted) structure data with fresh download."""
        deepwater_flag = cfg.get("data", {}).get("deepwater_structure", False)
        if deepwater_flag:
            logger.info(
                "Processing deepwater structure data with enhanced optimizations"
            )
            try:
                deepwater_url = (
                    "https://www.data.bsee.gov/Platform/Files/PermStrucRawData.zip"
                )
                if self.use_chunked_downloads:
                    logger.info("Using chunk-based download with change detection")
                    change_info = self.chunk_manager.check_remote_changes(
                        deepwater_url, "deepwater_structure"
                    )
                    if not change_info["has_changed"]:
                        logger.info(
                            "Deepwater structure data unchanged - checking cache"
                        )
                        self.stats["bytes_cached"] += change_info[
                            "remote_metadata"
                        ].get("content_length", 0)
                    zip_data = self.chunk_manager.download_with_chunks(
                        deepwater_url,
                        "deepwater_structure",
                        force_refresh=cfg.get("force_refresh", False),
                    )
                else:
                    logger.info(
                        f"Downloading deepwater structure data from {deepwater_url}"
                    )
                    zip_data = self.web_scraper.download_zip_to_memory(
                        deepwater_url, data_type="deepwater_structure"
                    )
                if zip_data:
                    self.stats["bytes_downloaded"] += len(zip_data)
                    logger.info(
                        "Processing deepwater structure data with memory processor"
                    )
                    processed_data = (
                        self.memory_processor.process_deepwater_structure_data(
                            zip_data, cfg
                        )
                    )
                    logger.info("Saving deepwater structure data to binary format")
                    self._save_deepwater_structure_data_binary(processed_data, cfg)
                    logger.info("Deepwater structure data refresh completed")
                else:
                    logger.error("Failed to download deepwater structure data")
            except Exception as e:
                logger.error(f"Error refreshing deepwater structure data: {str(e)}")

    def refresh_pipeline_location_data_enhanced(self, cfg: Dict[str, Any]) -> None:
        """Refresh pipeline location data with fresh download."""
        pipeline_loc_flag = cfg.get("data", {}).get("pipeline_location", False)
        if pipeline_loc_flag:
            logger.info("Processing pipeline location data with enhanced optimizations")
            try:
                pipeline_loc_url = (
                    "https://www.data.bsee.gov/Pipeline/Files/PipeLocAllRawData.zip"
                )
                if self.use_chunked_downloads:
                    logger.info("Using chunk-based download with change detection")
                    change_info = self.chunk_manager.check_remote_changes(
                        pipeline_loc_url, "pipeline_location"
                    )
                    if not change_info["has_changed"]:
                        logger.info("Pipeline location data unchanged - checking cache")
                        self.stats["bytes_cached"] += change_info[
                            "remote_metadata"
                        ].get("content_length", 0)
                    zip_data = self.chunk_manager.download_with_chunks(
                        pipeline_loc_url,
                        "pipeline_location",
                        force_refresh=cfg.get("force_refresh", False),
                    )
                else:
                    logger.info(
                        f"Downloading pipeline location data from {pipeline_loc_url}"
                    )
                    zip_data = self.web_scraper.download_zip_to_memory(
                        pipeline_loc_url, data_type="pipeline_location"
                    )
                if zip_data:
                    self.stats["bytes_downloaded"] += len(zip_data)
                    logger.info(
                        "Processing pipeline location data with memory processor"
                    )
                    processed_data = (
                        self.memory_processor.process_pipeline_location_data(
                            zip_data, cfg
                        )
                    )
                    logger.info("Saving pipeline location data to binary format")
                    self._save_pipeline_location_data_binary(processed_data, cfg)
                    logger.info("Pipeline location data refresh completed")
                else:
                    logger.error("Failed to download pipeline location data")
            except Exception as e:
                logger.error(f"Error refreshing pipeline location data: {str(e)}")

    def _save_platform_data_binary(self, data: Any, cfg: Dict[str, Any]) -> None:
        """Save platform data to binary format."""
        try:
            bin_path = (
                cfg.get("parameters", {})
                .get("filepath", {})
                .get("platform", {})
                .get("bin", "data/modules/bsee/bin/platform")
            )
            current_dir = Path(__file__).parent
            while current_dir != current_dir.parent:
                if (current_dir / "pyproject.toml").exists():
                    project_root = current_dir
                    break
                current_dir = current_dir.parent
            else:
                project_root = Path(__file__).parent.parent.parent.parent.parent.parent
            abs_bin_path = project_root / bin_path
            abs_bin_path.mkdir(parents=True, exist_ok=True)
            self.memory_processor.save_to_binary(
                data, str(abs_bin_path), "platform_data"
            )
            logger.info(f"Platform data saved to {abs_bin_path}")
        except Exception as e:
            logger.error(f"Error saving platform data binary: {str(e)}")

    def _save_pipeline_permit_data_binary(self, data: Any, cfg: Dict[str, Any]) -> None:
        """Save pipeline permit data to binary format."""
        try:
            bin_path = (
                cfg.get("parameters", {})
                .get("filepath", {})
                .get("pipeline_permit", {})
                .get("bin", "data/modules/bsee/bin/pipeline_permit")
            )
            current_dir = Path(__file__).parent
            while current_dir != current_dir.parent:
                if (current_dir / "pyproject.toml").exists():
                    project_root = current_dir
                    break
                current_dir = current_dir.parent
            else:
                project_root = Path(__file__).parent.parent.parent.parent.parent.parent
            abs_bin_path = project_root / bin_path
            abs_bin_path.mkdir(parents=True, exist_ok=True)
            self.memory_processor.save_to_binary(
                data, str(abs_bin_path), "pipeline_permit_data"
            )
            logger.info(f"Pipeline permit data saved to {abs_bin_path}")
        except Exception as e:
            logger.error(f"Error saving pipeline permit data binary: {str(e)}")

    def _save_deepwater_structure_data_binary(
        self, data: Any, cfg: Dict[str, Any]
    ) -> None:
        """Save deepwater structure data to binary format."""
        try:
            bin_path = (
                cfg.get("parameters", {})
                .get("filepath", {})
                .get("deepwater_structure", {})
                .get("bin", "data/modules/bsee/bin/deepwater_structure")
            )
            current_dir = Path(__file__).parent
            while current_dir != current_dir.parent:
                if (current_dir / "pyproject.toml").exists():
                    project_root = current_dir
                    break
                current_dir = current_dir.parent
            else:
                project_root = Path(__file__).parent.parent.parent.parent.parent.parent
            abs_bin_path = project_root / bin_path
            abs_bin_path.mkdir(parents=True, exist_ok=True)
            self.memory_processor.save_to_binary(
                data, str(abs_bin_path), "deepwater_structure_data"
            )
            logger.info(f"Deepwater structure data saved to {abs_bin_path}")
        except Exception as e:
            logger.error(f"Error saving deepwater structure data binary: {str(e)}")

    def _save_pipeline_location_data_binary(
        self, data: Any, cfg: Dict[str, Any]
    ) -> None:
        """Save pipeline location data to binary format."""
        try:
            bin_path = (
                cfg.get("parameters", {})
                .get("filepath", {})
                .get("pipeline_location", {})
                .get("bin", "data/modules/bsee/bin/pipeline_location")
            )
            current_dir = Path(__file__).parent
            while current_dir != current_dir.parent:
                if (current_dir / "pyproject.toml").exists():
                    project_root = current_dir
                    break
                current_dir = current_dir.parent
            else:
                project_root = Path(__file__).parent.parent.parent.parent.parent.parent
            abs_bin_path = project_root / bin_path
            abs_bin_path.mkdir(parents=True, exist_ok=True)
            self.memory_processor.save_to_binary(
                data, str(abs_bin_path), "pipeline_location_data"
            )
            logger.info(f"Pipeline location data saved to {abs_bin_path}")
        except Exception as e:
            logger.error(f"Error saving pipeline location data binary: {str(e)}")
