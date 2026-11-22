"""Explicit-source adapter for the existing heuristic incident classifier."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .data_loaders import HseIncident

if TYPE_CHECKING:
    from worldenergydata.safety_analysis.taxonomy.incident_classifier import (
        IncidentClassifier,
    )


@dataclass(frozen=True)
class ClassifiedIncident:
    """Internal classification, excluding narrative and source raw values.

    Confidence is the upstream matching heuristic, not measured accuracy.
    Membership in an intervention cohort must be established independently.
    """

    record_id: str
    activity: str
    subactivity: str
    confidence: float
    match_method: str


def classify_incidents(
    incidents: Iterable[HseIncident], *, source: str, classifier: IncidentClassifier
) -> tuple[ClassifiedIncident, ...]:
    """Classify a verified single-source cohort using a caller-supplied classifier.

    The caller establishes source provenance before invoking this function;
    directory location alone does not establish BSEE provenance. Install the
    safety_analysis distribution to use its IncidentClassifier. Loading data
    alone does not require that optional classifier distribution.
    """
    from worldenergydata.safety_analysis.taxonomy.incident_classifier import (
        VALID_SOURCES,
    )

    if source not in VALID_SOURCES:
        raise ValueError("A recognized, verified source is required")
    rows = tuple(incidents)
    if len({row.record_id for row in rows}) != len(rows):
        raise ValueError("HSE record IDs must be unique")
    results = []
    for row in rows:
        result = classifier.classify(row.classifier_fields(), source=source)
        results.append(
            ClassifiedIncident(
                row.record_id,
                result.activity,
                result.subactivity,
                result.confidence,
                result.match_method,
            )
        )
    return tuple(results)
