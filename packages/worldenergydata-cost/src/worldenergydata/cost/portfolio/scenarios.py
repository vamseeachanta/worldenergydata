"""Joint architecture-specific scenarios with exact conserving allocations.

Accounting contract: repository synthesis plan (2026), task 6. The output
quantum is required input; no independent marginal bands are added together.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from .basis import Project, known


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    architecture: str
    shares: tuple[tuple[str, Decimal], ...]
    unallocated_share: Decimal
    source: str
    derivation: str

    def __post_init__(self) -> None:
        if not all(
            known(v) for v in (self.scenario_id, self.architecture, self.source)
        ):
            raise ValueError("scenario identity, architecture and source required")
        if self.derivation not in {"allocated", "modeled"}:
            raise ValueError("scenario must retain inferred derivation")
        keys = [key for key, _ in self.shares]
        if len(set(keys)) != len(keys) or any(not known(key) for key in keys):
            raise ValueError("unique known share identities required")
        values = [v for _, v in self.shares] + [self.unallocated_share]
        if any(
            not isinstance(v, Decimal) or not v.is_finite() or v < 0 for v in values
        ):
            raise ValueError("finite nonnegative Decimal shares required")
        if sum(map(Fraction, values)) != 1:
            raise ValueError("joint shares including unallocated must sum to one")


@dataclass(frozen=True)
class Allocation:
    scenario_id: str
    total: Decimal
    amounts: tuple[tuple[str, Decimal], ...]
    unallocated: Decimal
    unreconciled_variance: Decimal
    derivation: str
    source: str


def comparable(
    project: Project, scenarios: tuple[Scenario, ...]
) -> tuple[Scenario, ...]:
    return tuple(s for s in scenarios if s.architecture == project.architecture)


def decimal_units(units: int, quantum: Decimal) -> Decimal:
    """Exact integer multiple without dependence on the Decimal context."""
    sign, digits, exponent = quantum.as_tuple()
    coefficient = int("".join(map(str, digits))) * units
    return Decimal((sign, tuple(map(int, str(coefficient))), exponent))


def allocate(total: Decimal, scenario: Scenario, quantum: Decimal) -> Allocation:
    if not isinstance(quantum, Decimal) or not quantum.is_finite() or quantum <= 0:
        raise ValueError("positive finite Decimal quantum required")
    if not isinstance(total, Decimal) or not total.is_finite() or total < 0:
        raise ValueError("finite nonnegative Decimal total required")
    units = Fraction(total) / Fraction(quantum)
    if units.denominator != 1:
        raise ValueError("total must be quantum-aligned")
    # Tuple keys keep unallocated distinct from any caller-supplied identity.
    shares = {(False, k): v for k, v in scenario.shares}
    shares[(True, "")] = scenario.unallocated_share
    raw = {k: units * Fraction(v) for k, v in shares.items()}
    floors = {k: v.numerator // v.denominator for k, v in raw.items()}
    remainder = int(units) - sum(floors.values())
    order = sorted(raw, key=lambda k: (-(raw[k] - floors[k]), k))
    for key in order[:remainder]:
        floors[key] += 1
    amounts = tuple(
        (k, decimal_units(floors[(False, k)], quantum))
        for k, _ in sorted(scenario.shares)
    )
    unallocated = decimal_units(floors[(True, "")], quantum)
    variance_units = int(units) - sum(floors.values())
    return Allocation(
        scenario.scenario_id,
        total,
        amounts,
        unallocated,
        decimal_units(variance_units, quantum),
        scenario.derivation,
        scenario.source,
    )
