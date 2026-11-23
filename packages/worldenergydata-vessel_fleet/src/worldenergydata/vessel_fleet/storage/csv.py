"""Human-readable CSV export for vessel fleet data."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any, Union

logger = logging.getLogger(__name__)


def export_records_to_csv(
    records: list[dict[str, Any]],
    filepath: Union[str, Path],
) -> Path:
    """Write records to a CSV file.

    Creates parent directories as needed. Returns the file path.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        path.write_text("")
        return path

    fieldnames = list(records[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    logger.info("Exported %d records to %s", len(records), path)
    return path
