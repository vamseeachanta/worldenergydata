"""Worked source-day replay, expected values transcribed from publisher fixtures.

NDBC: 144 retained data lines, of which 75 are MM in WVHT, leaving 69 valid
heights. The first valid row chronologically is 00:10, 1.8 m; the last is
23:50, 0.9 m. CO-OPS: 240 six-minute rows (24 * 60 / 6 = 240), first 00:00,
0.035 m MLLW; last 23:54, 0.355 m MLLW. Row provenance is recorded alongside
fixtures. Counts describe these responses; they are not completeness limits.
"""

from datetime import date
from pathlib import Path

import httpx
import pytest

from worldenergydata.metocean.clients.endpoint_checks import EndpointError
from worldenergydata.metocean.station_day import fetch_station_day, summarize_day

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures/metocean/endpoints"


@pytest.mark.parametrize(
    "source,station,day,file,expected",
    [
        (
            "ndbc_realtime",
            "42001",
            date(2026, 10, 21),
            "ndbc_station_day.txt",
            {"rows": 144, "nonmissing": 69, "first_value": 1.8, "last_value": 0.9},
        ),
        (
            "coops",
            "9414290",
            date(2025, 1, 1),
            "coops_station_day.json",
            {"rows": 240, "nonmissing": 240, "first_value": 0.035, "last_value": 0.355},
        ),
    ],
)
def test_station_day_worked_example(source, station, day, file, expected):
    def respond(request):
        if source == "coops":
            assert request.url.params["units"] == "metric"
            assert request.url.params["time_zone"] == "gmt"
            assert request.url.params["datum"] == "MLLW"
            assert (
                request.url.params["begin_date"]
                == request.url.params["end_date"]
                == "20250101"
            )
        return httpx.Response(200, content=(FIXTURES / file).read_bytes())

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        rows = fetch_station_day(
            source, station, day, http=http, user_agent="test application"
        )
    answer = summarize_day(rows)
    for key, value in expected.items():
        assert answer[key] == value
    assert answer["date"] == day.isoformat()
    assert answer["station"] == station
    assert answer["unit"] == "m"
    if source == "coops":
        assert answer["datum"] == "MLLW"


def test_absent_day_is_not_an_empty_success():
    with (
        httpx.Client(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(
                    200, content=(FIXTURES / "ndbc_station_day.txt").read_bytes()
                )
            )
        ) as http,
        pytest.raises(EndpointError, match="not available"),
    ):
        fetch_station_day(
            "ndbc_realtime",
            "42001",
            date(2000, 1, 1),
            http=http,
            user_agent="test application",
        )


def test_station_id_in_the_ndbc_request_is_preserved():
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200, content=(FIXTURES / "ndbc_station_day.txt").read_bytes()
            )
        )
    ) as http:
        rows = fetch_station_day(
            "ndbc_realtime",
            "TEST",
            date(2026, 10, 21),
            http=http,
            user_agent="test application",
        )
    assert all(row.station == "TEST" for row in rows)


def test_coops_response_must_match_requested_station():
    with (
        httpx.Client(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(
                    200, content=(FIXTURES / "coops_station_day.json").read_bytes()
                )
            )
        ) as http,
        pytest.raises(EndpointError, match="station"),
    ):
        fetch_station_day(
            "coops",
            "0000000",
            date(2025, 1, 1),
            http=http,
            user_agent="test application",
        )


@pytest.mark.parametrize("station", ["../bad", "", "with space", "ø"])
def test_invalid_input_makes_no_request(station):
    with pytest.raises(ValueError, match="station"):
        fetch_station_day(
            "ndbc_realtime",
            station,
            date(2026, 10, 21),
            http=None,
            user_agent="test application",
        )


def test_summary_rejects_empty_or_mixed_days():
    from worldenergydata.metocean.clients.endpoint_checks import parse_sample

    with pytest.raises(ValueError, match="empty"):
        summarize_day([])
    ndbc = parse_sample(
        "ndbc_realtime", (FIXTURES / "ndbc_station_day.txt").read_bytes()
    )
    coops = parse_sample("coops", (FIXTURES / "coops_station_day.json").read_bytes())
    with pytest.raises(ValueError, match="single"):
        summarize_day(ndbc + coops)


def test_documented_example_matches_committed_table(tmp_path):
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [
            sys.executable,
            str(root / "examples/metocean/endpoint_station_day.py"),
            "--output",
            str(tmp_path / "example.csv"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert not result.stdout
    assert (tmp_path / "example.csv").read_bytes() == (
        root / "examples/metocean/endpoint_station_day.csv"
    ).read_bytes()
