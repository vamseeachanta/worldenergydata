"""Exact bidirectional accounting for project cost maps."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True)
class ComparisonBasis:
    currency: str
    price_basis: str
    ownership_basis: str
    scope_basis: str
    capex_basis: str


@dataclass(frozen=True)
class ClosedInterval:
    low: Decimal
    high: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.low, Decimal) or not isinstance(self.high, Decimal):
            raise TypeError("interval bounds must be Decimal")
        if self.low > self.high:
            raise ValueError("interval low exceeds high")


@dataclass(frozen=True)
class ObservedContribution:
    award_id: str
    requirement_ids: tuple[str, ...]
    amount: ClosedInterval | None
    source_basis: ComparisonBasis
    comparison_basis: ComparisonBasis | None
    counting_disposition: Literal["included", "excluded", "overlap"]
    value_basis: str = "point"

    def __post_init__(self) -> None:
        if self.amount is not None and self.amount.low < 0:
            raise ValueError("negative monetary contribution")

    @classmethod
    def point(cls, **values: Any) -> ObservedContribution:
        value = values.pop("value")
        return cls(amount=ClosedInterval(value, value), **values)

    @classmethod
    def not_public(cls, **values: Any) -> ObservedContribution:
        return cls(amount=None, value_basis="not_public", **values)


@dataclass(frozen=True)
class BottomUpReconciliation:
    eligible: ClosedInterval
    excluded: ClosedInterval
    overlap: ClosedInterval
    residual: ClosedInterval
    coverage: ClosedInterval | None
    residual_percentage: ClosedInterval | None
    evidence_vintage: str
    target_event_id: str | None
    not_public_awards: tuple[str, ...]


@dataclass(frozen=True)
class IntervalMetrics:
    residual: ClosedInterval
    coverage: ClosedInterval | None
    residual_percentage: ClosedInterval | None


@dataclass(frozen=True)
class TopDownAccounting:
    residual: Decimal
    unallocated: Decimal
    unreconciled_variance: Decimal


@dataclass(frozen=True)
class AllocationBand:
    low: Decimal
    high: Decimal
    derivation: Literal["allocated"] = "allocated"
    provenance: Literal["assumed"] = "assumed"
    scenario_status: Literal["proposed"] = "proposed"
    confidence: Literal["low"] = "low"


@dataclass(frozen=True)
class AwardReference:
    award_id: str
    additive: bool


@dataclass(frozen=True)
class JointScenario:
    scenario_id: str
    shares: dict[str, Decimal]
    derivation: str = "assumed"
    status: str = "proposed"
    confidence: str = "low"
    reuse_allowed: bool = False
    rationale: str = "Big Foot TLP pilot joint allocation; not a disclosure"


class BandedAllocations(dict[str, AllocationBand]):
    additive = False


@dataclass(frozen=True)
class BigFootEvidence:
    requirement_ids: tuple[str, ...]
    linked_requirement_ids: tuple[str, ...]
    contributions: tuple[ObservedContribution, ...]
    target_basis: ComparisonBasis
    award_references_by_requirement: dict[str, tuple[AwardReference, ...]]


@dataclass(frozen=True)
class TargetReconciliation:
    event_id: str
    target: Decimal
    target_kind: str
    target_basis: str
    target_vintage: str
    currency: str
    provenance: str
    confidence: str
    source_title: str
    source_url: str
    accounting: BottomUpReconciliation


_BASIS_FIELDS = ("currency", "price_basis", "ownership_basis", "scope_basis",
                 "capex_basis")
_REQUIREMENT_IDS = tuple(f"req-{number:06d}" for number in range(1, 9))


def _shares(values: str) -> dict[str, Decimal]:
    return dict(zip(_REQUIREMENT_IDS, map(Decimal, values.split()), strict=True))


BIG_FOOT_JOINT_SCENARIOS = {
    "reference": JointScenario("reference", _shares("0.29 0.06 0.12 0.22 0.06 0.07 0.12 0.06")),
    "host_heavy": JointScenario("host_heavy", _shares("0.38 0.05 0.10 0.17 0.05 0.06 0.13 0.06")),
    "well_heavy": JointScenario("well_heavy", _shares("0.20 0.08 0.15 0.28 0.07 0.08 0.09 0.05")),
}
_TARGET_BASES = {("evt-000003", "sanction_estimate"): "gross project cost at Dec-2010 sanction", ("evt-000004", "final_outturn"): "final gross project cost at first oil (Nov 2018), +28% vs FID"}


def _find_data_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "data" / "modules" / "cost" / "curated"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("cost curated data root not found")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _source_awards(data_root: Path) -> dict[tuple[str, str], dict[str, str]]:
    rows = _read_csv(data_root / "contract_awards.csv")
    return {
        (row["AWARD_YEAR"], row["CONTRACTOR"]): row
        for row in rows
        if row["PROJECT"] == "Big Foot"
    }


def _award_key(locator: str) -> tuple[str, str]:
    fields = dict(part.split("=", 1) for part in locator.split("|")[1:])
    return fields["AWARD_YEAR"], fields["CONTRACTOR"]


def _contribution_from_link(link: dict[str, str], source: dict[str, str], target: ComparisonBasis) -> ObservedContribution:
    value = Decimal(source["VALUE_LOW_MM"])
    included = link["COUNTING_DISPOSITION"] == "included"
    ownership = "gross" if included else "third_party"
    scope = "component" if included else "midstream"
    capex = "component_capex" if included else "non_capex"
    source_basis = ComparisonBasis("USD", "nominal", ownership, scope, capex)
    return ObservedContribution.point(
        award_id=link["AWARD_ID"],
        requirement_ids=tuple(re.split(r"[|;]", link["REQUIREMENT_IDS"])),
        value=value,
        source_basis=source_basis,
        comparison_basis=target if included else None,
        counting_disposition=link["COUNTING_DISPOSITION"],
        value_basis=source["VALUE_BASIS"],
    )


def requirement_award_references(rows: tuple[ObservedContribution, ...]) -> dict[str, tuple[AwardReference, ...]]:
    references: dict[str, list[AwardReference]] = {}
    for row in rows:
        reference = AwardReference(row.award_id, len(row.requirement_ids) == 1)
        for requirement_id in row.requirement_ids:
            references.setdefault(requirement_id, []).append(reference)
    return {key: tuple(value) for key, value in references.items()}


def load_big_foot_evidence(data_root: Path | None = None) -> BigFootEvidence:
    root = data_root or _find_data_root()
    requirements = _read_csv(root / "project_asset_requirements.csv")
    links = _read_csv(root / "award_asset_links.csv")
    requirements = [row for row in requirements if row["PROJECT_ID"] == "prj-000001"]
    links = [row for row in links if row["PROJECT_ID"] == "prj-000001"]
    sources = _source_awards(root)
    target = ComparisonBasis("USD", "nominal", "gross", "project", "project_capex")
    contributions = tuple(
        _contribution_from_link(link, sources[_award_key(link["SOURCE_LOCATOR"])], target)
        for link in links
    )
    requirement_ids = tuple(row["REQUIREMENT_ID"] for row in requirements)
    linked_ids = tuple(sorted(rid for row in contributions for rid in row.requirement_ids))
    references = requirement_award_references(contributions)
    return BigFootEvidence(requirement_ids, linked_ids, contributions, target, references)


def _event_key(locator: str) -> tuple[str, str]:
    fields = dict(part.split("=", 1) for part in locator.split("|")[1:])
    return fields["STATEMENT_DATE"], fields["KIND"]


def _load_big_foot_events(data_root: Path) -> tuple[dict[str, str], ...]:
    revisions = _read_csv(data_root / "cost_revision_trails.csv")
    source = {
        (row["STATEMENT_DATE"], row["KIND"]): row
        for row in revisions
        if row["PROJECT"] == "Big Foot"
    }
    identities = _read_csv(data_root / "cost_event_identity.csv")
    rows = []
    for identity in identities:
        if identity["OPAQUE_ID"] not in {"evt-000003", "evt-000004"}:
            continue
        rows.append({**source[_event_key(identity["SOURCE_RECORD_LOCATOR"])], **identity})
    return tuple(rows)


def reconcile_big_foot_targets(data_root: Path | None = None) -> dict[str, TargetReconciliation]:
    root = data_root or _find_data_root()
    evidence = load_big_foot_evidence(root)
    rows = _load_big_foot_events(root)
    return {row["OPAQUE_ID"]: reconcile_target_event(row, evidence) for row in rows}


def reconcile_target_event(event: dict[str, str], evidence: BigFootEvidence) -> TargetReconciliation:
    basis = evidence.target_basis
    if event["CURRENCY"] != basis.currency:
        raise ValueError("incompatible target currency")
    key = event["OPAQUE_ID"], event["KIND"]
    if _TARGET_BASES.get(key) != event["BASIS"]:
        raise ValueError("incompatible target price basis")
    event_id, target = event["OPAQUE_ID"], Decimal(event["VALUE_MM"])
    accounting = reconcile_bottom_up(
        target, basis, evidence.contributions, target_event_id=event_id
    )
    return TargetReconciliation(
        event_id, target, event["KIND"], event["BASIS"], event["STATEMENT_DATE"],
        event["CURRENCY"], event["PROVENANCE"], event["CONFIDENCE"],
        event["SOURCE_TITLE"], event["SOURCE_URL"], accounting)


def _validate_contribution(target: ComparisonBasis, row: ObservedContribution) -> None:
    for field in ("currency", "price_basis"):
        if getattr(row.source_basis, field) != getattr(target, field):
            raise ValueError(f"incompatible source {field}")
    if row.counting_disposition == "excluded":
        return
    if row.comparison_basis is None:
        raise ValueError("comparison_basis mapping is required")
    for field in _BASIS_FIELDS:
        if getattr(row.comparison_basis, field) != getattr(target, field):
            raise ValueError(f"incompatible {field}")


def _dedupe_contributions(rows: tuple[ObservedContribution, ...]) -> dict[str, ObservedContribution]:
    unique = {}
    for row in rows:
        prior = unique.get(row.award_id)
        if prior is not None and prior != row:
            raise ValueError(f"conflicting duplicate award_id {row.award_id}")
        unique[row.award_id] = row
    return unique


def _sum_intervals(rows: tuple[ObservedContribution, ...]) -> ClosedInterval:
    low = Decimal("0")
    high = Decimal("0")
    for row in rows:
        if row.amount is not None:
            low += row.amount.low
            high += row.amount.high
    return ClosedInterval(low, high)


def interval_residual(target: ClosedInterval, eligible: ClosedInterval) -> ClosedInterval:
    return ClosedInterval(target.low - eligible.high, target.high - eligible.low)


def _ratio_envelope(numerator: ClosedInterval, denominator: ClosedInterval) -> ClosedInterval | None:
    if denominator.low <= 0:
        return None
    values = tuple(
        value / divisor
        for value in (numerator.low, numerator.high)
        for divisor in (denominator.low, denominator.high)
    )
    return ClosedInterval(min(values), max(values))


def compute_interval_metrics(target: ClosedInterval, eligible: ClosedInterval) -> IntervalMetrics:
    residual = interval_residual(target, eligible)
    return IntervalMetrics(
        residual,
        _ratio_envelope(eligible, target),
        _ratio_envelope(residual, target),
    )


def reconcile_top_down(*, total: Decimal, allocations: dict[str, Decimal], unallocated: Decimal, bottom_up_residual: Decimal) -> TopDownAccounting:
    allocated = sum(allocations.values(), Decimal("0"))
    variance = total - allocated - unallocated
    return TopDownAccounting(bottom_up_residual, unallocated, variance)


def largest_remainder_allocate(total: Decimal, shares: dict[str, Decimal], quantum: Decimal = Decimal("0.01")) -> dict[str, Decimal]:
    if quantum <= 0:
        raise ValueError("quantum must be positive")
    if total < 0 or any(share < 0 for share in shares.values()):
        raise ValueError("total and shares must be nonnegative")
    if total % quantum:
        raise ValueError("total must be quantum-aligned")
    if sum(shares.values(), Decimal("0")) != Decimal("1.00"):
        raise ValueError("scenario shares must sum exactly to 1.00")
    raw = {requirement_id: total * share for requirement_id, share in shares.items()}
    allocated = {
        requirement_id: (value / quantum).to_integral_value(rounding=ROUND_FLOOR)
        * quantum
        for requirement_id, value in raw.items()
    }
    units = int((total - sum(allocated.values(), Decimal("0"))) / quantum)
    ranked = sorted(raw, key=lambda key: (-(raw[key] - allocated[key]), key))
    for requirement_id in ranked[:units]:
        allocated[requirement_id] += quantum
    if sum(allocated.values(), Decimal("0")) != total:
        raise ValueError("allocation failed to conserve total")
    return {key: allocated[key] for key in sorted(allocated)}


def allocate_big_foot_bands(total: Decimal) -> BandedAllocations:
    allocations = tuple(
        largest_remainder_allocate(total, scenario.shares)
        for scenario in BIG_FOOT_JOINT_SCENARIOS.values()
    )
    return BandedAllocations({
        requirement_id: AllocationBand(
            min(rows[requirement_id] for rows in allocations),
            max(rows[requirement_id] for rows in allocations),
        )
        for requirement_id in _REQUIREMENT_IDS
    })


def reconcile_bottom_up(target_total: Decimal | ClosedInterval, target_basis: ComparisonBasis, contributions: tuple[ObservedContribution, ...], *, evidence_vintage: str = "current_registry", target_event_id: str | None = None) -> BottomUpReconciliation:
    target = (
        target_total
        if isinstance(target_total, ClosedInterval)
        else ClosedInterval(target_total, target_total)
    )
    unique = _dedupe_contributions(contributions)
    for row in unique.values():
        _validate_contribution(target_basis, row)
    grouped = {
        disposition: tuple(
            row
            for row in unique.values()
            if row.counting_disposition == disposition
        )
        for disposition in ("included", "excluded", "overlap")
    }
    eligible = _sum_intervals(grouped["included"])
    excluded = _sum_intervals(grouped["excluded"])
    overlap = _sum_intervals(grouped["overlap"])
    metrics = compute_interval_metrics(target, eligible)
    unavailable = tuple(sorted(row.award_id for row in unique.values() if row.amount is None))
    return BottomUpReconciliation(eligible, excluded, overlap, metrics.residual,
                                  metrics.coverage, metrics.residual_percentage,
                                  evidence_vintage, target_event_id, unavailable)
