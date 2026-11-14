"""Sourced screening estimates; these do not establish installed pipe properties."""

from __future__ import annotations

import math
import re

from scipy.constants import mile

from worldenergydata.bsee.pipeline.adapters.units import (
    feet_to_metres,
    inches_to_metres,
    psi_to_pa,
)
from worldenergydata.bsee.pipeline_screening_common import _known, _put


def length_to_m(value: float, unit: str) -> float:
    """Convert lengths using existing SI helpers and SciPy's mile definition."""
    factors = {"ft": feet_to_metres(1), "mile": mile, "m": 1.0}
    if unit not in factors or not math.isfinite(value) or value < 0:
        raise ValueError("A finite nonnegative length and a known unit are required")
    return value * factors[unit]


def decode_size_code(code: str | None) -> float | None:
    """Decode a single inch-coded size; ranges do not establish one diameter.

    The result is a nominal size. Actual OD requires a qualified dimensional
    lookup; substituting nominal size as OD is an explicitly labelled default.
    """
    text = (code or "").strip()
    if not re.fullmatch(r"\d+(?:\.\d+)?", text) or float(text) <= 0:
        return None
    return inches_to_metres(float(text))


def _bearing(a, b):
    lat1, lat2 = map(math.radians, (a[0], b[0]))
    delta = math.radians(b[1] - a[1])
    return math.atan2(
        math.sin(delta) * math.cos(lat2),
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1) * math.cos(lat2) * math.cos(delta),
    )


def _interpolate(a, b, fraction):
    def vector(point):
        lat, lon = map(math.radians, point)
        return (
            math.cos(lat) * math.cos(lon),
            math.cos(lat) * math.sin(lon),
            math.sin(lat),
        )

    av, bv = vector(a), vector(b)
    angle = math.acos(max(-1.0, min(1.0, sum(x * y for x, y in zip(av, bv)))))
    if angle == 0:
        return a
    if abs(math.sin(angle)) <= math.ulp(1.0):
        raise ValueError("Antipodal route leg has no unique midpoint")
    wa = math.sin((1 - fraction) * angle) / math.sin(angle)
    wb = math.sin(fraction * angle) / math.sin(angle)
    x, y, z = (wa * u + wb * v for u, v in zip(av, bv))
    return math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))


def route_geometry(points):
    """Length along ordered points, half-length midpoint and circular mean bearing.

    Conflicting sequence numbers or incomplete coordinates reject a route.
    """
    from worldenergydata.bsee.data.schemas.pipeline import PipelineLocationSchema
    from worldenergydata.metocean.utils.coordinates import haversine_distance

    ordered = {}
    for raw in points:
        point = PipelineLocationSchema.model_validate(
            {**raw, "POINT_NUM": raw.get("POINT_NUM") or raw.get("ASBUILT_SEQ_NUM")}
        )
        values = (point.LATITUDE, point.LONGITUDE)
        if point.POINT_NUM is None:
            raise ValueError("Route sequence is missing")
        if any(v is None or not math.isfinite(v) for v in values):
            raise ValueError("Route coordinate is missing or nonfinite")
        if point.POINT_NUM in ordered and ordered[point.POINT_NUM] != values:
            raise ValueError("Conflicting route sequence")
        ordered[point.POINT_NUM] = values
    coords = [ordered[key] for key in sorted(ordered)]
    result = dict.fromkeys(
        (
            "length_m",
            "midpoint_latitude_deg",
            "midpoint_longitude_deg",
            "mean_bearing_deg",
        )
    )
    if not coords:
        return result
    legs = [
        (a, b, 1000 * haversine_distance(*a, *b)) for a, b in zip(coords, coords[1:])
    ]
    total = sum(leg[2] for leg in legs)
    result["length_m"] = total if legs else None
    midpoint = coords[0]
    remaining = total / 2
    for a, b, distance in legs:
        if distance and remaining <= distance:
            midpoint = _interpolate(a, b, remaining / distance)
            break
        remaining -= distance
    result["midpoint_latitude_deg"], result["midpoint_longitude_deg"] = midpoint
    x = sum(d * math.sin(_bearing(a, b)) for a, b, d in legs)
    y = sum(d * math.cos(_bearing(a, b)) for a, b, d in legs)
    if total and math.hypot(x, y) > math.ulp(total) * len(legs):
        result["mean_bearing_deg"] = math.degrees(math.atan2(x, y)) % 360
    return result


