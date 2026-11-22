"""Exact-year cost basis with explicit comparability and retained evidence.

This API does not choose field assumptions, normalize currencies, fill gaps,
fit curves, or replace an approved economics deck. An evaluated result means
only that comparable, sourced observations exist for the requested year.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite
from statistics import mean
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from worldenergydata.cost.timeseries.schema import (
    CostComponent,
    CostObservation,
    DevelopmentSystemBand,
    FigureType,
    PriceBasis,
    Provenance,
)

# NIST/SEMATECH e-Handbook of Statistical Methods (2003), section 1.3.5.1,
# "Measures of Location": arithmetic mean = sum(observed values) / count.
MEAN_SOURCE = "https://www.itl.nist.gov/div898/handbook/eda/section3/eda351.htm"


class CostBasisQuery(BaseModel):
    """Caller-supplied comparison basis; None means an exact absent attribute.

    All fields are required, including nullable fields. No wildcard or implicit
    market-wide fallback is applied. Nominal queries require basis_year=None;
    real queries require the explicit year in which money is denominated.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    component: CostComponent
    band: DevelopmentSystemBand
    # ISO 4217:2015, public "Alphabetic code" overview (accessed 2026-10-19):
    # https://www.iso.org/iso-4217-currency-codes.html
    currency: str = Field(min_length=3, max_length=3)
    unit: str = Field(min_length=1)
    region: str = Field(min_length=1)
    segment: str | None
    figure_type: FigureType
    price_basis: PriceBasis
    basis_year: int | None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_money_basis(self) -> CostBasisQuery:
        if self.price_basis is PriceBasis.REAL and self.basis_year is None:
            raise ValueError("Real queries require a basis_year")
        if self.price_basis is PriceBasis.NOMINAL and self.basis_year is not None:
            raise ValueError("Nominal queries require basis_year=None")
        return self


@dataclass(frozen=True)
class AnnualCostBasis:
    """Derived mean and full input rows, or a named reason for a missing value.

    Equal observation weighting is descriptive, not a duration-weighted market
    estimate. Observations retain citations and access dates for audit; neither
    their freshness nor their applicability to a field is certified here.
    """

    year: int
    query: CostBasisQuery
    status: Literal["EVALUATED", "NOT_EVALUATED"]
    value: float | None
    observations: tuple[CostObservation, ...]
    reason: str | None
    method_source: str = MEAN_SOURCE


def lookup_annual_cost(
    rows: Iterable[CostObservation], *, year: int, query: CostBasisQuery
) -> AnnualCostBasis:
    """Return an equal-weight mean of sourced, exactly comparable observations.

    No nearby year, other band, other region or derived observation can stand
    in for missing evidence. Exact duplicate rows require upstream resolution
    rather than silently weighting the same evidence more than once.
    """
    dimensions = query.model_dump()
    matches = tuple(
        row
        for row in rows
        if row.year == year
        and row.provenance is Provenance.SOURCED
        and all(getattr(row, name) == value for name, value in dimensions.items())
    )
    reason = None
    if not matches:
        reason = "No sourced observations match the requested year and basis"
    elif any(row.value is None or not isfinite(row.value) for row in matches):
        reason = "All matching values must be finite"
    elif len({row.model_dump_json() for row in matches}) != len(matches):
        reason = "Duplicate observations require resolution before averaging"
    if reason is not None:
        return AnnualCostBasis(year, query, "NOT_EVALUATED", None, matches, reason)
    # Mean definition and method citation: NIST/SEMATECH (2003), section
    # 1.3.5.1, MEAN_SOURCE above. No cost coefficient or acceptance limit.
    value = mean(row.value for row in matches)
    return AnnualCostBasis(year, query, "EVALUATED", value, matches, None)


def build_cost_deck(
    rows: Iterable[CostObservation], *, years: Iterable[int], query: CostBasisQuery
) -> tuple[AnnualCostBasis, ...]:
    """Evaluate unique requested years in order, retaining explicit gaps.

    Materializing evidence once also supports single-pass CSV/generator inputs.
    The caller selects the year range; no extrapolation policy is implied.
    """
    evidence = tuple(rows)
    return tuple(
        lookup_annual_cost(evidence, year=year, query=query)
        for year in sorted(set(years))
    )
