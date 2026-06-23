# ABOUTME: Main Texas RRC module router implementation following SODIR pattern
# ABOUTME: Orchestrates data collection and analysis for Texas oil and gas data

"""
Main Texas RRC module router implementation.

This module follows the SODIR architectural pattern to provide a consistent
interface for Texas RRC data collection and analysis within the WorldEnergyData framework.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class TexasRRC:
    """
    Main Texas RRC module class implementing the router pattern.

    This class orchestrates data collection from the Texas Railroad Commission
    public data sources and integrates with existing WorldEnergyData analysis tools.
    """

    # Valid data types for Texas RRC
    VALID_DATA_TYPES = [
        "production",
        "wells",
        "drilling_permits",
        "completions",
        "operators",
        "leases",
        "fields",
    ]

    # Valid Texas RRC districts
    VALID_DISTRICTS = [
        "01",
        "02",
        "03",
        "04",
        "05",
        "06",
        "7B",
        "7C",
        "08",
        "8A",
        "09",
        "10",
    ]

    def __init__(self):
        """Initialize Texas RRC module."""
        self.module_name = "texas_rrc"
        self.data_instance = None
        self.analysis_instance = None
        self._initialize_components()

    def _initialize_components(self):
        """Initialize data and analysis components lazily."""
        # Components will be imported when needed to avoid circular imports
        pass

    def router(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main router method following SODIR pattern.

        Args:
            cfg: Configuration dictionary containing:
                - module: Module name (should be 'texas_rrc')
                - data_types: List of data types to collect
                - api: API configuration (base_url, rate_limit, cache_ttl)
                - output: Output configuration (directory, format)
                - analysis: Analysis configuration (optional)
                - districts: List of districts to filter (optional)
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
                from .data import TexasRRCData

                self.data_instance = TexasRRCData()

            # Route to data collection
            logger.info(
                f"Starting Texas RRC data collection for types: {cfg.get('data_types', [])}"
            )
            cfg, data = self.data_instance.router(cfg)

            # Route to analysis if configured
            if cfg.get("analysis", {}).get("enabled", False):
                if self.analysis_instance is None:
                    from .analysis import TexasRRCAnalysis

                    self.analysis_instance = TexasRRCAnalysis()

                logger.info("Running Texas RRC analysis")
                cfg = self.analysis_instance.router(cfg, data)

            if cfg.get("data", {}).get("source") == "csv":
                cfg = self._write_csv_workflow_outputs(cfg, data)

            # Add status information
            cfg[cfg["basename"]]["status"] = "completed"
            cfg[cfg["basename"]]["data_collected"] = list(data.keys()) if data else []

            logger.info("Texas RRC module processing completed successfully")
            return cfg

        except Exception as e:
            logger.error(f"Error in Texas RRC router: {str(e)}")
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
                f"Module mismatch: expected '{self.module_name}', got '{cfg['module']}'"
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

        # Validate districts if specified
        if "districts" in cfg:
            invalid_districts = [
                d for d in cfg["districts"] if d not in self.VALID_DISTRICTS
            ]
            if invalid_districts:
                raise ValueError(
                    f"Invalid districts: {invalid_districts}. "
                    f"Valid districts: {self.VALID_DISTRICTS}"
                )

        # Validate API configuration if specified
        if "api" in cfg:
            api_config = cfg["api"]
            if "base_url" in api_config:
                if not api_config["base_url"].startswith("http"):
                    raise ValueError(f"Invalid API base URL: {api_config['base_url']}")

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

    def get_valid_data_types(self) -> list:
        """Return list of valid data types."""
        return self.VALID_DATA_TYPES.copy()

    def get_valid_districts(self) -> list:
        """Return list of valid Texas RRC districts."""
        return self.VALID_DISTRICTS.copy()

    def _write_csv_workflow_outputs(
        self,
        cfg: Dict[str, Any],
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Persist deterministic outputs for local CSV registry workflows."""
        from .processors import ProductionProcessor

        production_records = data.get("production", {}).get("records", [])
        processor = ProductionProcessor()
        processed = processor.process(production_records, validate=False)
        districts = processor.aggregate_by_district(processed)

        label = cfg.get("meta", {}).get("label", "texas_rrc_production_summary")
        result_folder = Path(cfg["Analysis"]["result_folder"])
        result_folder.mkdir(parents=True, exist_ok=True)
        districts_path = result_folder / f"{label}_districts.csv"
        summary_path = result_folder / f"{label}_summary.json"

        districts.to_csv(districts_path, index=False)
        summary = {
            "total_records": len(processed),
            "district_count": int(len(districts)),
            "oil_production_total": float(districts["oil_production"].sum()),
            "gas_production_total": float(districts["gas_production"].sum()),
        }
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        cfg[cfg["basename"]]["outputs"] = {
            "districts_csv": str(districts_path),
            "summary_json": str(summary_path),
        }
        return cfg
