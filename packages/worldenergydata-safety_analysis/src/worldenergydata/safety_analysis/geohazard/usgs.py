"""Bounded USGS earthquake event queries and reproducible provenance.

Protocol source: https://earthquake.usgs.gov/fdsnws/event/1/ (2026-10-11).
The count request omits limit so the guard sees the entire selection. A second
request can observe catalogue changes; the event limit remains on that request.
No retries, redirects, credentials, background fetching, or disk cache are used.
"""

import hashlib
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, NoReturn
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

REPOSITORY_URL = "https://github.com/vamseeachanta/worldenergydata"
SERVICE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/"
MAX_EVENTS = 20000
MAX_BYTES = 5_000_000
CREDIT = "Credit: U.S. Geological Survey"


class ServiceError(RuntimeError):
    """The service response could not be used."""


class TooManyEvents(ServiceError):
    """Selection exceeds the requested or service event ceiling."""


class AccessRefused(ServiceError):
    """Automated access was refused; stop rather than retry."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str,
                         headers: Any, newurl: str) -> None:
        raise AccessRefused("Redirect refused; inspect the service URL")


@dataclass(frozen=True)
class EarthquakeEvent:
    """One typed table row; unknown magnitude and depth remain None."""

    event_id: str
    time_utc: datetime
    latitude: float
    longitude: float
    depth_km: float | None
    magnitude: float | None
    magnitude_type: str | None
    place: str | None
    event_url: str | None
    source_url: str
    citation: str = CREDIT


@dataclass(frozen=True)
class QueryResult:
    events: tuple[EarthquakeEvent, ...]
    raw: bytes | None
    source_url: str
    retrieved_at_utc: str
    matched_count: int


def _number(value: Any, low: float = -math.inf,
            high: float = math.inf) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Expected a finite number")
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError("Number outside supported range")
    return float(value)


def _utc(value: datetime) -> str:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("Time must be a timezone-aware datetime")
    return value.astimezone(timezone.utc).isoformat()


def _optional_number(value: Any) -> float | None:
    return None if value is None else _number(value)


def _optional_text(value: Any) -> str | None:
    if value is not None and not isinstance(value, str):
        raise ValueError("Expected text or null")
    return value


def _event(feature: dict[str, Any], source_url: str) -> EarthquakeEvent:
    geometry, props = feature["geometry"], feature["properties"]
    if feature["type"] != "Feature" or geometry["type"] != "Point":
        raise ValueError("Expected Point feature")
    coords = geometry["coordinates"]
    if len(coords) != 3 or not isinstance(feature["id"], str):
        raise ValueError("Expected id and three coordinates")
    timestamp = _number(props["time"])
    return EarthquakeEvent(
        event_id=feature["id"],
        time_utc=datetime.fromtimestamp(timestamp / 1000, timezone.utc),
        latitude=_number(coords[1], -90, 90),
        longitude=_number(coords[0], -180, 180),
        depth_km=_optional_number(coords[2]),
        magnitude=_optional_number(props["mag"]),
        magnitude_type=_optional_text(props.get("magType")),
        place=_optional_text(props.get("place")),
        event_url=_optional_text(props.get("url")),
        source_url=source_url,
    )


def parse_geojson(raw: bytes | None, source_url: str) -> tuple[EarthquakeEvent, ...]:
    """Parse the documented GeoJSON summary fields without filling nulls."""
    if raw is None:
        return ()
    try:
        data = json.loads(raw)
        if data["type"] != "FeatureCollection" or not isinstance(data["features"], list):
            raise ValueError("Expected FeatureCollection")
        return tuple(_event(feature, source_url) for feature in data["features"])
    except (KeyError, TypeError, ValueError, OverflowError, OSError) as exc:
        raise ServiceError("Invalid USGS GeoJSON response") from exc


class USGSClient:
    """GET-only synchronous client. Each attempt is at least two seconds apart.

    Access refusal (403/429 or a challenge page) stops immediately. Retry-After
    is never acted upon: no retries means no server-requested wait or extra load.
    Calls on one client must be sequential; instances are not thread-safe.
    """

    def __init__(self, *, timeout: float = 30, max_bytes: int = MAX_BYTES):
        _number(timeout, 0.001, 60)
        if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_BYTES:
            raise ValueError("Byte cap must be an integer from 1 to 5000000")
        self.timeout = timeout
        self.max_bytes = max_bytes
        self._last_finished: float | None = None
        self._opener = build_opener(_NoRedirect())

    def _pause(self) -> None:
        if self._last_finished is not None:
            # A full pause after the previous response also covers slow reads.
            time.sleep(max(2.0, 2.0 - (time.monotonic() - self._last_finished)))

    def _http_error(self, exc: HTTPError) -> NoReturn:
        with exc:
            body = exc.read(min(self.max_bytes, 4096) + 1).decode("utf-8", "replace")
        if exc.code in (403, 429):
            raise AccessRefused(f"USGS refused access (HTTP {exc.code}); no retry") from exc
        text = body.lower()
        if exc.code == 400 and any(s in text for s in ("20000", "20,000", "too many")):
            raise TooManyEvents("USGS event ceiling exceeded. Narrow the selection.") from exc
        raise ServiceError(f"USGS request failed (HTTP {exc.code})") from exc

    def _get(self, url: str) -> bytes | None:
        self._pause()
        request = Request(url, method="GET", headers={
            "User-Agent": f"WorldEnergyData earthquake research client ({REPOSITORY_URL})",
            "Accept": "application/json, text/plain",
        })
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                if response.status == 204:
                    return None
                raw = bytes(response.read(self.max_bytes + 1))
                if len(raw) > self.max_bytes:
                    raise ServiceError(f"Response exceeds {self.max_bytes} bytes")
                if b"<html" in raw.lower() or b"<!doctype html" in raw.lower():
                    raise AccessRefused("HTML/challenge response refused; no retry")
                return raw
        except HTTPError as exc:
            self._http_error(exc)
        except (URLError, TimeoutError, OSError) as exc:
            raise ServiceError("USGS transport failed; no retry") from exc
        finally:
            self._last_finished = time.monotonic()

    def _query(self, location: dict[str, int | float], *, start: datetime,
               end: datetime, min_magnitude: float, limit: int) -> QueryResult:
        if type(limit) is not int or not 1 <= limit <= MAX_EVENTS:
            raise ValueError("Event limit must be an integer from 1 to 20000")
        start_text, end_text = _utc(start), _utc(end)
        if start >= end:
            raise ValueError("Start time must precede end time")
        _number(min_magnitude)
        params = {**location, "starttime": start_text, "endtime": end_text,
                  "minmagnitude": min_magnitude, "eventtype": "earthquake"}
        count_url = SERVICE_URL + "count?" + urlencode(params)
        try:
            count_raw = self._get(count_url)
            count = int(count_raw) if count_raw is not None else 0
        except ValueError as exc:
            raise ServiceError("Invalid USGS count response") from exc
        if count < 0:
            raise ServiceError("Negative USGS count response")
        if count > limit:
            raise TooManyEvents(f"{count} events exceed limit {limit}. Narrow the selection.")
        url = SERVICE_URL + "query?" + urlencode({**params, "format": "geojson", "limit": limit})
        raw = self._get(url) if count else None
        rows = parse_geojson(raw, url)
        if len(rows) > limit:
            raise TooManyEvents("Response exceeds event limit. Narrow the selection.")
        return QueryResult(rows, raw, url, datetime.now(timezone.utc).isoformat(), count)

    def query_box(self, min_latitude: float, max_latitude: float,
                  min_longitude: float, max_longitude: float, *, start: datetime,
                  end: datetime, min_magnitude: float, limit: int) -> QueryResult:
        """Rectangle query; date-line crossing uses bounds outside +/-180."""
        _number(min_latitude, -90, 90)
        _number(max_latitude, -90, 90)
        _number(min_longitude, -360, 360)
        _number(max_longitude, -360, 360)
        if min_latitude >= max_latitude or min_longitude >= max_longitude:
            raise ValueError("Minimum bounds must be less than maximum bounds")
        return self._query({"minlatitude": min_latitude, "maxlatitude": max_latitude,
                            "minlongitude": min_longitude, "maxlongitude": max_longitude},
                           start=start, end=end, min_magnitude=min_magnitude, limit=limit)

    def query_radius(self, latitude: float, longitude: float, radius_km: float, *,
                     start: datetime, end: datetime, min_magnitude: float,
                     limit: int) -> QueryResult:
        """Use USGS's maxradiuskm filter; no local geospatial approximation."""
        _number(latitude, -90, 90)
        _number(longitude, -180, 180)
        _number(radius_km, 0, 20001.6)
        return self._query({"latitude": latitude, "longitude": longitude,
                            "maxradiuskm": radius_km}, start=start, end=end,
                           min_magnitude=min_magnitude, limit=limit)


def emit_manifest(payloads: list[bytes], inputs: list[dict[str, Any]]) -> bytes:
    """Emit provenance from exact saved bytes and recorded retrieval metadata.

    Caller supplies source_url, retrieved_at_utc, terms_quote and terms_url.
    Synthetic inputs must be identified by kind='synthetic'; they are not data.
    """
    if len(payloads) != len(inputs):
        raise ValueError("Each payload requires one provenance input")
    records = []
    for raw, metadata in zip(payloads, inputs):
        for key in ("source_url", "retrieved_at_utc", "terms_quote", "terms_url", "kind"):
            if not metadata.get(key):
                raise ValueError(f"Missing provenance: {key}")
        records.append({**metadata, "sha256": hashlib.sha256(raw).hexdigest(),
                        "size_bytes": len(raw)})
    return (json.dumps({"schema_version": 1, "datasets": records},
                       indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