SERVICE_STATES = {
    "ACT": "in_service",
    "OUT": "out_of_service",
    "PABN": "abandonment_proposed",
    "PREM": "removal_proposed",
}


def _base_row(permit, raw, points, defaults, input_source, schedule):
    row = {}
    _put(
        row,
        "service_state",
        SERVICE_STATES[permit.STATUS_CODE],
        "PUBLIC:bsee-status-dictionary",
    )
    for field, value in (
        ("segment_id", permit.SEGMENT_NUM),
        ("status", permit.STATUS_CODE),
        ("size_code", permit.PPL_SIZE_CODE),
        ("product_code", permit.PROD_CODE),
    ):
        _known(row, field, value, input_source)
    _known(
        row,
        "nominal_size_m",
        decode_size_code(permit.PPL_SIZE_CODE),
        "DERIVED:inch_size_code",
    )
    try:
        geometry = route_geometry(points)
    except ValueError as exc:
        geometry = route_geometry([])
        route_issue = type(exc).__name__ + ": " + str(exc)
    else:
        route_issue = None
    _known(row, "route_rejection_reason", route_issue, "DERIVED:route_validation")
    for field, value in geometry.items():
        _known(row, field, value, "DERIVED:ordered_spherical_route")
    unit = defaults["permit_length_unit"]["value"]
    _put(row, "permit_length_unit", unit, "DEFAULT:permit_length_unit")
    length = (
        None if permit.SEG_LENGTH in (None, 0) else length_to_m(permit.SEG_LENGTH, unit)
    )
    _known(row, "permit_length_m", length, "DERIVED:permit_length_conversion")
    row.update(
        estimate_wall(permit.PPL_SIZE_CODE, permit.MAOP_PRSS, defaults, schedule)
    )
    return row


def status_selected(status, defaults):
    """Select only ACT, OUT, PABN and PREM under acceptance policy I-0248."""
    code = str(status or "").strip() or None
    meanings = defaults.get("status_meanings", {}).get("value")
    if not isinstance(meanings, dict) or not meanings:
        raise ValueError("A public status dictionary is required")
    return code in SERVICE_STATES and code in meanings


def _active_permits(permits, defaults):
    from worldenergydata.bsee.data.schemas.pipeline import PipelinePermitSchema

    seen = {}
    fields = (
        "STATUS_CODE",
        "PPL_SIZE_CODE",
        "MAOP_PRSS",
        "SEG_LENGTH",
        "PROD_CODE",
    )
    for raw in sorted(permits, key=lambda r: str(r.get("SEGMENT_NUM", ""))):
        if not status_selected(raw.get("STATUS_CODE"), defaults):
            continue
        permit = PipelinePermitSchema.model_validate(raw)
        if not permit.SEGMENT_NUM:
            raise ValueError("Missing segment identifier")
        signature = tuple(getattr(permit, key) for key in fields)
        if permit.SEGMENT_NUM in seen:
            if seen[permit.SEGMENT_NUM] != signature:
                raise ValueError("Conflicting permit engineering values")
            continue
        seen[permit.SEGMENT_NUM] = signature
        yield permit, raw


