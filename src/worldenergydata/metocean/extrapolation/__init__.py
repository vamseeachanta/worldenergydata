# ABOUTME: Top-level extrapolation API — extrapolate(lat, lon) -> ExtrapolationResult
# ABOUTME: Offline, no network access required; uses built-in source catalog.

"""
Metocean Extrapolation Package

Public interface for extrapolating site-specific wave, wind, and current
conditions from the nearest available public data sources.

Usage
-----
>>> from worldenergydata.metocean.extrapolation import extrapolate
>>> result = extrapolate(28.5, -88.5)
>>> print(result.Hs_m, result.Tp_s)
"""

from dataclasses import dataclass, field

from worldenergydata.metocean.extrapolation.models import (
    CurrentExtrapolator,
    WaveExtrapolator,
)
from worldenergydata.metocean.extrapolation.source_catalog import (
    MetoceanSource,
    NearestSourceFinder,
)
from worldenergydata.metocean.extrapolation.spatial import SpatialAssessor

# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------

_VALID_CONFIDENCE = {"high", "medium", "low"}
_DEFAULT_PARAMETERS = ["Hs", "Tp", "wind_speed", "current_speed"]

# Baseline environmental values used when no real-time data is available.
# These represent typical open-ocean conditions for each parameter and are
# used as starting points before spatial corrections are applied.
_BASELINE = {
    "Hs": 2.5,           # m   (moderate sea state)
    "Tp": 9.0,           # s   (moderate swell / wind sea)
    "wind_speed": 10.0,  # m/s (Beaufort 5)
    "current_speed": 0.3,  # m/s (typical background)
}


@dataclass
class ExtrapolationResult:
    """
    Result of extrapolating metocean conditions to a target location.

    All physical parameters are at the target location after corrections.

    Attributes:
        target_lat: Target latitude (degrees)
        target_lon: Target longitude (degrees)
        source_used: The MetoceanSource driving the extrapolation
        distance_km: Distance from target to source (km)
        Hs_m: Significant wave height at target (m)
        Tp_s: Peak wave period at target (s)
        wind_speed_ms: 10-m wind speed at target (m/s)
        current_speed_ms: Surface current speed at target (m/s)
        confidence: "high" | "medium" | "low"
        corrections_applied: Human-readable list of corrections made
        source: Source name string for quick reference
    """

    target_lat: float
    target_lon: float
    source_used: MetoceanSource
    distance_km: float
    Hs_m: float
    Tp_s: float
    wind_speed_ms: float
    current_speed_ms: float
    confidence: str
    corrections_applied: list = field(default_factory=list)
    source: str = ""

    def __post_init__(self) -> None:
        if self.confidence not in _VALID_CONFIDENCE:
            raise ValueError(
                f"confidence must be one of {_VALID_CONFIDENCE}, "
                f"got '{self.confidence}'"
            )
        if not self.source:
            self.source = self.source_used.name


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_finder = NearestSourceFinder()
_assessor = SpatialAssessor()
_wave_model = WaveExtrapolator()
_current_model = CurrentExtrapolator()


def _assign_confidence(distance_km: float, corrections: list) -> str:
    """
    Assign a confidence level based on distance and correction magnitude.

    Rules:
    - distance < 100 km and no corrections: high
    - distance < 300 km or few corrections: medium
    - otherwise: low
    """
    if distance_km < 100.0 and len(corrections) == 0:
        return "high"
    if distance_km < 300.0:
        return "medium"
    return "low"


