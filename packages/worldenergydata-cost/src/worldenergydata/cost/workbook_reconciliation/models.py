"""Accounting contracts. Monetary inputs and policy limits are supplied explicitly."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Basis:
    project_id: str
    component: str
    start: str
    end: str
    currency: str
    unit: str
    price_basis: str
    basis_year: str
    ownership: str
    scope: str
    capex_basis: str
    assumption_vintage: str
    normalization_vintage: str


@dataclass(frozen=True)
class Interval:
    low: Decimal | None
    high: Decimal | None

    def __post_init__(self):
        if any(x is not None and not x.is_finite() for x in (self.low, self.high)):
            raise ValueError("interval bounds must be finite or explicitly unavailable")
        if self.low is not None and self.high is not None and self.low > self.high:
            raise ValueError("interval bounds are reversed")

    @property
    def closed(self):
        return self.low is not None and self.high is not None


@dataclass(frozen=True)
class Observation:
    basis: Basis
    amount: Interval
    provenance: str
    source: str

    def __post_init__(self):
        if (
            self.provenance
            not in {
                "workbook_assumption",
                "disclosed",
                "mapped",
                "modeled",
                "allocated",
            }
            or not self.source.strip()
        ):
            raise ValueError("observation requires provenance and a source locator")


@dataclass(frozen=True)
class MaterialityPolicy:
    absolute: Decimal
    relative: Decimal
    source: str
    approved: bool

    def __post_init__(self):
        if not isinstance(self.approved, bool):
            raise TypeError("policy approval must be a boolean")
        if any(not x.is_finite() or x < 0 for x in (self.absolute, self.relative)):
            raise ValueError("policy limits must be finite and nonnegative")
        if not self.source.strip():
            raise ValueError("materiality policy requires a source")


@dataclass(frozen=True)
class Result:
    status: str
    reason: str
    variance: Interval | None = None
    materiality: str = "NOT_EVALUATED"
    threshold: Decimal | None = None
    classification: str = "missing_evidence"
    evidence: str = ""
