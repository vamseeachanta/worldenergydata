"""Local stub collection cases; no network access is needed."""

import socket
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar
from urllib.error import HTTPError

import pandas as pd
import pytest

from worldenergydata.modules.state_regulators.colorado_ecmc.facility_detail import (
    classify_facility_detail_pressures,
)
from worldenergydata.modules.state_regulators.colorado_ecmc.facility_detail_candidates import (
    build_form5a_pressure_candidates,
)
from worldenergydata.modules.state_regulators.colorado_ecmc.facility_detail_ingest import (
    fetch_facility_detail_pages,
)
from worldenergydata.modules.state_regulators.colorado_ecmc.facility_detail_pipeline import (
    parse_facility_detail_pages,
)
from worldenergydata.modules.state_regulators.fetch import (
    BudgetExceeded,
    TermsDenied,
    client,
)


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("Only stub responses are permitted")

    monkeypatch.setattr(socket, "create_connection", refused)


def settings(tmp_path, **overrides):
    return {
        "storage": {"base_dir": str(tmp_path)},
        "facility_detail": {
            "base_url": "https://records.example/page.aspx",
            "user_agent": "offline-test",
            "terms_checks": [
                {
                    "origin": "https://records.example",
                    "terms_url": "https://records.example/terms",
                    "checked_at": "2020-01-01T00:00:00+00:00",
                    "bulk_allowed": True,
                }
            ],
            **overrides,
        },
    }


def source_rows():
    return pd.DataFrame(
        [
            {"api_fragment": "12300001", "facility_id": "1"},
            {"api_fragment": "12300002", "facility_id": "2"},
        ]
    )


