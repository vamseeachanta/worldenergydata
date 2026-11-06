"""Offline synthetic cases for the USGS event-service client."""

from __future__ import annotations

import importlib
import json
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType as Module
from typing import NoReturn
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

import pytest
from pytest import MonkeyPatch as Patch

MODULE = "worldenergydata.safety_analysis.geohazard.usgs"
START = datetime(2024, 1, 1, tzinfo=timezone.utc)
END = datetime(2024, 1, 2, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def api(monkeypatch: Patch) -> Module:
    # Any unmocked HTTP access is a test failure, including error paths.
    import urllib.request

    def blocked(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("Network forbidden in offline tests")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", blocked)
    return importlib.import_module(MODULE)


def synthetic_payload(
    depth: float | None = None, magnitude: float | None = None
) -> bytes:
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": "synthetic-event",
                    "properties": {
                        "time": 1704067200000,
                        "mag": magnitude,
                        "magType": None,
                        "place": "Synthetic offshore point",
                        "url": "https://example.invalid/synthetic-event",
                    },
                    "geometry": {"type": "Point", "coordinates": [137, 37, depth]},
                }
            ],
        }
    ).encode()


def box(api, client, limit=10):
    return client.query_box(
        36, 38, 136, 138, start=START, end=END, min_magnitude=5, limit=limit
    )


def test_module_exists() -> None:
    assert importlib.util.find_spec(MODULE) is not None


def test_count_first_and_typed_nulls(api: Module, monkeypatch: Patch) -> None:
    calls: list[str] = []
    client = api.USGSClient()

    def get(url: str) -> bytes:
        calls.append(url)
        return b"1" if "/count?" in url else synthetic_payload()

    monkeypatch.setattr(client, "_get", get)
    result = box(api, client)
    assert [urlparse(u).path.rsplit("/", 1)[1] for u in calls] == ["count", "query"]
    count = parse_qs(urlparse(calls[0]).query)
    query = parse_qs(urlparse(calls[1]).query)
    assert "limit" not in count
    assert count["minlatitude"] == ["36"]
    assert query["limit"] == ["10"]
    assert query["format"] == ["geojson"]
    assert query["minmagnitude"] == ["5"]
    assert query["eventtype"] == ["earthquake"]
    row = result.events[0]
    assert (row.event_id, row.latitude, row.longitude) == ("synthetic-event", 37, 137)
    assert row.time_utc == START
    assert row.depth_km is None and row.magnitude is None
    assert row.source_url == calls[1]
    assert row.citation == "Credit: U.S. Geological Survey"
    assert result.raw == synthetic_payload()


def test_radius_parameters(api: Module, monkeypatch: Patch) -> None:
    client = api.USGSClient()
    calls: list[str] = []

    def get(url: str) -> bytes:
        calls.append(url)
        return b"0"

    monkeypatch.setattr(client, "_get", get)
    result = client.query_radius(
        37, 137, 20, start=START, end=END, min_magnitude=5, limit=10
    )
    params = parse_qs(urlparse(calls[0]).query)
    assert params["latitude"] == ["37"]
    assert params["maxradiuskm"] == ["20"]
    assert not result.events and len(calls) == 1
    assert result.raw is None  # No fabricated response when only count is fetched.


def test_count_guard_prevents_download(api: Module, monkeypatch: Patch) -> None:
    client = api.USGSClient()
    monkeypatch.setattr(client, "_get", lambda url: b"11")
    with pytest.raises(api.TooManyEvents, match="Narrow"):
        box(api, client)


@pytest.mark.parametrize("limit", [0, 20001, True, 1.5])
def test_invalid_limit_never_fetches(api: Module, limit: int | float) -> None:
    with pytest.raises(ValueError):
        box(api, api.USGSClient(), limit=limit)


@pytest.mark.parametrize(
    "coords", [(38, 36, 136, 138), (-91, 38, 136, 138), (36, 38, float("nan"), 138)]
)
def test_invalid_box(api: Module, coords: tuple[float, float, float, float]) -> None:
    with pytest.raises(ValueError):
        api.USGSClient().query_box(
            *coords, start=START, end=END, min_magnitude=5, limit=10
        )


