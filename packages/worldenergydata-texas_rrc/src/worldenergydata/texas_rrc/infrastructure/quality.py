"""Quality summaries for Texas RRC infrastructure access metrics."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence

import pandas as pd

SCORING_THRESHOLDS_MILES = {
    "direct_access_max": 1.0,
    "near_access_max": 5.0,
    "regional_access_max": 10.0,
    "remote_access_max": 25.0,
}
DIRECT_SOURCE_CAVEATS = [
    "rrc_gis_screening_only",
    "field_centroid_pipeline_screening",
    "dominant_county_pipeline_filter",
    "pipeline_envelope_distance_screening",
    "pipeline_presence_not_capacity_or_tariff",
    "pipeline_route_not_engineered_tie_in",
    "patchops_validation_only",
]


@dataclass(frozen=True)
class InfrastructureAccessQualityReport:
    """Aggregate quality report for infrastructure access outputs."""

    row_count: int
    source_gaps: tuple[str, ...]
    access_class_counts: dict[str, int]
    caveat_counts: dict[str, int]
    missing_well_gis_count: int
    missing_pipeline_source_count: int
    malformed_source_file_count: int
    malformed_source_files: tuple[str, ...]
    nearest_pipeline_distance_min_miles: float | None
    nearest_pipeline_distance_max_miles: float | None


def assess_infrastructure_access_quality(
    metrics: pd.DataFrame,
    source_gaps: Sequence[str] = (),
    malformed_source_files: Sequence[str] = (),
) -> InfrastructureAccessQualityReport:
    """Summarize access-class mix, caveats, and source gaps."""
    distances = pd.to_numeric(
        metrics.get("nearest_pipeline_distance_miles", pd.Series(dtype="float64")),
        errors="coerce",
    ).dropna()
    return InfrastructureAccessQualityReport(
        row_count=len(metrics),
        source_gaps=tuple(source_gaps),
        access_class_counts=_value_counts(metrics, "infrastructure_access_class"),
        caveat_counts=_caveat_counts(metrics),
        missing_well_gis_count=_caveat_count(metrics, "missing_well_gis"),
        missing_pipeline_source_count=_caveat_count(metrics, "missing_pipeline_gis"),
        malformed_source_file_count=len(tuple(malformed_source_files)),
        malformed_source_files=tuple(malformed_source_files),
        nearest_pipeline_distance_min_miles=(
            None if distances.empty else float(distances.min())
        ),
        nearest_pipeline_distance_max_miles=(
            None if distances.empty else float(distances.max())
        ),
    )


def _value_counts(metrics: pd.DataFrame, column: str) -> dict[str, int]:
    if column not in metrics:
        return {}
    counts = metrics[column].dropna().value_counts()
    return {str(key): int(value) for key, value in sorted(counts.items())}


def _caveat_counts(metrics: pd.DataFrame) -> dict[str, int]:
    counter: Counter[str] = Counter()
    if "source_caveats" not in metrics:
        return {}
    for value in metrics["source_caveats"].dropna():
        counter.update(part for part in str(value).split("|") if part)
    return dict(sorted(counter.items()))


def _caveat_count(metrics: pd.DataFrame, caveat: str) -> int:
    return _caveat_counts(metrics).get(caveat, 0)


__all__ = [
    "DIRECT_SOURCE_CAVEATS",
    "SCORING_THRESHOLDS_MILES",
    "InfrastructureAccessQualityReport",
    "assess_infrastructure_access_quality",
]
