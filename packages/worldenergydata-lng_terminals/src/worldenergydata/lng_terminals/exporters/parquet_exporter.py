"""Parquet exporter for LNG terminal data."""

from __future__ import annotations

import logging
from pathlib import Path

from ..config import PROCESSED_DIR
from ..exceptions import LNGExportError
from ..models.terminal import LNGTerminal

logger = logging.getLogger(__name__)


class ParquetExporter:
    """Export LNG terminal data to Parquet format using pandas."""

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or PROCESSED_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        terminals: list[LNGTerminal],
        filename: str = "lng_terminals.parquet",
    ) -> Path:
        """Export terminals to Parquet file.

        Args:
            terminals: List of terminal records to export
            filename: Output filename

        Returns:
            Path to exported Parquet file

        Raises:
            LNGExportError: If export fails or pandas/pyarrow not available
        """
        if not terminals:
            raise LNGExportError.write_failed(
                str(self.output_dir / filename), "No terminals to export"
            )

        output_path = self.output_dir / filename

        try:
            import pandas as pd
        except ImportError as e:
            raise LNGExportError.write_failed(
                str(output_path),
                "pandas is required for Parquet export. Install with: pip install pandas pyarrow",
            ) from e

        try:
            rows = [t.to_flat_dict() for t in terminals]
            df = pd.DataFrame(rows)

            # Convert object columns to explicit string dtype so PyArrow
            # can infer a consistent Arrow type (avoids 'Input object was
            # not a NumPy array' errors on mixed str/None columns).
            for col in df.columns:
                if df[col].dtype == "object":
                    df[col] = df[col].astype(pd.StringDtype())

            df.to_parquet(output_path, engine="pyarrow", index=False)
            logger.info(f"Exported {len(terminals)} terminals to {output_path}")
            return output_path
        except LNGExportError:
            raise
        except Exception as e:
            raise LNGExportError.write_failed(str(output_path), str(e)) from e
