"""Collection and CLI behavior with in-memory storage and transport boundaries."""

import json
import socket
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock
from urllib.error import URLError

import pytest

from worldenergydata.modules.state_regulators.fetch import client
from worldenergydata.modules.state_regulators.fetch.job import FetchJob, main
from worldenergydata.modules.state_regulators.fetch.storage import read_record

from .fetch_cases import Clock, settings


@pytest.fixture
def memory(monkeypatch: Any) -> Any:
    clock = Clock()
    records: dict[str, Any] = {}
    state = {"hosts": {}, "completed": {}}

    def put(url: str, *args: Any) -> Any:
        records[url] = SimpleNamespace(cached=True)
        return SimpleNamespace(cached=False)

    store = SimpleNamespace(
        root=Path("unused"), state=state, get=records.get, put=put, save=Mock()
    )
    monkeypatch.setattr(client, "CacheStore", lambda root: store)
    monkeypatch.setattr(client, "atomic_json", lambda *args, **kwargs: None)
    requests: list[tuple[str, float]] = []

    def request(self: Any, url: str) -> Any:
        requests.append((url, clock.time()))
        return b"records", {}

    monkeypatch.setattr(client.Fetcher, "_request", request)
    return SimpleNamespace(clock=clock, requests=requests, store=store)


@pytest.mark.parametrize("sleep_cap", [6, 30])
def test_bulk_plan_executes_every_unique_url_at_projected_times(
    memory: Any, sleep_cap: int
) -> None:
    origin = "https://records.example.org"
    config = settings(Path.cwd(), origin)
    config["bulk_urls"] = [origin + f"/{i}" for i in [0, 1, 1, 2, 3]]
    config["fetch"]["max_sleep_seconds"] = sleep_cap
    job = FetchJob(config, execution_role="regulator-fetch")
    clock = memory.clock
    start = clock.time()
    fetcher = job.fetcher(clock=clock.time, sleep=clock.sleep)
    projection = job.run(fetcher, execute=False)
    assert memory.requests == []
    assert projection["projected_requests"] == 4
    assert projection["estimated_seconds"] == 10
    assert len(job.run(fetcher, execute=True)) == 4
    assert [url for url, _ in memory.requests] == [origin + f"/{i}" for i in range(4)]
    assert [time - start for _, time in memory.requests] == [0, 2, 4, 10]
    assert job.run(fetcher, execute=False)["projected_requests"] == 0


def test_cli_wait_cap_reports_exact_resume_and_reuses_completed_urls(
    memory: Any, monkeypatch: Any, capsys: Any
) -> None:
    from worldenergydata.modules.state_regulators.fetch import job as job_module

    origin = "https://records.example.org"
    config = settings(Path.cwd(), origin)
    config["crawl_urls"].append(origin + "/d")
    config["fetch"]["max_sleep_seconds"] = 5
    monkeypatch.setenv("STATE_FETCH_EXECUTION_ROLE", "regulator-fetch")
    monkeypatch.setattr(Path, "read_text", lambda *args, **kwargs: json.dumps(config))
    clock = memory.clock
    start = clock.time()
    monkeypatch.setattr(
        job_module,
        "Fetcher",
        lambda config, terms: client.Fetcher(
            config, terms, clock=clock.time, sleep=clock.sleep
        ),
    )
    for _ in range(2):
        with pytest.raises(SystemExit) as stopped:
            main(["unused.json", "--execute"])
        assert stopped.value.code == 4
        message = capsys.readouterr().err
        assert "BudgetExceeded" in message and origin + ":443" in message
        assert datetime.fromtimestamp(start + 10, timezone.utc).isoformat() in message
    assert len(memory.requests) == 3
    assert clock.waits == [2, 2]
    clock.now = start + 10
    assert main(["unused.json", "--execute"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "completed_urls": 4,
        "cached_urls": 3,
    }
    assert len(memory.requests) == 4


@pytest.mark.parametrize("layer", ["name-resolution", "network-reachability"])
def test_cli_preserves_failure_layer_without_transport_detail(
    monkeypatch: Any, capsys: Any, layer: str
) -> None:
    config = settings(Path.cwd(), "https://records.example.org")
    config["crawl_urls"] = ["https://records.example.org/private?secret=hidden"]
    monkeypatch.setenv("STATE_FETCH_EXECUTION_ROLE", "regulator-fetch")
    monkeypatch.setattr(Path, "read_text", lambda *args, **kwargs: json.dumps(config))
    store = SimpleNamespace(
        root=Path("unused"), state={"hosts": {}}, get=lambda url: None, save=Mock()
    )
    monkeypatch.setattr(client, "CacheStore", lambda root: store)
    monkeypatch.setattr(client, "atomic_json", lambda *args, **kwargs: None)
    reason = (
        socket.gaierror("hidden") if layer == "name-resolution" else OSError("hidden")
    )
    opener = Mock()
    opener.open.side_effect = URLError(reason)
    monkeypatch.setattr(client, "build_opener", lambda *args: opener)
    with pytest.raises(SystemExit) as stopped:
        main(["unused.json", "--execute"])
    assert stopped.value.code == 5
    assert capsys.readouterr().err == (
        f"UnreachableTarget: origin=https://records.example.org:443; layer={layer}\n"
    )
    assert opener.open.call_count == 1


def test_reduced_budget_releases_enough_retained_attempts(memory: Any) -> None:
    config = settings(Path.cwd(), "https://records.example.org")
    config["fetch"]["budget_requests"] = 1
    clock = memory.clock
    start = clock.time()
    memory.store.state["hosts"]["records.example.org"] = {
        "attempts": [start - 4, start - 2, start],
        "next_at": start + 2,
    }
    job = FetchJob(config, execution_role="regulator-fetch")
    job.urls = job.urls[:1]
    fetcher = job.fetcher(clock=clock.time, sleep=clock.sleep)
    assert job.run(fetcher, execute=False)["estimated_seconds"] == 10
    assert len(job.run(fetcher, execute=True)) == 1
    assert memory.requests[0][1] - start == 10


@pytest.mark.parametrize(
    "failure,code,name",
    [
        ("config", 2, "ValueError"),
        ("terms", 3, "TermsDenied"),
        ("cache", 6, "CacheIntegrityError"),
        ("missing", 11, "KeyError"),
        ("type", 12, "TypeError"),
    ],
)
def test_cli_distinguishes_configuration_permission_and_cache_failures(
    memory: Any, monkeypatch: Any, capsys: Any, failure: str, code: int, name: str
) -> None:
    config = settings(Path.cwd(), "https://records.example.org")
    if failure == "terms":
        config["terms"] = []
    elif failure == "missing":
        del config["fetch"]
    elif failure == "type":
        config["fetch"] = None
    elif failure == "cache":
        memory.store.get = lambda url: read_record(
            Path.cwd() / "unused.json", root=Path.cwd(), progress=True
        )
    monkeypatch.setenv("STATE_FETCH_EXECUTION_ROLE", "regulator-fetch")

    def read_text(path: Path, **kwargs: Any) -> str:
        if failure == "config" or path.name == "unused.json":
            return "{"
        return json.dumps(config)

    monkeypatch.setattr(Path, "read_text", read_text)
    with pytest.raises(SystemExit) as stopped:
        main(["config.json", "--execute"])
    assert stopped.value.code == code
    assert name in capsys.readouterr().err
    assert memory.requests == []
