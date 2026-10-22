"""Small anonymous publisher probes with schema, unit and UTC checks.

Contracts: NDBC measurement descriptions; CO-OPS API (Units, Time Zone);
ERDDAP tabledap JSON documentation; MET Oceanforecast data model. Exact URLs,
requests and recorded-response provenance live in the packaged source register
and tests/fixtures/metocean/endpoints/provenance.json. These are availability
checks, not engineering data qualification or dataset reuse permission.
"""

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import httpx

from worldenergydata.metocean.clients.coops_client import COOPSClient
from worldenergydata.metocean.clients.copernicus_clients import EndpointError
from worldenergydata.metocean.clients.erddap_client import ERDDAPClient
from worldenergydata.metocean.clients.met_norway_client import MetNorwayClient
from worldenergydata.metocean.clients.ndbc_client import NDBCClient
from worldenergydata.metocean.source_register import get_source


@dataclass(frozen=True)
class Sample:
    source: str
    station: str
    timestamp: datetime
    value: float | None
    unit: str
    variable: str
    datum: str | None = None


def _utc(timestamp: datetime) -> datetime:
    if timestamp.utcoffset() != timedelta(0):
        raise ValueError("expected explicit UTC")
    return timestamp


def parse_sample(
    source: str, content: bytes, *, station_id: str = "42001"
) -> list[Sample]:
    """Replay a known response contract through the existing client parsers.

    NDBC publishes UTC text. CO-OPS timestamps have no offset; only responses
    requested with time_zone=gmt, units=metric, datum=MLLW are accepted here.
    The response cannot attest those request options, so callers must preserve
    the request provenance. Missing wave heights remain None, never zero.
    """
    parsers = {
        "ndbc_realtime": lambda data: _ndbc(data, station_id),
        "coops": _coops,
        "irish_weather_buoys": _erddap,
        "met_norway": _met,
    }
    if source not in parsers:
        raise ValueError("No sample parser registered for source")
    try:
        samples = parsers[source](content)
        if not samples:
            raise ValueError("empty sample")
        for sample in samples:
            _utc(sample.timestamp)
            if sample.value is not None and not math.isfinite(sample.value):
                raise ValueError("nonfinite value")
        return samples
    except (ValueError, KeyError, TypeError, IndexError, AttributeError, UnicodeError):
        raise EndpointError(
            f"{source}: unexpected data schema, units or UTC timestamp"
        ) from None


def _ndbc(content: bytes, station_id: str) -> list[Sample]:
    text = content.decode("utf-8")
    lines = text.splitlines()
    columns = lines[0].split()
    units = lines[1].split()
    # NDBC standard meteorological format, measured in the two published header
    # rows. No unit conversion is applied: WVHT is m, DPD/APD are sec.
    if columns[:9] != ["#YY", "MM", "DD", "hh", "mm", "WDIR", "WSPD", "GST", "WVHT"]:
        raise ValueError("columns")
    if units[:9] != ["#yr", "mo", "dy", "hr", "mn", "degT", "m/s", "m/s", "m"]:
        raise ValueError("units")
    for line in lines[2:]:
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != len(columns):
            raise ValueError("row width")
        if fields[columns.index("WVHT")] != "MM":
            float(fields[columns.index("WVHT")])
    with NDBCClient() as client:
        rows = client._parse_realtime_data(station_id, text)
    if len(rows) != len([line for line in lines[2:] if line.strip()]):
        raise ValueError("discarded records")
    return [
        Sample(
            "ndbc_realtime",
            row.station_id,
            row.observation_time.replace(tzinfo=timezone.utc),
            row.wave_height_m,
            "m",
            "WVHT",
        )
        for row in rows
    ]


def _coops(content: bytes) -> list[Sample]:
    payload = json.loads(content)
    station = payload["metadata"]["id"]
    if not isinstance(station, str) or not station:
        raise ValueError("station")
    with COOPSClient() as client:
        rows = [
            client._parse_water_level(station, row, "MLLW") for row in payload["data"]
        ]
    return [
        Sample(
            "coops",
            row.station_id,
            row.observation_time.replace(tzinfo=timezone.utc),
            row.water_level_m,
            "m",
            "water_level",
            "MLLW",
        )
        for row in rows
    ]


