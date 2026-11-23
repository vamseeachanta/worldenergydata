"""Coverage-qualified environmental observations for screening only."""

import math

from worldenergydata.bsee.pipeline_screening_common import _known, _put


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


def _counted_maxima(records, atlantic):
    import calendar
    from collections import defaultdict

    hours, season, maxima = defaultdict(set), defaultdict(set), {}
    for record in records:
        value = record.wave_height_m
        if value is None or not math.isfinite(value) or value <= 0:
            continue
        time = record.observation_time
        if time.tzinfo is not None:
            from datetime import timezone

            time = time.astimezone(timezone.utc).replace(tzinfo=None)
        hour = time.replace(minute=0, second=0, microsecond=0)
        hours[time.year].add(hour)
        if 6 <= time.month <= 11:
            season[time.year].add(hour)
        previous = maxima.get(time.year)
        if previous is None or value > previous.wave_height_m:
            maxima[time.year] = record
    return {
        year: maxima[year]
        for year, covered in sorted(hours.items())
        if len(covered) >= 0.8 * (8784 if calendar.isleap(year) else 8760)
        and (not atlantic or len(season[year]) >= 0.8 * 183 * 24)
    }


def _qualified_fit(maxima, periods):
    import numpy as np
    import pandas as pd

    from worldenergydata.metocean.statistics.eva import ExtremeValueAnalysis

    series = pd.Series(
        {r.observation_time: r.wave_height_m for r in maxima.values()}, name="hs"
    ).sort_index()
    state = np.random.get_state()
    try:
        np.random.seed(0)
        return ExtremeValueAnalysis().fit_annual_maxima(
            series, periods=periods, confidence_level=0.95
        )
    finally:
        np.random.set_state(state)


def _return_levels(row, maxima):
    count = len(maxima)
    periods = [t for t in (10, 100) if count >= 10 and t <= 4 * count]
    fit = _qualified_fit(maxima, periods) if periods else None
    for t in (10, 100):
        values = (
            [
                mapping.get(t)
                for mapping in (fit.return_levels, fit.lower_ci, fit.upper_ci)
            ]
            if fit and t in periods
            else [None] * 3
        )
        valid = all(v is not None and math.isfinite(v) for v in values)
        valid = valid and 0 < values[1] <= values[0] <= values[2]
        tag = (
            "DERIVED:ndbc_annual_maxima_gev"
            if valid
            else (
                "UNKNOWN:missing_confidence_interval"
                if t in periods
                else "UNKNOWN:short_record"
            )
        )
        for suffix, value in zip(
            ("m", "lower_ci_m", "upper_ci_m", "distribution"),
            [*values, fit.distribution if fit else None],
        ):
            _put(row, f"hs_{t}yr_{suffix}", value if valid else None, tag)


def _station_record_summary(records, *, atlantic=True):
    """Apply I-0248: distinct covered hours, complete maxima and evidenced 95% CI."""
    row = {}
    times = sorted({r.observation_time for r in records})
    span = (
        (times[-1] - times[0]).total_seconds() / (365.25 * 86400)
        if len(times) > 1
        else None
    )
    _known(row, "record_length_years", span, "DERIVED:retained_record_span")
    _put(row, "retained_observations", len(times), "DERIVED:retained_observation_count")
    maxima = _counted_maxima(records, atlantic)
    count = len(maxima)
    _put(row, "complete_annual_maxima", count, "DERIVED:coverage_qualified_maxima")
    _known(
        row,
        "observed_maximum_years",
        ",".join(map(str, maxima)) or None,
        "DERIVED:observed_maximum",
    )
    maximum = max(maxima.values(), key=lambda r: r.wave_height_m) if maxima else None
    _known(
        row,
        "hs_max_observed_m",
        maximum.wave_height_m if maximum else None,
        "DERIVED:observed_maximum",
    )
    period = maximum.dominant_wave_period_s if maximum else None
    period = (
        period if period is not None and math.isfinite(period) and period > 0 else None
    )
    _known(row, "tp_at_hs_max_s", period, "DERIVED:period_at_observed_hs_max")
    _return_levels(row, maxima)
    return row