def stub_transport(monkeypatch, bodies, *, status=200):
    calls = []

    class Response:
        headers: ClassVar = {"Content-Type": "text/html"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def getcode(self):
            return status  # RFC 9110 (2022), section 15.3.1: 200 is OK.

        def read(self, size):
            return bodies.pop(0)

    def open_response(request, timeout):
        calls.append(request.full_url)
        return Response()

    monkeypatch.setattr(
        client, "build_opener", lambda *args: SimpleNamespace(open=open_response)
    )
    return calls


def test_shared_permission_blocks_collection(tmp_path, monkeypatch):
    """With no recorded permission, the independent expected request count is zero."""
    calls = stub_transport(monkeypatch, [])
    with pytest.raises(TermsDenied):
        fetch_facility_detail_pages(source_rows(), settings(tmp_path, terms_checks=[]))
    assert calls == []


def test_shared_default_delay_budget_and_cache(tmp_path, monkeypatch):
    """Shared FetchConfig in policy.py specifies a 2-second fallback.

    Hand timeline: first reservation at t=0, next at t=2; cache-only rerun
    adds no reservations. An explicit one-request budget blocks row two.
    """
    bodies = [b"<html>API# 05-123-00001</html>", b"<html>API# 05-123-00002</html>"]
    calls = stub_transport(monkeypatch, bodies)
    now, waits = [0.0], []

    def sleep(delay):
        waits.append(delay)
        now[0] += delay

    config = settings(tmp_path)
    result = fetch_facility_detail_pages(
        source_rows(), config, clock=lambda: now[0], sleep=sleep
    )
    assert len(result["fetched"]) == 2
    assert waits == [2.0]
    fetch_facility_detail_pages(
        source_rows(), config, clock=lambda: now[0], sleep=sleep
    )
    assert len(calls) == 2
    other = settings(tmp_path / "limited", fetch={"budget_requests": 1})
    bodies.extend([b"<html>API# 05-123-00001</html>"])
    with pytest.raises(BudgetExceeded):
        fetch_facility_detail_pages(
            source_rows(), other, clock=lambda: now[0], sleep=sleep
        )


@pytest.mark.parametrize(
    "body,status,keep",
    [
        (b"<html>API# 05-123-00001 FacilityID: 1</html>", "matched", False),
        (b"<html>API# 05-123-00002 FacilityID: 2</html>", "identity_mismatch", False),
        (b"<html>no identity</html>", "identity_unverified", False),
        (b"<html>API# 05-123-00002 FacilityID: 2</html>", "identity_mismatch", True),
        (b"<html>API# 05-123-00002</html>", "identity_mismatch", "false"),
        (b"<html>no identity</html>", "identity_unverified", True),
    ],
)
def test_default_identity_policy(tmp_path, monkeypatch, body, status, keep):
    """Compare literal requested/rendered identifiers by equality, with no inference.

    The absent identifier cannot prove a match. Explicit retention keeps its flag.
    """
    stub_transport(monkeypatch, [body])
    result = fetch_facility_detail_pages(
        source_rows().head(1), settings(tmp_path, keep_identity_mismatch=keep)
    )
    accepted = status == "matched" or keep is True
    row = result["fetched" if accepted else "failed"][0]
    assert row["identity_status"] == status
    assert bool(result["fetched"]) == accepted


def test_recorded_fixture_identity_run(tmp_path, monkeypatch):
    """Recorded fixture API and facility are visible in its opening table.

    Hand count: of three requested pairs, one matches, one has a different API,
    and one has a different facility. Default: one accepted, two rejected.
    Opt-in: three retained, two flagged. There are seven literal measure rows
    per retained page; therefore the default parsed count is seven.
    """
    payload = Path(
        "tests/fixtures/colorado_ecmc/facility_detail_12339345_excerpt.html"
    ).read_bytes()
    calls = stub_transport(monkeypatch, [payload, payload])
    rows = pd.DataFrame(
        [
            {"api_fragment": "12339345", "facility_id": "436953"},
            {"api_fragment": "12300001", "facility_id": "436953"},
            {"api_fragment": "12339345", "facility_id": "999999"},
        ]
    )
    now = [0.0]

    def sleep(delay):
        now[0] += delay

    config = settings(tmp_path)
    result = fetch_facility_detail_pages(
        rows, config, clock=lambda: now[0], sleep=sleep
    )
    assert [row["identity_status"] for row in result["fetched"]] == ["matched"]
    assert [row["identity_status"] for row in result["failed"]] == [
        "identity_mismatch"
    ] * 2
    parsed, quality = parse_facility_detail_pages(result)
    assert quality["parsed_initial_test_rows"] == 7
    assert parsed["identity_status"].eq("matched").all()
    config["facility_detail"]["keep_identity_mismatch"] = True
    kept = fetch_facility_detail_pages(rows, config, clock=lambda: now[0], sleep=sleep)
    assert [row["identity_status"] for row in kept["fetched"]] == [
        "matched",
        "identity_mismatch",
        "identity_mismatch",
    ]
    assert len(calls) == 2
    retained, _ = parse_facility_detail_pages(kept)
    candidates, _ = build_form5a_pressure_candidates(
        classify_facility_detail_pressures(retained),
        {"pressure_observations": {"atmospheric_psi": 0}},
    )
    # Synthetic zero offset is an input: p + 0 = p; no physical correction claimed.
    assert set(candidates["identity_status"]) == {"matched", "identity_mismatch"}
    assert candidates["api12_status"].eq("NOT_EVALUATED").all()
    # Two pressure measures per page: 3 * 2 = 6, including 2 * 2 = 4 flagged.
    assert len(candidates) == 6
    assert candidates["identity_status"].eq("identity_mismatch").sum() == 4


def test_invalid_facility_bytes_are_not_silently_decoded(tmp_path, monkeypatch):
    """FF is not UTF-8: collection raises rather than deleting the invalid byte."""
    stub_transport(monkeypatch, [b"<html>API# 05-123-00001\xff</html>"])
    with pytest.raises(UnicodeDecodeError):
        fetch_facility_detail_pages(source_rows().head(1), settings(tmp_path))


def test_shared_retry_records_attempts(tmp_path, monkeypatch):
    """Literal Retry-After=3 requires t=0 to t=3 before the successful retry.

    RFC 9110 (2022), section 10.2.3 defines delay-seconds. Shared retry semantics
    are also exercised in test_polite_fetch.py::test_429_retry_cache_and_provenance.
    One failed attempt followed by success means retry_count=1.
    """
    now, waits, calls = [0.0], [], []

    def request(self, url):
        calls.append(url)
        if len(calls) == 1:
            raise HTTPError(url, 429, "wait", {"Retry-After": "3"}, None)
        return b"<html>API# 05-123-00001</html>", {"Content-Type": "text/html"}

    def sleep(delay):
        waits.append(delay)
        now[0] += delay

    monkeypatch.setattr(client.Fetcher, "_request", request)
    result = fetch_facility_detail_pages(
        source_rows().head(1),
        settings(tmp_path, max_retries=1),
        clock=lambda: now[0],
        sleep=sleep,
    )
    assert waits == [3.0]
    assert result["fetched"][0]["retry_count"] == 1


def test_zero_delay_rejected_before_request(tmp_path, monkeypatch):
    """The shared positive-pacing contract rejects a caller's zero interval."""
    calls = stub_transport(monkeypatch, [])
    with pytest.raises(ValueError, match="positive"):
        fetch_facility_detail_pages(
            source_rows(), settings(tmp_path, request_delay_seconds=0)
        )
    assert calls == []


def test_non_ok_transport_response_not_cached(tmp_path, monkeypatch):
    """RFC 9110 (2022), sections 15.3.1 and 15.3.5: 204 is not 200 OK.

    Deliberately inconsistent stub bytes prove status alone rejects reuse.
    """
    stub_transport(monkeypatch, [b"<html>API# 05-123-00001</html>"], status=204)
    with pytest.raises(ValueError, match="non-200"):
        fetch_facility_detail_pages(source_rows().head(1), settings(tmp_path))
    cache = tmp_path / "raw" / "facility_detail" / "cache"
    assert not list((cache / "objects").iterdir())
    assert not list((cache / "records").iterdir())