def _erddap(content: bytes) -> list[Sample]:
    payload = json.loads(content)
    table = payload["table"]
    columns = table["columnNames"]
    if not {"time", "station_id", "WaveHeight", "Tp"}.issubset(columns):
        raise ValueError("columns")
    units = dict(zip(columns, table["columnUnits"], strict=True))
    if any(
        units[key] != value
        for key, value in {
            "time": "UTC",
            "WaveHeight": "meters",
            "Tp": "seconds",
        }.items()
    ):
        raise ValueError("units")
    for row in table["rows"]:
        if len(row) != len(columns):
            raise ValueError("row width")
        for field in ("WaveHeight", "Tp"):
            value = row[columns.index(field)]
            if value is not None and type(value) not in (int, float):
                raise ValueError("numeric field")
        _utc(datetime.fromisoformat(row[columns.index("time")].replace("Z", "+00:00")))
    with ERDDAPClient(server=get_source("irish_weather_buoys")["base_url"]) as client:
        rows = client._parse_tabledap_response("IWBNetwork", payload)
    if len(rows) != len(table["rows"]):
        raise ValueError("discarded records")
    return [
        Sample(
            "irish_weather_buoys",
            row.station_id,
            row.observation_time,
            row.wave_height_m,
            "m",
            "WaveHeight",
        )
        for row in rows
    ]


def _met(content: bytes) -> list[Sample]:
    payload = json.loads(content)
    if payload["type"] != "Feature" or payload["geometry"]["type"] != "Point":
        raise ValueError("GeoJSON")
    properties = payload["properties"]
    if properties["meta"]["units"]["sea_surface_wave_height"] != "m":
        raise ValueError("units")
    lon, lat = payload["geometry"]["coordinates"][:2]
    with MetNorwayClient() as client:
        rows = client._parse_ocean_response(lat, lon, payload)
    if len(rows) != len(properties["timeseries"]):
        raise ValueError("discarded records")
    for entry in properties["timeseries"]:
        details = entry["data"]["instant"]["details"]
        if "sea_surface_wave_height" not in details:
            raise ValueError("missing height")
        value = details["sea_surface_wave_height"]
        if value is not None and type(value) not in (int, float):
            raise ValueError("numeric field")
    return [
        Sample(
            "met_norway",
            "point",
            row.forecast_time,
            row.wave_height_m,
            "m",
            "sea_surface_wave_height",
        )
        for row in rows
    ]


class ProbeError(EndpointError):
    """Safe diagnostic with an HTTP code for report classification."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _request_contract(source: str, url: str) -> str:
    """Enforce request-side units/zone that CO-OPS cannot echo in its JSON."""
    parsed = urlsplit(url)
    if source == "coops":
        query = parse_qs(parsed.query)
        required = {
            "units": "metric",
            "time_zone": "gmt",
            "datum": "MLLW",
            "format": "json",
            "product": "water_level",
        }
        if any(query.get(key) != [value] for key, value in required.items()):
            raise ValueError(
                "CO-OPS probe requires metric units, GMT and MLLW water levels"
            )
    if source == "ndbc_realtime":
        match = re.fullmatch(r"/data/realtime2/([A-Za-z0-9]+)\.txt", parsed.path)
        if match is None:
            raise ValueError("NDBC probe requires a realtime station text URL")
        return match.group(1)
    return "42001"


def probe_sample(
    source: str, *, http: httpx.Client, user_agent: str, url: str | None = None
) -> list[Sample]:
    """One request, no redirects/retries; caller chooses timeout and User-Agent.

    An override URL is for station-day inputs of the same registered source.
    Authentication headers and cookies on the injected client are not copied.
    HTTP classification follows RFC 9110 (2022), sections 15.3-15.6.
    """
    from worldenergydata.metocean.source_register import registered_url

    row = get_source(source)
    destination = url or row["health_url"]
    if row["auth_requirement"] != "none" or not registered_url(
        destination, {"sources": [row]}
    ):
        raise ValueError("Probe requires a registered anonymous source URL")
    if not user_agent.strip():
        raise ValueError("An identifying User-Agent is required")
    station_id = _request_contract(source, destination)
    request = httpx.Request("GET", destination, headers={"User-Agent": user_agent})
    try:
        response = http.send(request, auth=None, follow_redirects=False)
    except httpx.RequestError:
        raise ProbeError(f"{source}: unreachable; retirement not established") from None
    try:
        if response.status_code in {404, 410}:
            raise ProbeError(
                f"{source}: endpoint retired or moved (HTTP {response.status_code})",
                response.status_code,
            )
        if response.status_code != 200:
            raise ProbeError(
                f"{source}: HTTP {response.status_code}; retirement not established",
                response.status_code,
            )
        return parse_sample(source, response.content, station_id=station_id)
    finally:
        response.close()
