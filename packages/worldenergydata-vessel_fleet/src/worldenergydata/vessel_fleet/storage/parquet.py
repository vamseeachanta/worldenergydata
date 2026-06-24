"""Parquet read/write with schema enforcement for vessel fleet data."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Union

import pandas as pd

logger = logging.getLogger(__name__)


class ParquetStore:
    """Parquet-based storage for vessel fleet records.

    Stores records as Parquet files for efficient columnar access
    and exports CSV for human-readable inspection.
    """

    def __init__(self, base_dir: Union[str, Path]) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        records: list[dict[str, Any]],
        filename: str,
    ) -> Path:
        """Save records to a Parquet file.

        Creates parent directories as needed. Returns the file path.
        """
        filepath = self.base_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        if not records:
            df = pd.DataFrame()
        else:
            df = pd.DataFrame(records)

        df.to_parquet(filepath, index=False, engine="pyarrow")
        logger.info("Saved %d records to %s", len(records), filepath)
        return filepath

    def load(self, filename: str) -> list[dict[str, Any]]:
        """Load records from a Parquet file.

        Returns an empty list if the file does not exist.
        """
        filepath = self.base_dir / filename
        if not filepath.exists():
            logger.warning("File not found: %s", filepath)
            return []

        df = pd.read_parquet(filepath, engine="pyarrow")
        if df.empty:
            return []

        records = df.where(df.notna(), None).to_dict(orient="records")
        return records

    def export_csv(
        self,
        parquet_filename: str,
        csv_filename: str,
    ) -> Path:
        """Export a Parquet file to CSV for human-readable inspection."""
        filepath = self.base_dir / parquet_filename
        csv_path = self.base_dir / csv_filename
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        df = pd.read_parquet(filepath, engine="pyarrow")
        df.to_csv(csv_path, index=False)
        logger.info("Exported %d records to %s", len(df), csv_path)
        return csv_path

    def list_files(self, pattern: str = "*.parquet") -> list[Path]:
        """List all Parquet files matching a glob pattern."""
        return sorted(self.base_dir.rglob(pattern))
