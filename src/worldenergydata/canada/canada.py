# ABOUTME: Main Canada module router orchestrating AER and BCER data collection
# ABOUTME: Follows BSEE/SODIR architectural pattern for consistent module interface

"""
Main Canada module router implementation.

This module follows the BSEE/SODIR architectural pattern to provide a consistent
interface for Canadian oil and gas data collection and analysis.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class Canada:
    """
    Main Canada module class implementing the router pattern.

    This class orchestrates data collection from Alberta Energy Regulator (AER)
    and BC Energy Regulator (BCER) APIs, integrating with existing WorldEnergyData
    analysis tools.

    Attributes:
        module_name: Module identifier used in configuration
        aer_instance: Lazy-loaded AER submodule instance
        bcer_instance: Lazy-loaded BCER submodule instance
        analysis_instance: Lazy-loaded analysis component instance
    """

    def __init__(self):
        """Initialize Canada module."""
        self.module_name = "canada"
        self.aer_instance = None
        self.bcer_instance = None
        self.analysis_instance = None
        self._initialize_components()

    def _initialize_components(self):
        """Initialize data and analysis components lazily."""
        # Components will be imported when needed to avoid circular imports
        pass

    def router(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main router method following BSEE/SODIR pattern.

        Args:
            cfg: Configuration dictionary containing:
                - module: Module name (should be 'canada')
                - provinces: List of provinces to collect data from ['ab', 'bc']
                - data_types: List of data types to collect
                - api: API configuration (rate_limit, cache_ttl)
                - output: Output configuration (directory, format)
                - analysis: Analysis configuration (optional)

        Returns:
            Updated configuration dictionary with results

        Raises:
            ValueError: If configuration is invalid
            CanadaError: If data collection fails
        """
        # Validate configuration first (outside try block for proper error propagation)
        self._validate_config(cfg)

        try:
            # Initialize module section in config
            if "basename" not in cfg:
                cfg["basename"] = self.module_name

            cfg[cfg["basename"]] = {}
            cfg[cfg["basename"]].update({"data": cfg.get("data", {}).copy()})
            cfg[cfg["basename"]].update({"analysis": cfg.get("analysis", {}).copy()})

            # Determine which provinces to collect data from
            provinces = cfg.get("provinces", ["ab", "bc"])
            collected_data = {}

            # Route to AER if Alberta is requested
            if "ab" in provinces or "alberta" in provinces:
                logger.info("Starting AER (Alberta) data collection")
                collected_data["aer"] = self._collect_aer_data(cfg)

            # Route to BCER if BC is requested
            if "bc" in provinces or "british_columbia" in provinces:
                logger.info("Starting BCER (British Columbia) data collection")
                collected_data["bcer"] = self._collect_bcer_data(cfg)

            # Route to analysis if configured
            if cfg.get("analysis", {}).get("enabled", False):
                if self.analysis_instance is None:
                    from .analysis import CanadaAnalysis

                    self.analysis_instance = CanadaAnalysis()

                logger.info("Running Canada cross-provincial analysis")
                cfg = self.analysis_instance.router(cfg, collected_data)

            # Add status information
            cfg[cfg["basename"]]["status"] = "completed"
            cfg[cfg["basename"]]["provinces_collected"] = list(collected_data.keys())
            cfg[cfg["basename"]]["data_collected"] = self._summarize_data(
                collected_data
            )

            logger.info("Canada module processing completed successfully")
            return cfg

        except Exception as e:
            logger.error(f"Error in Canada router: {str(e)}")
            if "basename" in cfg and cfg["basename"] in cfg:
                cfg[cfg["basename"]]["status"] = "error"
                cfg[cfg["basename"]]["error"] = str(e)
            raise

    def _collect_aer_data(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect data from Alberta Energy Regulator.

        Args:
            cfg: Configuration dictionary

        Returns:
            Dictionary containing collected AER data
        """
        if self.aer_instance is None:
            from .aer import AER

            self.aer_instance = AER()

        return self.aer_instance.router(cfg)

    def _collect_bcer_data(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect data from BC Energy Regulator.

        Args:
            cfg: Configuration dictionary

        Returns:
            Dictionary containing collected BCER data
        """
        if self.bcer_instance is None:
            from .bcer import BCER

            self.bcer_instance = BCER()

        return self.bcer_instance.router(cfg)

    def _summarize_data(self, collected_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Summarize collected data for status reporting.

        Args:
            collected_data: Dictionary of collected data by province

        Returns:
            Dictionary with counts of data items by type
        """
        summary = {}
        for province, data in collected_data.items():
            if isinstance(data, dict):
                for data_type, items in data.items():
                    key = f"{province}_{data_type}"
                    if isinstance(items, list):
                        summary[key] = len(items)
                    elif isinstance(items, dict):
                        summary[key] = len(items)
                    else:
                        summary[key] = 1
        return summary

    def _validate_config(self, cfg: Dict[str, Any]) -> None:
        """
        Validate configuration dictionary.

        Args:
            cfg: Configuration dictionary to validate

        Raises:
            ValueError: If configuration is invalid
        """
        if not cfg:
            raise ValueError("Configuration cannot be empty")

        # Validate module name if specified
        if "module" in cfg and cfg["module"] != self.module_name:
            logger.warning(
                f"Module mismatch: expected '{self.module_name}', got '{cfg['module']}'"
            )

        # Validate provinces if specified
        if "provinces" in cfg:
            valid_provinces = ["ab", "alberta", "bc", "british_columbia"]
            invalid_provinces = [
                p for p in cfg["provinces"] if p.lower() not in valid_provinces
            ]
            if invalid_provinces:
                raise ValueError(
                    f"Invalid provinces: {invalid_provinces}. "
                    f"Valid provinces: {valid_provinces}"
                )

        # Validate data types if specified
        if "data_types" in cfg:
            valid_types = [
                "wells",
                "production",
                "facilities",
                "licenses",
                "operators",
                "pools",
            ]
            invalid_types = [dt for dt in cfg["data_types"] if dt not in valid_types]
            if invalid_types:
                raise ValueError(
                    f"Invalid data types: {invalid_types}. Valid types: {valid_types}"
                )

        # Validate API configuration if specified
        if "api" in cfg:
            api_config = cfg["api"]
            if "rate_limit" in api_config:
                if (
                    not isinstance(api_config["rate_limit"], (int, float))
                    or api_config["rate_limit"] <= 0
                ):
                    raise ValueError(f"Invalid rate limit: {api_config['rate_limit']}")

            if "cache_ttl" in api_config:
                if (
                    not isinstance(api_config["cache_ttl"], (int, float))
                    or api_config["cache_ttl"] < 0
                ):
                    raise ValueError(f"Invalid cache TTL: {api_config['cache_ttl']}")

        logger.debug("Configuration validated successfully")

    def get_well_by_uwi(self, uwi: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve well data by Unique Well Identifier.

        Args:
            uwi: Canadian Unique Well Identifier (UWI)

        Returns:
            Well data dictionary or None if not found
        """
        from .common.uwi import parse_uwi

        parsed = parse_uwi(uwi)
        if not parsed:
            logger.warning(f"Could not parse UWI: {uwi}")
            return None

        province = parsed.get("province", "").lower()

        if province == "ab":
            if self.aer_instance is None:
                from .aer import AER

                self.aer_instance = AER()
            return self.aer_instance.get_well_by_uwi(uwi)

        elif province == "bc":
            if self.bcer_instance is None:
                from .bcer import BCER

                self.bcer_instance = BCER()
            return self.bcer_instance.get_well_by_uwi(uwi)

        else:
            logger.warning(f"Unknown province in UWI: {province}")
            return None
