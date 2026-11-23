# ABOUTME: Pydantic models for LNG terminal engineering design data.
# ABOUTME: Defines hull, pipeline, process, storage, and marine infrastructure specs.

"""
Engineering Design Models for LNG Terminals

Pydantic models representing the physical and mechanical design attributes
of LNG terminal facilities, including hull geometry, pipeline specifications,
process equipment, storage tanks, and marine infrastructure.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator

from ..constants import PipelineType


class HullDesign(BaseModel):
    """Hull design parameters for floating LNG terminals (FSRU / FLNG)."""

    hull_type: str = Field(
        ...,
        description="Hull configuration type",
        json_schema_extra={
            "enum": ["ship-shaped", "barge", "semi-submersible", "spar"],
        },
    )
    loa_m: Optional[float] = Field(
        default=None,
        ge=0,
        le=500,
        description="Length overall in meters",
    )
    beam_m: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Beam (breadth) in meters",
    )
    depth_m: Optional[float] = Field(
        default=None,
        ge=0,
        le=50,
        description="Moulded depth in meters",
    )
    draft_m: Optional[float] = Field(
        default=None,
        ge=0,
        le=30,
        description="Design draft in meters",
    )
    displacement_tonnes: Optional[float] = Field(
        default=None,
        ge=0,
        description="Displacement in metric tonnes",
    )
    mooring_type: Optional[str] = Field(
        default=None,
        description="Mooring system type",
        json_schema_extra={
            "enum": [
                "spread",
                "internal_turret",
                "external_turret",
                "tower",
                "calm",
            ],
        },
    )
    turret_details: Optional[str] = Field(
        default=None,
        description="Turret system details and specification",
    )
    riser_count: Optional[int] = Field(
        default=None,
        ge=0,
        le=50,
        description="Number of risers connected to the hull",
    )
    riser_details: Optional[str] = Field(
        default=None,
        description="Riser type, size, and configuration details",
    )
    conversion_vessel: Optional[str] = Field(
        default=None,
        description="Name of the vessel converted (if conversion project)",
    )
    builder_yard: Optional[str] = Field(
        default=None,
        description="Shipyard or fabrication yard name",
    )
    year_built: Optional[int] = Field(
        default=None,
        ge=1950,
        le=2040,
        description="Year the hull was built or converted",
    )


class PipelineSpec(BaseModel):
    """Specification for a pipeline connected to an LNG terminal."""

    pipeline_type: PipelineType = Field(
        ...,
        description="Classification of the pipeline",
    )
    diameter_inches: Optional[float] = Field(
        default=None,
        ge=0,
        le=60,
        description="Nominal pipe diameter in inches",
    )
    length_km: Optional[float] = Field(
        default=None,
        ge=0,
        description="Pipeline length in kilometres",
    )
    wall_thickness_mm: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Pipe wall thickness in millimetres",
    )
    material: Optional[str] = Field(
        default=None,
        description="Pipe material (e.g. carbon steel, duplex SS, 9% Ni)",
    )
    design_pressure_barg: Optional[float] = Field(
        default=None,
        ge=0,
        description="Design pressure in barg",
    )
    design_temperature_c: Optional[float] = Field(
        default=None,
        description="Design temperature in degrees Celsius",
    )
    insulation_type: Optional[str] = Field(
        default=None,
        description="Insulation material or system type",
    )
    offshore_segment: bool = Field(
        default=False,
        description="Whether the pipeline includes an offshore segment",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional pipeline notes",
    )


class ProcessEquipment(BaseModel):
    """Process equipment specification for liquefaction or regasification."""

    liquefaction_process: Optional[str] = Field(
        default=None,
        description="Liquefaction technology",
        json_schema_extra={
            "enum": [
                "C3MR",
                "AP-X",
                "DMR",
                "cascade",
                "PRICO",
                "MR",
                "nitrogen",
                "other",
            ],
        },
    )
    number_of_trains: Optional[int] = Field(
        default=None,
        ge=0,
        le=20,
        description="Number of liquefaction or regasification trains",
    )
    capacity_per_train_mtpa: Optional[float] = Field(
        default=None,
        ge=0,
        le=15,
        description="Nameplate capacity per train in MTPA",
    )
    compressor_type: Optional[str] = Field(
        default=None,
        description="Main refrigerant compressor type (e.g. centrifugal, axial)",
    )
    compressor_driver: Optional[str] = Field(
        default=None,
        description="Compressor driver type (e.g. gas turbine, electric motor)",
    )
    compressor_power_mw: Optional[float] = Field(
        default=None,
        ge=0,
        description="Total compressor power per train in MW",
    )
    main_heat_exchanger_type: Optional[str] = Field(
        default=None,
        description="Main cryogenic heat exchanger type (e.g. SWHE, PFHE)",
    )
    mche_vendor: Optional[str] = Field(
        default=None,
        description="Main cryogenic heat exchanger vendor",
    )
    regasification_capacity_mmscfd: Optional[float] = Field(
        default=None,
        ge=0,
        description="Regasification send-out capacity in MMSCFD",
    )
    regasification_type: Optional[str] = Field(
        default=None,
        description="Regasification vaporizer type",
        json_schema_extra={
            "enum": ["ORV", "SCV", "IFV", "AAV"],
        },
    )
    boil_off_rate_percent: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="Boil-off rate as a fraction (0.0 to 1.0)",
    )
    pre_treatment: Optional[str] = Field(
        default=None,
        description="Gas pre-treatment description (e.g. amine, mol-sieve)",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional process equipment notes",
    )


class StorageSpec(BaseModel):
    """LNG storage tank specification."""

    tank_type: str = Field(
        ...,
        description="Storage tank containment type",
        json_schema_extra={
            "enum": [
                "full_containment",
                "membrane_mark_iii",
                "membrane_no96",
                "spb",
                "moss",
                "in_ground",
            ],
        },
    )
    number_of_tanks: Optional[int] = Field(
        default=None,
        ge=0,
        le=20,
        description="Number of LNG storage tanks",
    )
    capacity_per_tank_m3: Optional[float] = Field(
        default=None,
        ge=0,
        description="Capacity per tank in cubic metres",
    )
    total_capacity_m3: Optional[float] = Field(
        default=None,
        ge=0,
        description="Total LNG storage capacity in cubic metres",
    )
    tank_material: Optional[str] = Field(
        default=None,
        description="Primary inner-tank material (e.g. 9% nickel steel, SUS304)",
    )
    insulation_type: Optional[str] = Field(
        default=None,
        description="Tank insulation material or system",
    )
    containment_vendor: Optional[str] = Field(
        default=None,
        description="Containment system vendor (e.g. GTT, IHI, TKL)",
    )

    @model_validator(mode="after")
    def compute_total_capacity(self) -> StorageSpec:
        """Derive total_capacity_m3 when individual values are available."""
        if (
            self.number_of_tanks is not None
            and self.capacity_per_tank_m3 is not None
            and self.total_capacity_m3 is None
        ):
            self.total_capacity_m3 = self.number_of_tanks * self.capacity_per_tank_m3
        return self


class MarineInfrastructure(BaseModel):
    """Marine and jetty infrastructure for LNG vessel operations."""

    water_depth_m: Optional[float] = Field(
        default=None,
        ge=0,
        le=5000,
        description="Water depth at berth in metres (or mooring depth for FLNG/FSRU)",
    )
    jetty_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of LNG jetties",
    )
    berth_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of LNG berths",
    )
    max_vessel_size_m3: Optional[float] = Field(
        default=None,
        ge=0,
        description="Maximum LNG carrier capacity the berth can accommodate in m3",
    )
    loading_arms_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of marine loading / unloading arms",
    )
    loading_arm_size_inches: Optional[float] = Field(
        default=None,
        ge=0,
        description="Loading arm nominal diameter in inches",
    )
    loading_rate_m3_per_hr: Optional[float] = Field(
        default=None,
        ge=0,
        description="LNG loading / unloading rate in m3 per hour",
    )
    fender_type: Optional[str] = Field(
        default=None,
        description="Jetty fender system type",
    )
    breakwater: Optional[bool] = Field(
        default=None,
        description="Whether a breakwater protects the berth",
    )
    approach_channel_depth_m: Optional[float] = Field(
        default=None,
        ge=0,
        description="Approach channel navigable depth in metres",
    )
    tug_requirements: Optional[str] = Field(
        default=None,
        description="Tug assist requirements for LNG carrier berthing",
    )
