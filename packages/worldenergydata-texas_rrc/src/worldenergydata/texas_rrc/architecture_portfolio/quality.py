"""Quality summaries for Texas RRC field-architecture portfolio outputs."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class FieldArchitecturePortfolioQuality:
    """Quality metadata for one portfolio output batch."""

    row_count: int
    blocking_source_gaps: tuple[str, ...]
    informational_source_gaps: tuple[str, ...]
    portfolio_action_counts: dict[str, int]
    development_theme_counts: dict[str, int]
    caveat_counts: dict[str, int]
    quality_flag_counts: dict[str, int]
    limitation_count: int


def assess_field_architecture_portfolio_quality(
    action_queue: pd.DataFrame,
    blocking_source_gaps: tuple[str, ...] = (),
    informational_source_gaps: tuple[str, ...] = (),
) -> FieldArchitecturePortfolioQuality:
    """Assess action, theme, caveat, flag, and inherited source-gap counts."""
    return FieldArchitecturePortfolioQuality(
        row_count=len(action_queue),
        blocking_source_gaps=tuple(blocking_source_gaps),
        informational_source_gaps=tuple(informational_source_gaps),
        portfolio_action_counts=_value_counts(action_queue, "portfolio_action"),
        development_theme_counts=_value_counts(action_queue, "development_theme"),
        caveat_counts=_token_counts(action_queue, "source_caveats"),
        quality_flag_counts=_token_counts(action_queue, "quality_flags"),
        limitation_count=len(
            {
                token
                for value in action_queue.get("portfolio_limitations", [])
                for token in _tokens(value, delimiter_pattern=r"[;]")
            }
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
    try:
        if pd.isna(value):
            return []
    except (TypeError, ValueError):
        pass
    return [
        part.strip() for part in re.split(delimiter_pattern, str(value)) if part.strip()
    ]


__all__ = [
    "FieldArchitecturePortfolioQuality",
    "assess_field_architecture_portfolio_quality",
]
