"""Boundary scenarios collected through the polite-fetch test module."""

import json
from typing import Any

import pytest

from worldenergydata.modules.state_regulators.fetch import (
    BudgetExceeded,
    FetchConfig,
    Fetcher,
    TermsCheck,
    TermsDenied,
    header_delay,
)

USER_AGENT = "records/1.0 (+https://github.com/vamseeachanta/worldenergydata; research)"


class Clock:
    def __init__(self) -> None:
        self.now = 1800000000.0
        self.waits: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.waits.append(seconds)
        self.now += seconds


def make_fetcher(root: Any, origin: str, clock: Clock, **kwargs: Any) -> Fetcher:
    config = FetchConfig(
        cache_root=root,
        user_agent=USER_AGENT,
        **kwargs,
    )
    terms = TermsCheck(
        origin=origin,
        terms_url=f"{origin}/terms",
        checked_at="2026-10-11T00:00:00+00:00",
        bulk_allowed=True,
    )
    return Fetcher(config, [terms], clock=clock.time, sleep=clock.sleep)


@pytest.mark.parametrize(
    "headers",
    [
        {"Retry-After": "86400"},
        {"Retry-After": "Fri, 01 Jan 2100 00:00:00 GMT"},
        {"RateLimit-Reset": "86400"},
        {"Retry-After": "86400", "RateLimit-Reset": "1e300"},
        {
            "x-dotratelimit-toks-remaining": "0",
            "x-dotrequest-cost": "1",
            "x-dotratelimit-reset": "86400",
        },
    ],
)
def case_long_wait_is_persisted_and_refused(
    tmp_path: Any, server: Any, headers: Any
) -> None:
    origin, state = server
    clock = Clock()
    state["responses"] = [(429, headers, b"wait")]
    fetcher = make_fetcher(tmp_path, origin, clock)
    with pytest.raises(BudgetExceeded, match="127.0.0.1.*UTC"):
        fetcher.fetch(origin + "/a")
    next_at = json.loads((tmp_path / "progress.json").read_text())["hosts"][
        "127.0.0.1"
    ]["next_at"]
    assert next_at > clock.time() + 300
    resumed = make_fetcher(tmp_path, origin, clock)
    with pytest.raises(BudgetExceeded):
        resumed.fetch(origin + "/a")
    assert clock.waits == []
    assert state["requests"] == ["/a"]
    clock.now = next_at
    resumed.fetch(origin + "/a")
    assert state["requests"] == ["/a", "/a"]


def case_wait_below_cap_proceeds(tmp_path: Any, server: Any) -> None:
    origin, state = server
    clock = Clock()
    state["responses"] = [(429, {"Retry-After": "299"}, b"wait")]
    make_fetcher(tmp_path, origin, clock).fetch(origin + "/a")
    assert clock.waits == [299]
    assert len(state["requests"]) == 2


@pytest.mark.parametrize("value", ["-1", "bad", "1e999", "nan", "9" * 400])
def case_invalid_retry_values_do_not_crash(value: Any) -> None:
    assert header_delay({"Retry-After": value}, 2, 60) == 2


@pytest.mark.parametrize("length,size", [(True, 9), (False, 9), (True, 8), (False, 8)])
@pytest.mark.parametrize("cooldown", [False, True])
def case_response_cap(
    tmp_path: Any, server: Any, length: Any, size: Any, cooldown: Any
) -> None:
    from worldenergydata.modules.state_regulators.fetch import ResponseTooLarge

    origin, state = server
    headers = {"Content-Length": str(size)} if length else {}
    if cooldown:
        headers["Retry-After"] = "86400"
    state["responses"] = [(200, headers, b"x" * size)]
    fetcher = make_fetcher(tmp_path, origin, Clock(), max_response_bytes=8)
    if size > 8:
        with pytest.raises(ResponseTooLarge, match="127.0.0.1.*8 bytes") as error:
            fetcher.fetch(origin + "/a?private=value")
        assert "private" not in str(error.value)
        assert not list(fetcher.store.objects.iterdir())
        assert not list(fetcher.store.records.iterdir())
        if cooldown:
            clock = Clock()
            resumed = make_fetcher(tmp_path, origin, clock, max_response_bytes=8)
            with pytest.raises(BudgetExceeded):
                resumed.fetch(origin + "/other")
            assert clock.waits == []
            assert len(state["requests"]) == 1
            assert (
                resumed.store.state["hosts"]["127.0.0.1"]["next_at"]
                == clock.time() + 86400
            )
    else:
        assert fetcher.fetch(origin + "/a").path.read_bytes() == b"x" * 8
    assert len(fetcher.store.state["hosts"]["127.0.0.1"]["attempts"]) == 1


