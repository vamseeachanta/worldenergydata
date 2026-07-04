"""Build field-level Texas RRC infrastructure access metrics."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any

import pandas as pd

from worldenergydata.texas_rrc.infrastructure.gis_sources import (
    PipelineGisRecord,
    WellGisRecord,
    normalize_api_number,
)
from worldenergydata.texas_rrc.infrastructure.spatial import field_geometry

FIELD_KEYS = ("district", "field_number")
OUTPUT_COLUMNS = [
    "district",
    "field_number",
    "field_name",
    "field_well_count_with_location",
    "field_centroid_latitude",
    "field_centroid_longitude",
    "field_latitude_min",
    "field_latitude_max",
    "field_longitude_min",
    "field_longitude_max",
    "field_extent_miles",
    "nearest_pipeline_distance_miles",
    "nearby_pipeline_count_1mi",
    "nearby_pipeline_count_5mi",
    "nearby_pipeline_count_10mi",
    "nearest_pipeline_source_county",
    "nearest_pipeline_identifier",
    "infrastructure_access_score",
    "infrastructure_access_class",
    "source_caveats",
    "quality_flags",
]
ACCESS_SCORE = {
    "direct_access": 1.0,
    "near_access": 0.75,
    "regional_access": 0.5,
    "remote_access": 0.25,
    "isolated_or_unknown": 0.0,
}
GRID_DEGREES = 0.25


@dataclass(frozen=True)
class InfrastructureAccessInputs:
    """Inputs needed to build field-level infrastructure access metrics."""

    field_development: pd.DataFrame
    lifecycle: pd.DataFrame
    well_gis: tuple[WellGisRecord, ...]
    pipeline_gis: tuple[PipelineGisRecord, ...]
    source_gaps: tuple[str, ...]


@dataclass(frozen=True)
class _IndexedPipeline:
    record: PipelineGisRecord
    bbox: tuple[float, float, float, float]


@dataclass(frozen=True)
class _PipelineDistance:
    record: PipelineGisRecord
    distance_miles: float


@dataclass(frozen=True)
class _PipelineSpatialIndex:
    by_cell: dict[tuple[str | None, int, int], tuple[_IndexedPipeline, ...]]
    all_records: tuple[_IndexedPipeline, ...]


def build_infrastructure_access_metrics(
    inputs: InfrastructureAccessInputs,
    nearby_radius_miles: float = 25.0,
) -> pd.DataFrame:
    """Join field-development, lifecycle, wells, and pipelines into metrics."""
    field_rows = _field_rows(inputs.field_development)
    lifecycle_rows = _lifecycle_rows(inputs.lifecycle)
    wells_by_api = _wells_by_api(inputs.well_gis)
    well_points_by_field = _well_points_by_field(lifecycle_rows, wells_by_api)
    pipeline_index = _pipeline_index(inputs.pipeline_gis)
    keys = sorted(set(field_rows) | set(well_points_by_field))
    records = [
        _record_for_field(
            key,
            field_rows.get(key),
            lifecycle_rows.get(key, []),
            well_points_by_field.get(key, ()),
            pipeline_index,
            len(inputs.pipeline_gis),
            set(inputs.source_gaps),
            nearby_radius_miles,
        )
        for key in keys
    ]
    return pd.DataFrame(records, columns=OUTPUT_COLUMNS)


def _record_for_field(
    key: tuple[str, str],
    field_row: dict[str, Any] | None,
    lifecycle_rows: list[dict[str, Any]],
    well_points: tuple[tuple[WellGisRecord, float, float], ...],
    pipeline_index: _PipelineSpatialIndex,
    pipeline_count: int,
    source_gaps: set[str],
    nearby_radius_miles: float,
) -> dict[str, Any]:
    district, field_number = key
    points = tuple((item[1], item[2]) for item in well_points)
    caveats = [
        "rrc_gis_screening_only",
        "field_centroid_pipeline_screening",
        "pipeline_envelope_distance_screening",
    ]
    flags: list[str] = []
    if field_row is None:
        caveats.append("missing_field_development_metrics")
    if "pipeline_gis_layers" in source_gaps or pipeline_count == 0:
        caveats.append("missing_pipeline_gis")
        flags.append("missing_pipeline_gis")
    if not points:
        caveats.append("missing_well_gis")
        flags.append("missing_well_gis")
        return _empty_geometry_record(
            district, field_number, field_row, lifecycle_rows, caveats, flags
        )

    geometry = field_geometry(points)
    screening_county = _dominant_county(well_points)
    counties = {screening_county} if screening_county else set()
    if screening_county:
        caveats.append("dominant_county_pipeline_filter")
    candidate_pipelines = ()
    if pipeline_count and "pipeline_gis_layers" not in source_gaps:
        candidate_pipelines = _indexed_candidate_pipelines(
            geometry,
            counties,
            pipeline_index,
            nearby_radius_miles,
        )
    screening_point = (geometry.centroid_latitude, geometry.centroid_longitude)
    pipeline_distances = _pipeline_distances(screening_point, candidate_pipelines)
    nearest = min(
        pipeline_distances,
        key=lambda item: item.distance_miles,
        default=None,
    )
    if nearest is None or nearest.distance_miles > nearby_radius_miles:
        caveats.append("no_pipeline_within_25_miles")
    access_class = _access_class(None if nearest is None else nearest.distance_miles)
    return {
        "district": district,
        "field_number": field_number,
        "field_name": _field_name(field_row, lifecycle_rows),
        "field_well_count_with_location": geometry.well_count,
        "field_centroid_latitude": round(geometry.centroid_latitude, 8),
        "field_centroid_longitude": round(geometry.centroid_longitude, 8),
        "field_latitude_min": geometry.latitude_min,
        "field_latitude_max": geometry.latitude_max,
        "field_longitude_min": geometry.longitude_min,
        "field_longitude_max": geometry.longitude_max,
        "field_extent_miles": geometry.extent_miles,
        "nearest_pipeline_distance_miles": (
            pd.NA if nearest is None else nearest.distance_miles
        ),
        "nearby_pipeline_count_1mi": _nearby_count(pipeline_distances, 1.0),
        "nearby_pipeline_count_5mi": _nearby_count(pipeline_distances, 5.0),
        "nearby_pipeline_count_10mi": _nearby_count(pipeline_distances, 10.0),
        "nearest_pipeline_source_county": (
            pd.NA if nearest is None else nearest.record.county_fips
        ),
        "nearest_pipeline_identifier": (
            pd.NA if nearest is None else nearest.record.pipeline_identifier
        ),
        "infrastructure_access_score": ACCESS_SCORE[access_class],
        "infrastructure_access_class": access_class,
        "source_caveats": "|".join(dict.fromkeys(caveats)),
        "quality_flags": "|".join(dict.fromkeys(flags)),
    }


def _empty_geometry_record(
    district: str,
    field_number: str,
    field_row: dict[str, Any] | None,
    lifecycle_rows: list[dict[str, Any]],
    caveats: list[str],
    flags: list[str],
) -> dict[str, Any]:
    return {
        "district": district,
        "field_number": field_number,
        "field_name": _field_name(field_row, lifecycle_rows),
        "field_well_count_with_location": 0,
        "field_centroid_latitude": pd.NA,
        "field_centroid_longitude": pd.NA,
        "field_latitude_min": pd.NA,
        "field_latitude_max": pd.NA,
        "field_longitude_min": pd.NA,
        "field_longitude_max": pd.NA,
        "field_extent_miles": pd.NA,
        "nearest_pipeline_distance_miles": pd.NA,
        "nearby_pipeline_count_1mi": 0,
        "nearby_pipeline_count_5mi": 0,
        "nearby_pipeline_count_10mi": 0,
        "nearest_pipeline_source_county": pd.NA,
        "nearest_pipeline_identifier": pd.NA,
        "infrastructure_access_score": 0.0,
        "infrastructure_access_class": "isolated_or_unknown",
        "source_caveats": "|".join(dict.fromkeys(caveats)),
        "quality_flags": "|".join(dict.fromkeys(flags)),
    }


def _field_rows(frame: pd.DataFrame) -> dict[tuple[str, str], dict[str, Any]]:
    if frame.empty:
        return {}
    rows = {}
    for row in frame.to_dict("records"):
        key = _field_key(row)
        if key:
            rows[key] = row
    return rows


def _lifecycle_rows(frame: pd.DataFrame) -> dict[tuple[str, str], list[dict[str, Any]]]:
    if frame.empty:
        return {}
    rows: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in frame.to_dict("records"):
        key = _field_key(row)
        if key:
            rows.setdefault(key, []).append(row)
    return rows


def _field_key(row: dict[str, Any]) -> tuple[str, str] | None:
    district = _string(row.get("district"))
    field_number = _string(row.get("field_number"))
    if not district or not field_number:
        return None
    return district, field_number


def _wells_by_api(
    well_gis: tuple[WellGisRecord, ...],
) -> dict[str, list[WellGisRecord]]:
    wells: dict[str, list[WellGisRecord]] = {}
    for well in well_gis:
        api_number = normalize_api_number(well.api_number)
        if api_number:
            wells.setdefault(api_number, []).append(well)
    return wells


def _well_points_by_field(
    lifecycle_rows: dict[tuple[str, str], list[dict[str, Any]]],
    wells_by_api: dict[str, list[WellGisRecord]],
) -> dict[tuple[str, str], tuple[tuple[WellGisRecord, float, float], ...]]:
    result = {}
    for key, rows in lifecycle_rows.items():
        matched = []
        seen = set()
        for row in rows:
            for column in ("api14", "api10", "api_number"):
                api_number = normalize_api_number(row.get(column))
                for well in wells_by_api.get(api_number or "", []):
                    point_key = (well.api_number, well.latitude, well.longitude)
                    if point_key not in seen:
                        matched.append((well, well.latitude, well.longitude))
                        seen.add(point_key)
        if matched:
            result[key] = tuple(matched)
    return result


def _dominant_county(
    well_points: tuple[tuple[WellGisRecord, float, float], ...],
) -> str | None:
    counts = Counter(item[0].county_fips for item in well_points if item[0].county_fips)
    if not counts:
        return None
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _pipeline_distances(
    point: tuple[float, float],
    pipelines: tuple[_IndexedPipeline, ...],
) -> tuple[_PipelineDistance, ...]:
    return tuple(
        _PipelineDistance(
            pipeline.record,
            round(_point_bbox_distance_miles(point, pipeline.bbox), 6),
        )
        for pipeline in pipelines
    )


def _point_bbox_distance_miles(
    point: tuple[float, float],
    bbox: tuple[float, float, float, float],
) -> float:
    latitude, longitude = point
    min_lon, min_lat, max_lon, max_lat = bbox
    if longitude < min_lon:
        delta_lon = min_lon - longitude
    elif longitude > max_lon:
        delta_lon = longitude - max_lon
    else:
        delta_lon = 0.0
    if latitude < min_lat:
        delta_lat = min_lat - latitude
    elif latitude > max_lat:
        delta_lat = latitude - max_lat
    else:
        delta_lat = 0.0
    return math.hypot(
        delta_lat * 69.0,
        delta_lon * 69.0 * abs(math.cos(math.radians(latitude))),
    )


def _nearby_count(
    pipeline_distances: tuple[_PipelineDistance, ...],
    radius_miles: float,
) -> int:
    nearby = set()
    for item in pipeline_distances:
        if item.distance_miles <= radius_miles:
            nearby.add(item.record.pipeline_identifier or item.record.source_file)
    return len(nearby)


def _pipeline_index(pipelines: tuple[PipelineGisRecord, ...]) -> _PipelineSpatialIndex:
    buckets: dict[tuple[str | None, int, int], list[_IndexedPipeline]] = {}
    all_records = []
    for pipeline in pipelines:
        indexed = _IndexedPipeline(pipeline, _pipeline_bbox(pipeline))
        all_records.append(indexed)
        min_x, min_y, max_x, max_y = indexed.bbox
        for cell_x in range(_cell(min_x), _cell(max_x) + 1):
            for cell_y in range(_cell(min_y), _cell(max_y) + 1):
                buckets.setdefault((pipeline.county_fips, cell_x, cell_y), []).append(
                    indexed
                )
    return _PipelineSpatialIndex(
        by_cell={key: tuple(value) for key, value in buckets.items()},
        all_records=tuple(all_records),
    )


def _indexed_candidate_pipelines(
    geometry,
    field_counties: set[str],
    pipeline_index: _PipelineSpatialIndex,
    padding_miles: float,
) -> tuple[_IndexedPipeline, ...]:
    bbox = _padded_centroid_bbox(geometry, padding_miles)
    indexed = _indexed_candidates_for_bbox(bbox, field_counties, pipeline_index)
    return tuple(item for item in indexed if _bboxes_intersect(bbox, item.bbox))


def _indexed_candidates_for_bbox(
    bbox: tuple[float, float, float, float],
    field_counties: set[str],
    pipeline_index: _PipelineSpatialIndex,
) -> tuple[_IndexedPipeline, ...]:
    if not field_counties:
        return pipeline_index.all_records
    counties: tuple[str | None, ...] = (*tuple(sorted(field_counties)), None)
    min_x, min_y, max_x, max_y = bbox
    seen = set()
    candidates = []
    for county in counties:
        for cell_x in range(_cell(min_x), _cell(max_x) + 1):
            for cell_y in range(_cell(min_y), _cell(max_y) + 1):
                for item in pipeline_index.by_cell.get((county, cell_x, cell_y), ()):
                    key = id(item.record)
                    if key in seen:
                        continue
                    seen.add(key)
                    candidates.append(item)
    return tuple(candidates)


def _cell(value: float) -> int:
    return math.floor(value / GRID_DEGREES)


def _padded_centroid_bbox(
    geometry, padding_miles: float
) -> tuple[float, float, float, float]:
    padding_lat = padding_miles / 69.0
    miles_per_lon = 69.0
    if geometry.centroid_latitude:
        miles_per_lon = 69.0 * abs(math.cos(math.radians(geometry.centroid_latitude)))
    padding_lon = padding_miles / miles_per_lon if miles_per_lon else padding_lat
    return (
        geometry.centroid_longitude - padding_lon,
        geometry.centroid_latitude - padding_lat,
        geometry.centroid_longitude + padding_lon,
        geometry.centroid_latitude + padding_lat,
    )


def _pipeline_bbox(pipeline: PipelineGisRecord) -> tuple[float, float, float, float]:
    longitudes = [point[0] for point in pipeline.coordinates]
    latitudes = [point[1] for point in pipeline.coordinates]
    return min(longitudes), min(latitudes), max(longitudes), max(latitudes)


def _bboxes_intersect(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> bool:
    first_min_x, first_min_y, first_max_x, first_max_y = first
    second_min_x, second_min_y, second_max_x, second_max_y = second
    return not (
        first_max_x < second_min_x
        or second_max_x < first_min_x
        or first_max_y < second_min_y
        or second_max_y < first_min_y
    )


def _access_class(distance_miles: float | None) -> str:
    if distance_miles is None:
        return "isolated_or_unknown"
    if distance_miles <= 1.0:
        return "direct_access"
    if distance_miles <= 5.0:
        return "near_access"
    if distance_miles <= 10.0:
        return "regional_access"
    if distance_miles <= 25.0:
        return "remote_access"
    return "isolated_or_unknown"


def _field_name(
    field_row: dict[str, Any] | None,
    lifecycle_rows: list[dict[str, Any]],
) -> object:
    if field_row and _string(field_row.get("field_name")):
        return field_row["field_name"]
    for row in lifecycle_rows:
        if _string(row.get("field_name")):
            return row["field_name"]
    return pd.NA


def _string(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


__all__ = [
    "ACCESS_SCORE",
    "FIELD_KEYS",
    "OUTPUT_COLUMNS",
    "InfrastructureAccessInputs",
    "build_infrastructure_access_metrics",
]
