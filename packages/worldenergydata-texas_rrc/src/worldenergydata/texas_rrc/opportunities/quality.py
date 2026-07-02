"""Quality assessment for Texas RRC field-opportunity rankings."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class FieldOpportunityQuality:
    """Quality summary for a field-opportunity ranking batch."""

    row_count: int
    source_gaps: tuple[str, ...]
    opportunity_class_counts: dict[str, int]
    architecture_class_counts: dict[str, int]
    caveat_counts: dict[str, int]
    quality_flag_counts: dict[str, int]
    low_data_confidence_count: int
    score_min: float | None
    score_max: float | None
    score_mean: float | None


def assess_field_opportunity_quality(
    rankings: pd.DataFrame,
    source_gaps: tuple[str, ...],
) -> FieldOpportunityQuality:
    """Assess score, caveat, and class quality for ranking outputs."""
    scores = pd.to_numeric(rankings.get("opportunity_score"), errors="coerce")
    architecture = rankings.get("architecture_signal_class", pd.Series(dtype=object))
    return FieldOpportunityQuality(
        row_count=len(rankings),
        source_gaps=tuple(source_gaps),
        opportunity_class_counts=_value_counts(rankings.get("opportunity_class")),
        architecture_class_counts=_value_counts(architecture),
        caveat_counts=_term_counts(rankings.get("source_caveats")),
        quality_flag_counts=_term_counts(rankings.get("quality_flags")),
        low_data_confidence_count=int((architecture == "low_data_confidence").sum()),
        score_min=_score(scores.min()),
        score_max=_score(scores.max()),
        score_mean=_score(scores.mean()),
    )


def _value_counts(series: pd.Series | None) -> dict[str, int]:
    if series is None:
        return {}
    counts = Counter(str(value) for value in series.dropna() if str(value))
    return dict(sorted(counts.items()))


def _term_counts(series: pd.Series | None) -> dict[str, int]:
    counts: Counter[str] = Counter()
    if series is None:
        return {}
    for value in series.dropna():
        normalized = str(value).replace(",", ";").replace("|", ";")
        counts.update(term.strip() for term in normalized.split(";") if term.strip())
    return dict(sorted(counts.items()))


def _score(value: object) -> float | None:
    try:
        if pd.isna(value):
            return None
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


__all__ = [
    "FieldOpportunityQuality",
    "assess_field_opportunity_quality",
]
