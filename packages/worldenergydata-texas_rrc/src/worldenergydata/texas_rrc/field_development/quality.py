"""Quality summaries for Texas RRC field-development metrics."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import pandas as pd

from worldenergydata.texas_rrc.field_development.sources import (
    FieldDevelopmentInputs,
)


@dataclass(frozen=True)
class FieldDevelopmentQualityReport:
    """Aggregate caveat and maturity counts for field-development outputs."""

    row_count: int
    source_gaps: tuple[str, ...]
    caveat_counts: dict[str, int]
    maturity_counts: dict[str, int]


def assess_field_development_quality(
    metrics: pd.DataFrame,
    inputs: FieldDevelopmentInputs,
) -> FieldDevelopmentQualityReport:
    """Summarize field-development caveats, maturity mix, and source gaps."""
    return FieldDevelopmentQualityReport(
        row_count=len(metrics),
        source_gaps=tuple(inputs.source_gaps),
        caveat_counts=_caveat_counts(metrics),
        maturity_counts=_maturity_counts(metrics),
    )


def _caveat_counts(metrics: pd.DataFrame) -> dict[str, int]:
    counter: Counter[str] = Counter()
    if "source_caveats" not in metrics:
        return {}
    for value in metrics["source_caveats"].dropna():
        counter.update(part for part in str(value).split("|") if part)
    return dict(sorted(counter.items()))


def _maturity_counts(metrics: pd.DataFrame) -> dict[str, int]:
    if "production_maturity_class" not in metrics:
        return {}
    counts = metrics["production_maturity_class"].dropna().value_counts()
    return {str(key): int(value) for key, value in sorted(counts.items())}


__all__ = [
    "FieldDevelopmentQualityReport",
    "assess_field_development_quality",
]
