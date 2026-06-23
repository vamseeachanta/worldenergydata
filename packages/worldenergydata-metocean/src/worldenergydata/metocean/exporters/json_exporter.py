# ABOUTME: JSON exporter for metocean data with metadata and GeoJSON support.
# ABOUTME: Supports pretty printing, nested structures, and geographic data export.

"""
JSON Exporter for Metocean Data

Exports metocean observations to JSON format with metadata.
Includes GeoJSON export for geographic visualization.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from worldenergydata.metocean.exceptions import ExportError, ExportWriteError
from worldenergydata.metocean.processors.data_harmonizer import (
    HarmonizedObservation,
)


class JSONExporter:
    """
    Export metocean data to JSON format.

    Features:
    - Pretty printing option
    - Metadata inclusion (export time, sources, date range)
    - Date range filtering
    - GeoJSON export for geographic data

    Example usage:
        exporter = JSONExporter(pretty=True, include_metadata=True)

        # Export to JSON
        count = exporter.export(observations, Path("output.json"))

        # Export as GeoJSON for mapping
        count = exporter.export_geojson(observations, Path("output.geojson"))
    """

    def __init__(
        self,
        pretty: bool = True,
        include_metadata: bool = True,
    ):
        """
        Initialize JSON exporter.

        Args:
            pretty: Whether to pretty-print with indentation
            include_metadata: Whether to include export metadata
        """
        self.pretty = pretty
        self.include_metadata = include_metadata

    def export(
        self,
        observations: List[HarmonizedObservation],
        output_path: Path,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """
        Export observations to JSON file.

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

        # Build output structure
        output: Dict[str, Any] = {
            "records": [obs.to_dict() for obs in filtered],
            "count": len(filtered),
        }

        if self.include_metadata:
            output["metadata"] = self._build_metadata(filtered, start_date, end_date)

        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    output,
                    f,
                    indent=2 if self.pretty else None,
                    default=self._json_serializer,
                )
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

    def export_geojson(
        self,
        observations: List[HarmonizedObservation],
        output_path: Path,
    ) -> int:
        """
        Export as GeoJSON FeatureCollection.

        Only includes observations with valid latitude/longitude.
        Each observation becomes a Point feature with properties.

        Args:
            observations: List of harmonized observations
            output_path: Output file path (.geojson)

        Returns:
            Number of features exported

        Raises:
            ExportError: If no observations with coordinates
            ExportWriteError: If writing to file fails
        """
        features: List[Dict[str, Any]] = []

        for obs in observations:
            if obs.latitude is not None and obs.longitude is not None:
                feature = self._observation_to_geojson_feature(obs)
                features.append(feature)

        if not features:
            raise ExportError(
                "No observations with valid coordinates for GeoJSON export"
            )

        geojson: Dict[str, Any] = {
            "type": "FeatureCollection",
            "features": features,
        }

        if self.include_metadata:
            geojson["properties"] = {
                "exported_at": datetime.utcnow().isoformat(),
                "feature_count": len(features),
                "sources": list(set(obs.source.value for obs in observations)),
            }

        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    geojson,
                    f,
                    indent=2 if self.pretty else None,
                    default=self._json_serializer,
                )
            return len(features)

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

    def export_by_station(
        self,
        observations: List[HarmonizedObservation],
        output_path: Path,
    ) -> int:
        """
        Export JSON organized by station ID.

        Creates a nested structure with station IDs as keys.

        Args:
            observations: List of harmonized observations
            output_path: Output file path

        Returns:
            Number of stations exported

        Raises:
            ExportError: If no observations to export
            ExportWriteError: If writing to file fails
        """
        if not observations:
            raise ExportError("No observations to export")

        # Group by station
        by_station: Dict[str, List[Dict[str, Any]]] = {}
        for obs in observations:
            station_id = obs.station_id or "unknown"
            if station_id not in by_station:
                by_station[station_id] = []
            by_station[station_id].append(obs.to_dict())

        output: Dict[str, Any] = {
            "stations": by_station,
            "station_count": len(by_station),
            "total_observations": len(observations),
        }

        if self.include_metadata:
            output["metadata"] = {
                "exported_at": datetime.utcnow().isoformat(),
                "sources": list(set(obs.source.value for obs in observations)),
            }

        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    output,
                    f,
                    indent=2 if self.pretty else None,
                    default=self._json_serializer,
                )
            return len(by_station)

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

    def _build_metadata(
        self,
        observations: List[HarmonizedObservation],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> Dict[str, Any]:
        """Build metadata dictionary for export."""
        sources = list(set(o.source.value for o in observations))
        stations = list(set(o.station_id for o in observations if o.station_id))

        # Find actual date range in data
        times = [o.observation_time for o in observations]
        data_start = min(times) if times else None
        data_end = max(times) if times else None

        return {
            "exported_at": datetime.utcnow().isoformat(),
            "filter_start_date": start_date.isoformat() if start_date else None,
            "filter_end_date": end_date.isoformat() if end_date else None,
            "data_start_date": data_start.isoformat() if data_start else None,
            "data_end_date": data_end.isoformat() if data_end else None,
            "sources": sources,
            "station_ids": stations,
            "station_count": len(stations),
        }

    def _observation_to_geojson_feature(
        self, obs: HarmonizedObservation
    ) -> Dict[str, Any]:
        """Convert observation to GeoJSON Feature."""
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [obs.longitude, obs.latitude],
            },
            "properties": {
                "observation_time": obs.observation_time.isoformat(),
                "source": obs.source.value,
                "station_id": obs.station_id,
                "wave_height_m": obs.wave_height_m,
                "wave_period_s": obs.wave_period_s,
                "wave_direction_deg": obs.wave_direction_deg,
                "wind_speed_ms": obs.wind_speed_ms,
                "wind_direction_deg": obs.wind_direction_deg,
                "sea_surface_temp_c": obs.sea_surface_temp_c,
                "water_level_m": obs.water_level_m,
                "pressure_hpa": obs.pressure_hpa,
                "quality_flag": obs.quality_flag.value,
            },
        }

    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for non-standard types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "value"):  # Enum
            return obj.value
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
