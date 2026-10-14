# ABOUTME: Catalog of available public metocean data sources with coverage polygons.
# ABOUTME: NearestSourceFinder identifies the best source(s) for a target (lat, lon).

"""
Metocean Source Catalog

Provides a built-in catalog of public metocean data sources (NDBC buoys,
CO-OPS stations, ERA5/CFSR reanalysis, OpenMeteo, Met Norway) and a
NearestSourceFinder that locates the best source(s) for a target (lat, lon).
"""

import math
from dataclasses import dataclass, field

EARTH_RADIUS_KM = 6371.0


@dataclass
class MetoceanSource:
    """
    Represents a single public metocean data source.

    Attributes:
        name: Short identifier, e.g. "ndbc_41001"
        source_type: "buoy" | "tide_gauge" | "reanalysis" | "model"
        lat: Station/grid-centre latitude
        lon: Station/grid-centre longitude
        coverage_radius_km: Effective spatial coverage radius
        parameters: Physical variables this source provides
        priority: 1=highest quality (measured), 3=lowest (reanalysis)
        region: Rough geographic label for filtering
    """

    name: str
    source_type: str
    lat: float
    lon: float
    coverage_radius_km: float
    parameters: list = field(default_factory=list)
    priority: int = 2
    region: str = "global"


class NearestSourceFinder:
    """
    Finds the nearest / most relevant metocean source(s) for a target location.

    Uses the built-in catalog which includes ~30 NDBC buoys, 5 CO-OPS
    tide-gauge stations, ERA5 global reanalysis, CFSR global reanalysis,
    OpenMeteo global model, and Met Norway NWP coverage.
    """

    def __init__(self) -> None:
        self._catalog: list[MetoceanSource] = _build_catalog()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_sources(self) -> list[MetoceanSource]:
        """Return all sources in the catalog."""
        return list(self._catalog)

    def find_nearest(self, lat: float, lon: float, n: int = 3) -> list[MetoceanSource]:
        """
        Return the n nearest sources sorted by great-circle distance.

        Args:
            lat: Target latitude
            lon: Target longitude
            n: Maximum number of sources to return

        Returns:
            List of MetoceanSource sorted nearest-first (length <= n).
        """
        if not self._catalog:
            return []

        ranked = sorted(
            self._catalog,
            key=lambda s: self.distance_km(lat, lon, s.lat, s.lon),
        )
        return ranked[:n]

    def find_by_parameter(
        self, lat: float, lon: float, parameter: str
    ) -> list[MetoceanSource]:
        """
        Return sources that provide *parameter*, sorted nearest-first.

        Args:
            lat: Target latitude
            lon: Target longitude
            parameter: Variable name, e.g. "Hs", "wind_speed", "current_speed"

        Returns:
            List of MetoceanSource providing the requested parameter.
        """
        matching = [s for s in self._catalog if parameter in s.parameters]
        return sorted(
            matching,
            key=lambda s: self.distance_km(lat, lon, s.lat, s.lon),
        )

    @staticmethod
    def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Haversine great-circle distance between two coordinates.

        Args:
            lat1, lon1: First point (degrees)
            lat2, lon2: Second point (degrees)

        Returns:
            Distance in kilometres.
        """
        lat1_r = math.radians(lat1)
        lat2_r = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return EARTH_RADIUS_KM * c


# ---------------------------------------------------------------------------
# Catalog builder — 30+ representative sources
# ---------------------------------------------------------------------------

_WAVE_WIND = ["Hs", "Tp", "wind_speed", "wind_direction"]
_WAVE_WIND_CURRENT = _WAVE_WIND + ["current_speed", "current_direction"]
_FULL = _WAVE_WIND_CURRENT + ["water_temperature", "air_temperature", "pressure"]
_REANALYSIS = _FULL + ["Hs_swell", "Tp_swell", "wave_direction"]
_WIND_ONLY = ["wind_speed", "wind_direction", "air_temperature", "pressure"]
_TIDE_PARAMS = ["water_level", "tidal_current", "current_speed", "wind_speed"]


def _buoy(
    name: str,
    lat: float,
    lon: float,
    region: str,
    params: list | None = None,
    radius_km: float = 200.0,
) -> MetoceanSource:
    return MetoceanSource(
        name=name,
        source_type="buoy",
        lat=lat,
        lon=lon,
        coverage_radius_km=radius_km,
        parameters=params if params is not None else _WAVE_WIND,
        priority=1,
        region=region,
    )


def _tide_gauge(
    name: str,
    lat: float,
    lon: float,
    region: str,
) -> MetoceanSource:
    return MetoceanSource(
        name=name,
        source_type="tide_gauge",
        lat=lat,
        lon=lon,
        coverage_radius_km=100.0,
        parameters=_TIDE_PARAMS,
        priority=1,
        region=region,
    )


def _reanalysis(
    name: str,
    lat: float,
    lon: float,
    region: str,
    radius_km: float = 5000.0,
) -> MetoceanSource:
    return MetoceanSource(
        name=name,
        source_type="reanalysis",
        lat=lat,
        lon=lon,
        coverage_radius_km=radius_km,
        parameters=_REANALYSIS,
        priority=3,
        region=region,
    )


def _model(
    name: str,
    lat: float,
    lon: float,
    region: str,
    radius_km: float = 5000.0,
) -> MetoceanSource:
    return MetoceanSource(
        name=name,
        source_type="model",
        lat=lat,
        lon=lon,
        coverage_radius_km=radius_km,
        parameters=_REANALYSIS,
        priority=3,
        region=region,
    )


def _build_catalog() -> list[MetoceanSource]:
    """Load legacy representative entries; these do not establish data readiness."""
    from worldenergydata.metocean.source_register import load_register

    return [MetoceanSource(**row) for row in load_register()["legacy_catalog"]]
