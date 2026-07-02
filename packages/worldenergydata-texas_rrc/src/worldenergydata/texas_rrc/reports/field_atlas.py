"""Assemble Texas RRC field-atlas report models."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

import pandas as pd

from worldenergydata.texas_rrc.reports.sources import FieldAtlasReportInputs

SUMMARY_COLUMNS = [
    "district",
    "field_number",
    "field_name",
    "field_slug",
    "report_path",
    "field_page_filename",
    "well_count",
    "active_well_count",
    "permit_count",
    "completion_count",
    "production_maturity_class",
    "remaining_activity_score",
    "rank_cumulative_boe",
    "rank_remaining_activity",
    "rank_well_density_proxy",
    "cumulative_oil_bbl",
    "cumulative_gas_mcf",
    "cumulative_condensate_bbl",
    "cumulative_boe",
    "production_per_well_boe",
    "lease_count",
    "operator_count",
    "top_operator_number",
    "top_operator_name",
    "top_operator_share",
    "infrastructure_access_class",
    "infrastructure_access_score",
    "nearest_pipeline_distance_miles",
    "nearby_pipeline_count_1mi",
    "nearby_pipeline_count_5mi",
    "nearby_pipeline_count_10mi",
    "source_caveats",
    "quality_flags",
]

_FIELD_COLUMNS = [
    "well_count",
    "active_well_count",
    "permit_count",
    "completion_count",
    "production_maturity_class",
    "remaining_activity_score",
    "rank_cumulative_boe",
    "rank_remaining_activity",
    "rank_well_density_proxy",
    "cumulative_oil_bbl",
    "cumulative_gas_mcf",
    "cumulative_condensate_bbl",
    "cumulative_boe",
    "production_per_well_boe",
    "lease_count",
    "operator_count",
    "top_operator_number",
    "top_operator_name",
    "top_operator_share",
]
_INFRASTRUCTURE_COLUMNS = [
    "infrastructure_access_class",
    "infrastructure_access_score",
    "nearest_pipeline_distance_miles",
    "nearest_pipeline_identifier",
    "nearby_pipeline_count_1mi",
    "nearby_pipeline_count_5mi",
    "nearby_pipeline_count_10mi",
]
_LEASE_COLUMNS = [
    "lease_number",
    "lease_name",
    "operator_number",
    "operator_name",
    "cumulative_oil_bbl",
    "cumulative_gas_mcf",
    "cumulative_condensate_bbl",
    "cumulative_boe",
    "first_production_month",
    "last_production_month",
    "still_producing",
]


@dataclass(frozen=True)
class FieldAtlasPage:
    """One field deep-dive page and its machine-readable summary row."""

    district: str
    field_number: str
    field_name: str
    field_slug: str
    field_page_filename: str
    report_path: str
    summary: dict[str, Any]
    lease_rows: tuple[dict[str, Any], ...]
    source_caveats: tuple[str, ...]
    quality_flags: tuple[str, ...]


def build_field_atlas_pages(
    inputs: FieldAtlasReportInputs, max_fields: int | None = None
) -> tuple[FieldAtlasPage, ...]:
    """Build report page models from curated source inputs."""
    if inputs.field_development.empty:
        return ()
    infrastructure = _indexed_rows(inputs.infrastructure_access)
    leases = _lease_rows_by_field(inputs.production_atlas)
    pages = [_build_page(row, infrastructure, leases) for row in _records(inputs)]
    pages.sort(key=lambda page: _sort_value(page.summary.get("rank_cumulative_boe")))
    return tuple(pages[:max_fields] if max_fields else pages)


def build_field_atlas_summary(pages: tuple[FieldAtlasPage, ...]) -> pd.DataFrame:
    """Build the machine-readable summary dataframe for report outputs."""
    records = [page.summary for page in pages]
    if not records:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)
    summary = pd.DataFrame(records)
    return summary.reindex(columns=SUMMARY_COLUMNS)


def slugify_field(value: object) -> str:
    """Return a stable slug suitable for field report filenames."""
    text = str(value or "").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return slug or "field"


def _records(inputs: FieldAtlasReportInputs) -> list[dict[str, Any]]:
    return inputs.field_development.where(
        pd.notna(inputs.field_development), None
    ).to_dict("records")


def _build_page(
    field: dict[str, Any],
    infrastructure: dict[tuple[str, str], dict[str, Any]],
    leases: dict[tuple[str, str], tuple[dict[str, Any], ...]],
) -> FieldAtlasPage:
    district = _text(field.get("district"))
    field_number = _text(field.get("field_number"))
    field_name = _text(field.get("field_name"))
    key = (district, field_number)
    infra = infrastructure.get(key)
    caveats = _merged_terms(field.get("source_caveats"))
    flags = _merged_terms(field.get("quality_flags"))
    if infra:
        caveats = _merged_terms(*caveats, infra.get("source_caveats"))
        flags = _merged_terms(*flags, infra.get("quality_flags"))
    else:
        caveats = _merged_terms(*caveats, "missing_infrastructure_access")
    slug = slugify_field(field_name)
    filename = f"{_slug_token(district)}-{_slug_token(field_number)}-{slug}.html"
    report_path = str(PurePosixPath("fields") / filename)
    summary = _summary_row(field, infra, caveats, flags, slug, filename, report_path)
    return FieldAtlasPage(
        district=district,
        field_number=field_number,
        field_name=field_name,
        field_slug=slug,
        field_page_filename=filename,
        report_path=report_path,
        summary=summary,
        lease_rows=leases.get(key, ()),
        source_caveats=caveats,
        quality_flags=flags,
    )


def _summary_row(
    field: dict[str, Any],
    infra: dict[str, Any] | None,
    caveats: tuple[str, ...],
    flags: tuple[str, ...],
    slug: str,
    filename: str,
    report_path: str,
) -> dict[str, Any]:
    row = {column: field.get(column) for column in _FIELD_COLUMNS}
    row.update(
        {
            "district": _text(field.get("district")),
            "field_number": _text(field.get("field_number")),
            "field_name": _text(field.get("field_name")),
            "field_slug": slug,
            "report_path": report_path,
            "field_page_filename": filename,
            "source_caveats": "; ".join(caveats),
            "quality_flags": "; ".join(flags),
        }
    )
    row.update(_infrastructure_summary(infra))
    selected = {column: row.get(column) for column in SUMMARY_COLUMNS}
    if infra:
        selected["nearest_pipeline_identifier"] = infra.get(
            "nearest_pipeline_identifier"
        )
    return selected


def _infrastructure_summary(infra: dict[str, Any] | None) -> dict[str, Any]:
    if not infra:
        return {
            "infrastructure_access_class": "not_available",
            "infrastructure_access_score": None,
            "nearest_pipeline_distance_miles": None,
            "nearby_pipeline_count_1mi": None,
            "nearby_pipeline_count_5mi": None,
            "nearby_pipeline_count_10mi": None,
        }
    return {column: infra.get(column) for column in _INFRASTRUCTURE_COLUMNS}


def _indexed_rows(frame: pd.DataFrame) -> dict[tuple[str, str], dict[str, Any]]:
    if frame.empty:
        return {}
    records = frame.where(pd.notna(frame), None).to_dict("records")
    return {_key(row): row for row in records if _key(row) != ("", "")}


def _lease_rows_by_field(
    frame: pd.DataFrame,
) -> dict[tuple[str, str], tuple[dict[str, Any], ...]]:
    rows_by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    if frame.empty or "aggregation_level" not in frame:
        return {}
    records = frame.where(pd.notna(frame), None).to_dict("records")
    for row in records:
        if _text(row.get("aggregation_level")).lower() != "lease":
            continue
        rows_by_key[_key(row)].append(_lease_row(row))
    return {key: tuple(_sorted_leases(rows)[:10]) for key, rows in rows_by_key.items()}


def _lease_row(row: dict[str, Any]) -> dict[str, Any]:
    return {column: row.get(column) for column in _LEASE_COLUMNS if column in row}


def _sorted_leases(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: _descending_value(row.get("cumulative_boe")))


def _key(row: dict[str, Any]) -> tuple[str, str]:
    return _text(row.get("district")), _text(row.get("field_number"))


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def _merged_terms(*values: object) -> tuple[str, ...]:
    terms: list[str] = []
    for value in values:
        for term in _split_terms(value):
            if term not in terms:
                terms.append(term)
    return tuple(terms)


def _split_terms(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, tuple | list):
        tokens = []
        for item in value:
            tokens.extend(_split_terms(item))
        return tokens
    text = _text(value)
    if not text or text.lower() == "nan":
        return []
    return [part.strip() for part in re.split(r"[;,]", text) if part.strip()]


def _sort_value(value: object) -> tuple[int, float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return (1, float("inf"))
    if math.isnan(number):
        return (1, float("inf"))
    return (0, number)


def _descending_value(value: object) -> tuple[int, float]:
    missing, number = _sort_value(value)
    return (missing, -number)


def _slug_token(value: object) -> str:
    token = re.sub(r"[^A-Za-z0-9]+", "-", _text(value)).strip("-").lower()
    return token or "unknown"


__all__ = [
    "FieldAtlasPage",
    "SUMMARY_COLUMNS",
    "build_field_atlas_pages",
    "build_field_atlas_summary",
    "slugify_field",
]