def build_rows(
    permits, locations, defaults, input_source="PUBLIC:bsee-data-center", schedule=()
):
    """Build two screening cases from validated, status-selected bulk records.

    The explicit installed-status policy is independent of is_active. Repeated
    grant joins with identical engineering values collapse; conflicts reject.
    Unsupported minimum-depth and burial fields are not exported.
    Empty contents govern by assumption;
    unknown product density remains distinct from a true empty density of zero.
    """
    from collections import defaultdict

    grouped = defaultdict(list)
    for point in locations:
        grouped[str(point.get("SEGMENT_NUM", "")).strip()].append(point)
    result = []
    for permit, raw in _active_permits(permits, defaults):
        base = _base_row(
            permit, raw, grouped[permit.SEGMENT_NUM], defaults, input_source, schedule
        )
        for case, density_key in (
            ("empty", "empty_density"),
            ("product", "product_density"),
        ):
            row = base.copy()
            _put(row, "load_case", case, "DERIVED:screening_case_expansion")
            _put(row, "governing_case", case == "empty", "DEFAULT:empty_case_governs")
            _known(
                row,
                "contents_density_kg_m3",
                defaults[density_key]["value"],
                "DEFAULT:" + density_key,
            )
            result.append(row)
    return result


def _supplied_dimensions(row, nominal, defaults, schedule):
    preferred = defaults.get("schedule", {}).get("value")
    candidates = [
        r
        for r in schedule
        if nominal is not None
        and math.isclose(inches_to_metres(float(r["nps_in"])), nominal)
        and (preferred is None or r["schedule"] == preferred)
    ]
    _put(row, "wall_thickness_m", None, "UNKNOWN:no_evidenced_wall")
    if candidates:
        if any(
            not r.get("rights") or not r.get("edition") or not r.get("source")
            for r in candidates
        ):
            raise ValueError("Supplied dimensions require rights, edition and source")
        chosen = min(candidates, key=lambda r: float(r["wt_mm"]))
        od, wall = (float(chosen[key]) / 1000 for key in ("od_mm", "wt_mm"))
        if not all(math.isfinite(v) and v > 0 for v in (od, wall)) or wall >= od / 2:
            raise ValueError("Invalid supplied dimensions")
        _put(row, "od_m", od, "DERIVED:schedule_lookup")
        _put(row, "wall_thickness_m", wall, "DERIVED:schedule_lookup")
    else:
        _known(row, "od_m", nominal, "DEFAULT:nominal_od_proxy")


def estimate_wall(size_code, maop_psi, defaults, schedule=()):
    """Select a supplied schedule or estimate thickness by hoop force equilibrium.

    A diametral cut gives p*D = 2*t*stress. The fallback uses the nominal size
    as an OD proxy and the labelled strength assumption. It includes no design
    factor, corrosion allowance, mill tolerance or collapse check. The hoop
    value is never assigned to installed wall. Supplied dimensional data
    require independent rights and edition qualification before reuse.
    """
    row = {}
    nominal = decode_size_code(size_code)
    for field in ("grade", "smys_pa"):
        value = defaults.get(field, {}).get("value")
        _known(row, field, value, "DEFAULT:" + field)
    pressure = None if maop_psi in (None, 0) else psi_to_pa(maop_psi)
    if pressure is not None and (not math.isfinite(pressure) or pressure < 0):
        raise ValueError("MAOP must be finite and nonnegative")
    _known(row, "maop_pa", pressure, "DERIVED:psi_to_pa")
    _supplied_dimensions(row, nominal, defaults, schedule)
    strength = row["smys_pa"]
    wall = None
    if (
        nominal is not None
        and pressure is not None
        and pressure > 0
        and strength is not None
    ):
        if not math.isfinite(strength) or strength <= 0:
            raise ValueError("Assumed strength must be finite and positive")
        wall = pressure * nominal / (2 * strength)
        if wall >= nominal / 2:
            raise ValueError("Hoop estimate exceeds the dimensional range")
    _known(
        row,
        "hoop_yield_wall_at_assumed_smys_m",
        wall,
        "DERIVED:hoop_yield_at_assumed_smys",
    )
    return row


# Preserve the public builder API while separating environmental qualification.
from worldenergydata.bsee.pipeline_screening_environment import (
    _station_record_summary,
    enrich_rows,
    read_ndbc_stations,
    station_environment,
)
