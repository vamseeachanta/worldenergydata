"""Domain models for drilling riser components."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Literal, Optional

from worldenergydata.vessel_fleet.constants import FT_TO_M


RiserClass = Literal["drilling", "lift", "production"]


@dataclass(frozen=True)
class RiserLineEntry:
    """One strapped auxiliary line; dimensions are caller-supplied inches."""

    function: str
    od_in: float
    wall_thickness_in: float

    def __post_init__(self) -> None:
        if not self.function.strip():
            raise ValueError("Auxiliary line function must be populated")
        if not all(
            isfinite(value) and value > 0
            for value in (
                self.od_in,
                self.wall_thickness_in,
            )
        ):
            raise ValueError("Auxiliary line dimensions must be finite and positive")
        # Circular geometry: ID = OD - 2*wall > 0 (a hollow line, not a design limit).
        if self.wall_thickness_in * 2 >= self.od_in:
            raise ValueError("Auxiliary wall must be less than half its OD")


@dataclass
class RiserJointEntry:
    """A riser joint, with optional lines strapped to its main tube.

    Legacy records default to drilling. Lift includes hydraulic-lift/mining
    risers; class selection does not imply BOP or kill/choke equipment.
    """

    component_id: str
    component_type: str = "riser_joint"
    manufacturer: Optional[str] = None
    model: Optional[str] = None

    od_in: Optional[float] = None
    id_in: Optional[float] = None
    wall_thickness_in: Optional[float] = None
    length_ft: Optional[float] = None
    weight_air_kips: Optional[float] = None
    weight_water_kips: Optional[float] = None
    grade: Optional[str] = None
    connection_type: Optional[str] = None
    buoyancy_coverage_pct: Optional[float] = None
    buoyancy_od_in: Optional[float] = None
    pressure_rating_psi: Optional[float] = None

    data_source: Optional[str] = None
    notes: Optional[str] = None

    riser_class: RiserClass = "drilling"
    auxiliary_lines: list[RiserLineEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.riser_class not in ("drilling", "lift", "production"):
            raise ValueError("Unknown riser_class")

    @property
    def buoyancy_od_ratio(self) -> Optional[float]:
        """Buoyancy OD / main-tube OD, dimensionless (issue 1138 definition).

        Return None for bare joints, missing/nonpositive/nonfinite dimensions
        or coverage. This is not a bundle-envelope or handling-clearance check.
        The observed catalog range is not an industry acceptance criterion.
        """
        values = (self.od_in, self.buoyancy_od_in, self.buoyancy_coverage_pct)
        if any(value is None or not isfinite(value) or value <= 0 for value in values):
            return None
        ratio = self.buoyancy_od_in / self.od_in
        return ratio if isfinite(ratio) else None

    @property
    def od_m(self) -> Optional[float]:
        if self.od_in is None:
            return None
        return self.od_in * 0.0254

    @property
    def length_m(self) -> Optional[float]:
        if self.length_ft is None:
            return None
        return self.length_ft * FT_TO_M

    @property
    def has_buoyancy(self) -> bool:
        return (self.buoyancy_coverage_pct or 0) > 0

    @property
    def is_pup_joint(self) -> bool:
        if self.length_ft is None:
            return False
        return self.length_ft < 60.0


@dataclass
class BOPEntry:
    """A blowout preventer stack."""

    component_id: str
    component_type: str = "bop"
    bop_type: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None

    bore_size_in: Optional[float] = None
    pressure_rating_psi: Optional[float] = None
    height_ft: Optional[float] = None
    weight_air_kips: Optional[float] = None
    weight_water_kips: Optional[float] = None

    annular_count: Optional[int] = None
    shear_ram_count: Optional[int] = None
    pipe_ram_count: Optional[int] = None
    casing_shear_ram: Optional[bool] = None

    data_source: Optional[str] = None
    notes: Optional[str] = None

    @property
    def is_subsea(self) -> bool:
        return (self.bop_type or "").lower() == "subsea"

    @property
    def total_ram_count(self) -> int:
        return (self.shear_ram_count or 0) + (self.pipe_ram_count or 0)

    @property
    def height_m(self) -> Optional[float]:
        if self.height_ft is None:
            return None
        return self.height_ft * FT_TO_M

    @property
    def weight_air_tonnes(self) -> Optional[float]:
        if self.weight_air_kips is None:
            return None
        return self.weight_air_kips * 0.453592


@dataclass
class LMRPEntry:
    """A Lower Marine Riser Package."""

    component_id: str
    component_type: str = "lmrp"
    manufacturer: Optional[str] = None
    model: Optional[str] = None

    bore_size_in: Optional[float] = None
    pressure_rating_psi: Optional[float] = None
    height_ft: Optional[float] = None
    weight_air_kips: Optional[float] = None
    weight_water_kips: Optional[float] = None
    annular_count: Optional[int] = None
    connector_type: Optional[str] = None

    data_source: Optional[str] = None
    notes: Optional[str] = None

    @property
    def height_m(self) -> Optional[float]:
        if self.height_ft is None:
            return None
        return self.height_ft * FT_TO_M


@dataclass
class FlexJointEntry:
    """A flex or ball joint."""

    component_id: str
    component_type: str = "flex_joint"
    position: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None

    bore_size_in: Optional[float] = None
    max_angle_deg: Optional[float] = None
    stiffness_ft_kip_per_deg: Optional[float] = None
    height_ft: Optional[float] = None
    weight_air_kips: Optional[float] = None
    pressure_rating_psi: Optional[float] = None

    data_source: Optional[str] = None
    notes: Optional[str] = None

    @property
    def is_upper(self) -> bool:
        return (self.position or "").lower() == "upper"

    @property
    def height_m(self) -> Optional[float]:
        if self.height_ft is None:
            return None
        return self.height_ft * FT_TO_M


@dataclass
class TelescopicJointEntry:
    """A telescopic (slip) joint."""

    component_id: str
    component_type: str = "telescopic_joint"
    manufacturer: Optional[str] = None
    model: Optional[str] = None

    od_in: Optional[float] = None
    bore_size_in: Optional[float] = None
    stroke_ft: Optional[float] = None
    outer_barrel_length_ft: Optional[float] = None
    inner_barrel_length_ft: Optional[float] = None
    weight_air_kips: Optional[float] = None
    pressure_rating_psi: Optional[float] = None

    data_source: Optional[str] = None
    notes: Optional[str] = None

    @property
    def stroke_m(self) -> Optional[float]:
        if self.stroke_ft is None:
            return None
        return self.stroke_ft * FT_TO_M

    @property
    def total_length_ft(self) -> Optional[float]:
        if self.outer_barrel_length_ft is None:
            return None
        return self.outer_barrel_length_ft + (self.inner_barrel_length_ft or 0)
