# ABOUTME: Main data collection router for Texas RRC module
# ABOUTME: Coordinates data downloads and processing based on configuration

"""
Texas RRC Data Collection Router.

Orchestrates data collection from Texas Railroad Commission sources
based on configuration settings.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ..api_client import TexasRRCClient
from ..errors import TexasRRCDataError

logger = logging.getLogger(__name__)


class TexasRRCData:
    """
    Data collection orchestrator for Texas RRC module.

    Coordinates downloading and initial processing of data from
    Texas RRC public data sources.
    """

    # Mapping of data types to download methods
    DATA_TYPE_METHODS = {
        "production": "download_production_data",
        "wells": "download_well_data",
        "drilling_permits": "download_drilling_permits",
        "completions": "download_completion_data",
        "operators": "download_operator_data",
    }

    def __init__(self, client: Optional[TexasRRCClient] = None):
        """
        Initialize data router.

        Args:
            client: Optional pre-configured TexasRRCClient instance
        """
        self._client = client

    @property
    def client(self) -> TexasRRCClient:
        """Get or create API client."""
        if self._client is None:
            self._client = TexasRRCClient()
        return self._client

    def router(self, cfg: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Route data collection based on configuration.

        Args:
            cfg: Configuration dictionary containing:
                - data_types: List of data types to collect
                - output: Output configuration (directory, format)
                - districts: Optional list of districts to filter
                - date_range: Optional date range filter

        Returns:
            Tuple of (updated config, collected data dictionary)

        Raises:
            TexasRRCDataError: If data collection fails
        """
        data_types = cfg.get("data_types", ["production"])
        output_cfg = cfg.get("output", {})
        output_dir = Path(output_cfg.get("directory", "./data/texas_rrc"))

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        collected_data: Dict[str, Any] = {}
        errors: Dict[str, str] = {}

        for data_type in data_types:
            try:
                logger.info(f"Collecting Texas RRC {data_type} data")
                data = self._collect_data_type(data_type, cfg, output_dir)
                collected_data[data_type] = data
                logger.info(f"Successfully collected {data_type} data")
            except Exception as e:
                logger.error(f"Failed to collect {data_type} data: {e}")
                errors[data_type] = str(e)

        # Update config with results
        if cfg.get("basename"):
            cfg[cfg["basename"]]["data"] = {
                "collected": list(collected_data.keys()),
                "errors": errors,
                "output_dir": str(output_dir),
            }

        return cfg, collected_data

    def _collect_data_type(
        self,
        data_type: str,
        cfg: Dict[str, Any],
        output_dir: Path,
    ) -> Dict[str, Any]:
        """
        Collect specific data type.

        Args:
            data_type: Type of data to collect
            cfg: Configuration dictionary
            output_dir: Output directory path

        Returns:
            Dictionary with collected data metadata

        Raises:
            TexasRRCDataError: If collection fails
        """
        method_name = self.DATA_TYPE_METHODS.get(data_type)
        if method_name is None:
            raise TexasRRCDataError(
                f"Unknown data type: {data_type}",
                code="TEXAS_RRC_UNKNOWN_DATA_TYPE",
                context={"data_type": data_type},
            )

        method = getattr(self, method_name, None)
        if method is None:
            raise TexasRRCDataError(
                f"Method not implemented: {method_name}",
                code="TEXAS_RRC_NOT_IMPLEMENTED",
            )

        return method(cfg, output_dir)

    def download_production_data(
        self,
        cfg: Dict[str, Any],
        output_dir: Path,
    ) -> Dict[str, Any]:
        """
        Download production data from Texas RRC.

        Args:
            cfg: Configuration with optional filters
            output_dir: Output directory

        Returns:
            Dictionary with download metadata
        """
        use_cache = cfg.get("api", {}).get("use_cache", True)

        try:
            file_path = self.client.download_pdq_dump(
                output_dir=output_dir,
                data_type="og_production",
                use_cache=use_cache,
            )

            return {
                "file_path": str(file_path),
                "data_type": "production",
                "status": "downloaded",
            }
        except Exception as e:
            raise TexasRRCDataError.parse_failed("production", str(e), e)

    def download_well_data(
        self,
        cfg: Dict[str, Any],
        output_dir: Path,
    ) -> Dict[str, Any]:
        """
        Download well data from Texas RRC.

        Args:
            cfg: Configuration with optional district filter
            output_dir: Output directory

        Returns:
            Dictionary with download metadata
        """
        use_cache = cfg.get("api", {}).get("use_cache", True)
        districts = cfg.get("districts", [])

        results = []

        if districts:
            # Download for specific districts
            for district in districts:
                try:
                    district_num = int(
                        district.replace("0", "")
                        .replace("A", "")
                        .replace("B", "")
                        .replace("C", "")
                    )
                    file_path = self.client.download_wellbore_data(
                        output_dir=output_dir,
                        district=district_num,
                        use_cache=use_cache,
                    )
                    results.append(
                        {
                            "district": district,
                            "file_path": str(file_path),
                            "status": "downloaded",
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to download well data for district {district}: {e}"
                    )
                    results.append(
                        {
                            "district": district,
                            "status": "error",
                            "error": str(e),
                        }
                    )
        else:
            # Download all well data
            try:
                file_path = self.client.download_pdq_dump(
                    output_dir=output_dir,
                    data_type="og_well",
                    use_cache=use_cache,
                )
                results.append(
                    {
                        "file_path": str(file_path),
                        "status": "downloaded",
                    }
                )
            except Exception as e:
                raise TexasRRCDataError.parse_failed("wells", str(e), e)

        return {
            "data_type": "wells",
            "results": results,
        }

    def download_drilling_permits(
        self,
        cfg: Dict[str, Any],
        output_dir: Path,
    ) -> Dict[str, Any]:
        """
        Download drilling permit data from Texas RRC.

        Args:
            cfg: Configuration with optional date range
            output_dir: Output directory

        Returns:
            Dictionary with download metadata
        """
        use_cache = cfg.get("api", {}).get("use_cache", True)
        date_range = cfg.get("date_range")

        try:
            file_path = self.client.download_drilling_permits(
                output_dir=output_dir,
                date_range=date_range,
                use_cache=use_cache,
            )

            return {
                "file_path": str(file_path),
                "data_type": "drilling_permits",
                "status": "downloaded",
                "date_range": date_range,
            }
        except Exception as e:
            raise TexasRRCDataError.parse_failed("drilling_permits", str(e), e)

    def download_completion_data(
        self,
        cfg: Dict[str, Any],
        output_dir: Path,
    ) -> Dict[str, Any]:
        """
        Download completion data from Texas RRC.

        Args:
            cfg: Configuration
            output_dir: Output directory

        Returns:
            Dictionary with download metadata
        """
        use_cache = cfg.get("api", {}).get("use_cache", True)

        try:
            file_path = self.client.download_pdq_dump(
                output_dir=output_dir,
                data_type="og_completion",
                use_cache=use_cache,
            )

            return {
                "file_path": str(file_path),
                "data_type": "completions",
                "status": "downloaded",
            }
        except Exception as e:
            raise TexasRRCDataError.parse_failed("completions", str(e), e)

    def download_operator_data(
        self,
        cfg: Dict[str, Any],
        output_dir: Path,
    ) -> Dict[str, Any]:
        """
        Download operator data from Texas RRC.

        Note: This uses a placeholder until proper endpoint is identified.

        Args:
            cfg: Configuration
            output_dir: Output directory

        Returns:
            Dictionary with download metadata
        """
        return {
            "data_type": "operators",
            "status": "not_implemented",
            "message": "Operator data download not yet implemented",
        }

    def close(self) -> None:
        """Close the data client."""
        if self._client:
            self._client.close()
            self._client = None


__all__ = ["TexasRRCData"]