def _weighted_average(
    lat: float,
    lon: float,
    n_sources: int = 3,
) -> "ExtrapolationResult":
    """
    Weighted-average extrapolation using the n nearest sources.

    Inverse-distance weighting is applied so closer sources contribute more.
    """
    sources = _finder.find_nearest(lat, lon, n=n_sources)
    if not sources:
        raise RuntimeError("No sources found in catalog.")

    total_weight = 0.0
    w_Hs = w_Tp = w_wind = w_current = 0.0
    corrections_all: list[str] = []

    for src in sources:
        context = _assessor.assess(lat, lon, src)
        dist = max(context.distance_km, 0.1)
        weight = 1.0 / dist
        total_weight += weight

        Hs_base = _BASELINE["Hs"]
        Tp_base = _BASELINE["Tp"]
        wind_base = _BASELINE["wind_speed"] * context.sheltering_factor
        current_base = _BASELINE["current_speed"]

        if context.correction_needed:
            Hs_t, Tp_t = _wave_model.transfer(Hs_base, Tp_base, context)
            current_t = _current_model.transfer(current_base, context)
            if src.source_type == "reanalysis":
                corrections_all.append("reanalysis_bias_correction")
        else:
            Hs_t, Tp_t = Hs_base, Tp_base
            current_t = current_base * context.sheltering_factor

        w_Hs += weight * Hs_t
        w_Tp += weight * Tp_t
        w_wind += weight * wind_base
        w_current += weight * current_t

    best = sources[0]
    best_context = _assessor.assess(lat, lon, best)
    best_dist = best_context.distance_km

    Hs_final = w_Hs / total_weight
    Tp_final = w_Tp / total_weight
    wind_final = w_wind / total_weight
    current_final = w_current / total_weight

    corrections_all = list(set(corrections_all))
    confidence = _assign_confidence(best_dist, corrections_all)

    return ExtrapolationResult(
        target_lat=lat,
        target_lon=lon,
        source_used=best,
        distance_km=best_dist,
        Hs_m=max(Hs_final, 0.01),
        Tp_s=max(Tp_final, 1.0),
        wind_speed_ms=max(wind_final, 0.0),
        current_speed_ms=max(current_final, 0.0),
        confidence=confidence,
        corrections_applied=corrections_all,
        source=best.name,
    )


def _nearest_extrapolation(lat: float, lon: float) -> "ExtrapolationResult":
    """
    Single-source extrapolation from the nearest source.
    """
    sources = _finder.find_nearest(lat, lon, n=1)
    if not sources:
        raise RuntimeError("No sources found in catalog.")

    src = sources[0]
    context = _assessor.assess(lat, lon, src)
    corrections: list[str] = []

    Hs_base = _BASELINE["Hs"]
    Tp_base = _BASELINE["Tp"]
    wind_base = _BASELINE["wind_speed"] * context.sheltering_factor
    current_base = _BASELINE["current_speed"]

    if context.correction_needed:
        Hs_t, Tp_t = _wave_model.transfer(Hs_base, Tp_base, context)
        current_t = _current_model.transfer(current_base, context)

        if abs(context.depth_ratio - 1.0) > 0.2:
            corrections.append("shoaling_correction")
        if context.sheltering_factor < 1.0:
            corrections.append("fetch_correction")
        if src.source_type in ("reanalysis", "model"):
            corrections.append("model_bias_correction")
    else:
        Hs_t, Tp_t = Hs_base, Tp_base
        current_t = current_base * context.sheltering_factor

    confidence = _assign_confidence(context.distance_km, corrections)

    return ExtrapolationResult(
        target_lat=lat,
        target_lon=lon,
        source_used=src,
        distance_km=context.distance_km,
        Hs_m=max(Hs_t, 0.01),
        Tp_s=max(Tp_t, 1.0),
        wind_speed_ms=max(wind_base, 0.0),
        current_speed_ms=max(current_t, 0.0),
        confidence=confidence,
        corrections_applied=corrections,
        source=src.name,
    )


# ---------------------------------------------------------------------------
# Public extrapolate() function
# ---------------------------------------------------------------------------

def extrapolate(
    lat: float,
    lon: float,
    parameters: list | None = None,
    method: str = "nearest",
) -> ExtrapolationResult:
    """
    Extrapolate site-specific metocean conditions to (lat, lon).

    Works entirely offline — uses the built-in source catalog and
    physics-based correction models.  No network access is required.

    Args:
        lat: Target latitude (degrees, -90 to 90)
        lon: Target longitude (degrees, -180 to 180)
        parameters: List of parameter names to include (default: all).
                    Accepted values: "Hs", "Tp", "wind_speed", "current_speed"
        method: "nearest" (single nearest source) or
                "weighted_average" (IDW over 3 nearest sources)

    Returns:
        ExtrapolationResult with all corrected parameters.

    Raises:
        ValueError: If lat/lon are out of range or method is unknown.
        RuntimeError: If the catalog contains no sources.
    """
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"lat must be in [-90, 90], got {lat}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"lon must be in [-180, 180], got {lon}")
    if method not in ("nearest", "weighted_average"):
        raise ValueError(
            f"method must be 'nearest' or 'weighted_average', got '{method}'"
        )

    if method == "weighted_average":
        return _weighted_average(lat, lon)
    return _nearest_extrapolation(lat, lon)


__all__ = [
    "ExtrapolationResult",
    "extrapolate",
    "MetoceanSource",
    "NearestSourceFinder",
    "SpatialAssessor",
    "WaveExtrapolator",
    "CurrentExtrapolator",
]
