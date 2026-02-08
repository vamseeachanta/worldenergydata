"""
Safety Data Loaders

File-based data loading for CSV, Excel, and Parquet safety data files.
"""

from pathlib import Path
from typing import Optional

import pandas as pd

from worldenergydata.common.types import PathLike
from worldenergydata.modules.safety_analysis.exceptions import SafetyDataError


class SafetyDataLoader:
    """Load safety data from CSV, Excel, or Parquet files."""

    SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".parquet", ".pq"}

    def load(
        self,
        path: PathLike,
        sheet_name: Optional[str] = None,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Load safety data from a file.

        Args:
            path: Path to the data file.
            sheet_name: Sheet name for Excel files.
            **kwargs: Additional arguments passed to the pandas reader.

        Returns:
            DataFrame with the loaded data.

        Raises:
            SafetyDataError: If the file cannot be loaded.
        """
        path = Path(path)

        if not path.exists():
            raise SafetyDataError.load_failed(str(path), "File does not exist")

        suffix = path.suffix.lower()
        if suffix not in self.SUPPORTED_EXTENSIONS:
            raise SafetyDataError.load_failed(
                str(path),
                f"Unsupported file type '{suffix}'. "
                f"Supported: {', '.join(sorted(self.SUPPORTED_EXTENSIONS))}",
            )

        try:
            if suffix == ".csv":
                return pd.read_csv(path, **kwargs)
            elif suffix in (".xlsx", ".xls"):
                return pd.read_excel(path, sheet_name=sheet_name or 0, **kwargs)
            elif suffix in (".parquet", ".pq"):
                return pd.read_parquet(path, **kwargs)
        except Exception as e:
            raise SafetyDataError.load_failed(str(path), str(e), cause=e)

        raise SafetyDataError.load_failed(str(path), "Unknown error")

    def load_multiple(
        self,
        paths: list[PathLike],
        **kwargs,
    ) -> pd.DataFrame:
        """Load and concatenate multiple data files."""
        frames = []
        for p in paths:
            frames.append(self.load(p, **kwargs))
        if not frames:
            raise SafetyDataError(
                message="No files provided to load",
                code="SAFETY_NO_FILES",
            )
        return pd.concat(frames, ignore_index=True)
