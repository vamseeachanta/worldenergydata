"""Injected health-report outcomes, independently specified by HTTP standards.

RFC 9110 (2022), sections 15.3.1, 15.5.2, 15.5.4, 15.5.5, 15.5.11,
15.6.4; RFC 6585 (2012), section 4. Schema success uses the recorded CO-OPS
fixture; no numeric oceanographic acceptance criterion is introduced.
"""

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from worldenergydata.metocean.source_health import source_health
from worldenergydata.metocean.source_register import get_source

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures/metocean/endpoints/coops_station_day.json"
)
NOW = datetime(2026, 10, 22, tzinfo=timezone.utc)  # Synthetic report clock.


@pytest.mark.parametrize(
    "status,expected",
    [
        (200, "OK"),
        (401, "CREDENTIALS_REQUIRED"),
        (403, "CREDENTIALS_REQUIRED"),
        (404, "RETIRED"),
        (410, "RETIRED"),
        (429, "UNREACHABLE"),
        (503, "UNREACHABLE"),
        (302, "UNREACHABLE"),
    ],
)
def test_health_classification(status, expected, tmp_path):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(status, content=FIXTURE.read_bytes())
        )
    ) as http:
        report = source_health(
            http=http,
            user_agent="test application",
            now=lambda: NOW,
            register={"sources": [get_source("coops")]},
            json_path=tmp_path / "health.json",
            markdown_path=tmp_path / "health.md",
        )
    assert len(report) == 1
    row = report[0]
    assert row["source"] == "coops"
    assert row["status"] == expected
    assert row["last_checked"] == NOW.isoformat()
    assert row["terms_url"] == get_source("coops")["terms_url"]
    assert json.loads((tmp_path / "health.json").read_text())["sources"] == report
    assert f"| coops | {expected} |" in (tmp_path / "health.md").read_text()
    assert "Revision history" in (tmp_path / "health.md").read_text()


def test_account_sources_and_unconfigured_sources_make_no_requests():
    def forbidden(request):
        pytest.fail("unconfigured or account source attempted a request")

    with httpx.Client(transport=httpx.MockTransport(forbidden)) as http:
        report = source_health(
            http=http,
            user_agent="test application",
            now=lambda: NOW,
            register={"sources": [get_source("era5"), get_source("hycom")]},
        )
    assert [r["status"] for r in report] == ["CREDENTIALS_REQUIRED", "UNREACHABLE"]
    assert all(r["last_checked"] is None for r in report)
    assert "NOT_EVALUATED" in report[1]["detail"]


def test_legacy_retirement_does_not_mark_current_service_retired():
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("account request"))
    ) as http:
        report = source_health(
            http=http,
            user_agent="test application",
            register={"sources": [get_source("cmems")]},
        )
    assert report[0]["status"] == "CREDENTIALS_REQUIRED"


def test_transport_and_schema_errors_are_sanitized():
    def disconnected(request):
        raise httpx.ConnectError("private connection detail", request=request)

    for responder in [disconnected, lambda r: httpx.Response(200, text="private body")]:
        with httpx.Client(transport=httpx.MockTransport(responder)) as http:
            (row,) = source_health(
                http=http,
                user_agent="test application",
                register={"sources": [get_source("coops")]},
            )
        assert row["status"] == "UNREACHABLE"
        assert "private" not in row["detail"]


def test_unknown_probe_and_naive_clock_are_rejected():
    register = {"sources": [deepcopy(get_source("coops"))]}
    register["sources"][0]["health_url"] = "https://example.org/unregistered"
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("unknown URL"))
    ) as http:
        with pytest.raises(ValueError, match="registered"):
            source_health(http=http, user_agent="test application", register=register)
        with pytest.raises(ValueError, match="UTC"):
            source_health(
                http=http,
                user_agent="test application",
                now=lambda: datetime(2026, 10, 22),
            )


def test_reissued_report_preserves_revision_history(tmp_path):
    json_path, markdown_path = tmp_path / "health.json", tmp_path / "health.md"
    register = {"sources": [get_source("era5")]}
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("account request"))
    ) as http:
        for _ in range(2):
            source_health(
                http=http,
                user_agent="test application",
                register=register,
                now=lambda: NOW,
                json_path=json_path,
                markdown_path=markdown_path,
            )
    history = json.loads(json_path.read_text())["revision_history"]
    assert [row["revision"] for row in history] == [1, 2]
    assert f"| 1 | {NOW.isoformat()} |" in markdown_path.read_text()
    assert f"| 2 | {NOW.isoformat()} |" in markdown_path.read_text()


def test_unrelated_markdown_does_not_partially_replace_json(tmp_path):
    json_path, markdown_path = tmp_path / "health.json", tmp_path / "health.md"
    register = {"sources": [get_source("era5")]}
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("account request"))
    ) as http:
        source_health(
            http=http,
            user_agent="test application",
            register=register,
            now=lambda: NOW,
            json_path=json_path,
        )
        original = json_path.read_bytes()
        markdown_path.write_text("Unrelated document\n")
        with pytest.raises(ValueError, match="not a source-health report"):
            source_health(
                http=http,
                user_agent="test application",
                register=register,
                now=lambda: NOW,
                json_path=json_path,
                markdown_path=markdown_path,
            )
    assert json_path.read_bytes() == original
    assert markdown_path.read_text() == "Unrelated document\n"
