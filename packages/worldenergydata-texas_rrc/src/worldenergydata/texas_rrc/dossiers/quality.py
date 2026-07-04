"""Quality summaries for Texas RRC field-architecture dossiers."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re

import pandas as pd


@dataclass(frozen=True)
class FieldArchitectureDossierQuality:
    """Quality metadata for a field-architecture dossier batch."""

    row_count: int
    blocking_source_gaps: tuple[str, ...]
    informational_source_gaps: tuple[str, ...]
    architecture_class_counts: dict[str, int]
    selection_reason_counts: dict[str, int]
    caveat_counts: dict[str, int]
    quality_flag_counts: dict[str, int]
    limitation_count: int


def assess_field_architecture_dossier_quality(
    index: pd.DataFrame,
    blocking_source_gaps: tuple[str, ...] = (),
    informational_source_gaps: tuple[str, ...] = (),
) -> FieldArchitectureDossierQuality:
    """Assess row counts, class distribution, caveats, flags, and limitations."""
    return FieldArchitectureDossierQuality(
        row_count=len(index),
        blocking_source_gaps=tuple(blocking_source_gaps),
        informational_source_gaps=tuple(informational_source_gaps),
        architecture_class_counts=_value_counts(index, "architecture_signal_class"),
        selection_reason_counts=_value_counts(index, "selection_reason"),
        caveat_counts=_token_counts(index, "source_caveats"),
        quality_flag_counts=_token_counts(index, "quality_flags"),
        limitation_count=sum(
            len(_tokens(value, delimiter_pattern=r"[;]"))
            for value in index.get("dossier_limitations", [])
        ),
    )


def _value_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if column not in frame:
        return {}
    counts = frame[column].dropna().astype(str).value_counts(sort=False)
    return {key: int(value) for key, value in counts.items()}


def _token_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if column not in frame:
        return {}
    counter: Counter[str] = Counter()
    for value in frame[column]:
        counter.update(_tokens(value))
    return dict(counter)


def _tokens(value: object, delimiter_pattern: str = r"[;|,]") -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        tokens: list[str] = []
        for item in value:
            tokens.extend(_tokens(item, delimiter_pattern=delimiter_pattern))
        return tokens
    try:
        if pd.isna(value):
            return []
    except (TypeError, ValueError):
        pass
    return [part.strip() for part in re.split(delimiter_pattern, str(value)) if part.strip()]


__all__ = [
    "FieldArchitectureDossierQuality",
    "assess_field_architecture_dossier_quality",
]
