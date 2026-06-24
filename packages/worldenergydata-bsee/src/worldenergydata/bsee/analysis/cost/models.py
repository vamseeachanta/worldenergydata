# ABOUTME: Core data models for WRK-171 sanctioned project cost calibration.
# ABOUTME: Defines CostRecord schema, CostEstimate output, and CalibrationComparison.

"""Data models for sanctioned project cost calibration (WRK-171).

Depth band boundaries (metres):
    Water: shallow <=300, mid <=1524 (5000 ft), deep <=3048 (10 000 ft), ultra_deep >3048
    Well:  shallow <=3048 (10 000 ft), medium <=6096 (20 000 ft),
           deep <=7620 (25 000 ft), ultra_deep >7620
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class WaterDepthBand(str, Enum):
    """Water depth classification (metres)."""

    SHALLOW = "shallow"  # <=300 m (~1 000 ft)
    MID = "mid"  # 301–1 524 m (~1 000–5 000 ft)
    DEEP = "deep"  # 1 525–3 048 m (~5 000–10 000 ft)
    ULTRA_DEEP = "ultra_deep"  # >3 048 m (>10 000 ft)


class WellDepthBand(str, Enum):
    """Total well depth classification (TVD metres)."""

    SHALLOW = "shallow"  # <=3 048 m (~10 000 ft)
    MEDIUM = "medium"  # 3 049–6 096 m (~10 000–20 000 ft)
    DEEP = "deep"  # 6 097–7 620 m (~20 000–25 000 ft)
    ULTRA_DEEP = "ultra_deep"  # >7 620 m (>25 000 ft)


class RigType(str, Enum):
    """Drilling rig type."""

    DRILLSHIP = "drillship"
    SEMI_SUB = "semi_sub"
    JACK_UP = "jack_up"
    PLATFORM = "platform"
    LAND_RIG = "land_rig"


class ActivityType(str, Enum):
    """Well activity category."""

    DRILLING = "drilling"
    COMPLETION = "completion"
    INTERVENTION = "intervention"


class CostType(str, Enum):
    """What the cost covers."""

    WELL_COST = "well_cost"
    DAY_RATE = "day_rate"
    TOTAL_CAPEX = "total_capex"


class ConfidenceLevel(str, Enum):
    """Data quality / estimation confidence."""

    HIGH = "high"  # Calibrated model, >=5 data points per cell
    MEDIUM = "medium"  # Proxy estimate or sparse calibration (1–4 points)
    LOW = "low"  # Extrapolated or benchmark-only


# ---------------------------------------------------------------------------
# Depth-band classifiers
# ---------------------------------------------------------------------------

_WATER_DEPTH_THRESHOLDS = (
    (300.0, WaterDepthBand.SHALLOW),
    (1524.0, WaterDepthBand.MID),
    (3048.0, WaterDepthBand.DEEP),
)

_WELL_DEPTH_THRESHOLDS = (
    (3048.0, WellDepthBand.SHALLOW),
    (6096.0, WellDepthBand.MEDIUM),
    (7620.0, WellDepthBand.DEEP),
)


def classify_water_depth_band(depth_m: float) -> WaterDepthBand:
    """Return the WaterDepthBand for a given depth in metres."""
    for threshold, band in _WATER_DEPTH_THRESHOLDS:
        if depth_m <= threshold:
            return band
    return WaterDepthBand.ULTRA_DEEP


def classify_well_depth_band(depth_m: float) -> WellDepthBand:
    """Return the WellDepthBand for a given TVD in metres."""
    for threshold, band in _WELL_DEPTH_THRESHOLDS:
        if depth_m <= threshold:
            return band
    return WellDepthBand.ULTRA_DEEP


# ---------------------------------------------------------------------------
# CostRecord — sanctioned project data point
# ---------------------------------------------------------------------------


@dataclass
class CostRecord:
    """A single sanctioned-project cost data point.

    Auto-computes water_depth_band and well_depth_band from metric depths.

    Raises:
        ValueError: If cost_usd_mm is not positive.
    """

    project_name: str
    region: str
    water_depth_m: float
    well_depth_m: float
    operator: str
    year_sanction: int
    year_drilling: int
    rig_type: RigType
    activity_type: ActivityType
    hpht: bool
    subsea: bool
    cost_usd_mm: float
    cost_type: CostType
    source: str
    confidence: ConfidenceLevel
    notes: str = ""

    # Computed in __post_init__
    water_depth_band: WaterDepthBand = field(init=False)
    well_depth_band: WellDepthBand = field(init=False)

    def __post_init__(self) -> None:
        if self.cost_usd_mm <= 0.0:
            raise ValueError(f"cost_usd_mm must be positive, got {self.cost_usd_mm}")
        self.water_depth_band = classify_water_depth_band(self.water_depth_m)
        self.well_depth_band = classify_well_depth_band(self.well_depth_m)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a flat dict suitable for DataFrame construction."""
        return {
            "project_name": self.project_name,
            "region": self.region,
            "water_depth_m": self.water_depth_m,
            "water_depth_band": self.water_depth_band.value,
            "well_depth_m": self.well_depth_m,
            "well_depth_band": self.well_depth_band.value,
            "operator": self.operator,
            "year_sanction": self.year_sanction,
            "year_drilling": self.year_drilling,
            "rig_type": self.rig_type.value,
            "activity_type": self.activity_type.value,
            "hpht": self.hpht,
            "subsea": self.subsea,
            "cost_usd_mm": self.cost_usd_mm,
            "cost_type": self.cost_type.value,
            "source": self.source,
            "confidence": self.confidence.value,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# CostEstimate — engine output
# ---------------------------------------------------------------------------


@dataclass
class CostEstimate:
    """Cost estimate produced by the CostEngine.

    Raises:
        ValueError: If cost_per_day_usd is not positive.
    """

    activity_type: ActivityType
    region: str
    water_depth_band: WaterDepthBand
    well_depth_band: WellDepthBand
    cost_usd_mm: float
    cost_per_day_usd: float
    duration_days: float
    confidence: ConfidenceLevel
    source: str
    year: int
    notes: str = ""

    def __post_init__(self) -> None:
        if self.cost_per_day_usd <= 0.0:
            raise ValueError(
                f"cost_per_day_usd must be positive, got {self.cost_per_day_usd}"
            )


# ---------------------------------------------------------------------------
# CalibrationComparison — calibrated vs proxy rate analysis
# ---------------------------------------------------------------------------


@dataclass
class CalibrationComparison:
    """Comparison of calibrated day rate versus proxy rate for a cell.

    bias_pct is computed as:
        (calibrated - proxy) / proxy * 100
    Positive means calibrated > proxy (proxy was an underestimate).
    """

    region: str
    water_depth_band: WaterDepthBand
    activity_type: ActivityType
    proxy_rate_usd_day: float
    calibrated_rate_usd_day: float
    n_data_points: int
    rmse_usd_mm: float
    confidence: ConfidenceLevel
    bias_pct: float = field(init=False)

    def __post_init__(self) -> None:
        if self.proxy_rate_usd_day == 0.0:
            self.bias_pct = 0.0
        else:
            self.bias_pct = (
                (self.calibrated_rate_usd_day - self.proxy_rate_usd_day)
                / self.proxy_rate_usd_day
                * 100.0
            )
