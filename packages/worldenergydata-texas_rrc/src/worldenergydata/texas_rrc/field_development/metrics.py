"""Build field-development metrics from Texas RRC lifecycle and production data."""

from __future__ import annotations

from typing import Any

import pandas as pd

from worldenergydata.texas_rrc.field_development._lifecycle_aggregation import (
    aggregate_lifecycle,
)
from worldenergydata.texas_rrc.field_development._metrics_helpers import (
    bool_value,
    coalesce_number,
    ensure_columns,
    first_present,
    has_value,
    horizontal_share,
    int_value,
    month_start,
    number_or_na,
    operator_count,
    pdq_water_or_well_count_gap,
    rank_desc,
    ratio,
    value_or_na,
    zero,
)
from worldenergydata.texas_rrc.field_development.sources import (
    FieldDevelopmentInputs,
)

FIELD_KEYS = ("district", "field_number")
OUTPUT_COLUMNS = [
    "district",
    "field_number",
    "field_name",
    "well_count",
    "active_well_count",
    "plugged_well_count",
    "permit_count",
    "completion_count",
    "horizontal_well_count",
    "directional_well_count",
    "horizontal_directional_share",
    "median_permit_to_completion_days",
    "median_completion_to_first_production_days",
    "first_production_month",
    "last_production_month",
    "still_producing",
    "production_maturity_class",
    "cumulative_oil_bbl",
    "cumulative_gas_mcf",
    "cumulative_condensate_bbl",
    "cumulative_boe",
    "production_per_well_boe",
    "lease_count",
    "operator_count",
    "well_density_proxy",
    "well_density_basis",
    "remaining_activity_score",
    "rank_cumulative_boe",
    "rank_remaining_activity",
    "rank_well_density_proxy",
    "rank_development_maturity",
    "top_operator_number",
    "top_operator_name",
    "top_operator_share",
    "source_caveats",
    "quality_flags",
]
MATURITY_SCORE = {
    "mature_active": 5,
    "growth": 4,
    "early_development": 3,
    "late_life": 2,
    "pre_production": 1,
    "unknown": 0,
}


def build_field_development_metrics(inputs: FieldDevelopmentInputs) -> pd.DataFrame:
    """Join lifecycle and production inputs into field-level development metrics."""
    lifecycle = _aggregate_lifecycle(inputs.lifecycle)
    production = _prepare_production(inputs.production)
    joined = lifecycle.merge(
        production,
        how="outer",
        on=list(FIELD_KEYS),
        suffixes=("", "_production"),
        indicator=True,
    )
    metric_gap = pdq_water_or_well_count_gap(inputs.production_quality)
    records = [_record_from_joined(row, metric_gap) for _, row in joined.iterrows()]
    metrics = pd.DataFrame(records, columns=OUTPUT_COLUMNS)
    return _with_ranks(metrics)


def _aggregate_lifecycle(lifecycle: pd.DataFrame) -> pd.DataFrame:
    return aggregate_lifecycle(
        lifecycle,
        FIELD_KEYS,
        _lifecycle_input_columns(),
        _empty_lifecycle(),
    )


def _prepare_production(production: pd.DataFrame) -> pd.DataFrame:
    if production.empty:
        return _empty_production()
    frame = production.copy()
    ensure_columns(frame, _production_columns())
    if "aggregation_level" in frame:
        frame = frame[frame["aggregation_level"] == "field"].copy()
    return frame.loc[:, _production_columns()]


def _record_from_joined(row: pd.Series, metric_gap: bool) -> dict[str, Any]:
    has_lifecycle = row["_merge"] in {"left_only", "both"}
    has_production = row["_merge"] in {"right_only", "both"}
    well_count = int_value(row.get("well_count"), default=0)
    lease_count = coalesce_number(
        row.get("lease_count"), row.get("lifecycle_lease_count")
    )
    cumulative_boe = number_or_na(row.get("cumulative_boe"))
    record = _base_record(row, has_lifecycle, well_count, lease_count)
    record.update(_production_values(row, well_count, cumulative_boe))
    record.update(_development_values(row, well_count, lease_count, cumulative_boe))
    record["production_maturity_class"] = _maturity_class(
        has_lifecycle,
        cumulative_boe,
        row.get("still_producing"),
        row.get("production_span_months"),
    )
    record["source_caveats"] = _source_caveats(
        row, has_lifecycle, has_production, metric_gap
    )
    record["quality_flags"] = ""
    return record


def _base_record(
    row: pd.Series,
    has_lifecycle: bool,
    well_count: int,
    lease_count: float | pd.NA,
) -> dict[str, Any]:
    return {
        "district": row["district"],
        "field_number": row["field_number"],
        "field_name": first_present(
            row.get("field_name"), row.get("lifecycle_field_name")
        ),
        "well_count": well_count,
        "active_well_count": int_value(row.get("active_well_count"), default=0),
        "plugged_well_count": int_value(row.get("plugged_well_count"), default=0),
        "permit_count": int_value(row.get("permit_count"), default=0),
        "completion_count": int_value(row.get("completion_count"), default=0),
        "horizontal_well_count": int_value(row.get("horizontal_well_count"), default=0),
        "directional_well_count": int_value(
            row.get("directional_well_count"), default=0
        ),
        "horizontal_directional_share": horizontal_share(row, well_count),
        "median_permit_to_completion_days": number_or_na(
            row.get("median_permit_to_completion_days")
        ),
        "median_completion_to_first_production_days": _completion_to_production(row),
        "lease_count": lease_count if has_value(lease_count) else pd.NA,
        "operator_count": operator_count(row, has_lifecycle),
    }


