"""CSV exporter for LNG terminal data."""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path

from ..config import PROCESSED_DIR
from ..exceptions import LNGExportError
from ..models.terminal import LNGTerminal

logger = logging.getLogger(__name__)


class CSVExporter:
    """Export LNG terminal data to CSV format."""

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or PROCESSED_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        terminals: list[LNGTerminal],
        filename: str = "lng_terminals.csv",
    ) -> Path:
        """Export terminals to CSV file.

        Uses LNGTerminal.to_flat_dict() for flattening sub-models.

        Args:
            terminals: List of terminal records to export
            filename: Output filename

        Returns:
            Path to the exported CSV file

        Raises:
            LNGExportError: If export fails
        """
        if not terminals:
            raise LNGExportError.write_failed(
                str(self.output_dir / filename), "No terminals to export"
            )

        output_path = self.output_dir / filename

        try:
            # Flatten all terminals
            rows = [t.to_flat_dict() for t in terminals]

            # Collect all column names from all rows (union)
            all_columns = []
            seen = set()
            for row in rows:
                for key in row:
                    if key not in seen:
                        all_columns.append(key)
                        seen.add(key)

            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=all_columns, extrasaction="ignore"
                )
                writer.writeheader()
                writer.writerows(rows)

            logger.info(f"Exported {len(terminals)} terminals to {output_path}")
            return output_path

        except LNGExportError:
            raise
        except Exception as e:
            raise LNGExportError.write_failed(str(output_path), str(e)) from e

    def export_metadata(
        self,
        terminals: list[LNGTerminal],
        filename: str = "lng_terminals_metadata.json",
    ) -> Path:
        """Export metadata about the dataset.

        Args:
            terminals: List of terminal records
            filename: Output filename

        Returns:
            Path to the metadata JSON file
        """
        output_path = self.output_dir / filename

        metadata = {
            "total_records": len(terminals),
            "export_timestamp": datetime.utcnow().isoformat(),
            "countries": sorted({t.country for t in terminals}),
            "status_distribution": self._count_by_attr(terminals, "status"),
            "type_distribution": self._count_by_attr(terminals, "terminal_type"),
            "region_distribution": self._count_by_attr(terminals, "region"),
        }

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, default=str)
            logger.info(f"Exported metadata to {output_path}")
            return output_path
        except Exception as e:
            raise LNGExportError.write_failed(str(output_path), str(e)) from e

    @staticmethod
    def _count_by_attr(terminals: list[LNGTerminal], attr: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for t in terminals:
            val = getattr(t, attr, None)
            key = val.value if hasattr(val, "value") else str(val)
            counts[key] = counts.get(key, 0) + 1
        return dict(sorted(counts.items()))
