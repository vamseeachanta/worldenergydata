# ABOUTME: Data completeness scoring for late-life assets prior to decommissioning.
# ABOUTME: Scores presence/quality of as-built drawings, inspection records, well records, mooring docs.

"""Data completeness scorer for late-life offshore asset documentation.

Provides structured scoring against five documentation categories and
derives an overall weighted score with risk classification.
"""

from dataclasses import dataclass, field
from typing import Union

import pandas as pd

# ---------------------------------------------------------------------------
# Weights per documentation category
# ---------------------------------------------------------------------------

_DEFAULT_WEIGHTS: dict[str, float] = {
    "as_built_drawings": 0.30,
    "inspection_records": 0.25,
    "well_records": 0.25,
    "mooring_documents": 0.10,
    "environmental_surveys": 0.10,
}

# For non-mooring asset types mooring_documents weight is redistributed
_NON_MOORING_TYPES = {"jacket", "concrete_gravity", "subsea"}

# Risk thresholds
_RISK_LOW_THRESHOLD = 0.70
_RISK_MEDIUM_THRESHOLD = 0.40

_ALL_CATEGORIES = list(_DEFAULT_WEIGHTS.keys())


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class CompletenessScore:
    """Completeness assessment for a single field's documentation."""

    field_name: str
    as_built_drawings: float  # 0.0–1.0
    inspection_records: float  # 0.0–1.0
    well_records: float  # 0.0–1.0
    mooring_documents: float  # 0.0–1.0 (0.0 if not applicable)
    environmental_surveys: float  # 0.0–1.0
    overall_score: float  # weighted average
    gaps: list[str]  # list of missing/incomplete items
    risk_level: str  # "low" | "medium" | "high"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _normalise_score(value: Union[bool, float, None]) -> float:
    """Convert a boolean or float into a [0.0, 1.0] score.

    True  → 1.0
    False or None → 0.0
    float → clamped to [0.0, 1.0]
    """
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    return float(max(0.0, min(1.0, value)))


def _derive_weights(asset_type: str) -> dict[str, float]:
    """Return category weights, redistributing mooring weight for fixed assets."""
    asset_type = asset_type.lower()
    if asset_type in _NON_MOORING_TYPES:
        # Redistribute mooring weight evenly across other categories
        mooring_w = _DEFAULT_WEIGHTS["mooring_documents"]
        others = [k for k in _DEFAULT_WEIGHTS if k != "mooring_documents"]
        extra = mooring_w / len(others)
        weights = {k: _DEFAULT_WEIGHTS[k] + extra for k in others}
        weights["mooring_documents"] = 0.0
    else:
        weights = dict(_DEFAULT_WEIGHTS)
    return weights


def _identify_gaps(scores: dict[str, float], threshold: float = 0.5) -> list[str]:
    """Return list of categories where score is below threshold."""
    return [cat for cat, score in scores.items() if score < threshold]


def _risk_level(overall: float) -> str:
    """Map overall score to risk level string."""
    if overall >= _RISK_LOW_THRESHOLD:
        return "low"
    if overall >= _RISK_MEDIUM_THRESHOLD:
        return "medium"
    return "high"


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class DataCompletenessScorer:
    """Scores data completeness for offshore decommissioning readiness.

    Uses five weighted documentation categories to derive an overall score
    and risk classification (low / medium / high).
    """

    def score(
        self,
        field_name: str,
        available_data: dict[str, Union[bool, float]],
        asset_type: str = "jacket",
    ) -> CompletenessScore:
        """Score completeness for a single field.

        Args:
            field_name: Field identifier.
            available_data: Dict mapping category names to availability
                indicators. Keys can include:
                - as_built_drawings
                - inspection_records
                - well_records
                - mooring_documents
                - environmental_surveys
                Values are bool (present/absent) or float in [0.0, 1.0].
                Missing keys default to 0.0 (absent).
            asset_type: Asset type string (e.g. 'jacket', 'fpso').
                Used to adjust mooring weight.

        Returns:
            CompletenessScore with per-category scores, overall weighted
            score, gap list, and risk level.
        """
        weights = _derive_weights(asset_type)

        raw_scores: dict[str, float] = {}
        for cat in _ALL_CATEGORIES:
            raw_value = available_data.get(cat, False)
            raw_scores[cat] = _normalise_score(raw_value)

        # Weighted overall score
        overall = sum(raw_scores[cat] * weights[cat] for cat in _ALL_CATEGORIES)
        overall = round(min(1.0, max(0.0, overall)), 4)

        gaps = _identify_gaps(raw_scores)
        risk = _risk_level(overall)

        return CompletenessScore(
            field_name=field_name,
            as_built_drawings=raw_scores["as_built_drawings"],
            inspection_records=raw_scores["inspection_records"],
            well_records=raw_scores["well_records"],
            mooring_documents=raw_scores["mooring_documents"],
            environmental_surveys=raw_scores["environmental_surveys"],
            overall_score=overall,
            gaps=gaps,
            risk_level=risk,
        )

    def portfolio_scores(
        self,
        fields: list[dict],
    ) -> pd.DataFrame:
        """Score a portfolio of fields and return results as a DataFrame.

        Args:
            fields: List of dicts, each with keys:
                - field_name (str)
                - available_data (dict)
                - asset_type (str, optional, defaults to 'jacket')

        Returns:
            DataFrame with columns: field_name, overall_score, risk_level,
            top_gap, as_built_drawings, inspection_records, well_records,
            mooring_documents, environmental_surveys.
        """
        rows = []
        for f in fields:
            cs = self.score(
                field_name=f["field_name"],
                available_data=f["available_data"],
                asset_type=f.get("asset_type", "jacket"),
            )
            top_gap = cs.gaps[0] if cs.gaps else ""
            rows.append(
                {
                    "field_name": cs.field_name,
                    "overall_score": cs.overall_score,
                    "risk_level": cs.risk_level,
                    "top_gap": top_gap,
                    "as_built_drawings": cs.as_built_drawings,
                    "inspection_records": cs.inspection_records,
                    "well_records": cs.well_records,
                    "mooring_documents": cs.mooring_documents,
                    "environmental_surveys": cs.environmental_surveys,
                }
            )
        return pd.DataFrame(rows)
