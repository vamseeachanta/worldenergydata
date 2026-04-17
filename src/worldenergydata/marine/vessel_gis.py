"""GIS integration for the heavy construction/installation vessel dataset.

Connects vessel records to spatial queries so agents can ask
"which vessels operate near field X?" and receive a filtered DataFrame
or a GeoJSON-compatible FeatureCollection for map visualisation.

No geopandas dependency: uses haversine distance and a simple
point-in-polygon ray-casting algorithm.
"""

from __future__ import annotations

import logging
import math
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known Gulf of Mexico field coordinates  (lat, lon)
# ---------------------------------------------------------------------------

GOM_FIELD_COORDS: dict[str, tuple[float, float]] = {
    "MARS": (27.97, -90.55),
    "THUNDER HORSE": (28.18, -88.47),
    "PERDIDO": (26.13, -94.90),
    "MAD DOG": (27.13, -91.20),
    "ATLANTIS": (27.20, -90.03),
    "CAESAR TONGA": (27.31, -90.54),
}

_EARTH_RADIUS_NM: float = 3440.065  # nautical miles


# ---------------------------------------------------------------------------
# Utility: haversine distance
# ---------------------------------------------------------------------------


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in nautical miles between two points.

    Args:
        lat1: Latitude of point 1 in decimal degrees.
        lon1: Longitude of point 1 in decimal degrees.
        lat2: Latitude of point 2 in decimal degrees.
        lon2: Longitude of point 2 in decimal degrees.

    Returns:
        Distance in nautical miles (>= 0).
    """
    if lat1 == lat2 and lon1 == lon2:
        return 0.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return _EARTH_RADIUS_NM * c


# ---------------------------------------------------------------------------
# Utility: point-in-polygon (ray casting, lon/lat coords)
# ---------------------------------------------------------------------------


def _point_in_polygon(lon: float, lat: float, polygon: list[tuple]) -> bool:
    """Return True when (lon, lat) lies inside a polygon.

    Args:
        lon: Point longitude.
        lat: Point latitude.
        polygon: List of (lon, lat) tuples forming a closed polygon.
            The last vertex is implicitly connected to the first.

    Returns:
        True if the point is inside the polygon, False otherwise.
    """
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / (yj - yi) + xi
        ):
            inside = not inside
        j = i
    return inside


# ---------------------------------------------------------------------------
# VesselGIS
# ---------------------------------------------------------------------------


class VesselGIS:
    """GIS integration for the heavy vessel dataset.

    Wraps a vessel DataFrame and exposes spatial query methods.
    Coordinate columns expected: ``lat`` and ``lon`` (decimal degrees).
    A ``vessel_id`` column is expected for ID-based filtering.

    Args:
        vessel_df: DataFrame of vessel records.  May be empty.
    """

    def __init__(self, vessel_df: pd.DataFrame) -> None:
        self._df = vessel_df.copy() if not vessel_df.empty else pd.DataFrame()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def query_vessels_by_field_area(
        self,
        field_name: str,
        bsee_fields_df: Optional[pd.DataFrame] = None,
        radius_nm: float = 50.0,
    ) -> pd.DataFrame:
        """Find vessels that operate in a given field area.

        Looks up field coordinates from *bsee_fields_df* when provided,
        falling back to the built-in :data:`GOM_FIELD_COORDS` dictionary.

        Args:
            field_name: Name of the field (case-insensitive).
            bsee_fields_df: Optional BSEE fields DataFrame with columns
                ``field_name``, ``lat``, ``lon``.
            radius_nm: Search radius in nautical miles.

        Returns:
            DataFrame of vessels within *radius_nm* of the field centre,
            with an added ``distance_nm`` column. Returns an empty
            DataFrame when the field is not found or no vessels match.
        """
        coords = self._resolve_field_coords(field_name, bsee_fields_df)
        if coords is None:
            logger.warning("Field not found: %s", field_name)
            return pd.DataFrame()

        lat, lon = coords
        return self.query_vessels_by_coords(lat, lon, radius_nm=radius_nm)

    def query_vessels_by_coords(
        self,
        lat: float,
        lon: float,
        radius_nm: float = 50.0,
    ) -> pd.DataFrame:
        """Find vessels within *radius_nm* of (lat, lon).

        Args:
            lat: Centre latitude in decimal degrees.
            lon: Centre longitude in decimal degrees.
            radius_nm: Search radius in nautical miles.

        Returns:
            DataFrame filtered to vessels within the radius, sorted by
            ascending ``distance_nm``.  Returns an empty DataFrame when
            no vessels qualify or the underlying dataset is empty.
        """
        if self._df.empty:
            return pd.DataFrame()

        if "lat" not in self._df.columns or "lon" not in self._df.columns:
            logger.warning("Vessel DataFrame missing lat/lon columns.")
            return pd.DataFrame()

        df = self._df.copy()
        df["distance_nm"] = df.apply(
            lambda row: haversine_nm(lat, lon, row["lat"], row["lon"]),
            axis=1,
        )
        result = df[df["distance_nm"] <= radius_nm].copy()
        return result.sort_values("distance_nm").reset_index(drop=True)

    def vessels_in_polygon(self, polygon_coords: list[tuple]) -> pd.DataFrame:
        """Find vessels whose position lies inside *polygon_coords*.

        Args:
            polygon_coords: List of ``(lon, lat)`` tuples defining the
                polygon vertices (need not be closed).

        Returns:
            DataFrame of vessels inside the polygon.  Returns an empty
            DataFrame when the dataset is empty or no vessels match.
        """
        if self._df.empty:
            return pd.DataFrame()

        if "lat" not in self._df.columns or "lon" not in self._df.columns:
            logger.warning("Vessel DataFrame missing lat/lon columns.")
            return pd.DataFrame()

        mask = self._df.apply(
            lambda row: _point_in_polygon(row["lon"], row["lat"], polygon_coords),
            axis=1,
        )
        return self._df[mask].copy().reset_index(drop=True)

    def get_vessel_map_data(self, vessel_ids: Optional[list[str]] = None) -> dict:
        """Return a GeoJSON FeatureCollection for map visualisation.

        Args:
            vessel_ids: Optional list of ``vessel_id`` values to include.
                When None, all vessels are returned.

        Returns:
            GeoJSON-compatible dict with ``type: "FeatureCollection"`` and
            a ``features`` list of Point Features.
        """
        if self._df.empty:
            return {"type": "FeatureCollection", "features": []}

        df = self._df.copy()

        if vessel_ids is not None and "vessel_id" in df.columns:
            df = df[df["vessel_id"].isin(vessel_ids)]

        if "lat" not in df.columns or "lon" not in df.columns:
            return {"type": "FeatureCollection", "features": []}

        features = []
        for _, row in df.iterrows():
            props = row.drop(labels=["lat", "lon"], errors="ignore").to_dict()
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [row["lon"], row["lat"]],
                    },
                    "properties": props,
                }
            )

        return {"type": "FeatureCollection", "features": features}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_field_coords(
        self,
        field_name: str,
        bsee_fields_df: Optional[pd.DataFrame],
    ) -> Optional[tuple[float, float]]:
        """Return (lat, lon) for *field_name* or None when not found.

        Searches *bsee_fields_df* first, then :data:`GOM_FIELD_COORDS`.

        Args:
            field_name: Field name string (matched case-insensitively).
            bsee_fields_df: Optional BSEE fields DataFrame with
                ``field_name``, ``lat``, ``lon`` columns.

        Returns:
            ``(lat, lon)`` tuple, or ``None`` when the field is unknown.
        """
        upper_name = field_name.strip().upper()

        if bsee_fields_df is not None and not bsee_fields_df.empty:
            col = "field_name" if "field_name" in bsee_fields_df.columns else None
            if col is not None:
                match = bsee_fields_df[bsee_fields_df[col].str.upper() == upper_name]
                if not match.empty:
                    row = match.iloc[0]
                    return float(row["lat"]), float(row["lon"])

        coords = GOM_FIELD_COORDS.get(upper_name)
        if coords is not None:
            return coords

        return None
