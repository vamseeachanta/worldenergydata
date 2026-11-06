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
from worldenergydata.metocean.source_register import get_source, load_register

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
    assert (
        json.loads((tmp_path / "health.json").read_text(encoding="utf-8"))["sources"]
        == report
    )
    markdown = (tmp_path / "health.md").read_text(encoding="utf-8")
    assert f"| coops | {expected} |" in markdown
    assert "Revision history" in markdown


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
    assert [r["status"] for r in report] == ["CREDENTIALS_REQUIRED", "NOT_EVALUATED"]
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


@pytest.mark.parametrize(
    "value,timestamp,expected",
    [
        ("", "2025-01-01 00:00", "OK"),
        (None, "2025-01-01 00:00", "OK"),
        ("", "invalid timestamp", "UNREACHABLE"),
        ("not numeric", "2025-01-01 00:00", "UNREACHABLE"),
    ],
)
def test_health_distinguishes_missing_readings_from_malformed_data(
    value, timestamp, expected
):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["data"][0].update(v=value, t=timestamp)
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload))
    ) as http:
        (row,) = source_health(
            http=http,
            user_agent="test application",
            register={"sources": [get_source("coops")]},
        )
    assert row["status"] == expected


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
    history = json.loads(json_path.read_text(encoding="utf-8"))["revision_history"]
    assert [row["revision"] for row in history] == [1, 2]
    assert f"| 1 | {NOW.isoformat()} |" in markdown_path.read_text(encoding="utf-8")
    assert f"| 2 | {NOW.isoformat()} |" in markdown_path.read_text(encoding="utf-8")


def test_unrelated_json_does_not_replace_either_output(tmp_path):
    json_path, markdown_path = tmp_path / "health.json", tmp_path / "health.md"
    original = (
        b'{"summary":"Unrelated report","revision_history":[],"retained_data":[1]}\n'
    )
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("account request"))
    ) as http:
        source_health(
            http=http,
            user_agent="test application",
            register={"sources": [get_source("era5")]},
            now=lambda: NOW,
            markdown_path=markdown_path,
        )
        original_markdown = markdown_path.read_bytes()
        json_path.write_bytes(original)
        with pytest.raises(ValueError, match="source-health report"):
            source_health(
                http=http,
                user_agent="test application",
                register={"sources": [get_source("era5")]},
                now=lambda: NOW,
                json_path=json_path,
                markdown_path=markdown_path,
            )
    assert json_path.read_bytes() == original
    assert markdown_path.read_bytes() == original_markdown


def test_legacy_report_is_validated_and_keeps_its_history(tmp_path):
    json_path = tmp_path / "health.json"
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
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert payload.pop("report_type") == "metocean_source_health"
        history = deepcopy(payload["revision_history"])
        json_path.write_text(json.dumps(payload), encoding="utf-8", newline="\n")
        source_health(
            http=http,
            user_agent="test application",
            register=register,
            now=lambda: NOW,
            json_path=json_path,
        )
    updated = json.loads(json_path.read_text(encoding="utf-8"))
    assert updated["report_type"] == "metocean_source_health"
    assert updated["revision_history"][:-1] == history
    assert updated["revision_history"][-1]["revision"] == 2


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(report_type="unrelated"),
        lambda p: p.update(retained_data=[1]),
        lambda p: p.pop("summary"),
        lambda p: p.update(summary="Unrelated report"),
        lambda p: p.update(generated_at="invalid timestamp"),
        lambda p: p.update(generated_at="2026-10-22T00:00:00"),
        lambda p: p.update(revision_history=[]),
        lambda p: p.update(revision_history=["invalid"]),
        lambda p: p["revision_history"][0].update(revision=True),
        lambda p: p["revision_history"][0].update(revision=2),
        lambda p: p["revision_history"][0].update(date="invalid timestamp"),
        lambda p: p["revision_history"][0].update(date="2026-10-21T00:00:00Z"),
        lambda p: p["revision_history"][0].pop("change"),
        lambda p: p["revision_history"][0].update(change=""),
        lambda p: p["revision_history"][0].update(retained_data=[1]),
        lambda p: p.update(sources={}),
        lambda p: p.update(sources=["invalid"]),
        lambda p: p["sources"][0].pop("terms_url"),
        lambda p: p["sources"][0].update(terms_url="invalid URL"),
        lambda p: p["sources"][0].update(source=""),
        lambda p: p["sources"].append(deepcopy(p["sources"][0])),
        lambda p: p["sources"][0].update(status="UNKNOWN"),
        lambda p: p["sources"][0].update(last_checked="invalid timestamp"),
        lambda p: p["sources"][0].update(detail=None),
        lambda p: p["sources"][0].update(retained_data=[1]),
    ],
)
def test_malformed_json_report_does_not_replace_either_output(tmp_path, mutate):
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
            markdown_path=markdown_path,
        )
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        mutate(payload)
        json_path.write_text(json.dumps(payload) + "\n", encoding="utf-8", newline="\n")
        original_json, original_markdown = (
            json_path.read_bytes(),
            markdown_path.read_bytes(),
        )
        with pytest.raises(ValueError, match="source-health report"):
            source_health(
                http=http,
                user_agent="test application",
                register=register,
                now=lambda: NOW,
                json_path=json_path,
                markdown_path=markdown_path,
            )
    assert json_path.read_bytes() == original_json
    assert markdown_path.read_bytes() == original_markdown


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
        markdown_path.write_text("Unrelated document\n", encoding="utf-8", newline="\n")
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
    assert markdown_path.read_text(encoding="utf-8") == "Unrelated document\n"


