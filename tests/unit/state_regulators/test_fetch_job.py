"""Offline deployment and configuration checks with independent arithmetic.

All pacing/budget numbers here are synthetic inputs, not regulator limits.
HTTP status meanings: RFC 9110 (2022); retry semantics: RFC 6585 (2012) §4.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from worldenergydata.modules.state_regulators.fetch import FetchConfig, Fetcher
from worldenergydata.modules.state_regulators.fetch.job import FetchJob, main

from . import test_polite_fetch
from .fetch_cases import Clock

server = test_polite_fetch.server


def settings(root: Path, origin: str) -> dict[str, Any]:
    """Synthetic operator choices: 2 s spacing, 3 attempts per 10 s window."""
    return {
        "execution_role": "regulator-fetch",
        "storage_root": str(root),
        "fetch": {
            "cache_root": str(root / "cache"),
            "user_agent": "public-records/1.0 (+https://records.example.org/contact)",
            "fallback_interval": 2,
            "budget_requests": 3,
            "budget_window": 10,
            "timeout": 5,
            "max_retries": 1,
            "max_sleep_seconds": 30,
            "max_response_bytes": 1024,
        },
        "terms": [
            {
                "origin": origin,
                "terms_url": origin + "/terms",
                "checked_at": "2026-10-11T00:00:00Z",
                "bulk_allowed": True,
            }
        ],
        "bulk_urls": [],
        "crawl_urls": [origin + "/a", origin + "/b", origin + "/c"],
        "use_crawl": False,
    }


def test_projection_and_restart(tmp_path: Path, server: Any) -> None:
    """Requests at 0, 2, 4 s => 4 s; one retry each => 3*(1+1)=6 attempts.

    On restart all three payloads exist, hence zero requests and zero wait.
    """
    origin, state = server
    clock = Clock()
    job = FetchJob(settings(tmp_path, origin), execution_role="regulator-fetch")
    fetcher = job.fetcher(clock=clock.time, sleep=clock.sleep)
    projection = job.run(fetcher, execute=False)
    assert projection["projected_requests"] == 3
    assert projection["estimated_seconds"] == 4
    assert projection["maximum_attempts"] == 6
    assert not state["requests"]
    results = job.run(fetcher, execute=True)
    assert len(results) == 3
    resumed = job.fetcher(clock=clock.time, sleep=clock.sleep)
    assert job.run(resumed, execute=False)["projected_requests"] == 0
    assert all(result.cached for result in job.run(resumed, execute=True))
    assert state["requests"] == ["/a", "/b", "/c"]


def test_role_mismatch_refuses_before_cache_creation(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="execution role"):
        FetchJob(settings(tmp_path, "https://records.example.org"), execution_role="")
    assert not (tmp_path / "cache").exists()


def test_cache_must_be_on_configured_storage(tmp_path: Path) -> None:
    config = settings(tmp_path / "data", "https://records.example.org")
    config["fetch"]["cache_root"] = str(tmp_path / "elsewhere")
    with pytest.raises(ValueError, match="storage root"):
        FetchJob(config, execution_role="regulator-fetch")
    assert not (tmp_path / "elsewhere").exists()


def test_symlink_cannot_escape_storage(tmp_path: Path) -> None:
    data, other = tmp_path / "data", tmp_path / "other"
    data.mkdir()
    other.mkdir()
    (data / "cache").symlink_to(other, target_is_directory=True)
    with pytest.raises(ValueError, match="storage root"):
        FetchJob(
            settings(data, "https://records.example.org"),
            execution_role="regulator-fetch",
        )


def test_bulk_route_preferred_and_override_audited(tmp_path: Path, caplog: Any) -> None:
    config = settings(tmp_path, "https://records.example.org")
    config["bulk_urls"] = ["https://records.example.org/all.zip"]
    job = FetchJob(config, execution_role="regulator-fetch")
    assert job.urls == config["bulk_urls"]
    config["use_crawl"] = True
    with caplog.at_level("WARNING"):
        job = FetchJob(config, execution_role="regulator-fetch")
    assert job.urls == config["crawl_urls"]
    assert "all.zip" in caplog.text


def test_permission_for_all_urls_checked_before_first_request(
    tmp_path: Path, server: Any
) -> None:
    origin, state = server
    config = settings(tmp_path, origin)
    config["crawl_urls"].append("https://other.example.org/a")
    job = FetchJob(config, execution_role="regulator-fetch")
    from worldenergydata.modules.state_regulators.fetch import TermsDenied

    with pytest.raises(TermsDenied):
        job.run(job.fetcher(), execute=True)
    assert not state["requests"]


@pytest.mark.parametrize("field", ["fallback_interval", "budget_window", "max_retries"])
def test_pacing_inputs_required(tmp_path: Path, field: str) -> None:
    config = settings(tmp_path, "https://records.example.org")
    del config["fetch"][field]
    with pytest.raises(ValueError, match="required fetch settings"):
        FetchJob(config, execution_role="regulator-fetch")


@pytest.mark.parametrize(
    "field,value",
    [
        ("budget_requests", True),
        ("max_retries", 1.5),
        ("fallback_interval", True),
        ("timeout", "5"),
    ],
)
def test_invalid_numeric_configuration(tmp_path: Path, field: str, value: Any) -> None:
    with pytest.raises(ValueError):
        FetchConfig(tmp_path, "records", **{field: value})


def test_cli_defaults_to_offline_projection(
    tmp_path: Path, server: Any, monkeypatch: Any, capsys: Any
) -> None:
    origin, state = server
    config = settings(tmp_path, origin)
    config["storage_root"] = "${FETCH_TEST_ROOT}"
    config["fetch"]["cache_root"] = "${FETCH_TEST_ROOT}/cache"
    monkeypatch.setenv("FETCH_TEST_ROOT", str(tmp_path))
    monkeypatch.setenv("STATE_FETCH_EXECUTION_ROLE", "regulator-fetch")
    path = tmp_path / "input.json"
    path.write_text(json.dumps(config))
    assert main([str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["projected_requests"] == 3
    assert not state["requests"]


def test_contact_is_required(tmp_path: Path) -> None:
    config = settings(tmp_path, "https://records.example.org")
    config["fetch"]["user_agent"] = "anonymous"
    with pytest.raises(ValueError, match="contact"):
        FetchJob(config, execution_role="regulator-fetch")


def test_budget_projection_has_no_trailing_sleep(tmp_path: Path) -> None:
    """3 attempts/window, spacing 2: 0,2,4 then 10 => fourth starts at 10 s."""
    fetcher = Fetcher(
        FetchConfig(
            tmp_path,
            "records",
            fallback_interval=2,
            budget_requests=3,
            budget_window=10,
        ),
        [],
        clock=lambda: 100,
    )
    assert (
        fetcher.project([f"https://records.example.org/{i}" for i in range(4)])[
            "estimated_seconds"
        ]
        == 10
    )


def test_example_is_offline_and_unpermitted(
    tmp_path: Path, monkeypatch: Any, capsys: Any
) -> None:
    """Example hand calculation: starts 0,2,4 => 4 s; 3*(1+1) => 6 attempts."""
    monkeypatch.setenv("STATE_FETCH_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("STATE_FETCH_EXECUTION_ROLE", "regulator-fetch")
    example = (
        Path(__file__).resolve().parents[3]
        / "config/state_regulator_fetch.example.json"
    )
    assert main([str(example)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["estimated_seconds"] == 4
    assert report["maximum_attempts"] == 6
    assert report["terms_permitted"] is False
    with pytest.raises(SystemExit) as refused:
        main([str(example), "--execute"])
    assert refused.value.code == 1


def test_cli_executes_and_reports_cached_results(
    tmp_path: Path, server: Any, monkeypatch: Any, capsys: Any
) -> None:
    """Synthetic zero-latency clock; second invocation reuses all three URLs."""
    origin, state = server
    monkeypatch.setenv("STATE_FETCH_EXECUTION_ROLE", "regulator-fetch")
    clock = Clock()
    from worldenergydata.modules.state_regulators.fetch import job as job_module

    constructor = job_module.Fetcher
    monkeypatch.setattr(
        job_module,
        "Fetcher",
        lambda config, terms: constructor(
            config, terms, clock=clock.time, sleep=clock.sleep
        ),
    )
    path = tmp_path / "input.json"
    path.write_text(json.dumps(settings(tmp_path, origin)))
    assert main([str(path), "--execute"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "completed_urls": 3,
        "cached_urls": 0,
    }
    assert main([str(path), "--execute"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "completed_urls": 3,
        "cached_urls": 3,
    }
    assert state["requests"] == ["/a", "/b", "/c"]