def test_invalid_time(api: Module) -> None:
    with pytest.raises(ValueError):
        api.USGSClient().query_radius(
            37, 137, 20, start=END, end=START, min_magnitude=5, limit=10
        )


def test_parse_non_null_and_invalid_shape(api: Module) -> None:
    rows = api.parse_geojson(synthetic_payload(12.5, 6.2), "https://example.invalid")
    assert rows[0].depth_km == 12.5 and rows[0].magnitude == 6.2
    with pytest.raises(api.ServiceError):
        api.parse_geojson(b'{"type":"FeatureCollection"}', "https://example.invalid")


def test_transport_caps_timeout_pause_and_headers(
    api: Module, monkeypatch: Patch
) -> None:
    client = api.USGSClient(max_bytes=8, timeout=7)
    pauses: list[float] = []
    monkeypatch.setattr(api.time, "sleep", pauses.append)
    ticks = iter([10.0, 10.5, 12.0])
    monkeypatch.setattr(api.time, "monotonic", lambda: next(ticks))

    class Response:
        status = 200

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def read(self, size: int) -> bytes:
            return b"123456789"[:size]

    def opened(request, timeout):
        assert request.get_method() == "GET"
        assert timeout == 7
        assert api.REPOSITORY_URL in request.get_header("User-agent")
        return Response()

    monkeypatch.setattr(client._opener, "open", opened)
    for attempt in range(2):
        with pytest.raises(api.ServiceError, match="bytes"):
            client._get(api.SERVICE_URL + "count")
        if attempt == 0:
            assert pauses == []
    assert pauses == [1.5]


@pytest.mark.parametrize(
    "status,body,error",
    [
        (400, b"Search is limited to 20000 events", "TooManyEvents"),
        (400, b"Bad parameter", "ServiceError"),
        (403, b"Forbidden", "AccessRefused"),
        (429, b"Rate limited", "AccessRefused"),
    ],
)
def test_http_errors_no_retry(
    api: Module,
    monkeypatch: Patch,
    status: int,
    body: bytes,
    error: str,
) -> None:
    from io import BytesIO

    client = api.USGSClient()

    def opened(*args, **kwargs):
        raise HTTPError(api.SERVICE_URL, status, "error", {}, BytesIO(body))

    monkeypatch.setattr(client._opener, "open", opened)
    with pytest.raises(getattr(api, error)):
        client._get(api.SERVICE_URL + "count")


def test_manifest_reproduction(api: Module) -> None:
    root = Path(__file__).parents[3] / "fixtures" / "geohazard"
    inputs = json.loads((root / "provenance_inputs.json").read_text())
    emitted = api.emit_manifest(
        [(root / item["file"]).read_bytes() for item in inputs], inputs
    )
    assert emitted == (root / "manifest.json").read_bytes()


def test_recorded_response_schema(api: Module) -> None:
    root = Path(__file__).parents[3] / "fixtures" / "geohazard"
    rows = api.parse_geojson(
        (root / "usgs_recorded.geojson").read_bytes(),
        "https://earthquake.usgs.gov/fdsnws/event/1/",
    )
    assert len(rows) == 2
    assert {r.event_id for r in rows} == {"us6000m0xm", "us6000m0xl"}
    assert all(r.time_utc.utcoffset().total_seconds() == 0 for r in rows)


@pytest.mark.parametrize("radius", [-1, 20002, float("inf")])
def test_invalid_radius(api: Module, radius: float) -> None:
    with pytest.raises(ValueError):
        api.USGSClient().query_radius(
            37, 137, radius, start=START, end=END, min_magnitude=5, limit=10
        )


