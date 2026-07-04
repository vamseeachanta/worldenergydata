"""Assemble Texas RRC field-architecture dossier page and index models."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

DOSSIER_INDEX_COLUMNS = [
    "dossier_rank",
    "district",
    "field_number",
    "field_name",
    "field_slug",
    "dossier_path",
    "source_field_atlas_report_path",
    "opportunity_rank",
    "opportunity_score",
    "opportunity_class",
    "architecture_signal_class",
    "architecture_signal_reason",
    "recommended_followup",
    "dossier_focus",
    "production_maturity_class",
    "first_production_month",
    "last_production_month",
    "still_producing",
    "production_span_months",
    "remaining_activity_score",
    "well_count",
    "active_well_count",
    "permit_count",
    "completion_count",
    "cumulative_boe",
    "production_per_well_boe",
    "lease_count",
    "operator_count",
    "infrastructure_access_class",
    "infrastructure_access_score",
    "nearest_pipeline_distance_miles",
    "nearby_pipeline_count_1mi",
    "nearby_pipeline_count_5mi",
    "nearby_pipeline_count_10mi",
    "top_operator_name",
    "top_operator_share",
    "selection_reason",
    "source_caveats",
    "quality_flags",
    "dossier_limitations",
]

DOSSIER_LIMITATIONS = (
    "screening-only RRC-derived decision support",
    "no reserves conclusions",
    "no economics, tariff, pipeline capacity, right-of-way, route, or facility-design conclusions",
)


@dataclass(frozen=True)
class FieldArchitectureDossierPage:
    """One field-architecture dossier page and its index row."""

    district: str
    field_number: str
    field_name: str
    field_slug: str
    dossier_filename: str
    dossier_path: str
    source_field_atlas_report_path: str | None
    source_field_atlas_href: str | None
    summary: dict[str, Any]
    source_caveats: tuple[str, ...]
    quality_flags: tuple[str, ...]
    limitations: tuple[str, ...]


def build_field_architecture_dossier_pages(
    selected: pd.DataFrame,
    field_atlas_summary: pd.DataFrame,
    field_development_metrics: pd.DataFrame,
    source_links_are_relative: bool = True,
) -> tuple[FieldArchitectureDossierPage, ...]:
    """Build per-field dossier page models from selected and context rows."""
    if selected.empty:
        return ()
    atlas = _rows_by_key(field_atlas_summary)
    development = _rows_by_key(field_development_metrics)
    return tuple(
        _build_page(
            row,
            atlas.get(_key(row)),
            development.get(_key(row)),
            source_links_are_relative,
        )
        for row in selected.to_dict("records")
    )


def build_field_architecture_dossier_index(
    pages: tuple[FieldArchitectureDossierPage, ...],
) -> pd.DataFrame:
    """Build a stable machine-readable dossier index from page models."""
    rows = []
    for page in pages:
        row = {column: page.summary.get(column) for column in DOSSIER_INDEX_COLUMNS}
        row["source_caveats"] = ";".join(page.source_caveats)
        row["quality_flags"] = ";".join(page.quality_flags)
        row["dossier_limitations"] = ";".join(page.limitations)
        rows.append(row)
    return pd.DataFrame(rows, columns=DOSSIER_INDEX_COLUMNS)


def _build_page(
    selected: dict[str, Any],
    atlas: dict[str, Any] | None,
    development: dict[str, Any] | None,
    source_links_are_relative: bool,
) -> FieldArchitectureDossierPage:
    atlas_missing = atlas is None
    development_missing = development is None
    atlas = atlas or {}
    development = development or {}
    district = str(selected.get("district", ""))
    field_number = str(selected.get("field_number", ""))
    field_name = str(_first_present(selected, atlas, development, "field_name") or "")
    field_slug = str(_first_present(atlas, selected, "field_slug") or _slug(field_name))
    filename = f"{district}-{field_number}-{field_slug}-dossier.html"
    caveats = _merge_tokens(
        selected.get("source_caveats"),
        atlas.get("source_caveats"),
        development.get("source_caveats"),
    )
    caveats = _merge_token_values(
        caveats,
        _context_caveats(atlas_missing, development_missing),
        _missing_column_caveats(selected, atlas, development),
    )
    flags = _merge_tokens(
        selected.get("quality_flags"),
        atlas.get("quality_flags"),
        development.get("quality_flags"),
    )
    source_path = _source_field_atlas_path(atlas.get("report_path"))
    source_href = _source_field_atlas_href(source_path, source_links_are_relative)
    if source_path and not source_links_are_relative:
        caveats = _merge_token_values(caveats, ("source_link_not_relative_to_output_root",))
    summary = _summary_row(
        selected,
        atlas,
        development,
        field_slug,
        f"fields/{filename}",
        source_path,
    )
    return FieldArchitectureDossierPage(
        district=district,
        field_number=field_number,
        field_name=field_name,
        field_slug=field_slug,
        dossier_filename=filename,
        dossier_path=f"fields/{filename}",
        source_field_atlas_report_path=source_path,
        source_field_atlas_href=source_href,
        summary=summary,
        source_caveats=caveats,
        quality_flags=flags,
        limitations=DOSSIER_LIMITATIONS,
    )


def _summary_row(
    selected: dict[str, Any],
    atlas: dict[str, Any],
    development: dict[str, Any],
    field_slug: str,
    dossier_path: str,
    source_path: str | None,
) -> dict[str, Any]:
    row = {column: None for column in DOSSIER_INDEX_COLUMNS}
    for column in DOSSIER_INDEX_COLUMNS:
        row[column] = _column_value(column, selected, atlas, development)
    row["field_slug"] = field_slug
    row["dossier_path"] = dossier_path
    row["source_field_atlas_report_path"] = source_path
    row["production_span_months"] = _production_span_months(
        row["first_production_month"], row["last_production_month"]
    )
    row["dossier_limitations"] = ";".join(DOSSIER_LIMITATIONS)
    return row


def _column_value(
    column: str,
    selected: dict[str, Any],
    atlas: dict[str, Any],
    development: dict[str, Any],
) -> Any:
    if column in {"permit_count", "completion_count", "lease_count", "operator_count"}:
        return _first_present(atlas, development, selected, column)
    if column in {"first_production_month", "last_production_month", "still_producing"}:
        return _first_present(development, selected, atlas, column)
    return _first_present(selected, atlas, development, column)


def _rows_by_key(frame: pd.DataFrame) -> dict[tuple[str, str], dict[str, Any]]:
    if frame.empty:
        return {}
    return {_key(row): row for row in frame.to_dict("records")}


def _key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row.get("district", "")), str(row.get("field_number", ""))


def _first_present(*values: Any) -> Any:
    *sources, column = values
    for source in sources:
        value = source.get(column)
        if _is_present(value):
            return value
    return None


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    try:
        return not bool(pd.isna(value))
    except (TypeError, ValueError):
        return True


def _merge_tokens(*values: Any) -> tuple[str, ...]:
    return _merge_token_values(*(_split_tokens(value) for value in values))


def _merge_token_values(*values: Any) -> tuple[str, ...]:
    tokens: list[str] = []
    for value in values:
        if not _is_present(value):
            continue
        if isinstance(value, (list, tuple)):
            parts = [str(item) for item in value]
        else:
            parts = _split_tokens(value)
        for part in parts:
            token = part.strip()
            if token and token not in tokens:
                tokens.append(token)
    return tuple(tokens)


def _split_tokens(value: Any) -> list[str]:
    if not _is_present(value):
        return []
    if isinstance(value, (list, tuple)):
        parts: list[str] = []
        for item in value:
            parts.extend(_split_tokens(item))
        return parts
    return [part.strip() for part in re.split(r"[;|,]", str(value)) if part.strip()]


def _context_caveats(
    atlas_missing: bool,
    development_missing: bool,
) -> tuple[str, ...]:
    caveats = []
    if atlas_missing:
        caveats.append("missing_field_atlas_context")
    if development_missing:
        caveats.append("missing_field_development_context")
    return tuple(caveats)


def _missing_column_caveats(
    selected: dict[str, Any],
    atlas: dict[str, Any],
    development: dict[str, Any],
) -> tuple[str, ...]:
    if not atlas and not development:
        return ()
    caveats = []
    sources = (selected, atlas, development)
    for column in _SOURCE_BACKED_COLUMNS:
        if not any(column in source for source in sources):
            caveats.append(f"missing_column:{column}")
    return tuple(caveats)


def _source_field_atlas_path(value: Any) -> str | None:
    if not _is_present(value):
        return None
    path = str(value)
    if path.startswith("reports/field_atlas/"):
        return path
    if path.startswith("fields/"):
        return f"reports/field_atlas/{path}"
    return path


def _source_field_atlas_href(
    source_path: str | None,
    source_links_are_relative: bool,
) -> str | None:
    if not source_path or not source_links_are_relative:
        return None
    return f"../../../{source_path}"


def _production_span_months(first_month: Any, last_month: Any) -> int | None:
    first = _parse_month(first_month)
    last = _parse_month(last_month)
    if first is None or last is None:
        return None
    return (last[0] - first[0]) * 12 + last[1] - first[1] + 1


def _parse_month(value: Any) -> tuple[int, int] | None:
    if not _is_present(value):
        return None
    match = re.match(r"^(\d{4})-(\d{2})", str(value))
    if not match:
        return None
    year = int(match.group(1))
    month = int(match.group(2))
    if not 1 <= month <= 12 or math.isnan(float(year)):
        return None
    return year, month


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "field"


_DERIVED_COLUMNS = {
    "dossier_rank",
    "district",
    "field_number",
    "field_name",
    "field_slug",
    "dossier_path",
    "source_field_atlas_report_path",
    "dossier_focus",
    "production_span_months",
    "selection_reason",
    "source_caveats",
    "quality_flags",
    "dossier_limitations",
}
_SOURCE_BACKED_COLUMNS = tuple(
    column for column in DOSSIER_INDEX_COLUMNS if column not in _DERIVED_COLUMNS
)


__all__ = [
    "DOSSIER_INDEX_COLUMNS",
    "DOSSIER_LIMITATIONS",
    "FieldArchitectureDossierPage",
    "build_field_architecture_dossier_index",
    "build_field_architecture_dossier_pages",
]
