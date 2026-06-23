"""
SODIR Data Storage System

Handles file storage and retrieval for SODIR data, following the patterns
established in the BSEE module.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Union

import pandas as pd

logger = logging.getLogger(__name__)


class DataStorage:
    """Manages data persistence for SODIR module."""

    def __init__(self, config: Union[str, Dict[str, Any]] = None):
        """
        Initialize DataStorage with base directory.

        Args:
            config: Base directory path string or configuration dictionary
        """
        if isinstance(config, dict):
            # Extract base_path from config dictionary
            base_path = config.get("base_path", config.get("path", "data/sodir"))
        elif isinstance(config, str):
            base_path = config
        else:
            base_path = "data/sodir"

        self.base_path = Path(base_path)
        self._ensure_directories()

    def _ensure_directories(self):
        """Create necessary directory structure."""
        directories = [
            self.base_path,
            self.base_path / "raw",
            self.base_path / "processed",
            self.base_path / "analysis",
            self.base_path / "cache",
            self.base_path / "exports",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def save(self, dataset_type: str, result: Dict[str, Any]) -> str:
        """
        Generic save method that routes to appropriate storage method.

        Args:
            dataset_type: Type of dataset
            result: Result dictionary containing data and metadata

        Returns:
            Path to saved file
        """
        # Extract data from result
        data = result.get("data", [])

        # If data is a DataFrame, save as processed
        if isinstance(data, pd.DataFrame):
            return self.save_processed_data(data, dataset_type)
        # Otherwise save as raw data
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return self.save_raw_data(data, dataset_type, timestamp)

    def save_raw_data(self, data: Any, dataset_type: str, timestamp: str = None) -> str:
        """
        Save raw data from SODIR API.

        Args:
            data: Raw data to save
            dataset_type: Type of dataset (e.g., 'wellbores', 'fields')
            timestamp: Optional timestamp for versioning

        Returns:
            Path to saved file
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = f"{dataset_type}_{timestamp}.json"
        filepath = self.base_path / "raw" / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                if isinstance(data, (dict, list)):
                    json.dump(data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump({"data": str(data)}, f, indent=2)

            logger.info(f"Saved raw {dataset_type} data to {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to save raw data: {e}")
            raise

    def save_processed_data(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]], Dict[str, Any]],
        dataset_type: str,
        format: str = "parquet",
    ) -> str:
        """
        Save processed data.

        Args:
            data: Data to save (DataFrame, list of dicts, or dict)
            dataset_type: Type of dataset
            format: Output format ('parquet', 'csv', 'json')

        Returns:
            Path to saved file
        """
        # Convert to DataFrame if necessary
        if isinstance(data, list):
            df = pd.DataFrame(data) if data else pd.DataFrame()
        elif isinstance(data, dict) and not isinstance(data, pd.DataFrame):
            # If it's a single dict, wrap it in a list
            df = pd.DataFrame([data])
        else:
            df = data

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == "parquet":
            filename = f"{dataset_type}_processed_{timestamp}.parquet"
            filepath = self.base_path / "processed" / filename
            df.to_parquet(filepath, engine="pyarrow", compression="snappy")

        elif format == "csv":
            filename = f"{dataset_type}_processed_{timestamp}.csv"
            filepath = self.base_path / "processed" / filename
            df.to_csv(filepath, index=False)

        elif format == "json":
            filename = f"{dataset_type}_processed_{timestamp}.json"
            filepath = self.base_path / "processed" / filename
            df.to_json(filepath, orient="records", date_format="iso")

        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"Saved processed {dataset_type} data to {filepath}")
        return str(filepath)

    def load_processed_data(
        self, dataset_type: str, latest: bool = True
    ) -> pd.DataFrame:
        """
        Load processed data.

        Args:
            dataset_type: Type of dataset to load
            latest: Whether to load the most recent file

        Returns:
            DataFrame with processed data
        """
        pattern = f"{dataset_type}_processed_*.parquet"
        files = list((self.base_path / "processed").glob(pattern))

        if not files:
            # Try CSV as fallback
            pattern = f"{dataset_type}_processed_*.csv"
            files = list((self.base_path / "processed").glob(pattern))

        if not files:
            raise FileNotFoundError(f"No processed data found for {dataset_type}")

        if latest:
            # Get most recent file
            file_path = max(files, key=lambda p: p.stat().st_mtime)
        else:
            file_path = files[0]

        if file_path.suffix == ".parquet":
            df = pd.read_parquet(file_path)
        elif file_path.suffix == ".csv":
            df = pd.read_csv(file_path)
        else:
            df = pd.read_json(file_path)

        logger.info(f"Loaded {len(df)} records from {file_path}")
        return df

    def save_analysis_results(self, results: Dict[str, Any], analysis_type: str) -> str:
        """
        Save analysis results.

        Args:
            results: Analysis results dictionary
            analysis_type: Type of analysis performed

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{analysis_type}_analysis_{timestamp}.json"
        filepath = self.base_path / "analysis" / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"Saved {analysis_type} analysis results to {filepath}")
        return str(filepath)

    def get_available_datasets(self) -> Dict[str, List[str]]:
        """
        Get list of available datasets.

        Returns:
            Dictionary mapping data types to available files
        """
        available = {"raw": [], "processed": [], "analysis": []}

        # Check raw data
        for file in (self.base_path / "raw").glob("*.json"):
            available["raw"].append(file.stem)

        # Check processed data
        for file in (self.base_path / "processed").glob("*"):
            available["processed"].append(file.stem)

        # Check analysis results
        for file in (self.base_path / "analysis").glob("*.json"):
            available["analysis"].append(file.stem)

        return available

    def clear_cache(self):
        """Clear cached data."""
        cache_dir = self.base_path / "cache"
        for file in cache_dir.glob("*"):
            try:
                file.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete cache file {file}: {e}")

        logger.info("Cache cleared")

    def export_data(
        self, df: pd.DataFrame, export_name: str, format: str = "excel"
    ) -> str:
        """
        Export data for external use.

        Args:
            df: DataFrame to export
            export_name: Name for export file
            format: Export format ('excel', 'csv', 'json')

        Returns:
            Path to exported file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == "excel":
            filename = f"{export_name}_{timestamp}.xlsx"
            filepath = self.base_path / "exports" / filename
            df.to_excel(filepath, index=False, engine="openpyxl")

        elif format == "csv":
            filename = f"{export_name}_{timestamp}.csv"
            filepath = self.base_path / "exports" / filename
            df.to_csv(filepath, index=False)

        elif format == "json":
            filename = f"{export_name}_{timestamp}.json"
            filepath = self.base_path / "exports" / filename
            df.to_json(filepath, orient="records", date_format="iso")

        else:
            raise ValueError(f"Unsupported export format: {format}")

        logger.info(f"Exported data to {filepath}")
        return str(filepath)

    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about storage usage.

        Returns:
            Dictionary with storage statistics
        """

        def get_dir_size(path):
            total = 0
            for entry in path.rglob("*"):
                if entry.is_file():
                    total += entry.stat().st_size
            return total

        info = {
            "base_path": str(self.base_path),
            "total_size_bytes": get_dir_size(self.base_path),
            "directories": {},
        }

        for subdir in ["raw", "processed", "analysis", "cache", "exports"]:
            dir_path = self.base_path / subdir
            if dir_path.exists():
                size = get_dir_size(dir_path)
                count = len(list(dir_path.glob("*")))
                info["directories"][subdir] = {
                    "size_bytes": size,
                    "file_count": count,
                    "size_mb": round(size / (1024 * 1024), 2),
                }

        info["total_size_mb"] = round(info["total_size_bytes"] / (1024 * 1024), 2)

        return info
