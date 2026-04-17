# ABOUTME: WRK-019 field/lease/region cost aggregation module.
# ABOUTME: Provides FieldCostSummary dataclass and summarize_*_costs functions
# ABOUTME: for drilling, completion, and intervention cost roll-ups.

"""Field, lease, and region cost aggregation (WRK-019).

Aggregates CostEstimate outputs from the CostEngine into structured summaries
at the field, lease, and region level.  Designed to handle LFS stub inputs
gracefully (empty estimate lists).

Exports:
    FieldCostSummary — dataclass for per-field cost roll-up
    summarize_field_costs — build FieldCostSummary from estimate lists
    summarize_lease_costs — dict of per-lease cost summaries
    summarize_region_costs — DataFrame of cross-field regional aggregation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from worldenergydata.bsee.analysis.cost.models import (
    ActivityType,
    ConfidenceLevel,
    CostEstimate,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FieldCostSummary
# ---------------------------------------------------------------------------


@dataclass
class FieldCostSummary:
    """Cost roll-up for a single field across all activity types.

    Totals are computed in ``__post_init__`` from the provided estimate lists.

    Args:
        field_name: Human-readable field identifier.
        region: Region key (e.g. ``"gom"``).
        drilling_estimates: List of drilling CostEstimate objects.
        completion_estimates: List of completion CostEstimate objects.
        intervention_estimates: List of intervention CostEstimate objects.
    """

    field_name: str
    region: str
    drilling_estimates: list[CostEstimate] = field(default_factory=list)
    completion_estimates: list[CostEstimate] = field(default_factory=list)
    intervention_estimates: list[CostEstimate] = field(default_factory=list)

    # Computed in __post_init__
    total_drilling_cost_usd_mm: float = field(init=False)
    total_completion_cost_usd_mm: float = field(init=False)
    total_intervention_cost_usd_mm: float = field(init=False)
    total_capex_usd_mm: float = field(init=False)
    n_wells: int = field(init=False)
    avg_well_cost_usd_mm: float = field(init=False)
    confidence_summary: str = field(init=False)

    def __post_init__(self) -> None:
        self.total_drilling_cost_usd_mm = sum(
            e.cost_usd_mm for e in self.drilling_estimates
        )
        self.total_completion_cost_usd_mm = sum(
            e.cost_usd_mm for e in self.completion_estimates
        )
        self.total_intervention_cost_usd_mm = sum(
            e.cost_usd_mm for e in self.intervention_estimates
        )
        self.total_capex_usd_mm = (
            self.total_drilling_cost_usd_mm
            + self.total_completion_cost_usd_mm
            + self.total_intervention_cost_usd_mm
        )
        self.n_wells = len(self.drilling_estimates)
        self.avg_well_cost_usd_mm = (
            self.total_drilling_cost_usd_mm / self.n_wells if self.n_wells > 0 else 0.0
        )
        self.confidence_summary = self._build_confidence_summary()

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a flat dict suitable for DataFrame construction."""
        return {
            "field_name": self.field_name,
            "region": self.region,
            "total_drilling_cost_usd_mm": round(self.total_drilling_cost_usd_mm, 4),
            "total_completion_cost_usd_mm": round(self.total_completion_cost_usd_mm, 4),
            "total_intervention_cost_usd_mm": round(
                self.total_intervention_cost_usd_mm, 4
            ),
            "total_capex_usd_mm": round(self.total_capex_usd_mm, 4),
            "n_wells": self.n_wells,
            "avg_well_cost_usd_mm": round(self.avg_well_cost_usd_mm, 4),
            "confidence_summary": self.confidence_summary,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_confidence_summary(self) -> str:
        """Return a short string summarising confidence levels across estimates."""
        all_estimates = (
            self.drilling_estimates
            + self.completion_estimates
            + self.intervention_estimates
        )
        if not all_estimates:
            return "no_data"

        counts: dict[str, int] = {}
        for est in all_estimates:
            key = est.confidence.value
            counts[key] = counts.get(key, 0) + 1

        parts = [f"{level}:{n}" for level, n in sorted(counts.items())]
        return ",".join(parts)


# ---------------------------------------------------------------------------
# summarize_field_costs
# ---------------------------------------------------------------------------


def summarize_field_costs(
    field_name: str,
    region: str,
    drilling_estimates: list[CostEstimate],
    completion_estimates: list[CostEstimate],
    intervention_estimates: list[CostEstimate],
) -> FieldCostSummary:
    """Build a FieldCostSummary from separate estimate lists.

    Args:
        field_name: Human-readable field identifier.
        region: Region key.
        drilling_estimates: Drilling CostEstimate list.
        completion_estimates: Completion CostEstimate list.
        intervention_estimates: Intervention CostEstimate list.

    Returns:
        FieldCostSummary with computed totals.
    """
    logger.debug(
        "Summarising costs for field=%s region=%s "
        "(drilling=%d, completion=%d, intervention=%d)",
        field_name,
        region,
        len(drilling_estimates),
        len(completion_estimates),
        len(intervention_estimates),
    )
    return FieldCostSummary(
        field_name=field_name,
        region=region,
        drilling_estimates=drilling_estimates,
        completion_estimates=completion_estimates,
        intervention_estimates=intervention_estimates,
    )


# ---------------------------------------------------------------------------
# summarize_lease_costs
# ---------------------------------------------------------------------------


def summarize_lease_costs(
    estimates_by_lease: dict[str, list[CostEstimate]],
    region: str,
) -> dict[str, dict[str, Any]]:
    """Aggregate cost estimates per lease.

    Args:
        estimates_by_lease: Dict mapping lease number to list of CostEstimate.
        region: Region key for all leases.

    Returns:
        Dict mapping lease number to summary dict with ``total_cost_usd_mm``,
        ``n_estimates``, and ``activity_breakdown`` keys.
    """
    result: dict[str, dict[str, Any]] = {}

    for lease, estimates in estimates_by_lease.items():
        if not estimates:
            result[lease] = {
                "total_cost_usd_mm": 0.0,
                "n_estimates": 0,
                "activity_breakdown": {},
                "region": region,
            }
            continue

        total = sum(e.cost_usd_mm for e in estimates)
        breakdown: dict[str, float] = {}
        for est in estimates:
            key = est.activity_type.value
            breakdown[key] = breakdown.get(key, 0.0) + est.cost_usd_mm

        result[lease] = {
            "total_cost_usd_mm": round(total, 4),
            "n_estimates": len(estimates),
            "activity_breakdown": {k: round(v, 4) for k, v in breakdown.items()},
            "region": region,
        }

    return result


# ---------------------------------------------------------------------------
# summarize_region_costs
# ---------------------------------------------------------------------------


def summarize_region_costs(
    field_summaries: list[FieldCostSummary],
) -> pd.DataFrame:
    """Produce a cross-field DataFrame aggregating all FieldCostSummary objects.

    Args:
        field_summaries: List of FieldCostSummary objects (may be multi-region).

    Returns:
        DataFrame with one row per field and columns:
        field_name, region, total_drilling_cost_usd_mm,
        total_completion_cost_usd_mm, total_intervention_cost_usd_mm,
        total_capex_usd_mm, n_wells, avg_well_cost_usd_mm, confidence_summary.
        Empty DataFrame if field_summaries is empty.
    """
    if not field_summaries:
        return pd.DataFrame()

    rows = [summary.to_dict() for summary in field_summaries]
    return pd.DataFrame(rows)