def test_count_query_drift_is_bounded(api: Module, monkeypatch: Patch) -> None:
    client = api.USGSClient()
    payload = json.loads(synthetic_payload())
    payload["features"] *= 2
    # Distinct synthetic IDs isolate overflow from duplicate-identity rejection.
    payload["features"][1] = {**payload["features"][1], "id": "synthetic-other"}
    monkeypatch.setattr(
        client,
        "_get",
        lambda url: b"1" if "/count?" in url else json.dumps(payload).encode(),
    )
    with pytest.raises(api.TooManyEvents):
        box(api, client, limit=1)


def test_challenge_response_stops(api: Module, monkeypatch: Patch) -> None:
    client = api.USGSClient()

    class Response:
        status = 200

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def read(self, size: int) -> bytes:
            return b"<!doctype html><html>challenge</html>"

    monkeypatch.setattr(client._opener, "open", lambda *a, **kw: Response())
    with pytest.raises(api.AccessRefused):
        client._get(api.SERVICE_URL + "count")


def test_nodata_204_after_count(api: Module, monkeypatch: Patch) -> None:
    client = api.USGSClient()

    class Response:
        status = 204

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def read(self, size: int) -> bytes:
            return b""

    monkeypatch.setattr(client._opener, "open", lambda *a, **kw: Response())
    raw = client._get(api.SERVICE_URL + "query")
    assert api.parse_geojson(raw, api.SERVICE_URL) == ()


@pytest.mark.parametrize("elapsed,expected", [(0.5, [1.5]), (2.0, []), (60.0, [])])
def test_pause_only_remaining_interval(
    api: Module,
    monkeypatch: Patch,
    elapsed: float,
    expected: list[float],
) -> None:
    client = api.USGSClient()
    client._last_finished = 10.0
    pauses: list[float] = []
    monkeypatch.setattr(api.time, "monotonic", lambda: 10.0 + elapsed)
    monkeypatch.setattr(api.time, "sleep", pauses.append)
    client._pause()
    assert pauses == expected


@pytest.mark.parametrize("longitude", [190, -190, 361])
def test_date_line_response_longitude(
    api: Module, monkeypatch: Patch, longitude: int
) -> None:
    payload = json.loads(synthetic_payload())
    payload["features"][0]["geometry"]["coordinates"][0] = longitude
    client = api.USGSClient()
    monkeypatch.setattr(
        client,
        "_get",
        lambda url: b"1" if "/count?" in url else json.dumps(payload).encode(),
    )
    if abs(longitude) > 360:
        with pytest.raises(api.ServiceError):
            client.query_box(
                36, 38, 170, 200, start=START, end=END, min_magnitude=5, limit=10
            )
    else:
        result = client.query_box(
            36, 38, 170, 200, start=START, end=END, min_magnitude=5, limit=10
        )
        assert result.events[0].longitude == longitude


@pytest.mark.parametrize("count", [0, 1])
def test_retrieval_stamp_precedes_parsing(
    api: Module, monkeypatch: Patch, count: int
) -> None:
    clock = [START]
    pauses: list[float] = []
    calls: list[str] = []

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock[0]

    class Response:
        status = 200

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def read(self, size: int) -> bytes:
            clock[0] = START
            return str(count).encode() if len(calls) == 1 else synthetic_payload()

    def opened(request, timeout):
        calls.append(request.full_url)
        return Response()

    original_parse = api.parse_geojson

    def parse(raw, url):
        clock[0] = END
        return original_parse(raw, url)

    monkeypatch.setattr(api, "datetime", Clock)
    monkeypatch.setattr(api, "parse_geojson", parse)
    monkeypatch.setattr(api.time, "sleep", pauses.append)
    monkeypatch.setattr(api.time, "monotonic", lambda: 10.0)
    client = api.USGSClient()
    monkeypatch.setattr(client._opener, "open", opened)
    result = client.query_box(
        36,
        38,
        136,
        138,
        start=Clock.fromtimestamp(START.timestamp(), timezone.utc),
        end=Clock.fromtimestamp(END.timestamp(), timezone.utc),
        min_magnitude=5,
        limit=10,
    )
    assert result.retrieved_at_utc == START.isoformat()
    assert len(calls) == (2 if count else 1)
    assert pauses == ([2.0] if count else [])
