"""Select Texas RRC fields for architecture dossier publication."""

from __future__ import annotations

import pandas as pd

_FOCUS_BY_ARCHITECTURE_CLASS = {
    "high_access_infill_redevelopment": "infill_redevelopment_review",
    "emerging_growth": "growth_pattern_review",
    "infrastructure_constrained_activity": "infrastructure_constraint_review",
    "mature_harvest": "late_life_harvest_review",
    "low_data_confidence": "source_gap_resolution",
    "monitor_only": "monitoring_context",
}


def select_dossier_candidates(
    rankings: pd.DataFrame,
    max_fields: int = 25,
    class_coverage_limit: int = 3,
) -> pd.DataFrame:
    """Select top-ranked dossier candidates with bounded class coverage."""
    if max_fields <= 0:
        raise ValueError("max_fields must be greater than 0")
    if class_coverage_limit < 0:
        raise ValueError("class_coverage_limit must be greater than or equal to 0")
    if rankings.empty:
        return _with_selection_columns(rankings.copy())

    ranked = rankings.copy()
    ranked["_numeric_opportunity_rank"] = pd.to_numeric(
        ranked.get("opportunity_rank"), errors="coerce"
    )
    ranked = ranked.sort_values(
        ["_numeric_opportunity_rank", "district", "field_number", "field_name"],
        kind="mergesort",
        na_position="last",
    )
    selected = ranked.head(max_fields).copy()
    selected["selection_reason"] = "top_ranked"
    if class_coverage_limit:
        selected = _append_class_coverage(ranked, selected, class_coverage_limit)
    selected = selected.drop_duplicates(subset=["district", "field_number"])
    selected = selected.sort_values(
        ["_numeric_opportunity_rank", "district", "field_number", "field_name"],
        kind="mergesort",
        na_position="last",
    )
    selected = selected.drop(columns=["_numeric_opportunity_rank"])
    return _with_selection_columns(selected.reset_index(drop=True))


def _append_class_coverage(
    ranked: pd.DataFrame,
    selected: pd.DataFrame,
    class_coverage_limit: int,
) -> pd.DataFrame:
    represented = set(selected["architecture_signal_class"].astype(str))
    additions = []
    for architecture_class in sorted(ranked["architecture_signal_class"].dropna().astype(str).unique()):
        if architecture_class in represented:
            continue
        class_rows = ranked[
            ranked["architecture_signal_class"].astype(str) == architecture_class
        ].head(class_coverage_limit)
        if class_rows.empty:
            continue
        covered = class_rows.copy()
        covered["selection_reason"] = f"class_coverage:{architecture_class}"
        additions.append(covered)
    if not additions:
        return selected
    return pd.concat([selected, *additions], ignore_index=True)


def _with_selection_columns(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["dossier_rank"] = range(1, len(result) + 1)
    if "selection_reason" not in result:
        result["selection_reason"] = pd.Series(dtype="string")
    result["dossier_focus"] = result.get(
        "architecture_signal_class", pd.Series(dtype="string")
    ).map(_focus_for_class)
    return result


def _focus_for_class(value: object) -> str:
    return _FOCUS_BY_ARCHITECTURE_CLASS.get(str(value), "unclassified_review")


__all__ = ["select_dossier_candidates"]
