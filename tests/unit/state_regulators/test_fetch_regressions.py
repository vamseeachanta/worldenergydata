"""Review regressions use synthetic clocks and loopback HTTP only."""

import hashlib
import json
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from worldenergydata.modules.state_regulators.fetch import TermsCheck
from worldenergydata.modules.state_regulators.fetch.job import (
    FetchJob,
    _storage_path,
    main,
)
from worldenergydata.modules.state_regulators.fetch.storage import (
    CacheIntegrityError,
    CacheStore,
    _checked_path,
)

from .fetch_cases import Clock, server, settings

__all__ = ["server"]


def test_all_bulk_urls_are_collected_once(tmp_path: Path, server: Any) -> None:
    origin, state = server
    config = settings(tmp_path, origin)
    config["bulk_urls"] = [origin + "/first", origin + "/second", origin + "/first"]
    job = FetchJob(config, execution_role="regulator-fetch")
    clock = Clock()
    fetcher = job.fetcher(clock=clock.time, sleep=clock.sleep)
    assert job.run(fetcher, execute=False)["projected_requests"] == 2
    results = job.run(fetcher, execute=True)
    assert len(results) == 2
    assert state["requests"] == ["/first", "/second"]


def test_fourth_request_matches_projected_window_release(
    tmp_path: Path, server: Any
) -> None:
    origin, state = server
    config = settings(tmp_path, origin)
    config["crawl_urls"].append(origin + "/d")
    job = FetchJob(config, execution_role="regulator-fetch")
    clock = Clock()
    start = clock.time()
    fetcher = job.fetcher(clock=clock.time, sleep=clock.sleep)
    projection = job.run(fetcher, execute=False)
    results = job.run(fetcher, execute=True)
    assert len(results) == 4
    assert state["requests"] == ["/a", "/b", "/c", "/d"]
    assert clock.waits == [2, 2, 6]
    assert clock.time() - start == projection["estimated_seconds"] == 10


def cli_config(tmp_path: Path, origin: str, monkeypatch: Any) -> Path:
    monkeypatch.setenv("STATE_FETCH_EXECUTION_ROLE", "regulator-fetch")
    path = tmp_path / "input.json"
    path.write_text(json.dumps(settings(tmp_path, origin)), encoding="utf-8")
    return path


def test_cli_unreachable_reports_only_origin_and_layer(
    tmp_path: Path, monkeypatch: Any, capsys: Any
) -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
        path = cli_config(tmp_path, origin, monkeypatch)
        config = json.loads(path.read_text(encoding="utf-8"))
        config["crawl_urls"] = [origin + "/sensitive?token=hidden"]
        config["fetch"]["timeout"] = 0.1
        path.write_text(json.dumps(config), encoding="utf-8")
        with pytest.raises(SystemExit) as error:
            main([str(path), "--execute"])
    assert error.value.code == 5
    message = capsys.readouterr().err
    assert "UnreachableTarget" in message
    assert "network-reachability" in message
    assert origin in message
    assert all(value not in message for value in ("sensitive", "hidden", str(tmp_path)))


