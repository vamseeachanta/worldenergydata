"""Offline behavioral checks; only the local fake server receives requests."""

import json
import shutil
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any, cast

import pytest

from worldenergydata.modules.state_regulators.fetch import (
    BudgetExceeded,
    FetchConfig,
    Fetcher,
    TermsCheck,
    TermsDenied,
    UnreachableTarget,
    choose_route,
    header_delay,
)

from .fetch_cases import (
    USER_AGENT,
    Clock,
)
from .fetch_cases import (
    case_cached_permission_survives_withdrawal as test_cached_permission_survives_withdrawal,
)
from .fetch_cases import (
    case_corrupt_progress_is_preserved as test_corrupt_progress_is_preserved,
)
from .fetch_cases import (
    case_corrupt_url_record_is_preserved as test_corrupt_url_record_is_preserved,
)
from .fetch_cases import (
    case_invalid_caps_are_rejected as test_invalid_caps_are_rejected,
)
from .fetch_cases import (
    case_invalid_retry_values_do_not_crash as test_invalid_retry_values_do_not_crash,
)
from .fetch_cases import (
    case_long_wait_is_persisted_and_refused as test_long_wait_is_persisted_and_refused,
)
from .fetch_cases import case_response_cap as test_response_cap
from .fetch_cases import case_wait_below_cap_proceeds as test_wait_below_cap_proceeds
from .fetch_cases import (
    make_fetcher,
    server,
)

__all__ = [
    "server",
    "test_cached_permission_survives_withdrawal",
    "test_corrupt_progress_is_preserved",
    "test_corrupt_url_record_is_preserved",
    "test_invalid_caps_are_rejected",
    "test_invalid_retry_values_do_not_crash",
    "test_long_wait_is_persisted_and_refused",
    "test_response_cap",
    "test_wait_below_cap_proceeds",
]


@pytest.fixture(autouse=True)
def clean_case_directory(tmp_path: Any) -> Iterator[None]:
    yield
    shutil.rmtree(tmp_path)


def test_recorded_vendor_budget_drives_delay() -> None:
    headers = {"x-dotratelimit-toks-max": "2389/10000", "x-dotrequest-cost": "56.00"}
    assert header_delay(headers, 0.1, 60) >= 60 * 56 / 2389


@pytest.mark.parametrize(
    "headers,expected",
    [
        ({"RateLimit-Remaining": "0", "RateLimit-Reset": "30"}, 30),
        ({"RateLimit-Remaining": "3", "RateLimit-Reset": "30"}, 10),
        ({"Retry-After": "7"}, 7),
        ({"RateLimit-Remaining": "bad", "RateLimit-Reset": "NaN"}, 2),
        ({}, 2),
    ],
)
def test_header_delay(headers: Any, expected: Any) -> None:
    assert header_delay(headers, 2, 60) == expected


def test_retry_after_http_date() -> None:
    now = datetime(2026, 10, 11, tzinfo=timezone.utc)
    assert (
        header_delay({"Retry-After": "Sun, 11 Oct 2026 00:00:09 GMT"}, 2, 60, now) == 9
    )


def test_429_retry_cache_and_provenance(tmp_path: Any, server: Any) -> None:
    origin, state = server
    clock = Clock()
    state["responses"] = [(429, {"Retry-After": "7"}, b"wait"), (200, {}, b"data")]
    fetcher = make_fetcher(tmp_path, origin, clock)
    result = fetcher.fetch(origin + "/records")
    assert len(state["requests"]) == 2
    assert clock.waits == [7]
    assert result.path.read_bytes() == b"data"
    assert result.metadata["size_bytes"] == 4
    assert len(result.metadata["sha256"]) == 64
    offset = datetime.fromisoformat(result.metadata["fetched_at"]).utcoffset()
    assert offset is not None and offset.total_seconds() == 0
    assert result.metadata["response_headers"]["Server"]
    assert USER_AGENT in state["headers"][0]["User-Agent"]
    assert fetcher.fetch(origin + "/records").cached
    assert len(state["requests"]) == 2


def test_server_headers_pace_next_request(tmp_path: Any, server: Any) -> None:
    origin, state = server
    clock = Clock()
    state["responses"] = [
        (200, {"RateLimit-Remaining": "1", "RateLimit-Reset": "12"}, b"a")
    ]
    fetcher = make_fetcher(tmp_path, origin, clock)
    fetcher.run([origin + "/a", origin + "/b"])
    assert clock.waits == [12]


