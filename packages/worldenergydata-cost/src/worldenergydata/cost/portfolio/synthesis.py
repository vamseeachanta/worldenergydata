"""Two-way accounting without pooling architectures or laundering uncertainty.

Definitions: repository cost synthesis plan (2026), tasks 4–6 and Pseudocode.
Residual = target - eligible observed. Unallocated is a scenario share with no
requirement. Variance = target - allocated - unallocated, per joint scenario.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from fractions import Fraction

from .basis import Contribution, Project
from .intervals import ZERO, Interval
from .scenarios import Allocation, Scenario, allocate, decimal_units


@dataclass(frozen=True)
class Synthesis:
    project: Project
    contributions: tuple[Contribution, ...]
    eligible: Interval
    excluded: Interval
    overlap: Interval
    residual: Interval
    coverage: Interval | None
    residual_fraction: Interval | None
    not_public: tuple[str, ...]
    allocations: tuple[Allocation, ...]
    bands: tuple[tuple[str, Interval], ...]
    top_down_status: str
    bands_additive: bool = False


def synthesize(
    project: Project,
    rows: tuple[Contribution, ...],
    scenarios: tuple[Scenario, ...] = (),
    *,
    quantum: Decimal | None = None,
) -> Synthesis:
    unique: dict[str, Contribution] = {}
    for row in rows:
        if row.award_id in unique and unique[row.award_id] != row:
            raise ValueError("conflicting rows for one award identity")
        unique[row.award_id] = row
    totals = {d: Interval.point(ZERO) for d in ("included", "excluded", "overlap")}
    groups: set[str] = set()
    for row in unique.values():
        row.validate_for(project)
        if row.disposition == "included" and row.overlap_group:
            if row.overlap_group in groups:
                raise ValueError("multiple included awards in one overlap group")
            groups.add(row.overlap_group)
        if row.amount is None:
            continue
        # Excluded foreign-basis amounts cannot form a meaningful monetary sum.
        # They remain in the evidence ledger; compatible diagnostics sum only.
        if row.basis == project.basis:
            totals[row.disposition] = totals[row.disposition] + row.amount
    eligible = totals["included"]
    residual = project.total - eligible
    if len({s.scenario_id for s in scenarios}) != len(scenarios):
        raise ValueError("unique scenario identities required")
    allocations = []
    for scenario in sorted(scenarios, key=lambda s: s.scenario_id):
        if scenario.architecture != project.architecture:
            raise ValueError("incompatible architecture")
        if not {k for k, _ in scenario.shares} <= set(project.requirement_ids):
            raise ValueError("scenario references unknown requirement")
        if {k for k, _ in scenario.shares} != set(project.requirement_ids):
            raise ValueError("scenario must list every project requirement explicitly")
        if quantum is None:
            raise ValueError("allocation quantum required")
        if not project.total.low.is_finite() or not project.total.high.is_finite():
            raise ValueError("top-down allocation requires finite total bounds")
        for total in sorted({project.total.low, project.total.high}):
            allocation = allocate(total, scenario, quantum)
            if project.total.low != project.total.high:
                lower = total == project.total.low
                allocation = replace(
                    allocation,
                    case_id="lower-bound" if lower else "upper-bound",
                    target_endpoint="low" if lower else "high",
                    target_open=(
                        project.total.low_open if lower else project.total.high_open
                    ),
                    limiting=True,
                )
            allocations.append(allocation)
    bands = []
    if allocations:
        for key in sorted(project.requirement_ids):
            values = [dict(a.amounts)[key] for a in allocations]
            if project.total.low != project.total.high:
                # Largest remainder is not monotonic in total (apportionment
                # paradox). Floor/ceil of raw shares encloses interior totals too.
                values = []
                for scenario in scenarios:
                    share = Fraction(dict(scenario.shares)[key])
                    low = Fraction(project.total.low) * share / Fraction(quantum)
                    high = Fraction(project.total.high) * share / Fraction(quantum)
                    values.extend(
                        (
                            decimal_units(low.numerator // low.denominator, quantum),
                            decimal_units(
                                -(-high.numerator // high.denominator), quantum
                            ),
                        )
                    )
            # Joint rows alone are additive; bands include rounding uncertainty.
            bands.append((key, Interval(min(values), max(values))))
    return Synthesis(
        project,
        tuple(unique[k] for k in sorted(unique)),
        eligible,
        totals["excluded"],
        totals["overlap"],
        residual,
        eligible.divide(project.total),
        residual.divide(project.total),
        tuple(sorted(r.award_id for r in unique.values() if r.amount is None)),
        tuple(allocations),
        tuple(bands),
        "evaluated" if allocations else "NOT_EVALUATED",
    )
