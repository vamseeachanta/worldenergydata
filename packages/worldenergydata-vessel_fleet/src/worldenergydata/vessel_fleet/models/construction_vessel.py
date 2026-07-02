"""Dataclass model for construction and service vessel records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from worldenergydata.vessel_fleet.models.base import BaseVesselEntry

_HEAVY_LIFT_THRESHOLD_T: float = 5000.0
_DEEPWATER_VESSEL_THRESHOLD_M: float = 2000.0


@dataclass
class ConstructionVesselEntry(BaseVesselEntry):
    """Domain model for a construction or service vessel."""

    main_crane_capacity_t: Optional[float] = None
    main_crane_reach_m: Optional[float] = None
    aux_crane_capacity_t: Optional[float] = None
    aux_crane_reach_m: Optional[float] = None
    pipelay_capacity_in: Optional[float] = None
    pipelay_tension_t: Optional[float] = None
    pipelay_method: Optional[str] = None
    deck_area_m2: Optional[float] = None
    deck_load_capacity_t: Optional[float] = None
    bollard_pull_t: Optional[float] = None
    heavy_lift_capacity_t: Optional[float] = None
    water_depth_rating_m: Optional[float] = None
    rov_systems: Optional[int] = None
    moonpool: Optional[bool] = None
    turbine_capacity_mw: Optional[float] = None
    foundation_type: Optional[str] = None

    # Pipelay firing line + burial capability (#701 — 2011 poster fields).
    # pipelay_capacity_in remains the MAX lay diameter.
    welding_stations_count: Optional[int] = None
    total_stations_count: Optional[int] = None
    ndt_stations_count: Optional[int] = None
    welding_method: Optional[str] = None
    tensioner_count: Optional[int] = None
    pipelay_min_diameter_in: Optional[float] = None
    slay_center_capable: Optional[bool] = None
    slay_side_capable: Optional[bool] = None
    jlay_capable: Optional[bool] = None
    reel_permanent_capable: Optional[bool] = None
    reel_removable_capable: Optional[bool] = None
    carousel_capable: Optional[bool] = None
    tow_install_capable: Optional[bool] = None
    tow_methods: Optional[str] = None
    burial_capable: Optional[bool] = None
    simultaneous_lay_bury_capable: Optional[bool] = None
    burial_min_diameter_in: Optional[float] = None
    burial_max_diameter_in: Optional[float] = None
    burial_max_water_depth_m: Optional[float] = None
    pipelay_min_water_depth_m: Optional[float] = None
    pipelay_max_water_depth_m: Optional[float] = None
    experience_water_depth_m: Optional[float] = None
    pipe_joint_length_max_m: Optional[float] = None
    davits_count: Optional[int] = None

    @property
    def is_heavy_lift(self) -> bool:
        """Vessel has heavy-lift capability (>= 5000t crane or lift)."""
        cap = self.main_crane_capacity_t or self.heavy_lift_capacity_t
        if cap is None:
            return False
        return cap >= _HEAVY_LIFT_THRESHOLD_T

    @property
    def is_deepwater_capable(self) -> bool:
        """Vessel rated for >= 2000m water depth."""
        if self.water_depth_rating_m is None:
            return False
        return self.water_depth_rating_m >= _DEEPWATER_VESSEL_THRESHOLD_M

    @property
    def is_pipelay(self) -> bool:
        """Whether this vessel has pipelay capability."""
        return (
            self.pipelay_capacity_in is not None or self.pipelay_tension_t is not None
        )

    @property
    def is_burial_capable(self) -> bool:
        """Whether this vessel can bury pipe (jetting/trenching/plough)."""
        return bool(self.burial_capable) or (
            self.burial_max_diameter_in is not None
        )

    @property
    def is_crane_vessel(self) -> bool:
        """Whether this vessel has significant crane capability."""
        return self.main_crane_capacity_t is not None

    @property
    def total_crane_capacity_t(self) -> float:
        """Sum of main and aux crane capacities."""
        main = self.main_crane_capacity_t or 0.0
        aux = self.aux_crane_capacity_t or 0.0
        return main + aux
