"""Portfolio action queue and rollup models for Texas RRC dossiers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

PORTFOLIO_LIMITATIONS = (
    "screening-only portfolio summary",
    "no reserves conclusions",
    "no economics, tariff, pipeline capacity, right-of-way, route, or facility-design conclusions",
)


@dataclass(frozen=True)
class PortfolioActionSpec:
    """Screening action vocabulary for one architecture signal class."""

    portfolio_action: str
    priority_sort: int
    followup_priority: str
    development_theme: str


ACTION_SPECS: dict[str, PortfolioActionSpec] = {
    "low_data_confidence": PortfolioActionSpec(
        portfolio_action="data_completion_review",
        priority_sort=10,
        followup_priority="source_data_first",
        development_theme="Source/data completion before architecture interpretation",
    ),
    "infrastructure_constrained_activity": PortfolioActionSpec(
        portfolio_action="infrastructure_constraint_screen",
        priority_sort=20,
        followup_priority="high",
        development_theme="Infrastructure constraint and route/market-access evidence review",
    ),
    "high_access_infill_redevelopment": PortfolioActionSpec(
        portfolio_action="infill_redevelopment_screen",
        priority_sort=30,
        followup_priority="high",
        development_theme="Infill, recompletion, redevelopment candidate review",
    ),
    "emerging_growth": PortfolioActionSpec(
        portfolio_action="growth_appraisal_screen",
        priority_sort=40,
        followup_priority="medium",
        development_theme="Growth-field activity and infrastructure follow-up",
    ),
    "mature_harvest": PortfolioActionSpec(
        portfolio_action="mature_harvest_review",
        priority_sort=50,
        followup_priority="medium",
        development_theme="Late-life harvest, recompletion, abandonment, or surveillance review",
    ),
    "monitor_only": PortfolioActionSpec(
        portfolio_action="monitor_only",
        priority_sort=90,
        followup_priority="low",
        development_theme="Watchlist monitoring without active development recommendation",
    ),
}

ACTION_QUEUE_COLUMNS = [
    "portfolio_rank",
    "district",
    "field_number",
    "field_name",
    "field_slug",
    "architecture_signal_class",
    "portfolio_action",
    "followup_priority",
    "development_theme",
    "review_sequence",
    "opportunity_rank",
    "opportunity_score",
    "recommended_followup",
    "dossier_focus",
    "dossier_path",
    "source_dossier_href",
    "source_field_atlas_report_path",
    "production_maturity_class",
    "remaining_activity_score",
    "active_well_count",
    "well_count",
    "permit_count",
    "completion_count",
    "cumulative_boe",
    "production_per_well_boe",
    "infrastructure_access_class",
    "infrastructure_access_score",
    "nearest_pipeline_distance_miles",
    "top_operator_name",
    "top_operator_share",
    "source_caveats",
    "quality_flags",
    "portfolio_limitations",
]


def build_field_architecture_action_queue(
    dossier_index: pd.DataFrame,
    input_dossier_dir: Path | str | None = None,
    output_root: Path | str | None = None,
) -> pd.DataFrame:
    """Build a deterministic screening action queue from the #702 dossier index."""
    queue = dossier_index.copy()
    for column in ACTION_QUEUE_COLUMNS:
        if column not in queue:
            queue[column] = ""

    specs = queue["architecture_signal_class"].astype(str).map(_action_spec)
    queue["_priority_sort"] = [spec.priority_sort for spec in specs]
    queue["portfolio_action"] = [spec.portfolio_action for spec in specs]
    queue["followup_priority"] = [spec.followup_priority for spec in specs]
    queue["development_theme"] = [spec.development_theme for spec in specs]
    queue["source_caveats"] = [
        _with_unknown_caveat(caveats, architecture_class)
        for caveats, architecture_class in zip(
            queue["source_caveats"],
            queue["architecture_signal_class"],
        )
    ]
    if input_dossier_dir is not None and output_root is not None:
        source_links = [
            _source_dossier_href(dossier_path, input_dossier_dir, output_root)
            for dossier_path in queue["dossier_path"]
        ]
        queue["source_dossier_href"] = [source_link[0] for source_link in source_links]
        queue["source_caveats"] = [
            _append_caveat(caveats, source_link[1])
            for caveats, source_link in zip(queue["source_caveats"], source_links)
        ]
    queue["portfolio_limitations"] = "; ".join(PORTFOLIO_LIMITATIONS)
    queue["_opportunity_rank_sort"] = pd.to_numeric(
        queue["opportunity_rank"],
        errors="coerce",
    ).fillna(float("inf"))

    queue = queue.sort_values(
        [
            "_priority_sort",
            "_opportunity_rank_sort",
            "district",
            "field_number",
            "field_name",
        ],
        kind="mergesort",
    ).reset_index(drop=True)
    queue["portfolio_rank"] = range(1, len(queue) + 1)
    queue["review_sequence"] = (
        queue.groupby("portfolio_action", sort=False).cumcount() + 1
    )
    return queue[ACTION_QUEUE_COLUMNS]


