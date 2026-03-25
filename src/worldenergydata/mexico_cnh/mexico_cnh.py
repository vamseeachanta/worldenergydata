# ABOUTME: Main Mexico CNH module router implementation following established patterns
# ABOUTME: Orchestrates data collection and analysis for Mexican oil and gas data

"""
Main Mexico CNH module router implementation.

This module follows the established architectural pattern to provide a consistent
interface for Mexico CNH data collection and analysis within the WorldEnergyData
framework. Data collection is performed via Selenium scraping of the SIH dashboard.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class MexicoCNH:
    """
    Main Mexico CNH module class implementing the router pattern.

    This class orchestrates data collection from Mexico's National Hydrocarbons
    Commission (CNH) data portals and integrates with existing WorldEnergyData
    analysis tools.
    """

    # Valid data types for Mexico CNH
    VALID_DATA_TYPES = [
        "production",
        "wells",
        "fields",
        "reserves",
        "contracts",
        "operators",
        "exploration",
    ]

    # Valid contract round identifiers
    VALID_CONTRACT_ROUNDS = [
        "R01",  # Round 1
        "R02",  # Round 2
        "R03",  # Round 3
        "R04",  # Round 4
        "MIG",  # Migration contracts
        "ASG",  # Assignments (PEMEX)
    ]

    # Valid Mexican oil/gas regions
    VALID_REGIONS = [
        "sureste",  # Southeast (Tabasco, Campeche)
        "norte",  # North (Tamaulipas, Nuevo Leon)
        "aguas_profundas",  # Deep waters
        "aguas_someras",  # Shallow waters
        "terrestre",  # Onshore
    ]

    def __init__(self):
        """Initialize Mexico CNH module."""
        self.module_name = "mexico_cnh"
        self.data_instance = None
        self.analysis_instance = None
        self._initialize_components()

    def _initialize_components(self):
        """Initialize data and analysis components lazily."""
        # Components will be imported when needed to avoid circular imports
        pass

    def router(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main router method following established pattern.

        Args:
            cfg: Configuration dictionary containing:
                - module: Module name (should be 'mexico_cnh')
                - data_types: List of data types to collect
                - selenium: Selenium configuration (headless, timeout, etc.)
                - output: Output configuration (directory, format)
                - analysis: Analysis configuration (optional)
                - regions: List of regions to filter (optional)
                - contract_rounds: List of contract rounds to filter (optional)
                - date_range: Date range for data (optional)

        Returns:
            Updated configuration dictionary with results

        Raises:
            ValueError: If configuration is invalid
            ImportError: If required components cannot be imported
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

            # Import and initialize data component
            if self.data_instance is None:
                from .data import MexicoCNHData

                self.data_instance = MexicoCNHData()

            # Route to data collection
            logger.info(
                f"Starting Mexico CNH data collection for types: "
                f"{cfg.get('data_types', [])}"
            )
            cfg, data = self.data_instance.router(cfg)

            # Route to analysis if configured
            if cfg.get("analysis", {}).get("enabled", False):
                if self.analysis_instance is None:
                    from .analysis import MexicoCNHAnalysis

                    self.analysis_instance = MexicoCNHAnalysis()

                logger.info("Running Mexico CNH analysis")
                cfg = self.analysis_instance.router(cfg, data)

            # Add status information
            cfg[cfg["basename"]]["status"] = "completed"
            cfg[cfg["basename"]]["data_collected"] = list(data.keys()) if data else []

            logger.info("Mexico CNH module processing completed successfully")
            return cfg

        except ImportError as e:
            logger.error(f"Failed to import Mexico CNH components: {str(e)}")
            if "basename" in cfg and cfg["basename"] in cfg:
                cfg[cfg["basename"]]["status"] = "error"
                cfg[cfg["basename"]]["error"] = f"Import error: {str(e)}"
            raise

        except Exception as e:
            logger.error(f"Error in Mexico CNH router: {str(e)}")
            if "basename" in cfg and cfg["basename"] in cfg:
                cfg[cfg["basename"]]["status"] = "error"
                cfg[cfg["basename"]]["error"] = str(e)
            raise

    def _validate_config(self, cfg: Dict[str, Any]) -> None:
        """
        Validate configuration dictionary.

        Args:
            cfg: Configuration dictionary to validate

        Raises:
            ValueError: If configuration is invalid
        """
        # Check for required fields
        if not cfg:
            raise ValueError("Configuration cannot be empty")

        # Validate module name if specified
        if "module" in cfg and cfg["module"] != self.module_name:
            logger.warning(
                f"Module mismatch: expected '{self.module_name}', "
                f"got '{cfg['module']}'"
            )

        # Validate data types if specified
        if "data_types" in cfg:
            invalid_types = [
                dt for dt in cfg["data_types"] if dt not in self.VALID_DATA_TYPES
            ]
            if invalid_types:
                raise ValueError(
                    f"Invalid data types: {invalid_types}. "
                    f"Valid types: {self.VALID_DATA_TYPES}"
                )

        # Validate regions if specified
        if "regions" in cfg:
            invalid_regions = [r for r in cfg["regions"] if r not in self.VALID_REGIONS]
            if invalid_regions:
                raise ValueError(
                    f"Invalid regions: {invalid_regions}. "
                    f"Valid regions: {self.VALID_REGIONS}"
                )

        # Validate contract rounds if specified
        if "contract_rounds" in cfg:
            invalid_rounds = [
                r for r in cfg["contract_rounds"] if r not in self.VALID_CONTRACT_ROUNDS
            ]
            if invalid_rounds:
                raise ValueError(
                    f"Invalid contract rounds: {invalid_rounds}. "
                    f"Valid rounds: {self.VALID_CONTRACT_ROUNDS}"
                )

        # Validate Selenium configuration if specified
        if "selenium" in cfg:
            selenium_config = cfg["selenium"]
            if "timeout" in selenium_config:
                timeout = selenium_config["timeout"]
                if not isinstance(timeout, (int, float)) or timeout <= 0:
                    raise ValueError(f"Invalid Selenium timeout: {timeout}")

            if "headless" in selenium_config:
                if not isinstance(selenium_config["headless"], bool):
                    raise ValueError(
                        f"Invalid headless setting: {selenium_config['headless']}"
                    )

        # Validate output configuration if specified
        if "output" in cfg:
            output_config = cfg["output"]
            if "format" in output_config:
                valid_formats = ["csv", "json", "parquet", "excel"]
                if output_config["format"] not in valid_formats:
                    raise ValueError(
                        f"Invalid output format: {output_config['format']}. "
                        f"Valid formats: {valid_formats}"
                    )

        logger.debug("Configuration validated successfully")

    def get_valid_data_types(self) -> list:
        """Return list of valid data types."""
        return self.VALID_DATA_TYPES.copy()

    def get_valid_regions(self) -> list:
        """Return list of valid Mexican oil/gas regions."""
        return self.VALID_REGIONS.copy()

    def get_valid_contract_rounds(self) -> list:
        """Return list of valid contract round identifiers."""
        return self.VALID_CONTRACT_ROUNDS.copy()
