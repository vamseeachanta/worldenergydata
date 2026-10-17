"""Sourced screening estimates; these do not establish installed pipe properties."""

from __future__ import annotations

import math
import re

from scipy.constants import inch, mile, psi


def feet_to_metres(value):
    """Preserve the decimal factor in bsee.pipeline.adapters.units."""
    return value * 0.3048


def inches_to_metres(value):
    """SI conversion from SciPy's unit definitions."""
    return value * inch


def psi_to_pa(value):
    """SI conversion from SciPy's unit definitions."""
    return value * psi


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

    Distances use the repository's spherical Haversine helper. Conflicting
    sequence numbers or incomplete coordinates reject a route rather than
    bridge an unknown section. Bearings are length weighted clockwise from north.
    """
    from worldenergydata.bsee.data.schemas.pipeline import PipelineLocationSchema
    from worldenergydata.metocean.utils.coordinates import haversine_distance

    ordered = {}
    for raw in points:
        point = PipelineLocationSchema.model_validate(raw)
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


def _put(row, field, value, source):
    row[field] = value
    row[field + "_source"] = source


def _known(row, field, value, source):
    _put(row, field, value, source if value is not None else "DEFAULT:unavailable")


def _minimum_depth(permit, points):
    candidates = [permit.MIN_WTR_DPTH]
    candidates.extend(point.get("WATER_DEPTH") for point in points)
    values = [float(v) for v in candidates if v not in (None, "")]
    values = [v for v in values if math.isfinite(v) and v >= 0]
    return feet_to_metres(min(values)) if values else None


def _base_row(permit, raw, points, defaults, input_source, schedule):
    row = {}
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
    _known(
        row,
        "min_water_depth_m",
        _minimum_depth(permit, points),
        "DERIVED:minimum_available_depth",
    )
    burial = raw.get("BURIAL_DESIGN")
    if not isinstance(burial, bool):
        burial = {"Y": True, "N": False}.get(str(burial).strip().upper())
    _known(row, "buried_design", burial, input_source)
    try:
        geometry = route_geometry(points)
    except ValueError:
        geometry = route_geometry([])
    for field, value in geometry.items():
        _known(row, field, value, "DERIVED:ordered_spherical_route")
    unit = defaults["permit_length_unit"]["value"]
    _put(row, "permit_length_unit", unit, "DEFAULT:permit_length_unit")
    length = None if permit.SEG_LENGTH is None else length_to_m(permit.SEG_LENGTH, unit)
    _known(row, "permit_length_m", length, "DERIVED:permit_length_conversion")
    row.update(
        estimate_wall(permit.PPL_SIZE_CODE, permit.MAOP_PRSS, defaults, schedule)
    )
    return row


def status_selected(status, defaults):
    """Exclude terminal statuses and dictionary-undefined codes when supplied.

    This is the screening exclusion rule, not proof of installed or operating
    condition. The public dictionary is versioned with the default assumptions.
    """
    from worldenergydata.bsee.data.models.pipeline import PipelinePermit

    code = str(status or "").strip() or None
    if not PipelinePermit(status_code=code).is_active:
        return False
    meanings = defaults.get("status_meanings", {}).get("value")
    if not isinstance(meanings, dict) or not meanings:
        raise ValueError("A public status dictionary is required")
    meaning = meanings.get(code)
    return meaning is not None and not (
        {"ABANDONED", "REMOVED", "OUT"} & set(meaning.split())
    )


def _active_permits(permits, defaults):
    from worldenergydata.bsee.data.schemas.pipeline import PipelinePermitSchema

    seen = {}
    fields = (
        "STATUS_CODE",
        "PPL_SIZE_CODE",
        "MAOP_PRSS",
        "RECV_MAOP_PRSS",
        "SEG_LENGTH",
        "MIN_WTR_DPTH",
        "MAX_WTR_DPTH",
        "PROD_CODE",
    )
    for raw in sorted(permits, key=lambda r: str(r.get("SEGMENT_NUM", ""))):
        if not status_selected(raw.get("STATUS_CODE"), defaults):
            continue
        permit = PipelinePermitSchema.model_validate(raw)
        if not permit.SEGMENT_NUM:
            raise ValueError("Missing segment identifier")
        signature = tuple(getattr(permit, key) for key in fields) + (
            raw.get("BURIAL_DESIGN"),
        )
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

    Public meanings supplement the existing inactive-status rule. Repeated
    grant joins with identical engineering values collapse; conflicts reject.
    A published maximum depth is never used as a minimum.
    Missing burial flags remain unknown. Empty contents govern by assumption;
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
            _put(
                row,
                "contents_density_kg_m3",
                defaults[density_key]["value"],
                "DEFAULT:" + density_key,
            )
            result.append(row)
    return result


def estimate_wall(size_code, maop_psi, defaults, schedule=()):
    """Select a supplied schedule or estimate thickness by hoop force equilibrium.

    A diametral cut gives p*D = 2*t*stress. The fallback uses the nominal size
    as an OD proxy and the labelled strength assumption. It includes no design
    factor, corrosion allowance, mill tolerance or collapse check. Neither
    route establishes installed wall thickness. Supplied dimensional data
    require independent rights and edition qualification before reuse.
    """
    row = {}
    nominal = decode_size_code(size_code)
    for field in ("grade", "smys_pa"):
        value = defaults.get(field, {}).get("value")
        _known(row, field, value, "DEFAULT:" + field)
    pressure = None if maop_psi is None else psi_to_pa(maop_psi)
    if pressure is not None and (not math.isfinite(pressure) or pressure < 0):
        raise ValueError("MAOP must be finite and nonnegative")
    _known(row, "maop_pa", pressure, "DERIVED:psi_to_pa")
    preferred = defaults.get("schedule", {}).get("value")
    candidates = [
        r
        for r in schedule
        if nominal is not None
        and math.isclose(inches_to_metres(float(r["nps_in"])), nominal)
        and (preferred is None or r["schedule"] == preferred)
    ]
    if candidates:
        chosen = min(candidates, key=lambda r: float(r["wt_mm"]))
        od, wall = (float(chosen[key]) / 1000 for key in ("od_mm", "wt_mm"))
        if not all(math.isfinite(v) and v > 0 for v in (od, wall)) or wall >= od / 2:
            raise ValueError("Invalid supplied dimensions")
        _put(row, "od_m", od, "DERIVED:schedule_lookup")
        _put(row, "wall_thickness_m", wall, "DERIVED:schedule_lookup")
        return row
    _known(row, "od_m", nominal, "DEFAULT:nominal_od_proxy")
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
    _known(row, "wall_thickness_m", wall, "DERIVED:hoop_stress_sizing")
    return row


def read_ndbc_stations(path):
    """Parse a retained public XML response through the existing NDBC client."""
    import httpx

    from worldenergydata.metocean.clients.ndbc_client import NDBCClient

    payload = path.read_bytes()

    def replay(request):
        if request.url.path != "/activestations.xml":
            raise ValueError("Unexpected snapshot request")
        return httpx.Response(200, content=payload)

    with NDBCClient() as client:
        client.client.close()
        client.client = httpx.Client(transport=httpx.MockTransport(replay))
        result = client.fetch_stations()
        if result.had_errors:
            raise ValueError("Invalid station snapshot")
        return result.data


def _station_record_summary(records):
    import pandas as pd

    row = {}
    retained = {r.observation_time: r for r in records}
    times = sorted(retained)
    span = (
        (times[-1] - times[0]).total_seconds()
        / pd.Timedelta(days=365.25).total_seconds()
        if len(times) > 1
        else None
    )
    _known(row, "record_length_years", span, "DERIVED:retained_record_span")
    _put(row, "retained_observations", len(times), "DERIVED:retained_observation_count")
    for quantity, attribute, unit in (
        ("hs", "wave_height_m", "m"),
        ("tp", "dominant_wave_period_s", "s"),
    ):
        valid = {t: getattr(retained[t], attribute) for t in times}
        valid = {
            t: v
            for t, v in valid.items()
            if v is not None and math.isfinite(v) and v > 0
        }
        levels = {}
        if span is not None and span >= 3 and len({t.year for t in valid}) >= 3:
            from worldenergydata.metocean.statistics.eva import ExtremeValueAnalysis

            series = pd.Series(valid, name=quantity).sort_index()
            levels = (
                ExtremeValueAnalysis()
                .fit_annual_maxima(series, periods=[10, 100])
                .return_levels
            )
        for period in (10, 100):
            value = levels.get(period)
            if value is not None and (not math.isfinite(value) or value <= 0):
                raise ValueError("Invalid extreme estimate")
            _known(
                row,
                f"{quantity}_{period}yr_{unit}",
                value,
                "DERIVED:ndbc_annual_maxima_gev",
            )
    return row


def station_environment(latitude, longitude, stations, histories, summary_cache=None):
    """Attach nearest station and independent marginal annual-maxima estimates.

    Retained record span is not archive lifetime or proof of coverage. Short or
    missing records leave return levels unknown. The fits are screening
    extrapolations, not coincident design Hs/Tp pairs or site qualification.
    """
    from worldenergydata.metocean.utils.coordinates import haversine_distance

    row = {}
    if stations and latitude is not None and longitude is not None:
        ranked = sorted(
            (
                haversine_distance(latitude, longitude, s.latitude, s.longitude),
                s.station_id,
                s,
            )
            for s in stations
        )
        distance, station_id, _ = ranked[0]
        _put(row, "station_id", station_id, "PUBLIC:noaa-ndbc")
        _put(row, "station_distance_m", distance * 1000, "DERIVED:nearest_ndbc")
        records = histories.get(station_id, [])
    else:
        _known(row, "station_id", None, "PUBLIC:noaa-ndbc")
        _known(row, "station_distance_m", None, "DERIVED:nearest_ndbc")
        records = []
    cache = summary_cache if summary_cache is not None else {}
    key = row["station_id"]
    if key not in cache:
        cache[key] = _station_record_summary(records)
    row.update(cache[key])
    return row


def _sediment_samples(sediment):
    samples = []
    for point in sediment:
        fractions = {
            name.lower(): float(point.get(name, -99))
            for name in ("Sand", "Mud", "Gravel", "Clay")
        }
        fractions = {k: v for k, v in fractions.items() if math.isfinite(v) and v >= 0}
        if not fractions or max(fractions.values()) == 0:
            continue
        lat, lon = float(point["Latitude"]), float(point["Longitude"])
        if not (
            math.isfinite(lat)
            and math.isfinite(lon)
            and -90 <= lat <= 90
            and -180 <= lon <= 180
        ):
            continue
        samples.append((lat, lon, max(sorted(fractions), key=fractions.get)))
    return samples


def _soil_assignment(row, defaults, samples, tree=None):
    from worldenergydata.metocean.utils.coordinates import haversine_distance

    lat, lon = row["midpoint_latitude_deg"], row["midpoint_longitude_deg"]
    if samples and lat is not None and lon is not None:
        if tree is not None:
            _, index = tree.query(_sphere_vector(lat, lon))
            a, b, soil = samples[int(index)]
            distance = haversine_distance(lat, lon, a, b)
        else:
            distance, _, _, soil = min(
                (haversine_distance(lat, lon, a, b), a, b, soil)
                for a, b, soil in samples
            )
        _put(row, "soil_type", soil, "DERIVED:nearest_usgs_texture")
        _put(
            row,
            "soil_sample_distance_m",
            distance * 1000,
            "DERIVED:nearest_usgs_texture",
        )
    else:
        depth = row["min_water_depth_m"]
        boundary = defaults.get("soil_depth_boundary_m", {}).get("value")
        key = (
            "soil_shallow"
            if depth is not None and boundary is not None and depth <= boundary
            else "soil_deep"
        )
        value = defaults.get(key, {}).get("value") if depth is not None else None
        _known(row, "soil_type", value, "DEFAULT:" + key)
        _known(row, "soil_sample_distance_m", None, "DERIVED:nearest_usgs_texture")


def enrich_rows(
    rows, defaults, stations=(), histories=None, sediment=(), station_summaries=None
):
    """Add public observations, explicit defaults and per-field provenance."""
    result, weather_cache = [], {}
    from scipy.spatial import cKDTree

    samples = sorted(_sediment_samples(sediment))
    tree = cKDTree([_sphere_vector(a, b) for a, b, _ in samples]) if samples else None
    summaries = station_summaries if station_summaries is not None else {}
    for base in rows:
        row = base.copy()
        for field in (
            "corrosion_coating",
            "corrosion_coating_thickness_m",
            "concrete_density_kg_m3",
            "seabed_current_m_s",
            "friction_coefficient",
        ):
            _put(row, field, defaults.get(field, {}).get("value"), "DEFAULT:" + field)
        bearing = row["mean_bearing_deg"]
        direction = (
            None if bearing is None else (bearing + math.degrees(math.pi / 2)) % 360
        )
        _known(row, "wave_direction_deg", direction, "DEFAULT:normal_wave_direction")
        if row["load_case"] == "product":
            densities = defaults.get("product_densities", {}).get("value", {})
            if row["product_code"] in densities:
                _put(
                    row,
                    "contents_density_kg_m3",
                    densities[row["product_code"]],
                    "DEFAULT:product_densities",
                )
        _soil_assignment(row, defaults, samples, tree)
        position = (row["midpoint_latitude_deg"], row["midpoint_longitude_deg"])
        if position not in weather_cache:
            weather_cache[position] = station_environment(
                *position, stations, histories or {}, summaries
            )
        row.update(weather_cache[position])
        result.append(row)
    return result


def _sphere_vector(latitude, longitude):
    lat, lon = map(math.radians, (latitude, longitude))
    return (math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat))
