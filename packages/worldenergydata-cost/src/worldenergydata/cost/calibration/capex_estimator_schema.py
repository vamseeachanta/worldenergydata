"""Strict prediction-time contracts; no empirical coefficients or default limits."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class CapexBasis(Contract):
    """Amounts use currency millions; equal basis includes normalization provenance.

    Field names follow timeseries.cost_map_schema.MoneyInterval. Normalization
    must be performed upstream: no FX, escalation, or deflator is supplied here.
    """

    currency: str = Field(pattern=r"^[A-Z]{3}$")
    price_basis: Literal["nominal", "real"]
    basis_year: int
    ownership_basis: str = Field(min_length=1)
    scope_basis: str = Field(min_length=1)
    capex_basis: str = Field(min_length=1)
    normalization_source: str = Field(min_length=1)


class Feature(Contract):
    value: float = Field(ge=0)
    available_on: date


FeatureName = Literal[
    "water_depth_m", "well_count", "capacity_boe_day", "asset_quantity", "vintage_year"
]


class FeatureSnapshot(Contract):
    project_id: str = Field(min_length=1)
    validation_group_id: str = Field(min_length=1)
    as_of: date
    architecture: str = Field(min_length=1)
    host_type: str = Field(min_length=1)
    region: str = Field(min_length=1)
    basis: CapexBasis
    features: dict[FeatureName, Feature | None]

    @model_validator(mode="after")
    def check_availability(self):
        if any(f and f.available_on > self.as_of for f in self.features.values()):
            raise ValueError("feature was not available at snapshot date")
        return self


class TrainingRecord(Contract):
    snapshot: FeatureSnapshot
    amount: float = Field(gt=0)
    disclosed_on: date
    derivation: Literal[
        "disclosed", "award_derived", "allocated", "modeled", "synthetic"
    ]
    bound_type: Literal["point", "range", "floor", "ceiling"]
    source: str = Field(min_length=1)

    @model_validator(mode="after")
    def check_snapshot(self):
        if self.snapshot.as_of > self.disclosed_on:
            raise ValueError("training features must precede target disclosure")
        return self


class EstimatorPolicy(Contract):
    """Required application criteria, not values inferred from a standard.

    The source shall identify the application decision that sets these inputs.
    No built-in accuracy, coverage, or minimum-sample acceptance is asserted.
    """

    min_training_projects: int = Field(ge=1, strict=True)
    calibration_projects: int = Field(ge=1, strict=True)
    min_backtests: int = Field(ge=1, strict=True)
    alpha: float = Field(gt=0, lt=1)
    max_median_ape: float = Field(ge=0)
    min_coverage: float = Field(ge=0, le=1)
    source: str = Field(min_length=1)
    split_salt: str = Field(min_length=1)