@pytest.mark.parametrize(
    "identifier",
    [
        "canada_gdwps",
        "brazil_pnboia",
        "india_incois",
        "pirata",
        "ncep_wave_hindcast",
        "ndbc_currents",
        "nhc_best_track",
    ],
)
def test_unconfirmed_access_does_not_claim_credentials_are_required(identifier):
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("unconfirmed request"))
    ) as http:
        (row,) = source_health(
            http=http,
            user_agent="test application",
            register={"sources": [get_source(identifier)]},
        )
    assert row["status"] == "NOT_EVALUATED"
    assert row["last_checked"] is None
    assert "anonymous download access not confirmed" in row["detail"]


def test_anonymous_sources_without_probes_are_not_reported_as_failures():
    sources = [
        source
        for source in load_register()["sources"]
        if source["auth_requirement"] == "none" and not source.get("health_url")
    ]
    assert sources
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("unconfigured request"))
    ) as http:
        report = source_health(
            http=http, user_agent="test application", register={"sources": sources}
        )
    assert all(row["status"] == "NOT_EVALUATED" for row in report)
    assert all(row["last_checked"] is None for row in report)


@pytest.mark.parametrize("identifier", ["australia_auswave", "era5", "cmems"])
def test_documented_account_status_states_its_evidence(identifier):
    source = get_source(identifier)
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("account request"))
    ) as http:
        (row,) = source_health(
            http=http, user_agent="test application", register={"sources": [source]}
        )
    assert row["status"] == "CREDENTIALS_REQUIRED"
    assert row["last_checked"] is None
    assert source["auth_evidence_url"] in row["detail"]


@pytest.mark.parametrize(
    "identifier", ["india_incois", "ndbc_currents", "indonesia_bmkg", "nhc_best_track"]
)
def test_null_terms_are_preserved_and_rendered_with_evidence(identifier, tmp_path):
    source = deepcopy(get_source(identifier))
    json_path, markdown_path = tmp_path / "health.json", tmp_path / "health.md"
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("unconfirmed request"))
    ) as http:
        for _ in range(2):
            (row,) = source_health(
                http=http,
                user_agent="test application",
                register={"sources": [source]},
                now=lambda: NOW,
                json_path=json_path,
                markdown_path=markdown_path,
            )
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["sources"] == [row]
    assert row["terms_url"] is None
    assert row["terms_evaluation"] == source["terms_evaluation"]
    assert [revision["revision"] for revision in payload["revision_history"]] == [1, 2]
    rendered = markdown_path.read_text(encoding="utf-8")
    assert "| NOT_EVALUATED; no terms statement found |" in rendered
    assert "| None |" not in rendered


@pytest.mark.parametrize(
    "evidence",
    [
        None,
        "",
        "confirmed",
        "NOT_EVALUATED; no confirmed reuse grant",
        "NOT_EVALUATEDx",
    ],
)
def test_null_terms_without_report_evidence_preserve_both_outputs(evidence, tmp_path):
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
            markdown_path=markdown_path,
        )
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        payload["sources"][0]["terms_url"] = None
        if evidence is not None:
            payload["sources"][0]["terms_evaluation"] = evidence
        json_path.write_text(json.dumps(payload) + "\n", encoding="utf-8", newline="\n")
        original_json = json_path.read_bytes()
        original_markdown = markdown_path.read_bytes()
        with pytest.raises(ValueError, match="source-health report"):
            source_health(
                http=http,
                user_agent="test application",
                register=register,
                now=lambda: NOW,
                json_path=json_path,
                markdown_path=markdown_path,
            )
    assert json_path.read_bytes() == original_json
    assert markdown_path.read_bytes() == original_markdown