def test_resume_after_interrupt_uses_retained_objects(
    tmp_path: Any, server: Any
) -> None:
    origin, state = server
    clock = Clock()
    fetcher = make_fetcher(tmp_path, origin, clock)
    urls = [origin + "/a", origin + "/b"]

    def interrupted() -> Iterator[str]:
        yield urls[0]
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        fetcher.run(interrupted())
    resumed = make_fetcher(tmp_path, origin, clock)
    resumed.run(urls)
    assert state["requests"] == ["/a", "/b"]
    assert set(
        json.loads((tmp_path / "progress.json").read_text())["completed"]
    ) == set(urls)


def test_per_host_budget_survives_restart_and_counts_retries(
    tmp_path: Any, server: Any
) -> None:
    """Restart refuses a retained window wait above the configured sleep cap."""
    origin, state = server
    clock = Clock()
    state["responses"] = [(429, {"Retry-After": "1"}, b"wait")]
    fetcher = make_fetcher(
        tmp_path, origin, clock, budget_requests=1, max_sleep_seconds=10
    )
    with pytest.raises(BudgetExceeded):
        fetcher.fetch(origin + "/a")
    resumed = make_fetcher(
        tmp_path, origin, clock, budget_requests=1, max_sleep_seconds=10
    )
    with pytest.raises(BudgetExceeded):
        resumed.fetch(origin + "/b")
    assert state["requests"] == ["/a"]
    clock.now += 60
    resumed.fetch(origin + "/b")
    assert state["requests"] == ["/a", "/b"]


def test_terms_refusal_precedes_any_network(tmp_path: Any, server: Any) -> None:
    origin, state = server
    fetcher = Fetcher(
        FetchConfig(
            tmp_path,
            USER_AGENT,
        ),
        [],
    )
    with pytest.raises(TermsDenied):
        fetcher.run([origin + "/a"])
    assert state["requests"] == []


def test_dry_run_deduplicates_and_subtracts_cache(tmp_path: Any, server: Any) -> None:
    origin, state = server
    clock = Clock()
    fetcher = make_fetcher(tmp_path, origin, clock)
    fetcher.fetch(origin + "/a")
    report = fetcher.run([origin + "/a", origin + "/b", origin + "/b"], dry_run=True)
    assert isinstance(report, dict)
    assert report["projected_requests"] == 1
    assert report["estimated_seconds"] >= 2
    assert report["maximum_attempts"] == 3
    assert len(state["requests"]) == 1


def test_unreachable_preflight_stops_before_second_url(
    tmp_path: Any, monkeypatch: Any
) -> None:
    import socket

    def unreachable(*args: Any, **kwargs: Any) -> None:
        raise socket.gaierror("name lookup failed")

    monkeypatch.setattr(socket, "getaddrinfo", unreachable)
    clock = Clock()
    fetcher = make_fetcher(tmp_path, "https://unreachable.invalid", clock)
    with pytest.raises(UnreachableTarget, match="name-resolution") as error:
        fetcher.run(["https://unreachable.invalid/a", "https://unreachable.invalid/b"])
    assert "machine=" in str(error.value)
    assert len(fetcher.store.state["hosts"]) == 1


def test_corrupt_cache_refuses_to_return_payload(tmp_path: Any, server: Any) -> None:
    origin, state = server
    fetcher = make_fetcher(tmp_path, origin, Clock())
    result = fetcher.fetch(origin + "/a")
    result.path.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="integrity"):
        fetcher.fetch(origin + "/a")
    assert len(state["requests"]) == 1


def test_same_bytes_keep_each_urls_provenance(tmp_path: Any, server: Any) -> None:
    origin, state = server
    fetcher = make_fetcher(tmp_path, origin, Clock())
    results = fetcher.run([origin + "/a", origin + "/b"])
    assert isinstance(results, list)
    a, b = results
    assert a.path == b.path
    assert a.metadata["url"] != b.metadata["url"]


@pytest.mark.parametrize("has_bulk", [False, True])
def test_bulk_preference_and_crawl_audit(
    caplog: Any, capsys: Any, has_bulk: bool
) -> None:
    bulk = "https://records.example.org/wells.zip?key=SYNTHETIC_BULK_MARKER"
    crawl = "https://crawl.example.org/search?key=SYNTHETIC_CRAWL_MARKER"
    routes = [bulk] if has_bulk else []
    if has_bulk:
        assert choose_route(routes, crawl) == bulk
        assert not caplog.records
    with caplog.at_level("WARNING"):
        assert choose_route(routes, crawl, use_crawl=has_bulk) == crawl
    assert len(caplog.records) == 1
    bulk_origins = ["https://records.example.org:443"] if has_bulk else []
    assert caplog.records[0].getMessage() == (
        "crawl selected: https://crawl.example.org:443; "
        f"available official bulk routes: {bulk_origins}"
    )
    captured = capsys.readouterr()
    output = caplog.text + captured.out + captured.err
    for value in (
        "SYNTHETIC_BULK_MARKER",
        "SYNTHETIC_CRAWL_MARKER",
        "/search",
        "/wells.zip",
    ):
        assert value not in output