def _production_values(
    row: pd.Series,
    well_count: int,
    cumulative_boe: float | pd.NA,
) -> dict[str, Any]:
    return {
        "first_production_month": value_or_na(row.get("first_production_month")),
        "last_production_month": value_or_na(row.get("last_production_month")),
        "still_producing": bool_value(row.get("still_producing")),
        "cumulative_oil_bbl": number_or_na(row.get("cumulative_oil_bbl")),
        "cumulative_gas_mcf": number_or_na(row.get("cumulative_gas_mcf")),
        "cumulative_condensate_bbl": number_or_na(row.get("cumulative_condensate_bbl")),
        "cumulative_boe": cumulative_boe,
        "production_per_well_boe": ratio(cumulative_boe, well_count),
        "top_operator_number": value_or_na(row.get("top_operator_number")),
        "top_operator_name": value_or_na(row.get("top_operator_name")),
        "top_operator_share": number_or_na(row.get("top_operator_share")),
    }


def _development_values(
    row: pd.Series,
    well_count: int,
    lease_count: float | pd.NA,
    cumulative_boe: float | pd.NA,
) -> dict[str, Any]:
    active_share = ratio(row.get("active_well_count"), well_count)
    current = 1.0 if bool_value(row.get("still_producing")) else 0.0
    density = ratio(well_count, lease_count) if well_count > 0 else pd.NA
    return {
        "well_density_proxy": density,
        "well_density_basis": "wells_per_lease" if has_value(density) else pd.NA,
        "remaining_activity_score": round(((zero(active_share) + current) / 2), 6),
    }


def _source_caveats(
    row: pd.Series,
    has_lifecycle: bool,
    has_production: bool,
    metric_gap: bool,
) -> str:
    caveats: list[str] = []
    if has_production:
        caveats.extend(["lease_level_production", "no_per_well_allocation"])
    if not has_production:
        caveats.append("missing_production")
    if not has_lifecycle:
        caveats.append("missing_lifecycle")
    if _missing_lifecycle_dates(row, has_lifecycle):
        caveats.append("missing_lifecycle_dates")
    if has_production and metric_gap:
        caveats.append("water_and_well_count_unavailable_from_pdq")
    return "|".join(caveats)


def _with_ranks(metrics: pd.DataFrame) -> pd.DataFrame:
    if metrics.empty:
        return metrics
    result = metrics.copy()
    result["rank_cumulative_boe"] = rank_desc(result["cumulative_boe"])
    result["rank_remaining_activity"] = rank_desc(result["remaining_activity_score"])
    result["rank_well_density_proxy"] = rank_desc(result["well_density_proxy"])
    maturity_scores = result["production_maturity_class"].map(MATURITY_SCORE)
    result["rank_development_maturity"] = rank_desc(maturity_scores)
    return result.sort_values(list(FIELD_KEYS), kind="mergesort").reset_index(drop=True)


def _maturity_class(
    has_lifecycle: bool,
    cumulative_boe: float | pd.NA,
    still_producing: Any,
    production_span_months: Any,
) -> str:
    if has_lifecycle and (not has_value(cumulative_boe) or float(cumulative_boe) == 0):
        return "pre_production"
    if not has_value(cumulative_boe):
        return "unknown"
    span = number_or_na(production_span_months)
    still = bool_value(still_producing)
    if not still:
        return "late_life"
    if has_value(span) and span < 24:
        return "early_development"
    if has_value(span) and span <= 84:
        return "growth"
    if has_value(span) and span > 84:
        return "mature_active"
    return "unknown"


def _completion_to_production(row: pd.Series) -> float | pd.NA:
    first_production = month_start(row.get("first_production_month"))
    if first_production is None:
        return pd.NA
    completion_dates = row.get("completion_dates")
    if not isinstance(completion_dates, tuple):
        return pd.NA
    values = [(first_production - value).days for value in completion_dates]
    valid = [value for value in values if value >= 0]
    return float(pd.Series(valid).median()) if valid else pd.NA


def _missing_lifecycle_dates(row: pd.Series, has_lifecycle: bool) -> bool:
    if not has_lifecycle:
        return False
    well_count = int_value(row.get("well_count"), default=0)
    if well_count == 0:
        return False
    return int_value(row.get("completion_count"), default=0) < well_count


def _lifecycle_input_columns() -> list[str]:
    return [
        "district",
        "field_number",
        "field_name",
        "lease_number",
        "operator_number",
        "well_status",
        "well_type",
        "wellbore_profile",
        "permit_number",
        "permit_issued_date",
        "completion_date",
    ]


def _production_columns() -> list[str]:
    return [
        "aggregation_level",
        "district",
        "field_number",
        "field_name",
        "first_production_month",
        "last_production_month",
        "still_producing",
        "production_span_months",
        "cumulative_oil_bbl",
        "cumulative_gas_mcf",
        "cumulative_condensate_bbl",
        "cumulative_boe",
        "lease_count",
        "operator_count",
        "top_operator_number",
        "top_operator_name",
        "top_operator_share",
    ]


def _empty_lifecycle() -> pd.DataFrame:
    columns = list(FIELD_KEYS) + [
        "lifecycle_field_name",
        "well_count",
        "active_well_count",
        "plugged_well_count",
        "permit_count",
        "completion_count",
        "horizontal_well_count",
        "directional_well_count",
        "median_permit_to_completion_days",
        "completion_dates",
        "lifecycle_lease_count",
        "lifecycle_operator_count",
    ]
    return pd.DataFrame(columns=columns)


def _empty_production() -> pd.DataFrame:
    return pd.DataFrame(columns=_production_columns())


__all__ = [
    "OUTPUT_COLUMNS",
    "build_field_development_metrics",
]
