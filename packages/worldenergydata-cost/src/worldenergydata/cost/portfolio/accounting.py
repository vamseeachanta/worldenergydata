"""Exact closed-range accounting; no currency or basis normalization.

Equations and identity/rounding policy: Shared Contract to Freeze,
docs/plans/2026-07-16-issue-1038-cost-map-program.md (2026).
Zero and unity below are algebraic identities, not empirical coefficients.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from worldenergydata.cost.timeseries.cost_map import largest_remainder_allocate

ZERO = Decimal(0)


@dataclass(frozen=True)
class Basis:
    """All fields must match; scope means the common accounting envelope.

    For a component, requirement IDs specify its commercial scope *within* that
    envelope. A component cannot assert a different envelope and still contribute.
    Nominal observations use an explicit vintage label; no escalation is inferred.
    """

    currency: str
    unit: str
    price_basis: str
    price_vintage: str
    ownership: str
    phase: str
    scope: str
    capex_basis: str

    def __post_init__(self):
        if any(
            not isinstance(value, str) or not value.strip()
            for value in self.__dict__.values()
        ):
            raise ValueError("every basis dimension is required")

    @property
    def known(self) -> bool:
        return all(
            value.strip().casefold() not in {"unknown", "unavailable", "not_disclosed"}
            for value in self.__dict__.values()
        )


@dataclass(frozen=True)
class Interval:
    """Closed finite interval. Unknown/open bounds must stay unavailable."""

    low: Decimal
    high: Decimal

    def __post_init__(self):
        if not all(isinstance(x, Decimal) for x in (self.low, self.high)):
            raise TypeError("bounds must be Decimal")
        if (
            not all(x.is_finite() for x in (self.low, self.high))
            or self.low > self.high
        ):
            raise ValueError("invalid finite interval")


@dataclass(frozen=True)
class Evidence:
    source: str
    available_on: date
    derivation: str

    def __post_init__(self):
        if not self.source.strip() or not isinstance(self.available_on, date):
            raise ValueError("source and availability date are required")
        if self.derivation not in {
            "disclosed",
            "award_derived",
            "allocated",
            "modeled",
            "assumed",
            "unavailable",
        }:
            raise ValueError("unknown evidence derivation")


@dataclass(frozen=True)
class CostItem:
    identity: str
    requirements: tuple[str, ...]
    amount: Interval | None
    basis: Basis
    evidence: Evidence
    disposition: str
    value_basis: str
    overlap_group: str = ""

    def __post_init__(self):
        if (
            not self.identity.strip()
            or not self.requirements
            or any(not key.strip() for key in self.requirements)
        ):
            raise ValueError("identity and requirements are required")
        if len(set(self.requirements)) != len(self.requirements):
            raise ValueError("duplicate requirement")
        if self.disposition not in {"included", "excluded", "overlap"}:
            raise ValueError("unknown counting disposition")
        if self.value_basis not in {
            "point",
            "range",
            "band",
            "not_public",
            "backlog",
            "lease_contract",
            "combined",
            "midstream",
        }:
            raise ValueError("unknown value basis")
        if self.value_basis == "not_public" and self.amount is not None:
            raise ValueError("not_public cannot carry an amount")
        if self.amount is not None and self.amount.low < ZERO:
            raise ValueError("negative cost")
        if (
            self.value_basis == "point"
            and self.amount is not None
            and self.amount.low != self.amount.high
        ):
            raise ValueError("point value must have identical bounds")


@dataclass(frozen=True)
class Reconciliation:
    eligible: Interval
    residual: Interval
    coverage: Interval | None
    residual_fraction: Interval | None
    covered_requirements: tuple[str, ...]
    missing_requirements: tuple[str, ...]
    unavailable: tuple[str, ...]
    excluded_ids: tuple[str, ...]
    overlap_ids: tuple[str, ...]
    items: tuple[CostItem, ...]
    total: Interval
    basis: Basis
    linked_requirements: tuple[str, ...]


def ratio(numerator: Interval, denominator: Interval) -> Interval | None:
    if denominator.low <= ZERO:
        return None
    values = [
        n / d
        for n in (numerator.low, numerator.high)
        for d in (denominator.low, denominator.high)
    ]
    return Interval(min(values), max(values))


def reconcile(
    total: Interval,
    basis: Basis,
    items: tuple[CostItem, ...],
    requirements: tuple[str, ...],
) -> Reconciliation:
    """Count each award once, even when linked to several requirements.

    Potential overlap between distinct included awards must be resolved before
    arithmetic. Excluded and overlap rows retain their native basis and values.
    """
    if not basis.known:
        raise ValueError("unavailable accounting basis")
    if total.low < ZERO:
        raise ValueError("negative total")
    if len(set(requirements)) != len(requirements) or not requirements:
        raise ValueError("unique requirements are required")
    unique: dict[str, CostItem] = {}
    for row in items:
        if row.identity in unique and row != unique[row.identity]:
            raise ValueError("conflicting duplicate award")
        if not set(row.requirements) <= set(requirements):
            raise ValueError("unknown requirement")
        unique[row.identity] = row
    included = []
    overlap_groups = set()
    for row in unique.values():
        if row.disposition != "included":
            continue
        if row.basis != basis:
            raise ValueError("incompatible accounting basis")
        if row.evidence.derivation not in {"disclosed", "award_derived"}:
            raise ValueError("bottom-up contributions must be observed")
        if row.value_basis in {"backlog", "lease_contract", "combined", "midstream"}:
            raise ValueError("value basis is not additive CAPEX")
        if row.overlap_group:
            if row.overlap_group in overlap_groups:
                raise ValueError("unresolved included overlap group")
            overlap_groups.add(row.overlap_group)
        if row.amount is not None:
            included.append(row)
    eligible = Interval(
        sum((r.amount.low for r in included), ZERO),
        sum((r.amount.high for r in included), ZERO),
    )
    residual = Interval(total.low - eligible.high, total.high - eligible.low)
    covered = {key for row in included for key in row.requirements}
    return Reconciliation(
        eligible,
        residual,
        ratio(eligible, total),
        ratio(residual, total),
        tuple(sorted(covered)),
        tuple(sorted(set(requirements) - covered)),
        tuple(sorted(r.identity for r in unique.values() if r.amount is None)),
        tuple(
            sorted(r.identity for r in unique.values() if r.disposition == "excluded")
        ),
        tuple(
            sorted(r.identity for r in unique.values() if r.disposition == "overlap")
        ),
        tuple(unique[key] for key in sorted(unique)),
        total,
        basis,
        tuple(sorted({key for row in unique.values() for key in row.requirements})),
    )


@dataclass(frozen=True)
class Scenario:
    identity: str
    architecture: str
    shares: Mapping[str, Decimal]
    source: str


@dataclass(frozen=True)
class Allocation:
    scenarios: dict[str, dict[str, Decimal]]
    bands: dict[str, Interval]
    unallocated: Interval
    sources: tuple[str, ...]
    derivation: str = "allocated"
    marginals_additive: bool = False


def allocate(
    total: Decimal,
    architecture: str,
    scenarios: tuple[Scenario, ...],
    requirements: tuple[str, ...],
    quantum: Decimal,
) -> Allocation:
    """Each joint scenario conserves the total; marginal bands are non-additive.

    The caller supplies every share, its source, and the output quantum. No
    engineering allocation prior is embedded in this API.
    """
    if not isinstance(total, Decimal) or not total.is_finite() or total < ZERO:
        raise ValueError("invalid total")
    if not isinstance(quantum, Decimal) or not quantum.is_finite() or quantum <= ZERO:
        raise ValueError("invalid quantum")
    if not scenarios or not architecture.strip() or not requirements:
        raise ValueError("architecture, requirements and scenarios are required")
    if len(set(requirements)) != len(requirements) or "unallocated" in requirements:
        raise ValueError("invalid requirements")
    allocations = {}
    for scenario in scenarios:
        if scenario.architecture != architecture:
            raise ValueError("incompatible architecture")
        if not scenario.identity.strip() or not scenario.source.strip():
            raise ValueError("scenario identity and source are required")
        if scenario.identity in allocations:
            raise ValueError("duplicate scenario")
        if not set(scenario.shares) <= {*requirements, "unallocated"}:
            raise ValueError("unknown requirement in scenario")
        if not all(
            isinstance(x, Decimal) and x.is_finite() for x in scenario.shares.values()
        ):
            raise ValueError("finite Decimal shares are required")
        shares = {
            key: scenario.shares.get(key, ZERO)
            for key in (*requirements, "unallocated")
        }
        allocations[scenario.identity] = largest_remainder_allocate(
            total, shares, quantum
        )
    bands = {
        key: Interval(
            min(a[key] for a in allocations.values()),
            max(a[key] for a in allocations.values()),
        )
        for key in (*sorted(requirements), "unallocated")
    }
    return Allocation(
        dict(sorted(allocations.items())),
        {key: value for key, value in bands.items() if key != "unallocated"},
        bands["unallocated"],
        tuple(sorted({s.source for s in scenarios})),
    )
