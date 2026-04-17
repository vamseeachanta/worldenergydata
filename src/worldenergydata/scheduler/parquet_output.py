"""Shared Parquet write utility for scheduler job adapters.

All adapters that produce tabular output use this helper to write
Parquet snapshots with consistent compression and directory handling.
"""

from pathlib import Path

import pandas as pd


def write_parquet(df: pd.DataFrame, output_dir: Path, filename: str) -> Path:
    """Write a DataFrame to Parquet with snappy compression.

    Args:
        df: DataFrame to write.
        output_dir: Directory for output file (created if missing).
        filename: Output filename (e.g., "eia_petroleum_weekly.parquet").

    Returns:
        Path to the written Parquet file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    df.to_parquet(output_path, engine="pyarrow", index=False, compression="snappy")
    return output_path
