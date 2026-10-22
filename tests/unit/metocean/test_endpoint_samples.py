"""Replays of recorded publisher data; expected values are literal source rows.

Provenance and digests: tests/fixtures/metocean/endpoints/provenance.json.
NDBC's first retained row has WVHT=0.9 m at 2026-10-21 23:50 UTC.
CO-OPS's first row is 0.035 m MLLW at 2025-01-01 00:00 GMT.
ERDDAP's first row is M3, WaveHeight=2.227 meters, 2025-12-31T00:00Z.
MET's first row has sea_surface_wave_height=2.9 m at 2026-10-22T16:00Z.
Values are transcribed independently of the parser; no fitted equations apply.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from worldenergydata.metocean.clients.endpoint_checks import (
    EndpointError,
    parse_sample,
    probe_sample,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures/metocean/endpoints"
CASES = [
    ("ndbc_realtime", "ndbc_station_day.txt", 0.9, "2026-10-21T23:50:00+00:00"),
    ("coops", "coops_station_day.json", 0.035, "2025-01-01T00:00:00+00:00"),
    ("irish_weather_buoys", "erddap_sample.json", 2.227, "2025-12-31T00:00:00+00:00"),
    ("met_norway", "met_sample.json", 2.9, "2026-10-22T16:00:00+00:00"),
]


def test_fixture_provenance_and_integrity():
    for entry in json.loads((FIXTURES / "provenance.json").read_text())["samples"]:
        assert entry["url"].startswith("https://")
        assert entry["http_status"] == 200  # RFC 9110 (2022), section 15.3.1.
        assert datetime.fromisoformat(entry["fetched_at"]).utcoffset() is not None
        assert (
            hashlib.sha256((FIXTURES / entry["file"]).read_bytes()).hexdigest()
            == entry["sha256"]
        )


@pytest.mark.parametrize("source,filename,value,timestamp", CASES)
def test_publisher_replay(source, filename, value, timestamp):
    samples = parse_sample(source, (FIXTURES / filename).read_bytes())
    assert samples[0].value == value
    assert samples[0].timestamp.isoformat() == timestamp
    assert samples[0].unit == "m"
    assert all(s.timestamp.utcoffset() == timezone.utc.utcoffset(None) for s in samples)


@pytest.mark.parametrize("source,filename,value,timestamp", CASES)
def test_live_contract_uses_same_parser(source, filename, value, timestamp):
    def respond(request):
        assert (
            request.headers["User-Agent"]
            == "audit-example (contact supplied by caller)"
        )
        assert "authorization" not in request.headers
        return httpx.Response(200, content=(FIXTURES / filename).read_bytes())

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        assert probe_sample(
            source, http=http, user_agent="audit-example (contact supplied by caller)"
        )


@pytest.mark.parametrize("source,filename,value,timestamp", CASES)
def test_html_is_not_a_healthy_data_endpoint(source, filename, value, timestamp):
    with pytest.raises(EndpointError, match=source):
        parse_sample(source, b"<html>removed endpoint</html>")


@pytest.mark.parametrize("status", [301, 401, 403, 404, 410, 429, 503])
def test_failed_endpoint_is_named_without_echoing_body(status):
    """RFC 9110 (2022), sections 15.4-15.6; RFC 6585 (2012), section 4."""
    with (
        httpx.Client(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(status, text="private detail")
            )
        ) as http,
        pytest.raises(EndpointError, match="coops") as error,
    ):
        probe_sample("coops", http=http, user_agent="test application")
    assert "private detail" not in str(error.value)
    if status in {404, 410}:
        assert "retired or moved" in str(error.value)


@pytest.mark.parametrize(
    "source,filename,mutate",
    [
        ("coops", "coops_station_day.json", lambda p: p.update(data=[])),
        (
            "irish_weather_buoys",
            "erddap_sample.json",
            lambda p: p["table"]["columnUnits"].__setitem__(2, "feet"),
        ),
        (
            "irish_weather_buoys",
            "erddap_sample.json",
            lambda p: p["table"]["rows"][0].__setitem__(0, "2025-12-31T00:00:00"),
        ),
        (
            "met_norway",
            "met_sample.json",
            lambda p: p["properties"]["meta"]["units"].update(
                sea_surface_wave_height="ft"
            ),
        ),
        (
            "met_norway",
            "met_sample.json",
            lambda p: p["properties"]["timeseries"][0].update(
                time="2026-10-22T16:00:00+01:00"
            ),
        ),
    ],
)
def test_changed_schema_units_or_zone_fail(source, filename, mutate):
    payload = json.loads((FIXTURES / filename).read_text())
    mutate(payload)
    with pytest.raises(EndpointError, match="schema"):
        parse_sample(source, json.dumps(payload).encode())


def test_ndbc_changed_columns_or_units_fail():
    content = (FIXTURES / "ndbc_station_day.txt").read_bytes()
    for altered in [
        content.replace(b"WVHT", b"OLDH"),
        content.replace(b"m   sec", b"ft  sec"),
    ]:
        with pytest.raises(EndpointError, match="schema"):
            parse_sample("ndbc_realtime", altered)


@pytest.mark.parametrize("change", ["units=english", "time_zone=lst", "datum=MSL"])
def test_coops_request_cannot_be_mislabelled_metric_utc_mllw(change):
    from worldenergydata.metocean.source_register import get_source

    url = get_source("coops")["health_url"]
    key = change.split("=")[0]
    original = {
        "units": "units=metric",
        "time_zone": "time_zone=gmt",
        "datum": "datum=MLLW",
    }[key]
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda r: pytest.fail("invalid request sent"))
        ) as http,
        pytest.raises(ValueError, match="metric"),
    ):
        probe_sample(
            "coops",
            http=http,
            user_agent="test application",
            url=url.replace(original, change),
        )
