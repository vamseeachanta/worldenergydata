# ABOUTME: NetCDF exporter for metocean data following CF conventions.
# ABOUTME: Requires optional netCDF4 dependency for oceanographic data exchange.

"""
NetCDF Exporter for Metocean Data

Exports metocean observations to CF-compliant NetCDF format.
Requires netCDF4 package (optional dependency).

CF conventions: https://cfconventions.org/
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from worldenergydata.modules.metocean.exceptions import ExportError, ExportWriteError
from worldenergydata.modules.metocean.processors.data_harmonizer import (
    HarmonizedObservation,
)

# NetCDF4 is an optional dependency
try:
    import netCDF4 as nc

    HAS_NETCDF4 = True
except ImportError:
    nc = None  # type: ignore
    HAS_NETCDF4 = False

# NumPy is required if netCDF4 is available
try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore
    HAS_NUMPY = False


class NetCDFExporter:
    """
    Export metocean data to CF-compliant NetCDF format.

    Follows CF (Climate and Forecast) conventions for metadata.
    Suitable for exchange with oceanographic software.

    Requires: netCDF4 package (pip install netCDF4)

    CF Standard Names Table:
    https://cfconventions.org/Data/cf-standard-names/current/build/cf-standard-name-table.html

    Example usage:
        exporter = NetCDFExporter()

        # Export all observations
        count = exporter.export(
            observations,
            Path("output.nc"),
            title="GOM Buoy Data 2024"
        )

        # Export single station
        count = exporter.export_station(
            observations,
            station_id="42001",
            output_path=Path("station_42001.nc")
        )
    """

    # CF standard names for variables
    CF_STANDARD_NAMES: Dict[str, str] = {
        "wave_height_m": "sea_surface_wave_significant_height",
        "wave_period_s": "sea_surface_wave_mean_period",
        "wave_direction_deg": "sea_surface_wave_from_direction",
        "wind_speed_ms": "wind_speed",
        "wind_direction_deg": "wind_from_direction",
        "wind_gust_ms": "wind_speed_of_gust",
        "current_speed_ms": "sea_water_speed",
        "current_direction_deg": "direction_of_sea_water_velocity",
        "sea_surface_temp_c": "sea_surface_temperature",
        "air_temp_c": "air_temperature",
        "water_level_m": "sea_surface_height_above_geoid",
        "pressure_hpa": "air_pressure_at_sea_level",
    }

    # CF units for variables
    CF_UNITS: Dict[str, str] = {
        "wave_height_m": "m",
        "wave_period_s": "s",
        "wave_direction_deg": "degree",
        "wind_speed_ms": "m s-1",
        "wind_direction_deg": "degree",
        "wind_gust_ms": "m s-1",
        "current_speed_ms": "m s-1",
        "current_direction_deg": "degree",
        "sea_surface_temp_c": "degree_Celsius",
        "air_temp_c": "degree_Celsius",
        "water_level_m": "m",
        "pressure_hpa": "hPa",
    }

    # Long names for variables
    LONG_NAMES: Dict[str, str] = {
        "wave_height_m": "Significant Wave Height",
        "wave_period_s": "Mean Wave Period",
        "wave_direction_deg": "Mean Wave Direction",
        "wind_speed_ms": "Wind Speed",
        "wind_direction_deg": "Wind Direction",
        "wind_gust_ms": "Wind Gust Speed",
        "current_speed_ms": "Ocean Current Speed",
        "current_direction_deg": "Ocean Current Direction",
        "sea_surface_temp_c": "Sea Surface Temperature",
        "air_temp_c": "Air Temperature",
        "water_level_m": "Water Level",
        "pressure_hpa": "Atmospheric Pressure",
    }

    def __init__(self) -> None:
        """
        Initialize NetCDF exporter.

        Raises:
            ImportError: If netCDF4 package is not installed
        """
        if not HAS_NETCDF4:
            raise ImportError(
                "netCDF4 is required for NetCDF export. "
                "Install with: pip install netCDF4"
            )
        if not HAS_NUMPY:
            raise ImportError(
                "numpy is required for NetCDF export. "
                "Install with: pip install numpy"
            )

    def export(
        self,
        observations: List[HarmonizedObservation],
        output_path: Path,
        title: str = "Metocean Data Export",
        institution: str = "World Energy Data",
    ) -> int:
        """
        Export observations to NetCDF file.

        Creates a CF-compliant NetCDF4 file with:
        - Time dimension and coordinate variable
        - Latitude and longitude variables
        - Data variables with standard names and units
        - Global metadata attributes

        Args:
            observations: List of harmonized observations
            output_path: Output file path (.nc)
            title: Dataset title for global attributes
            institution: Institution name for global attributes

        Returns:
            Number of records exported

        Raises:
            ExportError: If no observations to export
            ExportWriteError: If writing to file fails
        """
        if not observations:
            raise ExportError("No observations to export")

        # Sort by time
        sorted_obs = sorted(observations, key=lambda x: x.observation_time)

        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Create NetCDF file
            with nc.Dataset(output_path, "w", format="NETCDF4") as ds:
                self._write_global_attributes(ds, sorted_obs, title, institution)
                self._create_dimensions(ds, len(sorted_obs))
                self._write_time_variable(ds, sorted_obs)
                self._write_coordinate_variables(ds, sorted_obs)
                self._write_data_variables(ds, sorted_obs)

            return len(sorted_obs)

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

    def export_station(
        self,
        observations: List[HarmonizedObservation],
        station_id: str,
        output_path: Path,
    ) -> int:
        """
        Export data for a single station.

        Args:
            observations: List of harmonized observations
            station_id: Station ID to filter
            output_path: Output file path (.nc)

        Returns:
            Number of records exported

        Raises:
            ExportError: If no observations for station
            ExportWriteError: If writing to file fails
        """
        station_obs = [o for o in observations if o.station_id == station_id]
        if not station_obs:
            raise ExportError(f"No observations found for station: {station_id}")
        return self.export(
            station_obs, output_path, title=f"Station {station_id} Metocean Data"
        )

    def export_by_source(
        self,
        observations: List[HarmonizedObservation],
        output_dir: Path,
    ) -> Dict[str, int]:
        """
        Export data grouped by source to separate files.

        Args:
            observations: List of harmonized observations
            output_dir: Directory for output files

        Returns:
            Dictionary mapping source names to record counts

        Raises:
            ExportError: If no observations to export
            ExportWriteError: If writing to file fails
        """
        if not observations:
            raise ExportError("No observations to export")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Group by source
        by_source: Dict[str, List[HarmonizedObservation]] = {}
        for obs in observations:
            source_name = obs.source.value
            if source_name not in by_source:
                by_source[source_name] = []
            by_source[source_name].append(obs)

        results: Dict[str, int] = {}
        for source_name, source_obs in by_source.items():
            output_path = output_dir / f"{source_name}_data.nc"
            count = self.export(
                source_obs,
                output_path,
                title=f"{source_name.upper()} Metocean Data",
            )
            results[source_name] = count

        return results

    def _write_global_attributes(
        self,
        ds: Any,
        observations: List[HarmonizedObservation],
        title: str,
        institution: str,
    ) -> None:
        """Write CF-compliant global attributes."""
        ds.Conventions = "CF-1.8"
        ds.title = title
        ds.institution = institution
        ds.source = "WorldEnergyData Metocean Module"
        ds.history = f"Created {datetime.utcnow().isoformat()} UTC"
        ds.references = "https://github.com/worldenergydata"

        # Data range
        times = [o.observation_time for o in observations]
        ds.time_coverage_start = min(times).isoformat()
        ds.time_coverage_end = max(times).isoformat()

        # Geographic extent
        lats = [o.latitude for o in observations if o.latitude is not None]
        lons = [o.longitude for o in observations if o.longitude is not None]
        if lats and lons:
            ds.geospatial_lat_min = min(lats)
            ds.geospatial_lat_max = max(lats)
            ds.geospatial_lon_min = min(lons)
            ds.geospatial_lon_max = max(lons)

        # Data sources
        sources = list(set(o.source.value for o in observations))
        ds.data_sources = ", ".join(sources)

    def _create_dimensions(self, ds: Any, n_obs: int) -> None:
        """Create NetCDF dimensions."""
        ds.createDimension("time", n_obs)

    def _write_time_variable(
        self, ds: Any, observations: List[HarmonizedObservation]
    ) -> None:
        """Write time coordinate variable."""
        start_time = observations[0].observation_time
        time_var = ds.createVariable("time", "f8", ("time",))
        time_var.units = f"hours since {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        time_var.calendar = "gregorian"
        time_var.standard_name = "time"
        time_var.long_name = "Observation Time"
        time_var.axis = "T"

        # Convert times to hours since start
        time_values = [
            (obs.observation_time - start_time).total_seconds() / 3600
            for obs in observations
        ]
        time_var[:] = np.array(time_values)

    def _write_coordinate_variables(
        self, ds: Any, observations: List[HarmonizedObservation]
    ) -> None:
        """Write latitude and longitude coordinate variables."""
        # Latitude
        lat_var = ds.createVariable("latitude", "f4", ("time",), fill_value=np.nan)
        lat_var.units = "degrees_north"
        lat_var.standard_name = "latitude"
        lat_var.long_name = "Station Latitude"
        lat_var.axis = "Y"
        lat_var.valid_range = np.array([-90.0, 90.0], dtype="f4")
        lat_var[:] = np.array(
            [
                obs.latitude if obs.latitude is not None else np.nan
                for obs in observations
            ],
            dtype="f4",
        )

        # Longitude
        lon_var = ds.createVariable("longitude", "f4", ("time",), fill_value=np.nan)
        lon_var.units = "degrees_east"
        lon_var.standard_name = "longitude"
        lon_var.long_name = "Station Longitude"
        lon_var.axis = "X"
        lon_var.valid_range = np.array([-180.0, 180.0], dtype="f4")
        lon_var[:] = np.array(
            [
                obs.longitude if obs.longitude is not None else np.nan
                for obs in observations
            ],
            dtype="f4",
        )

    def _write_data_variables(
        self, ds: Any, observations: List[HarmonizedObservation]
    ) -> None:
        """Write data variables with CF metadata."""
        variables_to_export = [
            "wave_height_m",
            "wave_period_s",
            "wave_direction_deg",
            "wind_speed_ms",
            "wind_direction_deg",
            "wind_gust_ms",
            "current_speed_ms",
            "current_direction_deg",
            "sea_surface_temp_c",
            "air_temp_c",
            "water_level_m",
            "pressure_hpa",
        ]

        for var_name in variables_to_export:
            values = [getattr(obs, var_name) for obs in observations]

            # Skip if all values are None
            if all(v is None for v in values):
                continue

            var = ds.createVariable(var_name, "f4", ("time",), fill_value=np.nan)
            var.units = self.CF_UNITS.get(var_name, "1")
            var.standard_name = self.CF_STANDARD_NAMES.get(var_name, var_name)
            var.long_name = self.LONG_NAMES.get(var_name, var_name)

            # Add valid_range for direction variables
            if "direction" in var_name:
                var.valid_range = np.array([0.0, 360.0], dtype="f4")

            var[:] = np.array(
                [v if v is not None else np.nan for v in values], dtype="f4"
            )


def is_netcdf_available() -> bool:
    """Check if NetCDF export is available."""
    return HAS_NETCDF4 and HAS_NUMPY
