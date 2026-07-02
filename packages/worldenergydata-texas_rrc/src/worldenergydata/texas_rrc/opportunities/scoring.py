"""Score Texas RRC field opportunities from direct curated summary data."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from worldenergydata.texas_rrc.opportunities.architecture import (
    classify_architecture_signal,
)
from worldenergydata.texas_rrc.opportunities.sources import FieldOpportunityInputs

SCORING_VERSION = "texas_rrc_field_opportunity_v1"

SCORING_WEIGHTS = {
    "production_scale_component_score": 0.35,
    "remaining_activity_component_score": 0.30,
    "infrastructure_component_score": 0.20,
    "operator_concentration_component_score": 0.10,
    "active_well_component_score": 0.05,
}

OUTPUT_COLUMNS = [
    "district",
    "field_number",
    "field_name",
    "field_slug",
    "report_path",
    "field_page_filename",
    "opportunity_rank",
    "opportunity_score",
    "opportunity_class",
    "production_scale_component_score",
    "remaining_activity_component_score",
    "infrastructure_component_score",
    "operator_concentration_component_score",
    "active_well_component_score",
    "quality_penalty_score",
    "architecture_signal_class",
    "architecture_signal_reason",
    "recommended_followup",
    "cumulative_boe",
    "production_per_well_boe",
    "remaining_activity_score",
    "active_well_count",
    "well_count",
    "production_maturity_class",
    "infrastructure_access_class",
    "infrastructure_access_score",
    "nearest_pipeline_distance_miles",
    "nearby_pipeline_count_1mi",
    "nearby_pipeline_count_5mi",
    "nearby_pipeline_count_10mi",
    "top_operator_name",
    "top_operator_share",
    "key_drivers",
    "source_caveats",
    "quality_flags",
]


def build_field_opportunity_rankings(inputs: FieldOpportunityInputs) -> pd.DataFrame:
    """Build deterministic field-opportunity rankings."""
    if inputs.field_atlas_summary.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    frame = inputs.field_atlas_summary.copy().reset_index(drop=True)
    frame = frame.where(pd.notna(frame), None)
    frame["production_scale_component_score"] = _rank_score(frame["cumulative_boe"])
    frame["remaining_activity_component_score"] = _clipped_number(
        frame.get("remaining_activity_score")
    )
    frame["infrastructure_component_score"] = _infrastructure_scores(frame)
    frame["operator_concentration_component_score"] = _operator_scores(frame)
    frame["active_well_component_score"] = _rank_score(frame.get("active_well_count"))
    frame["quality_penalty_score"] = [
        _quality_penalty(row) for row in frame.to_dict("records")
    ]
    frame["opportunity_score"] = [
        _opportunity_score(row) for row in frame.to_dict("records")
    ]
    frame["opportunity_class"] = [
        _opportunity_class(row) for row in frame.to_dict("records")
    ]
    signals = [classify_architecture_signal(row) for row in frame.to_dict("records")]
    frame["architecture_signal_class"] = [
        signal.architecture_signal_class for signal in signals
    ]
    frame["architecture_signal_reason"] = [
        signal.architecture_signal_reason for signal in signals
    ]
    frame["recommended_followup"] = [signal.recommended_followup for signal in signals]
    frame["key_drivers"] = [_key_drivers(row) for row in frame.to_dict("records")]
    frame = _sort_rankings(frame)
    frame["opportunity_rank"] = range(1, len(frame) + 1)
    return frame.reindex(columns=OUTPUT_COLUMNS)


def _rank_score(values: Any) -> pd.Series:
    series = pd.to_numeric(values, errors="coerce")
    if series.empty:
        return pd.Series(dtype="float64")
    ranked = series.rank(method="average", pct=True) * 100.0
    return ranked.fillna(0.0).round(2)


def _clipped_number(values: Any) -> pd.Series:
    series = pd.to_numeric(values, errors="coerce")
    non_null = series.dropna()
    if not non_null.empty and non_null.between(0.0, 1.0).all():
        series = series * 100.0
    return series.fillna(0.0).clip(lower=0.0, upper=100.0).round(2)


def _infrastructure_scores(frame: pd.DataFrame) -> pd.Series:
    numeric = pd.to_numeric(frame.get("infrastructure_access_score"), errors="coerce")
    classes = frame.get("infrastructure_access_class", pd.Series(dtype="object"))
    fallback = classes.map(
        lambda value: _INFRASTRUCTURE_CLASS_SCORES.get(_text(value), 0)
    )
    scores = numeric.map(_scale_infrastructure_score).fillna(fallback)
    return scores.fillna(0.0).clip(0.0, 100.0).round(2)


def _operator_scores(frame: pd.DataFrame) -> pd.Series:
    name = frame.get("top_operator_name", pd.Series(dtype="object")).map(_text)
    share = pd.to_numeric(frame.get("top_operator_share"), errors="coerce")
    return ((name != "") & share.notna()).map(lambda known: 100.0 if known else 0.0)


def _quality_penalty(row: dict[str, Any]) -> float:
    terms = _terms(row.get("source_caveats")) + _terms(row.get("quality_flags"))
    penalty = min(25.0, len(terms) * 5.0)
    if _text(row.get("infrastructure_access_class")) == "not_available":
        penalty += 10.0
    for column in _REQUIRED_NUMERIC_COLUMNS:
        if _is_missing(row.get(column)):
            penalty += 2.5
    return round(min(penalty, 40.0), 2)


def _opportunity_score(row: dict[str, Any]) -> float:
    score = sum(
        _number(row.get(column)) * weight for column, weight in SCORING_WEIGHTS.items()
    )
    score -= _number(row.get("quality_penalty_score"))
    return round(min(100.0, max(0.0, score)), 2)


def _opportunity_class(row: dict[str, Any]) -> str:
    if _has_missing_core_evidence(row):
        return "low_confidence"
    score = _number(row.get("opportunity_score"))
    if score >= 75:
        return "high_priority"
    if score >= 45:
        return "screening_candidate"
    return "monitor_only"


def _has_missing_core_evidence(row: dict[str, Any]) -> bool:
    if _text(row.get("infrastructure_access_class")) == "not_available":
        return True
    if not _text(row.get("top_operator_name")) or _is_missing(
        row.get("top_operator_share")
    ):
        return True
    terms = set(_terms(row.get("source_caveats")) + _terms(row.get("quality_flags")))
    return bool(terms.intersection(_CRITICAL_MISSING_TERMS))


def _key_drivers(row: dict[str, Any]) -> str:
    drivers = []
    if _number(row.get("production_scale_component_score")) >= 75:
        drivers.append("high production scale")
    if _number(row.get("remaining_activity_component_score")) >= 75:
        drivers.append("strong remaining activity")
    access = _text(row.get("infrastructure_access_class"))
    if access in {"direct_access", "near_access"}:
        drivers.append(f"{access} infrastructure signal")
    if _number(row.get("operator_concentration_component_score")) == 100:
        drivers.append("operator context available")
    if _number(row.get("quality_penalty_score")) >= 20:
        drivers.append("material quality caveats")
    return "; ".join(drivers)


def _sort_rankings(frame: pd.DataFrame) -> pd.DataFrame:
    sort_columns = ["opportunity_score", "district", "field_number", "field_name"]
    return frame.sort_values(
        sort_columns,
        ascending=[False, True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)


_INFRASTRUCTURE_CLASS_SCORES = {
    "direct_access": 100.0,
    "near_access": 80.0,
    "regional_access": 55.0,
    "remote_access": 30.0,
    "isolated_or_unknown": 15.0,
    "not_available": 0.0,
}
_REQUIRED_NUMERIC_COLUMNS = (
    "cumulative_boe",
    "remaining_activity_score",
    "active_well_count",
    "infrastructure_access_score",
    "top_operator_share",
)
_CRITICAL_MISSING_TERMS = {
    "missing_field_atlas_summary",
    "missing_infrastructure_access",
    "missing_lifecycle",
    "missing_well_gis",
}


def _terms(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    normalized = str(value).replace(",", ";").replace("|", ";")
    return tuple(term.strip() for term in normalized.split(";") if term.strip())


def _scale_infrastructure_score(value: object) -> float | None:
    if _is_missing(value):
        return None
    score = _number(value)
    if 0.0 <= score <= 1.0:
        return score * 100.0
    return score


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip() == ""


def _number(value: object) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


__all__ = [
    "OUTPUT_COLUMNS",
    "SCORING_VERSION",
    "SCORING_WEIGHTS",
    "build_field_opportunity_rankings",
]
