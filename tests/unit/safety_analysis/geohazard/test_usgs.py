"""Offline synthetic cases for the USGS event-service client."""

import importlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

import pytest

MODULE = "worldenergydata.safety_analysis.geohazard.usgs"
START = datetime(2024, 1, 1, tzinfo=timezone.utc)
END = datetime(2024, 1, 2, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def api(monkeypatch):
    # Any unmocked HTTP access is a test failure, including error paths.
    import urllib.request

    def blocked(*args, **kwargs):
        raise AssertionError("Network forbidden in offline tests")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", blocked)
    return importlib.import_module(MODULE)


def synthetic_payload(depth=None, magnitude=None):
    return json.dumps({
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature", "id": "synthetic-event",
            "properties": {"time": 1704067200000, "mag": magnitude,
                           "magType": None, "place": "Synthetic offshore point",
                           "url": "https://example.invalid/synthetic-event"},
            "geometry": {"type": "Point", "coordinates": [137, 37, depth]},
        }],
    }).encode()


def box(api, client, limit=10):
    return client.query_box(36, 38, 136, 138, start=START, end=END,
                            min_magnitude=5, limit=limit)


def test_module_exists():
    assert importlib.util.find_spec(MODULE) is not None


def test_count_first_and_typed_nulls(api, monkeypatch):
    calls = []
    client = api.USGSClient()

    def get(url):
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


def test_radius_parameters(api, monkeypatch):
    client = api.USGSClient()
    calls = []

    def get(url):
        calls.append(url)
        return b"0"

    monkeypatch.setattr(client, "_get", get)
    result = client.query_radius(37, 137, 20, start=START, end=END,
                                 min_magnitude=5, limit=10)
    params = parse_qs(urlparse(calls[0]).query)
    assert params["latitude"] == ["37"]
    assert params["maxradiuskm"] == ["20"]
    assert not result.events and len(calls) == 1
    assert result.raw is None  # No fabricated response when only count is fetched.


def test_count_guard_prevents_download(api, monkeypatch):
    client = api.USGSClient()
    monkeypatch.setattr(client, "_get", lambda url: b"11")
    with pytest.raises(api.TooManyEvents, match="Narrow"):
        box(api, client)


@pytest.mark.parametrize("limit", [0, 20001, True, 1.5])
def test_invalid_limit_never_fetches(api, limit):
    with pytest.raises(ValueError):
        box(api, api.USGSClient(), limit=limit)


@pytest.mark.parametrize("coords", [(38, 36, 136, 138), (-91, 38, 136, 138),
                                    (36, 38, float("nan"), 138)])
def test_invalid_box(api, coords):
    with pytest.raises(ValueError):
        api.USGSClient().query_box(*coords, start=START, end=END,
                                  min_magnitude=5, limit=10)


def test_invalid_time(api):
    with pytest.raises(ValueError):
        api.USGSClient().query_radius(37, 137, 20, start=END, end=START,
                                     min_magnitude=5, limit=10)


def test_parse_non_null_and_invalid_shape(api):
    rows = api.parse_geojson(synthetic_payload(12.5, 6.2), "https://example.invalid")
    assert rows[0].depth_km == 12.5 and rows[0].magnitude == 6.2
    with pytest.raises(api.ServiceError):
        api.parse_geojson(b'{"type":"FeatureCollection"}', "https://example.invalid")


def test_transport_caps_timeout_pause_and_headers(api, monkeypatch):
    client = api.USGSClient(max_bytes=8, timeout=7)
    pauses = []
    monkeypatch.setattr(api.time, "sleep", pauses.append)

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size):
            return b"123456789"[:size]

    def opened(request, timeout):
        assert request.get_method() == "GET"
        assert timeout == 7
        assert api.REPOSITORY_URL in request.get_header("User-agent")
        return Response()

    monkeypatch.setattr(client._opener, "open", opened)
    for _ in range(2):
        with pytest.raises(api.ServiceError, match="bytes"):
            client._get(api.SERVICE_URL + "count")
    assert pauses and pauses[0] >= 2


@pytest.mark.parametrize("status,body,error", [
    (400, b"Search is limited to 20000 events", "TooManyEvents"),
    (400, b"Bad parameter", "ServiceError"),
    (403, b"Forbidden", "AccessRefused"),
    (429, b"Rate limited", "AccessRefused"),
])
def test_http_errors_no_retry(api, monkeypatch, status, body, error):
    from io import BytesIO

    client = api.USGSClient()

    def opened(*args, **kwargs):
        raise HTTPError(api.SERVICE_URL, status, "error", {}, BytesIO(body))

    monkeypatch.setattr(client._opener, "open", opened)
    with pytest.raises(getattr(api, error)):
        client._get(api.SERVICE_URL + "count")


def test_manifest_reproduction(api):
    root = Path(__file__).parents[3] / "fixtures" / "geohazard"
    inputs = json.loads((root / "provenance_inputs.json").read_text())
    emitted = api.emit_manifest([(root / item["file"]).read_bytes()
                                 for item in inputs], inputs)
    assert emitted == (root / "manifest.json").read_bytes()


def test_recorded_response_schema(api):
    root = Path(__file__).parents[3] / "fixtures" / "geohazard"
    rows = api.parse_geojson((root / "usgs_recorded.geojson").read_bytes(),
                            "https://earthquake.usgs.gov/fdsnws/event/1/")
    assert len(rows) == 2
    assert {r.event_id for r in rows} == {"us6000m0xm", "us6000m0xl"}
    assert all(r.time_utc.utcoffset().total_seconds() == 0 for r in rows)


@pytest.mark.parametrize("radius", [-1, 20002, float("inf")])
def test_invalid_radius(api, radius):
    with pytest.raises(ValueError):
        api.USGSClient().query_radius(37, 137, radius, start=START, end=END,
                                     min_magnitude=5, limit=10)


def test_count_query_drift_is_bounded(api, monkeypatch):
    client = api.USGSClient()
    payload = json.loads(synthetic_payload())
    payload["features"] *= 2
    monkeypatch.setattr(client, "_get", lambda url: b"1" if "/count?" in url
                        else json.dumps(payload).encode())
    with pytest.raises(api.TooManyEvents):
        box(api, client, limit=1)


def test_challenge_response_stops(api, monkeypatch):
    client = api.USGSClient()

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size):
            return b"<!doctype html><html>challenge</html>"

    monkeypatch.setattr(client._opener, "open", lambda *a, **kw: Response())
    with pytest.raises(api.AccessRefused):
        client._get(api.SERVICE_URL + "count")


def test_nodata_204_after_count(api, monkeypatch):
    client = api.USGSClient()

    class Response:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size):
            return b""

    monkeypatch.setattr(client._opener, "open", lambda *a, **kw: Response())
    raw = client._get(api.SERVICE_URL + "query")
    assert api.parse_geojson(raw, api.SERVICE_URL) == ()