def test_redirect_is_not_followed(tmp_path: Any, server: Any) -> None:
    from urllib.error import HTTPError

    origin, state = server
    state["responses"] = [(302, {"Location": origin + "/other"}, b"")]
    fetcher = make_fetcher(tmp_path, origin, Clock())
    with pytest.raises(HTTPError):
        fetcher.fetch(origin + "/a")
    assert state["requests"] == ["/a"]


def test_required_configuration(monkeypatch: Any) -> None:
    monkeypatch.delenv("STATE_FETCH_CACHE_ROOT", raising=False)
    with pytest.raises(ValueError, match="cache"):
        FetchConfig.from_env(user_agent=USER_AGENT)
    with pytest.raises(ValueError, match="User-Agent"):
        FetchConfig("cache", "")


def test_cache_write_error_is_not_reported_as_network_failure(
    tmp_path: Any, server: Any, monkeypatch: Any
) -> None:
    origin, state = server
    fetcher = make_fetcher(tmp_path, origin, Clock())

    def disk_failure(*args: Any, **kwargs: Any) -> None:
        raise OSError("storage unavailable")

    monkeypatch.setattr(fetcher.store, "put", disk_failure)
    with pytest.raises(OSError, match="storage unavailable"):
        fetcher.fetch(origin + "/a")
    assert state["requests"] == ["/a"]


def test_permission_record_is_retained_with_fetch(tmp_path: Any, server: Any) -> None:
    origin, state = server
    fetcher = make_fetcher(tmp_path, origin, Clock())
    result = fetcher.fetch(origin + "/a")
    assert result.metadata["terms_check"]["bulk_allowed"] is True
    assert result.metadata["terms_check"]["origin"] == origin


def test_standard_limit_window_is_respected() -> None:
    assert header_delay({"RateLimit-Limit": "10;w=3600"}, 2, 60) == 360


def test_429_exhaustion_stops_run(tmp_path: Any, server: Any) -> None:
    from urllib.error import HTTPError

    origin, state = server
    state["responses"] = [(429, {}, b"wait")] * 3
    fetcher = make_fetcher(tmp_path, origin, Clock())
    with pytest.raises(HTTPError):
        fetcher.run([origin + "/a", origin + "/b"])
    assert state["requests"] == ["/a"] * 3


def test_closed_local_target_fails_without_retry(tmp_path: Any) -> None:
    import socket

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
    fetcher = make_fetcher(tmp_path, origin, Clock(), timeout=0.1)
    with pytest.raises(UnreachableTarget, match="network-reachability"):
        fetcher.preflight(origin + "/records")
    assert len(fetcher.store.state["hosts"]["127.0.0.1"]["attempts"]) == 1


@pytest.mark.parametrize("allowed,other_origin", [(False, False), (True, True)])
def test_denied_or_wrong_origin_terms_refuse_network(
    tmp_path: Any, server: Any, allowed: Any, other_origin: Any
) -> None:
    origin, state = server
    terms = TermsCheck(
        origin="https://other.example.org" if other_origin else origin,
        terms_url=origin + "/terms",
        checked_at="2026-10-11T00:00:00Z",
        bulk_allowed=allowed,
    )
    fetcher = Fetcher(
        FetchConfig(
            tmp_path,
            USER_AGENT,
        ),
        [terms],
    )
    with pytest.raises(TermsDenied):
        fetcher.fetch(origin + "/a")
    assert not state["requests"]


def test_permission_requires_real_boolean() -> None:
    with pytest.raises(ValueError, match="Boolean"):
        TermsCheck(
            "https://records.example.org",
            "https://records.example.org/terms",
            "2026-10-11T00:00:00Z",
            cast(Any, "false"),
        )


def test_dry_run_combines_cooldown_and_pacing(tmp_path: Any, server: Any) -> None:
    origin, state = server
    clock = Clock()
    fetcher = make_fetcher(tmp_path, origin, clock)
    fetcher.store.state["hosts"]["127.0.0.1"] = {
        "attempts": [],
        "next_at": clock.time() + 100,
    }
    report = fetcher.project([origin + f"/{i}" for i in range(10)])
    assert report["estimated_seconds"] >= 118
    assert state["requests"] == []
    assert fetcher.store.state["hosts"]["127.0.0.1"]["attempts"] == []
