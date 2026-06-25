# ABOUTME: Pydantic model for the offshore field-development concept contract.
# ABOUTME: Issue #568 — FieldConcept is the single data model shared by the playbook.
"""
worldenergydata.field_development.models
========================================

The :class:`FieldConcept` is the **frozen contract** every downstream module of
the field-development playbook speaks: the recommendation engine, the
concept→graph-spec mapper, the renderers, and the economics integration all
consume and produce this one object. Defining it once prevents the classic trap
of several modules each carrying their own incompatible "field" object.

The model represents *both* a set of input parameters (what we know about a
field) and a *recommended concept* (what the engine proposes). Almost every
field is therefore optional — a concept is built up incrementally as the
playbook reasons about it. Only :attr:`FieldConcept.name` is required.

Per-field invariants (positivity, enum membership) are enforced here and *raise*
at construction. Cross-field engineering checks (e.g. depth within a host's
envelope) live in :mod:`worldenergydata.field_development.sanity` and *return*
a list of violations rather than raising, so callers — notably the Phase-2 LLM
concept-completion gate — can inspect and repair them.

The canonical short-vocabulary fields (``name``, ``water_depth_m``,
``concept_type`` …) intentionally match
:mod:`worldenergydata.subseaiq.analytics.normalize` so the private SubseaIQ
loader (issue #569) maps straight onto this model.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from worldenergydata.field_development.enums import (
    ConceptType,
    FlowlineMaterial,
    FluidType,
    MetoceanRegime,
    ReservoirDistribution,
    RiserType,
    Topology,
    TreeType,
)

SCHEMA_VERSION = "1.0.0"


class FieldConcept(BaseModel):
    """An offshore field-development concept — the playbook's shared contract.

    Groups (see ``data_dictionary.md`` for units): identity, reservoir/fluid,
    production, location/physical, concept/architecture, environment/regulatory,
    commercial, timeline, provenance.
    """

    model_config = ConfigDict(extra="forbid", use_enum_values=False)

    schema_version: str = SCHEMA_VERSION

    # --- Identity ---
    name: str = Field(..., description="Field/project name (required).")
    operator: Optional[str] = None
    region: Optional[str] = Field(None, description="Basin / geographic area.")

    # --- Reservoir / fluid ---
    recoverable_reserves_mmboe: Optional[float] = None
    fluid_type: Optional[FluidType] = None
    api_gravity: Optional[float] = None
    gor_scf_stb: Optional[float] = None
    viscosity_cp: Optional[float] = None
    wax_appearance_temp_c: Optional[float] = None
    sour: Optional[bool] = Field(None, description="H2S/CO2 present.")
    hpht: Optional[bool] = Field(None, description="High pressure / high temperature.")
    reservoir_distribution: Optional[ReservoirDistribution] = None

    # --- Production ---
    plateau_rate_boed: Optional[float] = None
    per_well_rate_boed: Optional[float] = None
    num_wells: Optional[int] = None
    num_trees: Optional[int] = None
    num_manifolds: Optional[int] = None
    water_injection: Optional[bool] = None
    gas_injection: Optional[bool] = None
    field_life_years: Optional[float] = None

    # --- Location / physical ---
    water_depth_m: Optional[float] = Field(
        None, description="Water depth at the field (m) — dominant concept gate."
    )
    distance_to_host_km: Optional[float] = None
    host_spare_capacity: Optional[bool] = None
    distance_to_shore_km: Optional[float] = None
    seabed_terrain: Optional[str] = None

    # --- Concept / architecture (the recommended / selected concept) ---
    concept_type: Optional[ConceptType] = None
    tree_type: Optional[TreeType] = None
    tieback_distance_km: Optional[float] = None
    topology: Optional[Topology] = None
    flowline_diameter_in: Optional[float] = None
    flowline_material: Optional[FlowlineMaterial] = None
    riser_type: Optional[RiserType] = None

    # --- Environment / regulatory ---
    metocean_regime: Optional[MetoceanRegime] = None

    # --- Commercial ---
    oil_price_usd_bbl: Optional[float] = None
    gas_price_usd_mmbtu: Optional[float] = None
    discount_rate: Optional[float] = Field(None, description="Fraction, e.g. 0.10.")

    # --- Timeline ---
    year_concept: Optional[int] = None
    year_feed: Optional[int] = None
    year_fid: Optional[int] = None
    year_first_oil: Optional[int] = None

    # --- Provenance ---
    data_source: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Per-field validators (raise at construction)
    # ------------------------------------------------------------------ #
    @field_validator("name")
    @classmethod
    def name_non_empty(cls, v: str) -> str:
        """Name must be a non-empty string."""
        if not v or not v.strip():
            raise ValueError("name must be a non-empty string")
        return v

    @field_validator(
        "recoverable_reserves_mmboe",
        "plateau_rate_boed",
        "per_well_rate_boed",
        "field_life_years",
        "water_depth_m",
        "distance_to_host_km",
        "distance_to_shore_km",
        "tieback_distance_km",
        "flowline_diameter_in",
        "gor_scf_stb",
        "viscosity_cp",
    )
    @classmethod
    def must_be_non_negative(cls, v: Optional[float]) -> Optional[float]:
        """Physical magnitudes cannot be negative (None is allowed)."""
        if v is not None and v < 0:
            raise ValueError("value must be >= 0")
        return v

    @field_validator("api_gravity")
    @classmethod
    def api_in_range(cls, v: Optional[float]) -> Optional[float]:
        """API gravity must be in a physically plausible range (0–100)."""
        if v is not None and not (0 < v < 100):
            raise ValueError("api_gravity must be between 0 and 100")
        return v

    @field_validator("discount_rate")
    @classmethod
    def discount_fraction(cls, v: Optional[float]) -> Optional[float]:
        """Discount rate is a fraction (0–1), not a percentage."""
        if v is not None and not (0 <= v < 1):
            raise ValueError("discount_rate must be a fraction in [0, 1)")
        return v

    @field_validator(
        "num_wells", "num_trees", "num_manifolds",
        "year_concept", "year_feed", "year_fid", "year_first_oil",
    )
    @classmethod
    def counts_and_years_non_negative(cls, v: Optional[int]) -> Optional[int]:
        """Counts and years cannot be negative."""
        if v is not None and v < 0:
            raise ValueError("value must be >= 0")
        return v
