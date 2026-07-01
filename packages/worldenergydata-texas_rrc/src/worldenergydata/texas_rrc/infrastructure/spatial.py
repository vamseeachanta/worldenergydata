"""Deterministic spatial helpers for Texas RRC infrastructure screening."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from worldenergydata.texas_rrc.infrastructure.gis_sources import PipelineGisRecord

EARTH_RADIUS_MILES = 3958.7613
MILES_PER_DEGREE_LATITUDE = 69.0


@dataclass(frozen=True)
class FieldGeometry:
    """Screening geometry for one field's well locations."""

    well_count: int
    centroid_latitude: float
    centroid_longitude: float
    latitude_min: float
    latitude_max: float
    longitude_min: float
    longitude_max: float
    extent_miles: float


@dataclass(frozen=True)
class NearestPipelineResult:
    """Nearest pipeline screening result."""

    distance_miles: float
    pipeline_identifier: str | None
    source_county: str | None
    source_file: str


def haversine_miles(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    """Return great-circle distance in miles."""
    lat_a = math.radians(latitude_a)
    lat_b = math.radians(latitude_b)
    delta_lat = math.radians(latitude_b - latitude_a)
    delta_lon = math.radians(longitude_b - longitude_a)
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(value))


def point_to_polyline_distance_miles(
    latitude: float,
    longitude: float,
    coordinates: tuple[tuple[float, float], ...],
) -> float:
    """Return the approximate nearest distance from a point to a polyline."""
    if not coordinates:
        raise ValueError("coordinates must not be empty")
    if len(coordinates) == 1:
        lon, lat = coordinates[0]
        return haversine_miles(latitude, longitude, lat, lon)
    ref_lat = latitude
    point = (0.0, 0.0)
    projected = [
        _project(lon, lat, origin_longitude=longitude, origin_latitude=ref_lat)
        for lon, lat in coordinates
    ]
    return min(
        _point_segment_distance(point, start, end)
        for start, end in zip(projected, projected[1:])
    )


def field_geometry(points: Iterable[tuple[float, float]]) -> FieldGeometry:
    """Build field centroid, bounds, and extent from ``(lat, lon)`` points."""
    values = tuple(points)
    if not values:
        raise ValueError("field geometry requires at least one point")
    latitudes = [point[0] for point in values]
    longitudes = [point[1] for point in values]
    centroid_latitude = sum(latitudes) / len(latitudes)
    centroid_longitude = sum(longitudes) / len(longitudes)
    return FieldGeometry(
        well_count=len(values),
        centroid_latitude=centroid_latitude,
        centroid_longitude=centroid_longitude,
        latitude_min=min(latitudes),
        latitude_max=max(latitudes),
        longitude_min=min(longitudes),
        longitude_max=max(longitudes),
        extent_miles=_extent_miles(values),
    )


def filter_candidate_pipelines(
    geometry: FieldGeometry,
    field_counties: set[str],
    pipelines: tuple[PipelineGisRecord, ...],
    padding_miles: float,
) -> tuple[PipelineGisRecord, ...]:
    """Prefilter pipelines by county and padded bounding box."""
    padding_lat = padding_miles / MILES_PER_DEGREE_LATITUDE
    miles_per_lon = _miles_per_degree_longitude(geometry.centroid_latitude)
    padding_lon = padding_miles / miles_per_lon if miles_per_lon else padding_lat
    bbox = (
        geometry.longitude_min - padding_lon,
        geometry.latitude_min - padding_lat,
        geometry.longitude_max + padding_lon,
        geometry.latitude_max + padding_lat,
    )
    candidates = []
    for pipeline in pipelines:
        if field_counties and pipeline.county_fips not in field_counties:
            if pipeline.county_fips is not None:
                continue
        if _bboxes_intersect(bbox, _pipeline_bbox(pipeline)):
            candidates.append(pipeline)
    return tuple(candidates)


def nearest_pipeline(
    field_points: tuple[tuple[float, float], ...],
    pipelines: tuple[PipelineGisRecord, ...],
) -> NearestPipelineResult | None:
    """Return nearest pipeline to any field well point."""
    best: tuple[float, PipelineGisRecord] | None = None
    for point in field_points:
        for pipeline in pipelines:
            distance = point_to_polyline_distance_miles(
                latitude=point[0],
                longitude=point[1],
                coordinates=pipeline.coordinates,
            )
            if best is None or distance < best[0]:
                best = (distance, pipeline)
    if best is None:
        return None
    distance, pipeline = best
    return NearestPipelineResult(
        distance_miles=round(distance, 6),
        pipeline_identifier=pipeline.pipeline_identifier,
        source_county=pipeline.county_fips,
        source_file=pipeline.source_file,
    )


def _project(
    longitude: float,
    latitude: float,
    *,
    origin_longitude: float,
    origin_latitude: float,
) -> tuple[float, float]:
    x = (longitude - origin_longitude) * _miles_per_degree_longitude(origin_latitude)
    y = (latitude - origin_latitude) * MILES_PER_DEGREE_LATITUDE
    return x, y


def _point_segment_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    px, py = point
    sx, sy = start
    ex, ey = end
    dx = ex - sx
    dy = ey - sy
    if dx == 0 and dy == 0:
        return math.hypot(px - sx, py - sy)
    t = max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (sx + t * dx), py - (sy + t * dy))


def _extent_miles(points: tuple[tuple[float, float], ...]) -> float:
    if len(points) < 2:
        return 0.0
    latitudes = [point[0] for point in points]
    longitudes = [point[1] for point in points]
    return round(
        haversine_miles(
            min(latitudes),
            min(longitudes),
            max(latitudes),
            max(longitudes),
        ),
        6,
    )


def _miles_per_degree_longitude(latitude: float) -> float:
    return MILES_PER_DEGREE_LATITUDE * abs(math.cos(math.radians(latitude)))


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


__all__ = [
    "FieldGeometry",
    "NearestPipelineResult",
    "field_geometry",
    "filter_candidate_pipelines",
    "haversine_miles",
    "nearest_pipeline",
    "point_to_polyline_distance_miles",
]