def station_environment(
    latitude, longitude, stations, histories, summary_cache=None, max_distance_km=50
):
    """Use a retained wave-reporting station within the declared screening radius."""
    from worldenergydata.metocean.utils.coordinates import haversine_distance

    row = {}
    ranked = []
    if latitude is not None and longitude is not None:
        ranked = sorted(
            (
                haversine_distance(latitude, longitude, s.latitude, s.longitude),
                s.station_id,
                s,
            )
            for s in stations
            if any(
                r.wave_height_m is not None
                and math.isfinite(r.wave_height_m)
                and r.wave_height_m > 0
                for r in histories.get(s.station_id, ())
            )
        )
    chosen = ranked[0] if ranked and ranked[0][0] <= max_distance_km else None
    distance, station_id, station = chosen if chosen else (None, None, None)
    _known(row, "station_id", station_id, "PUBLIC:noaa-ndbc")
    _known(
        row,
        "station_distance_m",
        distance * 1000 if distance is not None else None,
        "DERIVED:nearest_ndbc",
    )
    # Active-station XML elev is elevation, not water depth. Only an explicit
    # retained station-depth record may establish this field.
    depth = station.metadata.get("water_depth_m") if station else None
    _known(row, "station_water_depth_m", depth, "PUBLIC:noaa-ndbc")
    if station is None:
        for field in (
            "retained_observations",
            "complete_annual_maxima",
            "record_length_years",
            "observed_maximum_years",
            "hs_max_observed_m",
            "tp_at_hs_max_s",
            *(
                f"hs_{period}yr_{suffix}"
                for period in (10, 100)
                for suffix in ("m", "lower_ci_m", "upper_ci_m", "distribution")
            ),
        ):
            _put(row, field, None, "UNKNOWN:no_station_within_limit")
        return row
    cache = summary_cache if summary_cache is not None else {}
    if station_id not in cache:
        atlantic = -100 <= station.longitude <= 20 and 0 <= station.latitude <= 65
        cache[station_id] = _station_record_summary(
            histories.get(station_id, []), atlantic=atlantic
        )
    row.update(cache[station_id])
    return row


def _sediment_samples(sediment):
    samples = []
    for point in sediment:
        fractions = {
            name.lower(): float(point.get(name, -99))
            for name in ("Sand", "Mud", "Gravel")
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
        if distance <= defaults.get("spatial_match_limit_km", {}).get("value", 50):
            _put(row, "soil_type", soil, "DERIVED:nearest_usgs_texture")
            _put(
                row,
                "soil_sample_distance_m",
                distance * 1000,
                "DERIVED:nearest_usgs_texture",
            )
            return
    _known(row, "soil_type", None, "DERIVED:nearest_usgs_texture")
    _known(row, "soil_sample_distance_m", None, "DERIVED:nearest_usgs_texture")


def _wave_stations(stations, histories):
    return tuple(
        s
        for s in stations
        if any(
            r.wave_height_m is not None
            and math.isfinite(r.wave_height_m)
            and r.wave_height_m > 0
            for r in histories.get(s.station_id, ())
        )
    )


def enrich_rows(
    rows, defaults, stations=(), histories=None, sediment=(), station_summaries=None
):
    """Add public observations, explicit defaults and per-field provenance."""
    result, weather_cache = [], {}
    histories = histories or {}
    stations = _wave_stations(stations, histories)
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
            _known(row, field, defaults.get(field, {}).get("value"), "DEFAULT:" + field)
        bearing = row["mean_bearing_deg"]
        direction = (
            None if bearing is None else (bearing + math.degrees(math.pi / 2)) % 360
        )
        _known(row, "wave_direction_deg", direction, "DEFAULT:normal_wave_direction")
        if row["load_case"] == "product":
            densities = defaults.get("product_densities", {}).get("value", {})
            if row["product_code"] in densities:
                _known(
                    row,
                    "contents_density_kg_m3",
                    densities[row["product_code"]],
                    "DEFAULT:product_densities",
                )
        _soil_assignment(row, defaults, samples, tree)
        position = (row["midpoint_latitude_deg"], row["midpoint_longitude_deg"])
        if position not in weather_cache:
            weather_cache[position] = station_environment(
                *position,
                stations,
                histories or {},
                summaries,
                defaults.get("spatial_match_limit_km", {}).get("value", 50),
            )
        row.update(weather_cache[position])
        result.append(row)
    return result


def _sphere_vector(latitude, longitude):
    lat, lon = map(math.radians, (latitude, longitude))
    return (math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat))