def summarize_architecture_classes(action_queue: pd.DataFrame) -> pd.DataFrame:
    """Summarize action-queue metrics by architecture signal class."""
    rows = []
    for architecture_class, group in action_queue.groupby(
        "architecture_signal_class",
        sort=False,
    ):
        scores = _numeric(group, "opportunity_score")
        rows.append(
            {
                "architecture_signal_class": architecture_class,
                "field_count": int(len(group)),
                "portfolio_action": _first(group, "portfolio_action"),
                "development_theme": _first(group, "development_theme"),
                "mean_opportunity_score": (
                    float(scores.mean()) if not scores.empty else 0.0
                ),
                "median_opportunity_score": (
                    float(scores.median()) if not scores.empty else 0.0
                ),
                "total_cumulative_boe": _numeric(group, "cumulative_boe").sum(),
                "total_active_well_count": int(
                    _numeric(group, "active_well_count").sum()
                ),
                "total_permit_count": int(_numeric(group, "permit_count").sum()),
                "total_completion_count": int(
                    _numeric(group, "completion_count").sum()
                ),
                "direct_or_near_access_count": int(
                    group.get("infrastructure_access_class", pd.Series(dtype="string"))
                    .astype(str)
                    .isin({"direct_access", "near_access"})
                    .sum()
                ),
                "top_caveats": _top_tokens(group, "source_caveats"),
                "top_quality_flags": _top_tokens(group, "quality_flags"),
            }
        )
    return pd.DataFrame(rows)


def summarize_followup_recommendations(action_queue: pd.DataFrame) -> pd.DataFrame:
    """Summarize portfolio routing counts by follow-up recommendation."""
    rows = []
    group_columns = ["recommended_followup", "portfolio_action", "development_theme"]
    for keys, group in action_queue.groupby(group_columns, sort=False, dropna=False):
        scores = _numeric(group, "opportunity_score")
        rows.append(
            {
                "recommended_followup": keys[0],
                "portfolio_action": keys[1],
                "development_theme": keys[2],
                "field_count": int(len(group)),
                "min_opportunity_score": (
                    float(scores.min()) if not scores.empty else 0.0
                ),
                "max_opportunity_score": (
                    float(scores.max()) if not scores.empty else 0.0
                ),
                "mean_opportunity_score": (
                    float(scores.mean()) if not scores.empty else 0.0
                ),
            }
        )
    return pd.DataFrame(rows)


def _action_spec(value: object) -> PortfolioActionSpec:
    return ACTION_SPECS.get(str(value), ACTION_SPECS["low_data_confidence"])


def _with_unknown_caveat(caveats: object, architecture_class: object) -> str:
    tokens = _tokens(caveats)
    if str(architecture_class) not in ACTION_SPECS:
        tokens.append("unknown_architecture_signal_class")
    return "; ".join(_dedupe(tokens))


def _append_caveat(caveats: object, caveat: str) -> str:
    tokens = _tokens(caveats)
    if caveat:
        tokens.append(caveat)
    return "; ".join(_dedupe(tokens))


def _source_dossier_href(
    dossier_path: object,
    input_dossier_dir: Path | str,
    output_root: Path | str,
) -> tuple[str, str]:
    caveat = "source_dossier_link_not_relative_to_output_root"
    raw_path = _text(dossier_path)
    if not raw_path or "\x00" in raw_path or urlparse(raw_path).scheme:
        return "", caveat

    input_dir = Path(input_dossier_dir).resolve(strict=False)
    output_analysis_dir = (Path(output_root) / "curated" / "analysis").resolve(
        strict=False
    )
    portfolio_dir = output_analysis_dir / "field_architecture_portfolio"
    allowed_dir = (input_dir / "fields").resolve(strict=False)
    if input_dir.parent.resolve(strict=False) != output_analysis_dir:
        return "", caveat

    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = input_dir / candidate
    resolved_candidate = candidate.resolve(strict=False)
    if resolved_candidate.suffix.lower() != ".html":
        return "", caveat
    if not resolved_candidate.is_relative_to(allowed_dir):
        return "", caveat

    href = os.path.relpath(
        resolved_candidate,
        portfolio_dir.resolve(strict=False),
    ).replace(os.sep, "/")
    if not href or "\x00" in href or href.startswith("/") or urlparse(href).scheme:
        return "", caveat
    resolved_href = (portfolio_dir / href).resolve(strict=False)
    if resolved_href != resolved_candidate:
        return "", caveat
    return href, ""


def _tokens(value: object) -> list[str]:
    try:
        if pd.isna(value):
            return []
    except (TypeError, ValueError):
        pass
    return [part.strip() for part in str(value).split(";") if part.strip()]


def _text(value: object) -> str:
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _first(frame: pd.DataFrame, column: str) -> str:
    if column not in frame or frame.empty:
        return ""
    value = frame[column].iloc[0]
    return "" if pd.isna(value) else str(value)


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").dropna()


def _top_tokens(frame: pd.DataFrame, column: str, limit: int = 5) -> str:
    if column not in frame:
        return ""
    counts: dict[str, int] = {}
    for value in frame[column]:
        for token in _tokens(value):
            counts[token] = counts.get(token, 0) + 1
    tokens = sorted(counts, key=lambda token: (-counts[token], token))[:limit]
    return "; ".join(tokens)


__all__ = [
    "ACTION_SPECS",
    "PORTFOLIO_LIMITATIONS",
    "build_field_architecture_action_queue",
    "summarize_architecture_classes",
    "summarize_followup_recommendations",
]
