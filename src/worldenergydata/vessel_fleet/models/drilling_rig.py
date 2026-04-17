"""Dataclass model for drilling rig records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from worldenergydata.vessel_fleet.constants import (
    DEEPWATER_THRESHOLD_FT,
    ULTRA_DEEPWATER_THRESHOLD_FT,
)
from worldenergydata.vessel_fleet.models.base import BaseVesselEntry

_RIG_TYPE_DISPLAY_MAP: dict[str, str] = {
    "drillship": "Drillship",
    "semi_submersible": "Semi-Submersible",
    "jack_up": "Jack-Up",
    "platform_rig": "Platform Rig",
    "tender_assisted": "Tender Assisted",
    "inland_barge": "Inland Barge",
    "submersible": "Submersible",
    "land_rig": "Land Rig",
}

_OFFSHORE_RIG_TYPES: frozenset[str] = frozenset(
    {
        "drillship",
        "semi_submersible",
        "jack_up",
        "platform_rig",
        "tender_assisted",
        "inland_barge",
        "submersible",
    }
)


@dataclass
class DrillingRigEntry(BaseVesselEntry):
    """Domain model for a drilling rig record."""

    rig_name: Optional[str] = None
    rig_type: Optional[str] = None
    rig_status: Optional[str] = None
    rig_design: Optional[str] = None
    water_depth_rating_ft: Optional[float] = None
    drilling_depth_rating_ft: Optional[float] = None
    max_water_depth_ft: Optional[float] = None
    derrick_height_ft: Optional[float] = None
    hookload_rating_kips: Optional[float] = None
    drawworks_hp: Optional[float] = None
    rotary_table_size_in: Optional[float] = None
    top_drive_capacity_st: Optional[float] = None
    mud_pump_count: Optional[int] = None
    mud_pump_hp: Optional[float] = None
    bop_pressure_psi: Optional[float] = None
    bop_size_in: Optional[float] = None
    bop_manufacturer: Optional[str] = None
    riser_size_in: Optional[float] = None
    riser_length_ft: Optional[float] = None
    moonpool_length_m: Optional[float] = None
    moonpool_width_m: Optional[float] = None
    moonpool_diameter_m: Optional[float] = None
    variable_deck_load_st: Optional[float] = None
    deck_area_sq_ft: Optional[float] = None
    leg_length_ft: Optional[float] = None
    leg_type: Optional[str] = None
    cantilever_reach_ft: Optional[float] = None
    cantilever_capacity_kips: Optional[float] = None
    preload_capacity_st: Optional[float] = None
    spud_can_diameter_ft: Optional[float] = None
    ju_design: Optional[str] = None
    mast_height_ft: Optional[float] = None
    walking_system: Optional[bool] = None
    ac_scr_power: Optional[str] = None
    setback_capacity_kips: Optional[float] = None
    rig_model: Optional[str] = None
    super_spec: Optional[bool] = None
    wells_drilled_count: Optional[int] = None
    last_war_date: Optional[str] = None
    first_war_date: Optional[str] = None
    last_area_code: Optional[str] = None
    last_block_number: Optional[str] = None
    is_offshore: Optional[bool] = None

    @property
    def is_deepwater_capable(self) -> bool:
        """Rig is deepwater capable when rated >= 4000 ft."""
        if self.water_depth_rating_ft is None:
            return False
        return self.water_depth_rating_ft >= DEEPWATER_THRESHOLD_FT

    @property
    def is_ultra_deepwater(self) -> bool:
        """Rig is ultra-deepwater when rated >= 7500 ft."""
        if self.water_depth_rating_ft is None:
            return False
        return self.water_depth_rating_ft >= ULTRA_DEEPWATER_THRESHOLD_FT

    @property
    def rig_type_display(self) -> str:
        """Human-readable rig type."""
        return _RIG_TYPE_DISPLAY_MAP.get(self.rig_type or "", "Unknown")

    @property
    def is_offshore_derived(self) -> bool:
        """Whether the rig operates offshore.

        Uses explicit flag when set, otherwise infers from rig type.
        """
        if self.is_offshore is not None:
            return self.is_offshore
        if self.rig_type and self.rig_type in _OFFSHORE_RIG_TYPES:
            return True
        if self.rig_type == "land_rig":
            return False
        return True

    @property
    def is_jackup(self) -> bool:
        """Whether this is a jack-up rig."""
        return self.rig_type == "jack_up"

    @property
    def is_floater(self) -> bool:
        """Whether this is a floating rig (drillship or semi-sub)."""
        return self.rig_type in ("drillship", "semi_submersible")

    @property
    def display_name(self) -> str:
        """Prefer rig_name if set, else vessel_name."""
        return self.rig_name or self.vessel_name
