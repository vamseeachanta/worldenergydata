# ABOUTME: CSV exporter for metocean data with configurable columns.
# ABOUTME: Supports date range filtering, quality flags, and summary statistics export.

"""
CSV Exporter for Metocean Data

Exports metocean observations to CSV format with configurable columns.
"""

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from worldenergydata.modules.metocean.exceptions import ExportError, ExportWriteError
from worldenergydata.modules.metocean.processors.data_harmonizer import (
    HarmonizedObservation,
)


class CSVExporter:
    """
    Export metocean data to CSV format.

    Features:
    - Configurable column selection
    - Date range filtering
    - Automatic header generation
    - Multi-station export
    - Summary statistics export

    Example usage:
        exporter = CSVExporter(include_quality=True)

        # Export observations
        count = exporter.export(observations, Path("output.csv"))
        print(f"Exported {count} records")

        # Export with date filter
        count = exporter.export(
            observations,
            Path("output.csv"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 6, 30)
        )

        # Export daily summary
        count = exporter.export_summary(
            observations, Path("summary.csv"), group_by="day"
        )
    """

    # Default columns to export
    DEFAULT_COLUMNS = [
        "observation_time",
        "station_id",
        "source",
        "wave_height_m",
        "wave_period_s",
        "wave_direction_deg",
        "wind_speed_ms",
        "wind_direction_deg",
        "sea_surface_temp_c",
        "water_level_m",
        "pressure_hpa",
    ]

    def __init__(
        self,
        columns: Optional[List[str]] = None,
        include_quality: bool = True,
        date_format: str = "%Y-%m-%d %H:%M:%S",
    ):
        """
        Initialize CSV exporter.

        Args:
            columns: List of column names to export. If None, uses DEFAULT_COLUMNS
            include_quality: Whether to include quality_flag column
            date_format: Format string for datetime columns
        """
        self.columns = columns or self.DEFAULT_COLUMNS.copy()
        self.include_quality = include_quality
        self.date_format = date_format

    def export(
        self,
        observations: List[HarmonizedObservation],
        output_path: Path,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """
        Export observations to CSV file.

        Args:
            observations: List of harmonized observations
            output_path: Output file path
            start_date: Optional start date filter (inclusive)
            end_date: Optional end date filter (inclusive)

        Returns:
            Number of records exported

        Raises:
            ExportError: If no observations to export
            ExportWriteError: If writing to file fails
        """
        if not observations:
            raise ExportError("No observations to export")

        # Filter by date range
        filtered = self._filter_by_date(observations, start_date, end_date)

        if not filtered:
            raise ExportError(
                "No observations match the specified date range",
                details={
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                },
            )

        # Prepare headers
        headers = self.columns.copy()
        if self.include_quality:
            headers.append("quality_flag")

        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()

                for obs in filtered:
                    row = self._observation_to_row(obs, headers)
                    writer.writerow(row)

            return len(filtered)

        except OSError as e:
            raise ExportWriteError(
                path=str(output_path),
                reason=str(e),
            ) from e
        except Exception as e:
            raise ExportWriteError(
                path=str(output_path),
                reason=f"Unexpected error: {e}",
            ) from e

    def export_summary(
        self,
        observations: List[HarmonizedObservation],
        output_path: Path,
        group_by: str = "day",
    ) -> int:
        """
        Export summary statistics aggregated by time period.

        Args:
            observations: List of harmonized observations
            output_path: Output file path
            group_by: Grouping period - "hour", "day", or "station"

        Returns:
            Number of summary records exported

        Raises:
            ExportError: If invalid group_by value or no observations
            ExportWriteError: If writing to file fails
        """
        if not observations:
            raise ExportError("No observations to export")

        valid_groups = {"hour", "day", "station"}
        if group_by not in valid_groups:
            raise ExportError(
                f"Invalid group_by value: {group_by}. Must be one of {valid_groups}"
            )

        # Group observations
        groups = self._group_observations(observations, group_by)

        if not groups:
            raise ExportError("No groups created from observations")

        # Calculate statistics for each group
        summary_rows = []
        numeric_fields = [
            "wave_height_m",
            "wave_period_s",
            "wind_speed_ms",
            "sea_surface_temp_c",
            "water_level_m",
            "pressure_hpa",
        ]

        for group_key, group_obs in groups.items():
            row: Dict[str, Any] = {"group": group_key, "count": len(group_obs)}

            for field in numeric_fields:
                values = [
                    getattr(obs, field)
                    for obs in group_obs
                    if getattr(obs, field) is not None
                ]
                if values:
                    row[f"{field}_mean"] = sum(values) / len(values)
                    row[f"{field}_min"] = min(values)
                    row[f"{field}_max"] = max(values)
                else:
                    row[f"{field}_mean"] = None
                    row[f"{field}_min"] = None
                    row[f"{field}_max"] = None

            summary_rows.append(row)

        # Write summary CSV
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            headers = list(summary_rows[0].keys()) if summary_rows else []

            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(summary_rows)

            return len(summary_rows)

        except OSError as e:
            raise ExportWriteError(
                path=str(output_path),
                reason=str(e),
            ) from e
        except Exception as e:
            raise ExportWriteError(
                path=str(output_path),
                reason=f"Unexpected error: {e}",
            ) from e

    def _filter_by_date(
        self,
        observations: List[HarmonizedObservation],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> List[HarmonizedObservation]:
        """Filter observations by date range."""
        filtered = observations
        if start_date:
            filtered = [o for o in filtered if o.observation_time >= start_date]
        if end_date:
            filtered = [o for o in filtered if o.observation_time <= end_date]
        return filtered

    def _observation_to_row(
        self, obs: HarmonizedObservation, headers: List[str]
    ) -> Dict[str, Any]:
        """Convert observation to CSV row dictionary."""
        row: Dict[str, Any] = {}
        for col in headers:
            value = getattr(obs, col, None)
            if isinstance(value, datetime):
                value = value.strftime(self.date_format)
            elif hasattr(value, "value"):  # Enum
                value = value.value
            row[col] = value
        return row

    def _group_observations(
        self,
        observations: List[HarmonizedObservation],
        group_by: str,
    ) -> Dict[str, List[HarmonizedObservation]]:
        """Group observations by the specified key."""
        groups: Dict[str, List[HarmonizedObservation]] = defaultdict(list)

        key_func: Callable[[HarmonizedObservation], str]
        if group_by == "hour":
            key_func = lambda o: o.observation_time.strftime("%Y-%m-%d %H:00")
        elif group_by == "day":
            key_func = lambda o: o.observation_time.strftime("%Y-%m-%d")
        else:  # station
            key_func = lambda o: o.station_id or "unknown"

        for obs in observations:
            key = key_func(obs)
            groups[key].append(obs)

        return dict(groups)
