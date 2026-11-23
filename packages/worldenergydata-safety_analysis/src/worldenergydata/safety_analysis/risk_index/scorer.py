"""HSE Risk Index Scorer.

Computes three-dimensional risk scores (acute, chronic, compliance)
and a composite risk index for each activity in the assembled DataFrame.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from worldenergydata.safety_analysis.risk_index.config_loader import (
    RiskConfig,
    default_config,
)
from worldenergydata.safety_analysis.risk_index.models import (
    ActivityRiskScore,
    CompositeScore,
    DimensionScore,
)
from worldenergydata.safety_analysis.risk_index.normalizer import (
    normalize_to_scale,
)

logger = logging.getLogger(__name__)

# Metric columns that the scorer normalizes
_METRIC_COLUMNS = [
    "fatality_rate",
    "injury_rate",
    "total_incidents",  # proxy for frequency
    "tri_carcinogen_lbs",
    "inc_rate",
]


class RiskScorer:
    """Computes three-dimensional risk scores and composite index.

    Dimensions and weights are configurable via RiskConfig. Defaults:
        acute:      0.40 * fatality_rate + 0.35 * injury_rate + 0.25 * frequency
        chronic:    1.0 * tri_carcinogen_lbs
        compliance: 1.0 * inc_rate

    Composite:
        0.50 * acute + 0.25 * chronic + 0.25 * compliance
    """

    def __init__(self, config: Optional[RiskConfig] = None) -> None:
        cfg = config or default_config()
        self.ACUTE_WEIGHTS: Dict[str, float] = dict(cfg.acute_weights)
        self.CHRONIC_WEIGHTS: Dict[str, float] = dict(cfg.chronic_weights)
        self.COMPLIANCE_WEIGHTS: Dict[str, float] = dict(cfg.compliance_weights)
        self.COMPOSITE_WEIGHTS: Dict[str, float] = dict(cfg.composite_weights)
        self.DEFAULT_SCORE: float = cfg.default_missing_score

    def score(self, assembled: pd.DataFrame) -> CompositeScore:
        """Compute risk scores for all activities.

        Args:
            assembled: DataFrame from DataAssembler with columns:
                activity_code, activity_name, total_incidents, fatalities,
                injuries, fatality_rate, injury_rate, tri_carcinogen_lbs,
                inc_rate, confidence, sources, weighted_incident_count.

        Returns:
            CompositeScore containing one ActivityRiskScore per activity.
        """
        if len(assembled) == 0:
            return CompositeScore(
                scores=[],
                metadata=self._build_metadata(0),
            )

        normalized = self._normalize_metrics(assembled)
        activity_scores = self._build_activity_scores(assembled, normalized)

        return CompositeScore(
            scores=activity_scores,
            metadata=self._build_metadata(len(activity_scores)),
        )

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    def _normalize_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize all raw metrics to 1-10 scale.

        Returns a DataFrame with the same index as the input, containing
        columns: fatality_rate_score, injury_rate_score, frequency_score,
        tri_carcinogen_lbs_score, inc_rate_score.
        """
        result = pd.DataFrame(index=df.index)

        # fatality_rate -> fatality_rate_score
        result["fatality_rate_score"] = self._safe_normalize(df["fatality_rate"])

        # injury_rate -> injury_rate_score
        result["injury_rate_score"] = self._safe_normalize(df["injury_rate"])

        # total_incidents (proxy for frequency) -> frequency_score
        result["frequency_score"] = self._safe_normalize(
            df["total_incidents"].astype(float)
        )

        # tri_carcinogen_lbs -> tri_carcinogen_lbs_score
        result["tri_carcinogen_lbs_score"] = self._safe_normalize(
            df["tri_carcinogen_lbs"]
        )

        # inc_rate -> inc_rate_score
        result["inc_rate_score"] = self._safe_normalize(df["inc_rate"])

        return result

    def _safe_normalize(self, series: pd.Series) -> pd.Series:
        """Normalize a series, replacing NaN results with DEFAULT_SCORE.

        For single-value series or all-NaN series, normalize_to_scale
        may return NaN; this method fills those with DEFAULT_SCORE.
        """
        numeric = pd.to_numeric(series, errors="coerce")
        scaled = normalize_to_scale(numeric, low=1, high=10)
        return scaled.fillna(self.DEFAULT_SCORE)

    # ------------------------------------------------------------------
    # Dimension scoring
    # ------------------------------------------------------------------

    def _compute_acute(self, raw_row: pd.Series, norm_row: pd.Series) -> DimensionScore:
        """Compute acute risk dimension.

        acute = 0.40 * fatality_rate_score
              + 0.35 * injury_rate_score
              + 0.25 * frequency_score
        """
        subscores = {
            "fatality_rate": float(norm_row["fatality_rate_score"]),
            "injury_rate": float(norm_row["injury_rate_score"]),
            "frequency": float(norm_row["frequency_score"]),
        }

        weighted = (
            self.ACUTE_WEIGHTS["fatality_rate"] * subscores["fatality_rate"]
            + self.ACUTE_WEIGHTS["injury_rate"] * subscores["injury_rate"]
            + self.ACUTE_WEIGHTS["frequency"] * subscores["frequency"]
        )

        # Clamp to valid range
        weighted = max(1.0, min(10.0, weighted))

        raw_metrics = {
            "fatality_rate": _safe_float(raw_row.get("fatality_rate")),
            "injury_rate": _safe_float(raw_row.get("injury_rate")),
            "total_incidents": _safe_float(raw_row.get("total_incidents")),
        }

        return DimensionScore(
            dimension="acute",
            raw_metrics=raw_metrics,
            score=round(weighted, 4),
            subscores=subscores,
        )

    def _compute_chronic(
        self, raw_row: pd.Series, norm_row: pd.Series
    ) -> DimensionScore:
        """Compute chronic risk dimension.

        chronic = 1.0 * tri_carcinogen_lbs_score
        """
        tri_score = float(norm_row["tri_carcinogen_lbs_score"])

        subscores = {"tri_carcinogen_lbs": tri_score}
        score = tri_score

        score = max(1.0, min(10.0, score))

        raw_metrics = {
            "tri_carcinogen_lbs": _safe_float(raw_row.get("tri_carcinogen_lbs")),
        }

        return DimensionScore(
            dimension="chronic",
            raw_metrics=raw_metrics,
            score=round(score, 4),
            subscores=subscores,
        )

    def _compute_compliance(
        self, raw_row: pd.Series, norm_row: pd.Series
    ) -> DimensionScore:
        """Compute compliance risk dimension.

        compliance = 1.0 * inc_rate_score
        """
        inc_score = float(norm_row["inc_rate_score"])

        subscores = {"inc_rate": inc_score}
        score = inc_score

        score = max(1.0, min(10.0, score))

        raw_metrics = {
            "inc_rate": _safe_float(raw_row.get("inc_rate")),
        }

        return DimensionScore(
            dimension="compliance",
            raw_metrics=raw_metrics,
            score=round(score, 4),
            subscores=subscores,
        )

    def _compute_composite(
        self, acute: float, chronic: float, compliance: float
    ) -> float:
        """Compute composite score from dimension scores.

        composite = 0.50 * acute + 0.25 * chronic + 0.25 * compliance
        """
        raw = (
            self.COMPOSITE_WEIGHTS["acute"] * acute
            + self.COMPOSITE_WEIGHTS["chronic"] * chronic
            + self.COMPOSITE_WEIGHTS["compliance"] * compliance
        )
        return round(max(1.0, min(10.0, raw)), 4)

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------

    def _build_activity_scores(
        self, assembled: pd.DataFrame, normalized: pd.DataFrame
    ) -> List[ActivityRiskScore]:
        """Build ActivityRiskScore for each row."""
        scores: List[ActivityRiskScore] = []

        for idx in assembled.index:
            raw_row = assembled.loc[idx]
            norm_row = normalized.loc[idx]

            acute = self._compute_acute(raw_row, norm_row)
            chronic = self._compute_chronic(raw_row, norm_row)
            compliance = self._compute_compliance(raw_row, norm_row)

            composite = self._compute_composite(
                acute.score, chronic.score, compliance.score
            )

            # Parse sources (may be stored as list or string)
            sources = raw_row.get("sources", [])
            if isinstance(sources, str):
                sources = [s.strip() for s in sources.split(",")]

            activity_score = ActivityRiskScore(
                activity_code=str(raw_row["activity_code"]),
                activity_name=str(raw_row["activity_name"]),
                acute=acute,
                chronic=chronic,
                compliance=compliance,
                composite_score=composite,
                incident_count=int(raw_row.get("total_incidents", 0)),
                confidence=str(raw_row.get("confidence", "low")),
                sources=sources if isinstance(sources, list) else [],
            )

            scores.append(activity_score)

        return scores

    def _build_metadata(self, activity_count: int) -> Dict[str, Any]:
        """Build metadata dictionary for the CompositeScore."""
        return {
            "composite_weights": dict(self.COMPOSITE_WEIGHTS),
            "acute_weights": dict(self.ACUTE_WEIGHTS),
            "chronic_weights": dict(self.CHRONIC_WEIGHTS),
            "compliance_weights": dict(self.COMPLIANCE_WEIGHTS),
            "activity_count": activity_count,
            "normalization_method": "percentile_rank",
            "default_missing_score": self.DEFAULT_SCORE,
        }


def _safe_float(value: Any) -> float:
    """Convert a value to float, returning 0.0 for non-numeric values."""
    if value is None:
        return 0.0
    try:
        f = float(value)
        return 0.0 if np.isnan(f) else f
    except (TypeError, ValueError):
        return 0.0
