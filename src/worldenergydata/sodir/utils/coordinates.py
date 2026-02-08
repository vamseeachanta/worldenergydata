"""
Coordinate transformation utilities for SODIR data.

Handles conversion between:
- UTM (Universal Transverse Mercator) coordinates
- WGS84 (World Geodetic System 1984) coordinates

Norwegian Continental Shelf typically uses UTM zones 31-35.
"""

import logging
import math
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class CoordinateTransformer:
    """Transform coordinates between UTM and WGS84 systems."""

    # WGS84 ellipsoid parameters
    WGS84_A = 6378137.0  # Semi-major axis in meters
    WGS84_F = 1 / 298.257223563  # Flattening
    WGS84_E2 = 2 * WGS84_F - WGS84_F**2  # First eccentricity squared

    # UTM parameters
    UTM_K0 = 0.9996  # Scale factor
    UTM_E_PRIME_2 = WGS84_E2 / (1 - WGS84_E2)  # Second eccentricity squared

    def __init__(self):
        """Initialize the CoordinateTransformer."""
        self.conversions_count = 0
        self.error_count = 0

        # Try to import pyproj for more accurate conversions
        self.use_pyproj = False
        try:
            import pyproj

            self.use_pyproj = True
            self.pyproj = pyproj
            logger.info("Using pyproj for coordinate transformations")
        except ImportError:
            logger.warning(
                "pyproj not available, using internal transformation methods"
            )

    def utm_to_wgs84(
        self,
        easting: float,
        northing: float,
        zone: int,
        northern_hemisphere: bool = True,
    ) -> Tuple[float, float]:
        """
        Convert UTM coordinates to WGS84 latitude/longitude.

        Args:
            easting: UTM easting in meters
            northing: UTM northing in meters
            zone: UTM zone number (1-60)
            northern_hemisphere: True for northern hemisphere

        Returns:
            Tuple of (latitude, longitude) in decimal degrees
        """
        try:
            if self.use_pyproj:
                return self._utm_to_wgs84_pyproj(
                    easting, northing, zone, northern_hemisphere
                )
            else:
                return self._utm_to_wgs84_internal(
                    easting, northing, zone, northern_hemisphere
                )
        except Exception as e:
            logger.error(f"Error converting UTM to WGS84: {str(e)}")
            self.error_count += 1
            raise

    def wgs84_to_utm(
        self, latitude: float, longitude: float
    ) -> Tuple[float, float, int]:
        """
        Convert WGS84 latitude/longitude to UTM coordinates.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees

        Returns:
            Tuple of (easting, northing, zone)
        """
        try:
            if self.use_pyproj:
                return self._wgs84_to_utm_pyproj(latitude, longitude)
            else:
                return self._wgs84_to_utm_internal(latitude, longitude)
        except Exception as e:
            logger.error(f"Error converting WGS84 to UTM: {str(e)}")
            self.error_count += 1
            raise

    def batch_utm_to_wgs84(
        self, coordinates: List[Tuple[float, float, int]]
    ) -> List[Tuple[float, float]]:
        """
        Convert multiple UTM coordinates to WGS84.

        Args:
            coordinates: List of (easting, northing, zone) tuples

        Returns:
            List of (latitude, longitude) tuples
        """
        results = []
        for easting, northing, zone in coordinates:
            try:
                lat, lon = self.utm_to_wgs84(easting, northing, zone)
                results.append((lat, lon))
            except Exception as e:
                logger.error(
                    f"Error in batch conversion for {easting}, {northing}, zone {zone}: {str(e)}"
                )
                results.append((None, None))
        return results

    def _utm_to_wgs84_pyproj(
        self,
        easting: float,
        northing: float,
        zone: int,
        northern_hemisphere: bool = True,
    ) -> Tuple[float, float]:
        """
        Convert UTM to WGS84 using pyproj library.

        Args:
            easting: UTM easting in meters
            northing: UTM northing in meters
            zone: UTM zone number
            northern_hemisphere: True for northern hemisphere

        Returns:
            Tuple of (latitude, longitude) in decimal degrees
        """
        # Create projection strings
        utm_proj = self.pyproj.Proj(
            proj="utm", zone=zone, ellps="WGS84", south=not northern_hemisphere
        )
        wgs84_proj = self.pyproj.Proj(proj="latlong", ellps="WGS84")

        # Transform coordinates
        lon, lat = self.pyproj.transform(utm_proj, wgs84_proj, easting, northing)

        self.conversions_count += 1
        return (lat, lon)

    def _wgs84_to_utm_pyproj(
        self, latitude: float, longitude: float
    ) -> Tuple[float, float, int]:
        """
        Convert WGS84 to UTM using pyproj library.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees

        Returns:
            Tuple of (easting, northing, zone)
        """
        # Calculate UTM zone
        zone = self._calculate_utm_zone(longitude)

        # Create projection strings
        utm_proj = self.pyproj.Proj(
            proj="utm", zone=zone, ellps="WGS84", south=(latitude < 0)
        )
        wgs84_proj = self.pyproj.Proj(proj="latlong", ellps="WGS84")

        # Transform coordinates
        easting, northing = self.pyproj.transform(
            wgs84_proj, utm_proj, longitude, latitude
        )

        self.conversions_count += 1
        return (easting, northing, zone)

    def _utm_to_wgs84_internal(
        self,
        easting: float,
        northing: float,
        zone: int,
        northern_hemisphere: bool = True,
    ) -> Tuple[float, float]:
        """
        Convert UTM to WGS84 using internal calculation (less accurate than pyproj).

        Args:
            easting: UTM easting in meters
            northing: UTM northing in meters
            zone: UTM zone number
            northern_hemisphere: True for northern hemisphere

        Returns:
            Tuple of (latitude, longitude) in decimal degrees
        """
        # Remove false easting/northing
        x = easting - 500000.0  # Remove false easting
        y = northing

        if not northern_hemisphere:
            y -= 10000000.0  # Remove false northing for southern hemisphere

        # Calculate footpoint latitude
        M = y / self.UTM_K0
        mu = M / (
            self.WGS84_A
            * (
                1
                - self.WGS84_E2 / 4
                - 3 * self.WGS84_E2**2 / 64
                - 5 * self.WGS84_E2**3 / 256
            )
        )

        # Calculate latitude coefficients
        e1 = (1 - math.sqrt(1 - self.WGS84_E2)) / (1 + math.sqrt(1 - self.WGS84_E2))

        # Footpoint latitude
        phi1 = (
            mu
            + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu)
            + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
            + (151 * e1**3 / 96) * math.sin(6 * mu)
        )

        # Calculate latitude and longitude
        N1 = self.WGS84_A / math.sqrt(1 - self.WGS84_E2 * math.sin(phi1) ** 2)
        T1 = math.tan(phi1) ** 2
        C1 = self.UTM_E_PRIME_2 * math.cos(phi1) ** 2
        R1 = (
            self.WGS84_A
            * (1 - self.WGS84_E2)
            / (1 - self.WGS84_E2 * math.sin(phi1) ** 2) ** 1.5
        )
        D = x / (N1 * self.UTM_K0)

        # Calculate latitude
        lat = phi1 - (N1 * math.tan(phi1) / R1) * (
            D**2 / 2
            - (5 + 3 * T1 + 10 * C1 - 4 * C1**2 - 9 * self.UTM_E_PRIME_2) * D**4 / 24
            + (
                61
                + 90 * T1
                + 298 * C1
                + 45 * T1**2
                - 252 * self.UTM_E_PRIME_2
                - 3 * C1**2
            )
            * D**6
            / 720
        )

        # Calculate longitude
        lon = (
            D
            - (1 + 2 * T1 + C1) * D**3 / 6
            + (5 - 2 * C1 + 28 * T1 - 3 * C1**2 + 8 * self.UTM_E_PRIME_2 + 24 * T1**2)
            * D**5
            / 120
        ) / math.cos(phi1)

        # Add central meridian
        lon += math.radians((zone - 1) * 6 - 180 + 3)

        # Convert to degrees
        lat_deg = math.degrees(lat)
        lon_deg = math.degrees(lon)

        self.conversions_count += 1
        return (lat_deg, lon_deg)

    def _wgs84_to_utm_internal(
        self, latitude: float, longitude: float
    ) -> Tuple[float, float, int]:
        """
        Convert WGS84 to UTM using internal calculation (less accurate than pyproj).

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees

        Returns:
            Tuple of (easting, northing, zone)
        """
        # Calculate UTM zone
        zone = self._calculate_utm_zone(longitude)

        # Convert to radians
        lat_rad = math.radians(latitude)
        lon_rad = math.radians(longitude)

        # Calculate central meridian
        lon0 = math.radians((zone - 1) * 6 - 180 + 3)

        # Calculate parameters
        N = self.WGS84_A / math.sqrt(1 - self.WGS84_E2 * math.sin(lat_rad) ** 2)
        T = math.tan(lat_rad) ** 2
        C = self.UTM_E_PRIME_2 * math.cos(lat_rad) ** 2
        A = math.cos(lat_rad) * (lon_rad - lon0)

        # Calculate M (meridional arc)
        M = self.WGS84_A * (
            (
                1
                - self.WGS84_E2 / 4
                - 3 * self.WGS84_E2**2 / 64
                - 5 * self.WGS84_E2**3 / 256
            )
            * lat_rad
            - (
                3 * self.WGS84_E2 / 8
                + 3 * self.WGS84_E2**2 / 32
                + 45 * self.WGS84_E2**3 / 1024
            )
            * math.sin(2 * lat_rad)
            + (15 * self.WGS84_E2**2 / 256 + 45 * self.WGS84_E2**3 / 1024)
            * math.sin(4 * lat_rad)
            - (35 * self.WGS84_E2**3 / 3072) * math.sin(6 * lat_rad)
        )

        # Calculate easting
        easting = (
            self.UTM_K0
            * N
            * (
                A
                + (1 - T + C) * A**3 / 6
                + (5 - 18 * T + T**2 + 72 * C - 58 * self.UTM_E_PRIME_2) * A**5 / 120
            )
            + 500000.0
        )  # Add false easting

        # Calculate northing
        northing = self.UTM_K0 * (
            M
            + N
            * math.tan(lat_rad)
            * (
                A**2 / 2
                + (5 - T + 9 * C + 4 * C**2) * A**4 / 24
                + (61 - 58 * T + T**2 + 600 * C - 330 * self.UTM_E_PRIME_2) * A**6 / 720
            )
        )

        # Add false northing for southern hemisphere
        if latitude < 0:
            northing += 10000000.0

        self.conversions_count += 1
        return (easting, northing, zone)

    def _calculate_utm_zone(self, longitude: float) -> int:
        """
        Calculate UTM zone from longitude.

        Args:
            longitude: Longitude in decimal degrees

        Returns:
            UTM zone number (1-60)
        """
        # Special cases for Norway (zones 31-35)
        # Standard calculation
        zone = int((longitude + 180) / 6) + 1

        # Handle special cases at zone boundaries
        if zone > 60:
            zone = 60
        elif zone < 1:
            zone = 1

        return zone

    def validate_norwegian_coordinates(self, latitude: float, longitude: float) -> bool:
        """
        Validate if coordinates are within Norwegian Continental Shelf area.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees

        Returns:
            True if coordinates are valid for Norwegian waters
        """
        # Norwegian Continental Shelf approximate bounds
        # Latitude: 56°N to 72°N
        # Longitude: 5°W to 35°E

        if latitude < 56 or latitude > 72:
            return False

        if longitude < -5 or longitude > 35:
            return False

        return True

    def get_statistics(self) -> dict:
        """
        Get transformation statistics.

        Returns:
            Dictionary with conversion counts
        """
        return {
            "conversions": self.conversions_count,
            "errors": self.error_count,
            "using_pyproj": self.use_pyproj,
        }