def test_cli_budget_stop_has_resume_time_and_preserves_restart(
    tmp_path: Path, server: Any, monkeypatch: Any, capsys: Any
) -> None:
    from worldenergydata.modules.state_regulators.fetch import job as job_module

    origin, state = server
    path = cli_config(tmp_path, origin, monkeypatch)
    config = json.loads(path.read_text(encoding="utf-8"))
    config["crawl_urls"].append(origin + "/d")
    config["fetch"]["max_sleep_seconds"] = 5
    path.write_text(json.dumps(config), encoding="utf-8")
    clock = Clock()
    start = clock.time()
    constructor = job_module.Fetcher
    monkeypatch.setattr(
        job_module,
        "Fetcher",
        lambda config, terms: constructor(
            config, terms, clock=clock.time, sleep=clock.sleep
        ),
    )
    for _ in range(2):
        with pytest.raises(SystemExit) as error:
            main([str(path), "--execute"])
        assert error.value.code == 4
        message = capsys.readouterr().err
        assert "BudgetExceeded" in message and origin in message
        assert datetime.fromtimestamp(start + 10, timezone.utc).isoformat() in message
        assert str(tmp_path) not in message
    assert state["requests"] == ["/a", "/b", "/c"]
    assert clock.waits == [2, 2]
    clock.now = start + 10
    assert main([str(path), "--execute"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "completed_urls": 4,
        "cached_urls": 3,
    }
    assert state["requests"] == ["/a", "/b", "/c", "/d"]


@pytest.mark.parametrize("failure,code", [("terms", 3), ("config", 2), ("cache", 6)])
def test_cli_failure_categories(
    tmp_path: Path, monkeypatch: Any, capsys: Any, failure: str, code: int
) -> None:
    path = cli_config(tmp_path, "https://records.example.org", monkeypatch)
    if failure == "config":
        path.write_text("{", encoding="utf-8")
    elif failure == "terms":
        config = json.loads(path.read_text(encoding="utf-8"))
        config["terms"] = []
        path.write_text(json.dumps(config), encoding="utf-8")
    else:
        cache = tmp_path / "cache"
        cache.mkdir()
        (cache / "progress.json").write_text("{", encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main([str(path), "--execute"])
    assert error.value.code == code
    message = capsys.readouterr().err
    expected = {
        "terms": "TermsDenied",
        "config": "ValueError",
        "cache": "CacheIntegrityError",
    }
    assert expected[failure] in message
    assert str(tmp_path) not in message


def test_cache_under_linked_parent_preserves_binary_digests(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    actual.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(actual, target_is_directory=True)
    store = CacheStore(linked / "cache")
    for index, payload in enumerate((b"first\nrecord\n", b"second\nrecord\n")):
        url = f"https://records.example.org/{index}"
        result = store.put(url, payload, {}, {})
        assert store.get(url).path.read_bytes() == payload
        assert (
            result.metadata["sha256"]
            == hashlib.sha256(result.path.read_bytes()).hexdigest()
        )
    for record in store.records.iterdir():
        metadata = json.loads(record.read_bytes())
        digest = metadata["sha256"]
        assert (
            hashlib.sha256((store.objects / digest).read_bytes()).hexdigest() == digest
        )
        assert store.state["completed"][metadata["url"]] == digest
    assert len(CacheStore(linked / "cache").state["completed"]) == 2


def test_cache_root_itself_cannot_be_a_symlink(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    actual.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(actual, target_is_directory=True)
    with pytest.raises(CacheIntegrityError, match="symlinks"):
        CacheStore(linked)
    assert list(actual.iterdir()) == []


@pytest.mark.parametrize("entry", ["objects", "records", "progress.json"])
def test_cli_linked_cache_entry_is_cache_failure(
    tmp_path: Path, monkeypatch: Any, capsys: Any, entry: str
) -> None:
    path = cli_config(tmp_path, "https://records.example.org", monkeypatch)
    cache = tmp_path / "cache"
    cache.mkdir()
    target = tmp_path / "retained"
    if entry == "progress.json":
        target.write_bytes(b"retained\n")
    else:
        target.mkdir()
        (target / "evidence").write_bytes(b"retained\n")
    linked = cache / entry
    linked.symlink_to(target, target_is_directory=target.is_dir())
    with pytest.raises(SystemExit) as error:
        main([str(path), "--execute"])
    assert error.value.code == 6
    assert capsys.readouterr().err == (
        "CacheIntegrityError: preserve and inspect retained cache evidence\n"
    )
    assert linked.is_symlink()
    evidence = target / "evidence" if target.is_dir() else target
    assert evidence.read_bytes() == b"retained\n"


@pytest.mark.parametrize("traversal", [False, True])
def test_cache_escape_is_integrity_failure(tmp_path: Path, traversal: bool) -> None:
    root = tmp_path / "cache"
    path = root / ".." / "outside" if traversal else tmp_path / "outside"
    with pytest.raises(CacheIntegrityError, match="within the cache root"):
        _checked_path(path, root)
    assert not root.exists()


def test_literal_dollar_is_a_valid_storage_path() -> None:
    path = Path.cwd() / "data$"
    assert _storage_path(str(path)) == path.resolve()


@pytest.mark.parametrize(
    "token", ["$FETCH_MISSING", "${FETCH_MISSING}", "%FETCH_MISSING%"]
)
def test_unresolved_storage_variables_are_rejected(
    monkeypatch: Any, token: str
) -> None:
    monkeypatch.delenv("FETCH_MISSING", raising=False)
    with pytest.raises(ValueError, match="resolved variables"):
        _storage_path(str(Path.cwd() / token))


def test_cli_reads_utf8_explicitly(
    tmp_path: Path, monkeypatch: Any, capsys: Any
) -> None:
    path = cli_config(tmp_path, "https://records.example.org", monkeypatch)
    original = Path.read_text

    def read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self == path:
            assert kwargs.get("encoding") == "utf-8"
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    assert main([str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["projected_requests"] == 3


@pytest.mark.parametrize(
    "timestamp,message",
    [
        ("malformed", "ISO 8601"),
        ("2026-01-01T00:00:00", "UTC"),
        ("2026-01-01T00:00:00+01:00", "UTC"),
        ("9999-01-01T00:00:00Z", "future"),
    ],
)
def test_terms_timestamp_is_validated_at_load(timestamp: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        TermsCheck(
            "https://records.example.org",
            "https://records.example.org/terms",
            timestamp,
            True,
        )


def test_reduced_budget_waits_until_enough_reservations_expire(tmp_path: Path) -> None:
    config = settings(tmp_path, "https://records.example.org")
    config["fetch"]["budget_requests"] = 1
    clock = Clock()
    fetcher = FetchJob(config, execution_role="regulator-fetch").fetcher(
        clock=clock.time, sleep=clock.sleep
    )
    fetcher.store.state["hosts"]["records.example.org"] = {
        "attempts": [clock.now - 4, clock.now - 2, clock.now],
        "next_at": clock.now + 2,
    }
    url = "https://records.example.org/a"
    assert fetcher.project([url])["estimated_seconds"] == 10
    fetcher._reserve(url)
    assert clock.waits == [10]
    assert fetcher.store.state["hosts"]["records.example.org"]["attempts"] == [
        clock.now
    ]
