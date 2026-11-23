# ABOUTME: SQLModel data models for vessel hull models
# ABOUTME: Defines VesselHullModel with metadata and 3D geometry references

"""
SQLModel Data Models for Vessel Hull Models Module

Defines the data model for storing vessel hull metadata and 3D geometry references.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class VesselType(str, Enum):
    """Types of offshore installation vessels"""

    CRANE_VESSEL = "crane_vessel"
    PIPELAY_VESSEL = "pipelay_vessel"
    DERRICK_LAY_VESSEL = "derrick_lay_vessel"
    SINGLE_LIFT_VESSEL = "single_lift_vessel"
    PSV = "platform_supply_vessel"
    AHTS = "anchor_handling_tug_supply"
    CONSTRUCTION_VESSEL = "construction_vessel"
    DIVING_SUPPORT_VESSEL = "diving_support_vessel"
    FPSO = "floating_production_storage_offloading"
    SEMI_SUBMERSIBLE = "semi_submersible"
    JACK_UP = "jack_up"
    FPV = "floating_production_vessel"
    GENERIC = "generic"


class ModelSource(str, Enum):
    """Sources for 3D hull models"""

    CGTRADER = "cgtrader"
    SKETCHFAB = "sketchfab"
    TURBOSQUID = "turbosquid"
    GRABCAD = "grabcad"
    PARAMETRIC = "parametric"
    ORCAWAVE = "orcawave"
    RHINO = "rhino"
    MANUAL = "manual"


class ModelQuality(str, Enum):
    """Quality levels for 3D models"""

    ENGINEERING = "engineering"  # CFD/hydrodynamic grade
    PROFESSIONAL = "professional"  # High polygon, detailed
    ARTISTIC = "artistic"  # Visually appealing but not accurate
    SYNTHETIC = "synthetic"  # Parametrically generated
    PLACEHOLDER = "placeholder"  # Simple geometry for testing


class VesselHullModel(BaseModel):
    """
    Vessel hull model with metadata and 3D geometry reference.

    Stores information about acquired or generated hull models including
    vessel identification, dimensions, and 3D model metadata.
    """

    # Vessel identification
    id: Optional[int] = Field(default=None, description="Database primary key")
    imo_number: Optional[str] = Field(default=None, description="IMO vessel number")
    mmsi: Optional[str] = Field(default=None, description="MMSI number")
    vessel_name: str = Field(..., description="Vessel name")
    vessel_type: VesselType = Field(
        default=VesselType.GENERIC, description="Vessel type"
    )
    operator: Optional[str] = Field(default=None, description="Vessel operator/owner")

    # Hull dimensions (meters)
    length_overall: float = Field(
        ..., description="Length overall (LOA) in meters", ge=0
    )
    beam: float = Field(..., description="Beam (width) in meters", ge=0)
    depth: float = Field(default=0.0, description="Depth in meters", ge=0)
    draft: float = Field(default=0.0, description="Design draft in meters", ge=0)
    displacement: Optional[float] = Field(
        default=None, description="Displacement in tonnes"
    )

    # 3D model metadata
    obj_file_path: str = Field(..., description="Path to OBJ file")
    source: ModelSource = Field(default=ModelSource.MANUAL, description="Model source")
    source_url: Optional[str] = Field(
        default=None, description="Source URL if downloaded"
    )
    model_quality: ModelQuality = Field(
        default=ModelQuality.ENGINEERING, description="Model quality level"
    )
    vertex_count: int = Field(default=0, description="Number of vertices", ge=0)
    face_count: int = Field(default=0, description="Number of faces", ge=0)
    file_size_bytes: int = Field(default=0, description="File size in bytes", ge=0)
    units: str = Field(default="meters", description="Model units")

    # Timestamps
    acquired_at: datetime = Field(
        default_factory=datetime.utcnow, description="Acquisition date"
    )
    last_validated: Optional[datetime] = Field(
        default=None, description="Last validation date"
    )

    # Additional metadata
    notes: Optional[str] = Field(default=None, description="Additional notes")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Extra metadata"
    )

    @field_validator("obj_file_path", mode="before")
    @classmethod
    def convert_path_to_str(cls, v: Any) -> str:
        """Convert Path objects to strings"""
        if isinstance(v, Path):
            return str(v)
        return v

    class Config:
        use_enum_values = True


class VesselHullModelCreate(BaseModel):
    """Schema for creating a new vessel hull model entry"""

    vessel_name: str
    vessel_type: VesselType = VesselType.GENERIC
    imo_number: Optional[str] = None
    mmsi: Optional[str] = None
    operator: Optional[str] = None
    length_overall: float
    beam: float
    depth: float = 0.0
    draft: float = 0.0
    displacement: Optional[float] = None
    obj_file_path: str
    source: ModelSource = ModelSource.MANUAL
    source_url: Optional[str] = None
    model_quality: ModelQuality = ModelQuality.ENGINEERING
    notes: Optional[str] = None


class VesselHullModelUpdate(BaseModel):
    """Schema for updating a vessel hull model entry"""

    vessel_name: Optional[str] = None
    vessel_type: Optional[VesselType] = None
    imo_number: Optional[str] = None
    mmsi: Optional[str] = None
    operator: Optional[str] = None
    length_overall: Optional[float] = None
    beam: Optional[float] = None
    depth: Optional[float] = None
    draft: Optional[float] = None
    displacement: Optional[float] = None
    source: Optional[ModelSource] = None
    source_url: Optional[str] = None
    model_quality: Optional[ModelQuality] = None
    notes: Optional[str] = None
    last_validated: Optional[datetime] = None
