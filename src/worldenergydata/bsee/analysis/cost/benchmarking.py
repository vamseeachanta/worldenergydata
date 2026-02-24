# ABOUTME: WRK-019 cross-regional cost benchmarking module.
# ABOUTME: Provides BenchmarkResult dataclass, outlier detection, and cross-field
# ABOUTME: comparison against regional averages.

"""Cross-regional cost benchmarking (WRK-019).

Compares field-level cost summaries against regional averages, flags outliers,
and produces a tidy DataFrame suitable for visualisation or reporting.

Exports:
    BenchmarkResult — dataclass for per-field benchmarking result
    compare_fields_to_regional_average — compute deviation from regional mean
    detect_outliers — flag fields beyond a standard-deviation threshold
    build_comparison_dataframe — produce a tidy DataFrame from field summaries
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

import pandas as pd

from worldenergydata.bsee.analysis.cost.models import ConfidenceLevel
from worldenergydata.bsee.analysis.cost.cost_summary import FieldCostSummary

logger = logging.getLogger(__name__)

_DEFAULT_OUTLIER_STD = 2.0


# ---------------------------------------------------------------------------
# BenchmarkResult
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkResult:
    """Per-field benchmarking result relative to regional average.

    Attributes:
        field_name: Human-readable field identifier.
        region: Region key.
        total_cost_usd_mm: Field total cost in USD MM.
        regional_avg_usd_mm: Mean total cost for the region.
        deviation_pct: Signed deviation from regional mean (%).
        is_outlier: True if |deviation_pct| exceeds the outlier threshold.
        n_wells: Number of wells contributing to the total cost.
        confidence: Overall confidence level for the estimates.
        cost_per_well_usd_mm: Average cost per well (total / n_wells).
    """

    field_name: str
    region: str
    total_cost_usd_mm: float
    regional_avg_usd_mm: float
    deviation_pct: float
    is_outlier: bool
    n_wells: int
    confidence: ConfidenceLevel
    cost_per_well_usd_mm: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a flat dict suitable for DataFrame construction."""
        return {
            "field_name": self.field_name,
            "region": self.region,
            "total_cost_usd_mm": round(self.total_cost_usd_mm, 4),
            "regional_avg_usd_mm": round(self.regional_avg_usd_mm, 4),
            "deviation_pct": round(self.deviation_pct, 2),
            "is_outlier": self.is_outlier,
            "n_wells": self.n_wells,
            "confidence": self.confidence.value,
            "cost_per_well_usd_mm": round(self.cost_per_well_usd_mm, 4),
        }


# ---------------------------------------------------------------------------
# compare_fields_to_regional_average
# ---------------------------------------------------------------------------


def compare_fields_to_regional_average(
    field_summaries: list[FieldCostSummary],
    threshold_std: float = _DEFAULT_OUTLIER_STD,
) -> list[BenchmarkResult]:
    """Compare each field's total cost to the mean of all provided summaries.

    Computes the global average across all summaries, then derives signed
    deviation percentage for each field.  Outliers are flagged using the
    ``threshold_std`` parameter.

    Args:
        field_summaries: List of FieldCostSummary objects.
        threshold_std: Number of standard deviations from mean to flag outlier.

    Returns:
        List of BenchmarkResult, one per input summary.
        Empty list if input is empty.
    """
    if not field_summaries:
        return []

    costs = [s.total_capex_usd_mm for s in field_summaries]
    mean_cost = sum(costs) / len(costs)

    # Compute population std
    if len(costs) > 1:
        variance = sum((c - mean_cost) ** 2 for c in costs) / len(costs)
        std_dev = math.sqrt(variance)
    else:
        std_dev = 0.0

    results: list[BenchmarkResult] = []
    for summary in field_summaries:
        cost = summary.total_capex_usd_mm
        deviation_pct = (
            ((cost - mean_cost) / mean_cost * 100.0) if mean_cost != 0.0 else 0.0
        )
        is_outlier = (
            std_dev > 0.0
            and abs(cost - mean_cost) > threshold_std * std_dev
        )

        cost_per_well = (
            cost / summary.n_wells if summary.n_wells > 0 else 0.0
        )

        # Determine dominant confidence from estimates
        confidence = _dominant_confidence(summary)

        results.append(
            BenchmarkResult(
                field_name=summary.field_name,
                region=summary.region,
                total_cost_usd_mm=cost,
                regional_avg_usd_mm=mean_cost,
                deviation_pct=deviation_pct,
                is_outlier=is_outlier,
                n_wells=summary.n_wells,
                confidence=confidence,
                cost_per_well_usd_mm=cost_per_well,
            )
        )

    return results


# ---------------------------------------------------------------------------
# detect_outliers
# ---------------------------------------------------------------------------


def detect_outliers(
    field_summaries: list[FieldCostSummary],
    threshold_std: float = _DEFAULT_OUTLIER_STD,
) -> list[BenchmarkResult]:
    """Flag outlier fields using a standard-deviation threshold.

    Wrapper around ``compare_fields_to_regional_average`` that explicitly
    applies the outlier threshold.

    Args:
        field_summaries: List of FieldCostSummary objects.
        threshold_std: Number of standard deviations from mean to flag outlier.

    Returns:
        List of BenchmarkResult with ``is_outlier`` flags set.
    """
    return compare_fields_to_regional_average(
        field_summaries=field_summaries,
        threshold_std=threshold_std,
    )


# ---------------------------------------------------------------------------
# build_comparison_dataframe
# ---------------------------------------------------------------------------


def build_comparison_dataframe(
    field_summaries: list[FieldCostSummary],
    threshold_std: float = _DEFAULT_OUTLIER_STD,
) -> pd.DataFrame:
    """Produce a tidy DataFrame from a list of FieldCostSummary objects.

    Calls ``compare_fields_to_regional_average`` internally and converts the
    BenchmarkResult list to a DataFrame.

    Args:
        field_summaries: List of FieldCostSummary objects.
        threshold_std: Outlier flagging threshold (standard deviations).

    Returns:
        DataFrame with one row per field containing benchmark columns.
        Empty DataFrame if field_summaries is empty.
    """
    if not field_summaries:
        return pd.DataFrame()

    results = compare_fields_to_regional_average(
        field_summaries=field_summaries,
        threshold_std=threshold_std,
    )

    rows = [r.to_dict() for r in results]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _dominant_confidence(summary: FieldCostSummary) -> ConfidenceLevel:
    """Return the worst (lowest) confidence level across all estimates."""
    all_estimates = (
        summary.drilling_estimates
        + summary.completion_estimates
        + summary.intervention_estimates
    )
    if not all_estimates:
        return ConfidenceLevel.LOW

    # Confidence priority: LOW < MEDIUM < HIGH — return worst
    priority = {
        ConfidenceLevel.LOW: 0,
        ConfidenceLevel.MEDIUM: 1,
        ConfidenceLevel.HIGH: 2,
    }
    return min(all_estimates, key=lambda e: priority[e.confidence]).confidence
