# ABOUTME: Coverage rules — which metocean clients cover a given lat/lon.
# ABOUTME: Returns an ordered list of source names based on geographic coverage and priority.

"""
MetoceanCoverage: Geographic Coverage Rules

Determines which metocean data sources cover a specific lat/lon coordinate
and returns them in priority order: measured > reanalysis > forecast.

Coverage zones:
- NDBC:       US coastal/offshore (lat 15-65N, lon 60-180W)
- COOPS:      US tidal stations   (lat 15-65N, lon 60-180W)
- Met Norway: Norwegian waters    (lat 55-82N, lon 10W-35E)
- OpenMeteo:  global (any lat/lon) — forecast + historical reanalysis
- ERDDAP:     global gridded (any lat/lon) — slower, used as fallback
"""

from typing import List

# Source priority order within each tier
# Tier 0 = measured observations (highest priority)
# Tier 1 = reanalysis
# Tier 2 = forecast / model (lowest priority)
_SOURCE_PRIORITY = {
    "ndbc": 0,
    "coops": 0,
    "met_norway": 1,
    "open_meteo": 2,
    "erddap": 3,
}


class MetoceanCoverage:
    """
    Determines geographic coverage for each metocean data source.

    Uses bounding-box rules to decide which clients can provide data
    for a given coordinate, then returns them sorted by source priority
    (measured > reanalysis > forecast).

    Example:
        cov = MetoceanCoverage()
        sources = cov.get_clients(28.5, -88.5)
        # ['ndbc', 'coops', 'open_meteo', 'erddap']
    """

    # NDBC + CO-OPS: US coastal and offshore waters
    _NDBC_LAT_MIN = 15.0
    _NDBC_LAT_MAX = 65.0
    _NDBC_LON_MIN = -180.0  # western most: 180W
    _NDBC_LON_MAX = -60.0  # eastern most: 60W

    # Met Norway: Norwegian and adjacent seas
    _MET_NORWAY_LAT_MIN = 55.0
    _MET_NORWAY_LAT_MAX = 82.0
    _MET_NORWAY_LON_MIN = -10.0
    _MET_NORWAY_LON_MAX = 35.0

    def _covers_ndbc(self, lat: float, lon: float) -> bool:
        """Return True if coordinates fall within NDBC coverage zone."""
        return (
            self._NDBC_LAT_MIN <= lat <= self._NDBC_LAT_MAX
            and self._NDBC_LON_MIN <= lon <= self._NDBC_LON_MAX
        )

    def _covers_coops(self, lat: float, lon: float) -> bool:
        """Return True if coordinates fall within CO-OPS coverage zone."""
        return self._covers_ndbc(lat, lon)

    def _covers_met_norway(self, lat: float, lon: float) -> bool:
        """Return True if coordinates fall within Met Norway coverage zone."""
        return (
            self._MET_NORWAY_LAT_MIN <= lat <= self._MET_NORWAY_LAT_MAX
            and self._MET_NORWAY_LON_MIN <= lon <= self._MET_NORWAY_LON_MAX
        )

    def get_clients(self, lat: float, lon: float) -> List[str]:
        """
        Return source names that cover the given coordinate, ordered by priority.

        Priority order: measured (NDBC, CO-OPS) > reanalysis (Met Norway) >
        forecast (OpenMeteo) > fallback (ERDDAP).

        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees

        Returns:
            Ordered list of source identifier strings
        """
        sources: List[str] = []

        # Regional measured sources (highest priority)
        if self._covers_ndbc(lat, lon):
            sources.append("ndbc")
        if self._covers_coops(lat, lon):
            sources.append("coops")
        if self._covers_met_norway(lat, lon):
            sources.append("met_norway")

        # Global sources (always available)
        sources.append("open_meteo")
        sources.append("erddap")

        # Sort by priority tier (stable sort preserves insertion order within tier)
        sources.sort(key=lambda s: _SOURCE_PRIORITY.get(s, 99))

        return sources
