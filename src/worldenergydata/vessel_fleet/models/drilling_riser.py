"""Domain models for drilling riser components."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from worldenergydata.vessel_fleet.constants import FT_TO_M


@dataclass
class RiserJointEntry:
    """A marine drilling riser joint."""

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
