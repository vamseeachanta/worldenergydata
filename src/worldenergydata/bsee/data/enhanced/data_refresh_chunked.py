"""
Enhanced BSEE Data Refresh with Chunk-based Change Detection

This module extends the enhanced data refresh functionality with intelligent
chunk management to avoid re-downloading unchanged data portions.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

# Import chunk manager from cache module
from worldenergydata.bsee.data.cache import ChunkManager
from worldenergydata.bsee.data.config import ConfigRouter
from worldenergydata.bsee.data.processors import MemoryProcessor
from worldenergydata.bsee.data.scrapers import BSEEWebScraper
from worldenergydata.common.data_resolver import get_module_data_safe

_BSEE_BIN = str(get_module_data_safe("bsee") / "bin")

# Import existing components


class DataRefreshChunked:
    """
    Advanced data refresh implementation with chunk-based optimization.

    Features:
    - HTTP HEAD checks for change detection
    - ETag and Last-Modified tracking
    - Chunk-level checksums
    - Incremental downloads
    - Smart caching with TTL
    - Bandwidth optimization
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the chunked data refresh system.

        Args:
            cache_dir: Optional cache directory for chunk storage
        """
        self.chunk_manager = ChunkManager(cache_dir)
        self.web_scraper = BSEEWebScraper()
        self.memory_processor = MemoryProcessor()
        self.config_router = ConfigRouter()

        # Statistics tracking
        self.stats = {
            "bytes_downloaded": 0,
            "bytes_cached": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "chunks_reused": 0,
            "chunks_downloaded": 0,
            "start_time": None,
            "end_time": None,
        }

        logger.info("Chunked Data Refresh System initialized")

    def router(self, cfg: Dict[str, Any]) -> tuple:
        """
        Main routing method with chunk optimization.

        Args:
            cfg: Configuration dictionary from YAML

        Returns:
            Tuple of (cfg, None) for compatibility
        """
        logger.info("Starting chunked data refresh process")

        # Start timing
        self.stats["start_time"] = datetime.now()

        # Check configuration
        enhanced_mode = self.config_router.is_enhanced_mode(cfg)
        chunked_mode = cfg.get("chunked_refresh", True)  # Default to chunked mode

        if not enhanced_mode:
            logger.warning(
                "Enhanced mode not enabled, chunked refresh requires enhanced mode"
            )
            return cfg, None

        if not chunked_mode:
            logger.info("Chunked mode disabled in configuration")
            return cfg, None

        # Check data type flags
        well_flag = cfg.get("data", {}).get("well", False)
        war_flag = cfg.get("data", {}).get("war", False)
        production_flag = cfg.get("data", {}).get("production", False)

        if well_flag or war_flag or production_flag:
            logger.info("Processing data with chunk optimization")

            # Process each data type
            if well_flag:
                self._refresh_well_data_chunked(cfg)

            if war_flag:
                self._refresh_war_data_chunked(cfg)

            if production_flag:
                self._refresh_production_data_chunked(cfg)

            # End timing
            self.stats["end_time"] = datetime.now()

            # Report statistics
            self._report_statistics()

            logger.info("Chunked data refresh completed successfully")
        else:
            logger.info("No data type flags set, skipping refresh")

        return cfg, None

    def _refresh_well_data_chunked(self, cfg: Dict[str, Any]) -> None:
        """
        Refresh well data with chunk optimization.

        Args:
            cfg: Configuration dictionary
        """
        logger.info("Refreshing well data with chunk optimization")

        try:
            well_url = "https://www.data.bsee.gov/Well/Files/APDRawData.zip"

            # Check for changes first
            change_info = self.chunk_manager.check_remote_changes(well_url, "well")

            if not change_info["has_changed"]:
                logger.info("Well data unchanged, checking cache")
                self.stats["cache_hits"] += 1

                # Try to load from cache
                cached_data = self._load_cached_binary("well", cfg)
                if cached_data:
                    logger.info("Using cached well data")
                    return
            else:
                self.stats["cache_misses"] += 1

            # Download with chunk management
            force_refresh = cfg.get("force_refresh", False)
            zip_data = self.chunk_manager.download_with_chunks(
                well_url, "well", force_refresh
            )

            if zip_data:
                # Track download size
                self.stats["bytes_downloaded"] += len(zip_data)

                # Process the data
                logger.info("Processing well data")
                processed_data = self.memory_processor.process_well_data(zip_data, cfg)

                # Save to binary
                logger.info("Saving well data to binary format")
                self._save_well_data_binary(processed_data, cfg)

                logger.info("Well data refresh completed")
            else:
                logger.error("Failed to download well data")

        except Exception as e:
            logger.error(f"Error refreshing well data: {str(e)}")

    def _refresh_production_data_chunked(self, cfg: Dict[str, Any]) -> None:
        """
        Refresh production data with chunk optimization.

        Args:
            cfg: Configuration dictionary
        """
        logger.info("Refreshing production data with chunk optimization")

        try:
            prod_url = (
                "https://www.data.bsee.gov/Production/Files/ProductionRawData.zip"
            )

            # Check for changes
            change_info = self.chunk_manager.check_remote_changes(
                prod_url, "production"
            )

            if not change_info["has_changed"]:
                logger.info("Production data unchanged, checking cache")
                self.stats["cache_hits"] += 1

                # Try to load from cache
                cached_data = self._load_cached_binary("production", cfg)
                if cached_data:
                    logger.info("Using cached production data")
                    return
            else:
                self.stats["cache_misses"] += 1

            # Download with chunk management
            force_refresh = cfg.get("force_refresh", False)
            zip_data = self.chunk_manager.download_with_chunks(
                prod_url, "production", force_refresh
            )

            if zip_data:
                # Track download size
                self.stats["bytes_downloaded"] += len(zip_data)

                # Check for incremental processing
                if cfg.get("incremental_update", True):
                    # Load previous data for incremental update
                    previous_data = self._load_previous_dataframe("production", cfg)

                    # Process incrementally
                    processed_data = self.chunk_manager.process_incremental_changes(
                        zip_data, "production", previous_data
                    )
                else:
                    # Full processing
                    processed_data = self.memory_processor.process_production_data(
                        zip_data, cfg
                    )

                # Save to binary
                logger.info("Saving production data to binary format")
                self._save_production_data_binary(processed_data, cfg)

                logger.info("Production data refresh completed")
            else:
                logger.error("Failed to download production data")

        except Exception as e:
            logger.error(f"Error refreshing production data: {str(e)}")

    def _refresh_war_data_chunked(self, cfg: Dict[str, Any]) -> None:
        """
        Refresh WAR data with chunk optimization.

        This is especially important for WAR data which can be 120MB+.

        Args:
            cfg: Configuration dictionary
        """
        logger.info("Refreshing WAR data with chunk optimization (large file)")

        try:
            war_url = "https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip"

            # Check for changes
            change_info = self.chunk_manager.check_remote_changes(war_url, "war")

            if not change_info["has_changed"]:
                logger.info("WAR data unchanged, checking cache")
                self.stats["cache_hits"] += 1

                # Try to load from cache
                cached_data = self._load_cached_binary("war", cfg)
                if cached_data:
                    logger.info("Using cached WAR data")
                    return
            else:
                self.stats["cache_misses"] += 1
                logger.info(f"WAR data changed: {change_info['change_reasons']}")

            # For large WAR files, always use chunked download
            logger.info("Starting chunked download for large WAR file")

            force_refresh = cfg.get("force_refresh", False)
            zip_data = self.chunk_manager.download_with_chunks(
                war_url, "war", force_refresh
            )

            if zip_data:
                # Track download size
                self.stats["bytes_downloaded"] += len(zip_data)
                logger.info(
                    f"Downloaded {len(zip_data) / (1024*1024):.2f} MB of WAR data"
                )

                # Process the data (always use optimized processor for WAR)
                logger.info("Processing large WAR data with optimized processor")
                processed_data = self.memory_processor.process_war_data(zip_data, cfg)

                # Save to binary
                logger.info("Saving WAR data to binary format")
                self._save_war_data_binary(processed_data, cfg)

                logger.info("WAR data refresh completed")
            else:
                logger.error("Failed to download WAR data")

        except Exception as e:
            logger.error(f"Error refreshing WAR data: {str(e)}")

    def _save_well_data_binary(self, data: Any, cfg: Dict[str, Any]) -> None:
        """Save well data to binary format."""
        try:
            bin_path = self._get_binary_path(cfg, "well")
            self.memory_processor.save_to_binary(data, str(bin_path), "well_data")
            logger.info(f"Well data saved to {bin_path}")
        except Exception as e:
            logger.error(f"Error saving well data binary: {str(e)}")

    def _save_production_data_binary(self, data: Any, cfg: Dict[str, Any]) -> None:
        """Save production data to binary format."""
        try:
            bin_path = self._get_binary_path(cfg, "production")
            self.memory_processor.save_to_binary(data, str(bin_path), "production_data")
            logger.info(f"Production data saved to {bin_path}")
        except Exception as e:
            logger.error(f"Error saving production data binary: {str(e)}")

    def _save_war_data_binary(self, data: Any, cfg: Dict[str, Any]) -> None:
        """Save WAR data to binary format."""
        try:
            bin_path = self._get_binary_path(cfg, "war")
            self.memory_processor.save_to_binary(data, str(bin_path), "war_data")
            logger.info(f"WAR data saved to {bin_path}")
        except Exception as e:
            logger.error(f"Error saving WAR data binary: {str(e)}")

    def _get_binary_path(self, cfg: Dict[str, Any], data_type: str) -> Path:
        """Get the binary output path for a data type."""
        # Map data types to config paths
        path_map = {
            "well": cfg.get("parameters", {})
            .get("filepath", {})
            .get("apm", {})
            .get("bin", f"{_BSEE_BIN}/apd"),
            "production": cfg.get("parameters", {})
            .get("filepath", {})
            .get("production", {})
            .get("bin", f"{_BSEE_BIN}/production_raw"),
            "war": cfg.get("parameters", {})
            .get("filepath", {})
            .get("war", {})
            .get("bin", f"{_BSEE_BIN}/war"),
        }

        bin_path = path_map.get(data_type, f"{_BSEE_BIN}/{data_type}")

        # Find project root
        current_dir = Path(__file__).parent
        while current_dir != current_dir.parent:
            if (current_dir / "pyproject.toml").exists():
                project_root = current_dir
                break
            current_dir = current_dir.parent
        else:
            project_root = Path(__file__).parent.parent.parent.parent.parent.parent

        # Resolve path
        abs_bin_path = project_root / bin_path
        abs_bin_path.mkdir(parents=True, exist_ok=True)

        return abs_bin_path

    def _load_cached_binary(self, data_type: str, cfg: Dict[str, Any]) -> Optional[Any]:
        """
        Try to load data from cached binary files.

        Args:
            data_type: Type of data to load
            cfg: Configuration dictionary

        Returns:
            Cached data or None
        """
        try:
            bin_path = self._get_binary_path(cfg, data_type)

            # Check if binary files exist
            bin_files = list(bin_path.glob("*.bin"))
            if not bin_files:
                return None

            # Check age of files
            from datetime import datetime, timedelta

            for bin_file in bin_files:
                file_age = datetime.now() - datetime.fromtimestamp(
                    bin_file.stat().st_mtime
                )
                if file_age > timedelta(hours=24):  # Configurable TTL
                    logger.info(f"Binary cache expired for {bin_file.name}")
                    return None

            logger.info(f"Found {len(bin_files)} cached binary files for {data_type}")
            return True  # Indicate cache exists

        except Exception as e:
            logger.error(f"Error checking cached binary: {str(e)}")
            return None

    def _load_previous_dataframe(
        self, data_type: str, cfg: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Load previous DataFrame for incremental processing.

        Args:
            data_type: Type of data
            cfg: Configuration dictionary

        Returns:
            Previous DataFrame or None
        """
        try:
            import pickle

            bin_path = self._get_binary_path(cfg, data_type)

            # Find the most recent binary file
            bin_files = sorted(
                bin_path.glob("*.bin"), key=lambda x: x.stat().st_mtime, reverse=True
            )

            if bin_files:
                with open(bin_files[0], "rb") as f:
                    return pickle.load(
                        f
                    )  # nosec B301 - trusted pipeline-generated local .bin/.pkl (BSEE), not untrusted input  # noqa: E501

            return None

        except Exception as e:
            logger.error(f"Error loading previous DataFrame: {str(e)}")
            return None

    def _report_statistics(self):
        """Report refresh statistics."""
        if self.stats["start_time"] and self.stats["end_time"]:
            duration = (
                self.stats["end_time"] - self.stats["start_time"]
            ).total_seconds()
        else:
            duration = 0

        # Get cache statistics
        cache_stats = self.chunk_manager.get_cache_stats()

        logger.info("=" * 60)
        logger.info("CHUNKED REFRESH STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Duration: {duration:.1f} seconds")
        logger.info(
            f"Bytes downloaded: {self.stats['bytes_downloaded'] / (1024*1024):.2f} MB"
        )
        logger.info(f"Cache hits: {self.stats['cache_hits']}")
        logger.info(f"Cache misses: {self.stats['cache_misses']}")

        if self.stats["cache_hits"] + self.stats["cache_misses"] > 0:
            hit_rate = (
                self.stats["cache_hits"]
                / (self.stats["cache_hits"] + self.stats["cache_misses"])
            ) * 100
            logger.info(f"Cache hit rate: {hit_rate:.1f}%")

        logger.info(f"Cache size: {cache_stats['total_size_mb']:.2f} MB")
        logger.info(f"Cached chunks: {cache_stats['chunk_count']}")

        if duration > 0:
            speed_mbps = (self.stats["bytes_downloaded"] / (1024 * 1024)) / duration
            logger.info(f"Average download speed: {speed_mbps:.2f} MB/s")

        # Calculate bandwidth savings
        if self.stats["cache_hits"] > 0:
            # Estimate saved bandwidth (rough estimate based on typical file sizes)
            estimated_savings_mb = self.stats["cache_hits"] * 50  # Assume 50MB average
            logger.info(f"Estimated bandwidth saved: {estimated_savings_mb:.0f} MB")

        logger.info("=" * 60)

    def clear_cache(self, data_type: Optional[str] = None):
        """
        Clear cached data.

        Args:
            data_type: Specific data type to clear, or None for all
        """
        self.chunk_manager.clear_cache(data_type)
        logger.info(f"Cache cleared for {data_type if data_type else 'all data types'}")

    def validate_remote_sources(self) -> Dict[str, Any]:
        """
        Validate all remote data sources.

        Returns:
            Dictionary with validation results
        """
        logger.info("Validating remote data sources")

        urls = {
            "well": "https://www.data.bsee.gov/Well/Files/APDRawData.zip",
            "production": "https://www.data.bsee.gov/Production/Files/ProductionRawData.zip",
            "war": "https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip",
        }

        results = {}
        for data_type, url in urls.items():
            change_info = self.chunk_manager.check_remote_changes(url, data_type)
            file_info = self.web_scraper.get_file_info(url)

            results[data_type] = {
                "url": url,
                "accessible": file_info.get("error") is None,
                "size_mb": file_info.get("size_mb", 0),
                "last_modified": file_info.get("last_modified", "unknown"),
                "has_cached_version": data_type in self.chunk_manager.metadata,
                "cache_current": not change_info["has_changed"],
            }

            status = "✓" if results[data_type]["accessible"] else "✗"
            cache_status = (
                "(cached)"
                if results[data_type]["cache_current"]
                else (
                    "(outdated)"
                    if results[data_type]["has_cached_version"]
                    else "(no cache)"
                )
            )

            logger.info(
                f"{data_type}: {status} {results[data_type]['size_mb']:.1f} MB {cache_status}"
            )

        return results
