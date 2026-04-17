"""
ABOUTME: Well bore design data schemas — WellBoreDesign and EcdProfile.
ABOUTME: Covers slim-hole vs standard-hole geometry and ECD profiles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BoreType(Enum):
    SLIM_HOLE = "slim_hole"  # < 8.5" nominal bit size
    STANDARD = "standard"  # 8.5"–12.25"
    LARGE_BORE = "large_bore"  # > 12.25"


class CasingString(Enum):
    CONDUCTOR = "conductor"
    SURFACE = "surface"
    INTERMEDIATE = "intermediate"
    PRODUCTION = "production"
    LINER = "liner"


# Bit size boundaries (inches) for bore type classification
SLIM_HOLE_MAX_BIT_SIZE_IN = 8.5
LARGE_BORE_MIN_BIT_SIZE_IN = 12.25


def bore_type_from_bit_size(bit_size_in: float) -> BoreType:
    """Classify BoreType from nominal production bit size (inches)."""
    if bit_size_in < SLIM_HOLE_MAX_BIT_SIZE_IN:
        return BoreType.SLIM_HOLE
    if bit_size_in > LARGE_BORE_MIN_BIT_SIZE_IN:
        return BoreType.LARGE_BORE
    return BoreType.STANDARD


@dataclass
class WellBoreDesign:
    """Well bore geometry and mud system design parameters.

    ``bore_type`` should match the production bit size convention:
    - SLIM_HOLE  : production_bit_size_in < 8.5"
    - STANDARD   : 8.5" <= production_bit_size_in <= 12.25"
    - LARGE_BORE : production_bit_size_in > 12.25"
    """

    well_id: str
    bore_type: BoreType
    total_depth_m: float
    water_depth_m: float  # 0 for land wells

    # Geometry by section
    sections: list[dict] = field(default_factory=list)
    # Each entry: {
    #   "casing": CasingString,
    #   "bit_size_in": float,
    #   "depth_from_m": float,
    #   "depth_to_m": float,
    # }

    # Key design parameters (bit sizes by section)
    surface_bit_size_in: float = 0.0
    intermediate_bit_size_in: float = 0.0
    production_bit_size_in: float = 0.0

    # Mud system
    mud_weight_ppg: float = 9.0
    max_mud_weight_ppg: float = 0.0  # fracture gradient limit
    min_mud_weight_ppg: float = 0.0  # pore pressure equivalent

    formation_type: str = "mixed"  # "shale"|"carbonate"|"sandstone"|"mixed"
    notes: str = ""

    def pressure_window_ppg(self) -> float:
        """Available mud weight window (fracture - pore pressure, ppg)."""
        if self.max_mud_weight_ppg == 0.0 or self.min_mud_weight_ppg == 0.0:
            return 0.0
        return self.max_mud_weight_ppg - self.min_mud_weight_ppg

    def is_offshore(self) -> bool:
        """True when water_depth_m > 0."""
        return self.water_depth_m > 0.0


@dataclass
class EcdProfile:
    """Equivalent circulating density profile along the wellbore.

    ``pressure_window_ppg`` is fracture_gradient_ppg - ecd_ppg at each depth.
    Positive values are safe; negative values indicate a kick/loss risk.
    """

    well_id: str
    bore_type: BoreType
    depths_m: list[float]
    ecd_ppg: list[float]  # ECD at each depth
    mud_weight_ppg: float
    flow_rate_gpm: float
    annular_velocity_fps: list[float]
    pressure_window_ppg: list[
        float
    ]  # fracture_gradient_ppg - ecd_ppg (positive = safe)
    bottleneck_depth_m: Optional[float]  # depth of minimum pressure window
    min_pressure_window_ppg: float
    notes: str = ""

    def is_safe_at_all_depths(self) -> bool:
        """True when pressure window is positive at every depth point."""
        return all(pw > 0.0 for pw in self.pressure_window_ppg)

    def safe_depth_fraction(self) -> float:
        """Fraction of depth points with a positive pressure window (0–1)."""
        if not self.pressure_window_ppg:
            return 0.0
        safe = sum(1 for pw in self.pressure_window_ppg if pw > 0.0)
        return safe / len(self.pressure_window_ppg)