@pytest.mark.parametrize(
    "document",
    [
        "{",
        "[]",
        "{}",
        '{"completed": [], "hosts": {}}',
        '{"completed": {}, "hosts": []}',
        '{"completed": {}, "hosts": {"source": {"next_at": "bad", "attempts": []}}}',
        '{"completed": {}, "hosts": {"source": {"next_at": 0, "attempts": ["bad"]}}}',
        '{"completed": {}, "hosts": {"source": {"next_at": NaN, "attempts": []}}}',
        '{"completed": {}, "hosts": {"source": {"next_at": 1e100, "attempts": []}}}',
        json.dumps(
            {"completed": {}, "hosts": {"source": {"next_at": 10**400, "attempts": []}}}
        ),
    ],
)
def case_corrupt_progress_is_preserved(tmp_path: Any, document: Any) -> None:
    from worldenergydata.modules.state_regulators.fetch.storage import CacheStore

    progress = tmp_path / "progress.json"
    progress.write_text(document)
    with pytest.raises(
        ValueError, match="Cache integrity:.*progress.json.*full budget window"
    ):
        CacheStore(tmp_path)
    assert progress.read_text() == document
    progress.rename(tmp_path / "progress.saved")
    assert CacheStore(tmp_path).state == {"completed": {}, "hosts": {}}


@pytest.mark.parametrize("document", ["{", "[]", "{}", '{"sha256": 42}'])
def case_corrupt_url_record_is_preserved(
    tmp_path: Any, server: Any, document: Any
) -> None:
    origin, state = server
    fetcher = make_fetcher(tmp_path, origin, Clock())
    result = fetcher.fetch(origin + "/a")
    record = next(fetcher.store.records.iterdir())
    record.write_text(document)
    with pytest.raises(ValueError, match="Cache integrity:.*json"):
        fetcher.fetch(origin + "/a")
    assert record.read_text() == document
    assert result.path.read_bytes() == b"public records"
    assert len(state["requests"]) == 1


def case_cached_permission_survives_withdrawal(tmp_path: Any, server: Any) -> None:
    origin, state = server
    clock = Clock()
    result = make_fetcher(tmp_path, origin, clock).fetch(origin + "/a")
    state["requests"].clear()
    denied = Fetcher(
        make_fetcher(tmp_path, origin, clock).config,
        [],
        clock=clock.time,
        sleep=clock.sleep,
    )
    assert denied.fetch(origin + "/a").path == result.path
    with pytest.raises(TermsDenied):
        denied.fetch(origin + "/b")
    assert state["requests"] == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_sleep_seconds", 0),
        ("max_sleep_seconds", -1),
        ("max_sleep_seconds", float("inf")),
        ("max_sleep_seconds", "bad"),
        ("max_response_bytes", 0),
        ("max_response_bytes", -1),
        ("max_response_bytes", 1.5),
        ("max_response_bytes", True),
    ],
)
def case_invalid_caps_are_rejected(tmp_path: Any, field: Any, value: Any) -> None:
    with pytest.raises(ValueError):
        make_fetcher(tmp_path, "https://records.example.org", Clock(), **{field: value})
