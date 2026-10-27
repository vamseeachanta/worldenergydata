"""Fail-closed replay decisions using an in-memory API and clock."""

import importlib.util
import json
import socket
from http.client import HTTPConnection
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/ci/replay_gate.py"
HEAD = "a" * 40
TIP = "b" * 40
CONTEXT = {
    "repository": "example/repository",
    "run_id": 100,
    "head": HEAD,
    "pr": 7,
    "base_ref": "main",
    "base_repository_id": 1,
}


@pytest.fixture
def replay():
    """Load the standalone script without installing the project."""
    assert SCRIPT.is_file(), "the replay lookup is not implemented"
    spec = importlib.util.spec_from_file_location("replay_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(run_id=90, conclusion="success", status="completed", head=HEAD):
    """Describe an earlier workflow run attached to the current pull request."""
    return {
        "id": run_id,
        "run_attempt": 2,
        "head_sha": head,
        "event": "pull_request",
        "status": status,
        "conclusion": conclusion,
        "pull_requests": [{"number": 7, "base": {"ref": "main", "repo": {"id": 1}}}],
    }


class FakeAPI:
    """Supply paginated REST resources and advance running jobs on sleep."""

    def __init__(self):
        self.runs = [run()]
        self.tip = TIP
        self.artifacts = {90: [{"name": f"gate-tip-{TIP}-attempt-2", "expired": False}]}
        self.jobs = {90: [{"id": 3, "name": "Lint", "conclusion": "success"}]}
        self.elapsed = 0
        self.on_sleep = None
        self.calls = []

    def __call__(self, path):
        """Return the requested resource, preserving pagination semantics."""
        self.calls.append(path)
        url = urlsplit(path)
        page = int(parse_qs(url.query).get("page", ["1"])[0])
        if "/branches/" in url.path:
            return {"commit": {"sha": self.tip}}
        if url.path.endswith("/runs"):
            return {"workflow_runs": self.runs[(page - 1) * 100 : page * 100]}
        parts = url.path.split("/")
        run_id = int(parts[parts.index("runs") + 1])
        if url.path.endswith("/artifacts"):
            return {"artifacts": self.artifacts.get(run_id, []) if page == 1 else []}
        if url.path.endswith("/jobs"):
            return {"jobs": self.jobs.get(run_id, [])[(page - 1) * 100 : page * 100]}
        raise AssertionError(path)

    def sleep(self, seconds):
        """Advance only the fake clock and optionally finish a source run."""
        self.elapsed += seconds
        if self.on_sleep:
            self.on_sleep()


def decide(replay, api, **kwargs):
    """Invoke the real decision engine without real sleeping or networking."""
    return replay.decide(api, CONTEXT, "Lint", **kwargs)


def test_title_edit_after_green(replay):
    """Green jobs copy their source identity and exact comparison basis."""
    result = decide(replay, FakeAPI())
    assert result["decision"] == "PASS"
    assert result["run_id"] == 90
    assert result["attempt"] == 2
    assert result["job_id"] == 3
    assert result["head"] == HEAD
    assert result["recorded_tip"] == result["live_tip"] == TIP
    assert result["conclusion"] == "success"


def test_title_edit_after_red_with_newer_cancelled_run(replay):
    """A cancellation never hides the newest decisive failed job."""
    api = FakeAPI()
    api.runs = [run(95, "cancelled"), run(90, "failure")]
    api.jobs[90][0]["conclusion"] = "failure"
    assert decide(replay, api)["decision"] == "FAIL"
    assert decide(replay, api)["run_id"] == 90


def test_title_edit_after_main_moved(replay):
    """A different live base tip invalidates every copied job."""
    api = FakeAPI()
    api.tip = "c" * 40
    result = decide(replay, api)
    assert result["decision"] == "FAIL"
    assert "base moved" in result["reason"]
    assert result["job_id"] == 3
    assert result["conclusion"] == "success"


def test_no_earlier_run(replay):
    """Missing evidence fails instead of producing a skipped check."""
    api = FakeAPI()
    api.runs = []
    assert decide(replay, api)["decision"] == "FAIL"


def test_in_progress_newer_full_run_fails_closed(replay):
    """An active full run must never expose older green evidence."""
    api = FakeAPI()
    api.runs.insert(0, run(95, None, "in_progress"))
    api.artifacts[95] = api.artifacts[90]
    api.jobs[95] = [{"name": "Lint", "conclusion": "failure"}]
    result = decide(replay, api)
    assert result["decision"] == "FAIL"
    assert result["reason"] == "newer full run in progress"
    assert result["run_id"] is None
    assert api.elapsed == 0


def test_no_completed_run_fails_closed(replay):
    """An edit fails immediately when its only full run is still queued."""
    api = FakeAPI()
    api.runs[0].update(status="queued", conclusion=None)
    result = decide(replay, api)
    assert result["decision"] == "FAIL"
    assert api.elapsed == 0


@pytest.mark.parametrize("mode_result", ["failure", "cancelled", "skipped", None])
def test_newer_completed_full_run_without_marker_fails(replay, mode_result):
    """A newer unmarked full run must never fall back to older green evidence."""
    api = FakeAPI()
    api.runs.insert(0, run(95, "failure"))
    api.jobs[95] = [
        {"name": "Gate mode", "status": "completed", "conclusion": mode_result},
        {"name": "Lint", "conclusion": "failure"},
    ]
    result = decide(replay, api)
    assert result["decision"] == "FAIL"
    assert result["reason"] == "full run without base-tip evidence"


def test_completed_replay_reaches_older_full_run(replay):
    """A successful mode with no marker identifies a completed replay."""
    api = FakeAPI()
    api.runs.insert(0, run(95))
    api.jobs[95] = [
        {"name": "Gate mode", "status": "completed", "conclusion": "success"}
    ]
    result = decide(replay, api)
    assert result["decision"] == "PASS"
    assert result["run_id"] == 90


@pytest.mark.parametrize("status", [None, "queued", "in_progress"])
def test_unfinished_mode_cannot_identify_replay(replay, status):
    """A success conclusion alone cannot certify completed replay identity."""
    api = FakeAPI()
    api.runs.insert(0, run(95, "failure"))
    api.jobs[95] = [{"name": "Gate mode", "status": status, "conclusion": "success"}]
    assert decide(replay, api)["decision"] == "FAIL"


@pytest.mark.parametrize("conclusion", ["success", "failure"])
def test_duplicate_modes_cannot_identify_replay(replay, conclusion):
    """Ambiguous mode identity cannot hide a newer unmarked full run."""
    api = FakeAPI()
    api.runs.insert(0, run(95, "failure"))
    api.jobs[95] = [
        {"name": "Gate mode", "status": "completed", "conclusion": "success"},
        {"name": "Gate mode", "status": "completed", "conclusion": conclusion},
    ]
    assert decide(replay, api)["decision"] == "FAIL"


def test_startup_failure_without_jobs_reaches_older_full_run(replay):
    """The review permits skipping a startup failure that created no jobs."""
    api = FakeAPI()
    api.runs.insert(0, run(95, "failure"))
    result = decide(replay, api)
    assert result["decision"] == "PASS"
    assert result["run_id"] == 90


@pytest.mark.parametrize("conclusion", ["cancelled", "neutral", "action_required"])
def test_no_decisive_full_run(replay, conclusion):
    """Only success, failure and timed out are decisive workflow results."""
    api = FakeAPI()
    api.runs[0]["conclusion"] = conclusion
    assert decide(replay, api)["decision"] == "FAIL"


def test_replay_is_never_a_source(replay):
    """A completed run without a full-run marker cannot be copied."""
    api = FakeAPI()
    api.artifacts = {}
    assert decide(replay, api)["decision"] == "FAIL"


def test_active_replay_is_not_waited_for(replay):
    """An active replay with a finished mode cannot hold up another replay."""
    api = FakeAPI()
    api.runs.insert(0, run(95, None, "in_progress"))
    api.jobs[95] = [
        {"name": "Gate mode", "status": "completed", "conclusion": "success"}
    ]
    assert decide(replay, api)["decision"] == "PASS"
    assert api.elapsed == 0


@pytest.mark.parametrize("status", ["queued", "in_progress"])
@pytest.mark.parametrize(
    "modes",
    [
        [],
        [{"name": "Gate mode", "status": "in_progress", "conclusion": None}],
        [{"name": "Gate mode", "status": "completed", "conclusion": "failure"}],
        [{"name": "Gate mode", "status": "completed"}],
        [
            {"name": "Gate mode", "status": "completed", "conclusion": "success"},
            {"name": "Gate mode", "status": "completed", "conclusion": "success"},
        ],
    ],
)
def test_unidentified_active_run_blocks_older_green(replay, status, modes):
    """Only one successfully completed mode can identify an active replay."""
    api = FakeAPI()
    api.runs.insert(0, run(95, None, status))
    api.jobs[95] = modes
    result = decide(replay, api)
    assert result["decision"] == "FAIL"
    assert result["reason"] == "newer full run in progress"
    assert api.elapsed == 0


@pytest.mark.parametrize(
    "marker",
    [
        {"name": f"gate-tip-{TIP}-attempt-2", "expired": False},
        {"name": f"gate-tip-{TIP}-attempt-1", "expired": False},
        {"name": f"gate-tip-{TIP}-attempt-2", "expired": True},
        {"name": "gate-tip-malformed", "expired": False},
    ],
)
def test_active_mode_success_with_marker_is_not_replay(replay, marker):
    """Any base-tip artifact prevents treating an active full run as a replay."""
    api = FakeAPI()
    api.runs.insert(0, run(95, None, "in_progress"))
    api.artifacts[95] = [marker]
    api.jobs[95] = [
        {"name": "Gate mode", "status": "completed", "conclusion": "success"}
    ]
    result = decide(replay, api)
    assert result["decision"] == "FAIL"
    assert result["reason"] == "newer full run in progress"


@pytest.mark.parametrize(
    "conclusion", ["success", "skipped", "failure", "timed_out", "cancelled", None]
)
def test_same_named_job_conclusions(replay, conclusion):
    """Only a successful source job passes."""
    api = FakeAPI()
    api.jobs[90][0]["conclusion"] = conclusion
    result = decide(replay, api)
    assert result["decision"] == ("PASS" if conclusion == "success" else "FAIL")


@pytest.mark.parametrize(
    "change", ["head", "pr", "base", "repository", "event", "current", "future"]
)
def test_source_identity_must_match(replay, change):
    """Another head, PR, base, event or later run cannot supply evidence."""
    api = FakeAPI()
    if change == "head":
        api.runs[0]["head_sha"] = "d" * 40
    elif change == "pr":
        api.runs[0]["pull_requests"][0]["number"] = 8
    elif change == "base":
        api.runs[0]["pull_requests"][0]["base"]["ref"] = "other"
    elif change == "repository":
        api.runs[0]["pull_requests"][0]["base"]["repo"]["id"] = 2
    elif change == "event":
        api.runs[0]["event"] = "push"
    else:
        api.runs[0]["id"] = 100 if change == "current" else 101
    assert decide(replay, api)["decision"] == "FAIL"


def test_missing_same_named_job(replay):
    """A different successful check does not prove this required name."""
    api = FakeAPI()
    api.jobs[90][0]["name"] = "Other"
    assert decide(replay, api)["decision"] == "FAIL"


@pytest.mark.parametrize("reverse", [False, True])
def test_duplicate_job_names_fail_closed(replay, reverse):
    """Duplicate required names cannot certify an unambiguous result."""
    api = FakeAPI()
    api.jobs[90].append({"id": 4, "name": "Lint", "conclusion": "skipped"})
    if reverse:
        api.jobs[90].reverse()
    assert decide(replay, api)["decision"] == "FAIL"


def test_previous_attempt_marker_fails_closed(replay):
    """A retained marker from a previous attempt cannot certify a rerun."""
    api = FakeAPI()
    api.artifacts[90][0]["name"] = f"gate-tip-{TIP}-attempt-1"
    assert decide(replay, api)["decision"] == "FAIL"


def test_current_attempt_marker_ignores_previous_attempt(replay):
    """A fresh attempt record is selected even when old artifacts remain."""
    api = FakeAPI()
    api.artifacts[90] = [
        {"name": f"gate-tip-{'c' * 40}-attempt-1", "expired": False},
        {"name": f"gate-tip-{TIP}-attempt-2", "expired": False},
    ]
    assert decide(replay, api)["decision"] == "PASS"


@pytest.mark.parametrize(
    "marker", ["gate-tip-short", f"gate-tip-{TIP.upper()}", f"gate-tip-{TIP}-extra"]
)
def test_invalid_marker_fails_closed(replay, marker):
    """Only an exact full-length lowercase digest marker is evidence."""
    api = FakeAPI()
    api.artifacts[90][0]["name"] = marker
    assert decide(replay, api)["decision"] == "FAIL"


def test_expired_marker_fails_closed(replay):
    """Expired artifacts cannot identify a retained full run."""
    api = FakeAPI()
    api.artifacts[90][0]["expired"] = True
    assert decide(replay, api)["decision"] == "FAIL"


def test_run_pagination(replay):
    """A full run beyond the first API page is still found."""
    api = FakeAPI()
    api.runs = [run(i, "cancelled") for i in range(99, -1, -1)] + [run(90)]
    assert decide(replay, api)["decision"] == "PASS"
    assert any("page=2" in path for path in api.calls)


def test_api_error_fails_closed(replay):
    """Transport errors produce a failed decision without leaking responses."""

    def broken(path):
        raise OSError("response body must not be printed")

    result = replay.decide(broken, CONTEXT, "Lint")
    assert result["decision"] == "FAIL"
    assert "response body" not in result["reason"]


def test_transport_rejects_non_https_before_auth(replay, monkeypatch):
    """An unsupported URL scheme is rejected before credentials are accessed."""
    monkeypatch.setenv("GITHUB_API_URL", "file:///evidence")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    with pytest.raises(ValueError):
        replay.request_json("repos/example/repository")


@pytest.mark.parametrize(
    "name", ["Lint", "Type Check", "Security Scan", "Documentation", "Test (PR gate)"]
)
@pytest.mark.parametrize("conclusion", ["success", "failure"])
def test_wait_for_active_full_run(replay, name, conclusion):
    """Metadata edits wait for exact evidence and preserve the completed result."""
    api = FakeAPI()
    api.runs[0].update(status="in_progress", conclusion=None)
    api.jobs[90][0].update(name=name, conclusion=None)

    def finish():
        api.runs[0].update(status="completed", conclusion=conclusion)
        api.jobs[90][0]["conclusion"] = conclusion

    api.on_sleep = finish
    result = replay.wait_for_decision(
        api,
        CONTEXT,
        name,
        timeout=60,
        interval=30,
        clock=lambda: api.elapsed,
        sleep=api.sleep,
    )
    assert result["decision"] == ("PASS" if conclusion == "success" else "FAIL")
    assert result["run_id"] == 90
    assert result["job_id"] == 3
    assert api.elapsed == 30


def test_wait_times_out_without_older_green(replay):
    """A newer unfinished full run blocks older success until the deadline."""
    api = FakeAPI()
    api.runs.insert(0, run(95, None, "queued"))
    result = replay.wait_for_decision(
        api,
        CONTEXT,
        "Lint",
        timeout=45,
        interval=30,
        clock=lambda: api.elapsed,
        sleep=api.sleep,
    )
    assert result["decision"] == "FAIL"
    assert result["reason"] == "replay wait timed out"
    assert result["run_id"] is None
    assert api.elapsed == 45


def test_wait_rechecks_live_base_after_completion(replay):
    """Completion cannot bless a result whose recorded base is now stale."""
    api = FakeAPI()
    api.runs[0].update(status="in_progress", conclusion=None)

    def finish():
        api.runs[0].update(status="completed", conclusion="success")
        api.tip = "c" * 40

    api.on_sleep = finish
    result = replay.wait_for_decision(
        api,
        CONTEXT,
        "Lint",
        clock=lambda: api.elapsed,
        sleep=api.sleep,
    )
    assert result["decision"] == "FAIL"
    assert "base moved" in result["reason"]


@pytest.mark.parametrize("condition", ["failed", "missing", "malformed"])
def test_wait_does_not_retry_decisive_or_invalid_evidence(replay, condition):
    """Only an active full run is retryable; invalid evidence fails closed."""
    api = FakeAPI()
    if condition == "failed":
        api.jobs[90][0]["conclusion"] = "failure"
    elif condition == "missing":
        api.runs = []
    else:
        api.artifacts = {}
    result = replay.wait_for_decision(
        api,
        CONTEXT,
        "Lint",
        clock=lambda: api.elapsed,
        sleep=api.sleep,
    )
    assert result["decision"] == "FAIL"
    assert api.elapsed == 0


def test_cli_waits_for_full_evidence(replay, tmp_path, monkeypatch, capsys):
    """The workflow entry point waits, then emits the completed audit result."""
    api = FakeAPI()
    api.runs[0].update(status="in_progress", conclusion=None)

    def finish():
        api.runs[0].update(status="completed", conclusion="success")

    api.on_sleep = finish
    event = tmp_path / "event.json"
    event.write_text(
        json.dumps(
            {
                "pull_request": {
                    "number": CONTEXT["pr"],
                    "head": {"sha": HEAD},
                    "base": {"ref": "main", "repo": {"id": 1}},
                }
            }
        ),
        encoding="utf-8",
        newline="\n",
    )
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    monkeypatch.setenv("GITHUB_REPOSITORY", CONTEXT["repository"])
    monkeypatch.setenv("GITHUB_RUN_ID", str(CONTEXT["run_id"]))
    monkeypatch.setattr(replay.sys, "argv", [str(SCRIPT), "Lint"])

    def request(path, *, budget):
        budget.request()
        return api(path)

    monkeypatch.setattr(replay, "request_json", request)
    monkeypatch.setattr(
        replay,
        "time",
        SimpleNamespace(
            monotonic=lambda: api.elapsed,
            sleep=api.sleep,
        ),
    )
    assert replay.main() == 0
    assert json.loads(capsys.readouterr().out)["job_id"] == 3
    assert api.elapsed == 120


def test_wait_cannot_copy_a_superseded_run(replay):
    """A newer failed full run arriving while waiting supersedes older green."""
    api = FakeAPI()
    api.runs[0].update(status="in_progress", conclusion=None)

    def finish():
        api.runs[0].update(status="completed", conclusion="success")
        api.runs.insert(0, run(95, "failure"))
        api.artifacts[95] = api.artifacts[90]
        api.jobs[95] = [{"id": 4, "name": "Lint", "conclusion": "failure"}]

    api.on_sleep = finish
    result = replay.wait_for_decision(
        api,
        CONTEXT,
        "Lint",
        clock=lambda: api.elapsed,
        sleep=api.sleep,
    )
    assert result["decision"] == "FAIL"
    assert result["run_id"] == 95
    assert result["job_id"] == 4


def test_wait_rejects_success_after_oversleep(replay):
    """A source completing after expiry cannot turn the replay green."""
    api = FakeAPI()
    api.runs[0].update(status="in_progress", conclusion=None)

    def oversleep(seconds):
        api.elapsed += 90
        api.runs[0].update(status="completed", conclusion="success")

    result = replay.wait_for_decision(
        api, CONTEXT, "Lint", timeout=60, clock=lambda: api.elapsed, sleep=oversleep
    )
    assert result["decision"] == "FAIL"
    assert result["reason"] == "replay wait timed out"
    assert len(api.calls) == 3


@pytest.mark.parametrize("latency, calls", [(15, 4), (20, 3)])
def test_wait_rejects_success_at_or_after_api_deadline(replay, latency, calls):
    """Request latency counts toward expiry, including the live-base lookup."""
    api = FakeAPI()

    def slow(path):
        api.elapsed += latency
        return api(path)

    result = replay.wait_for_decision(
        slow, CONTEXT, "Lint", timeout=60, clock=lambda: api.elapsed, sleep=api.sleep
    )
    assert result["decision"] == "FAIL"
    assert result["reason"] == "replay wait timed out"
    assert len(api.calls) == calls


def test_five_gates_share_repository_request_quota(replay):
    """Five long waits retain capacity under the shared repository allowance."""
    remaining = 1000
    for name in (
        "Lint",
        "Type Check",
        "Security Scan",
        "Documentation",
        "Test (PR gate)",
    ):
        api = FakeAPI()
        api.runs[0].update(status="queued", conclusion=None)
        api.jobs[90][0]["name"] = name

        def limited(path):
            nonlocal remaining
            if remaining <= 0:
                raise OSError("request quota exhausted")
            remaining -= 1
            return api(path)

        def finish():
            if api.elapsed >= 3300:
                api.runs[0].update(status="completed", conclusion="success")

        api.on_sleep = finish
        result = replay.wait_for_decision(
            limited, CONTEXT, name, clock=lambda: api.elapsed, sleep=api.sleep
        )
        assert result["decision"] == "PASS"
        assert len(api.calls) <= 180
    # 28 unfinished polls * 3 reads + 4 final reads = 88 per gate; 5 * 88 = 440.
    assert remaining == 560


@pytest.fixture
def transport(replay, monkeypatch):
    """Replace only HTTPS I/O, retaining real retry and decision code."""
    api = FakeAPI()
    state = SimpleNamespace(
        replies=[],
        calls=[],
        timeouts=[],
        read_delay=0,
        header_delay=0,
        read_size=None,
        closed=0,
    )
    monkeypatch.setenv("GH_TOKEN", "synthetic-token")
    monkeypatch.delenv("GITHUB_API_URL", raising=False)
    monkeypatch.setattr(
        replay,
        "time",
        SimpleNamespace(
            monotonic=lambda: api.elapsed,
            sleep=api.sleep,
            time=lambda: 1000 + api.elapsed,
        ),
    )

    class Connection:
        def __init__(self, host, timeout):
            state.timeouts.append(timeout)
            self.sock = self

        def settimeout(self, timeout):
            state.timeouts.append(timeout)

        def connect(self):
            pass

        def request(self, method, path, headers):
            self.path = path.lstrip("/")
            state.calls.append(self.path)

        def getresponse(self):
            api.elapsed += state.header_delay
            status, headers = state.replies.pop(0) if state.replies else (200, {})
            payload = (
                json.dumps(api(self.path)).encode("utf-8") if status == 200 else b""
            )

            class Response:
                def __init__(self):
                    self.status = status
                    self.body = payload
                    self.length = len(payload)

                def getheader(self, name, default=None):
                    return headers.get(name.lower(), default)

                def read1(self, size):
                    api.elapsed += state.read_delay
                    count = state.read_size or size
                    data, self.body = self.body[:count], self.body[count:]
                    self.length -= len(data)
                    return data

                def isclosed(self):
                    return not self.body

            return Response()

        def close(self):
            state.closed += 1

    monkeypatch.setattr(replay, "HTTPSConnection", Connection)
    return api, state


@pytest.mark.parametrize(
    "status, headers, elapsed",
    [
        (429, {"retry-after": "10"}, 10),
        (403, {"retry-after": "10"}, 10),
        (403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1015"}, 15),
        (
            429,
            {
                "retry-after": "5",
                "x-ratelimit-remaining": "0",
                "x-ratelimit-reset": "1020",
            },
            20,
        ),
        (429, {}, 60),
    ],
)
def test_transport_recovers_from_rate_limit(
    replay, transport, status, headers, elapsed
):
    """Rate limits wait for the server's delay before retrying evidence."""
    api, state = transport
    state.replies = [(status, headers)]
    result = replay.wait_for_decision(None, CONTEXT, "Lint")
    assert result["decision"] == "PASS"
    assert api.elapsed == elapsed
    assert len(state.calls) == state.closed == 5


@pytest.mark.parametrize("status", [401, 403])
def test_transport_does_not_retry_auth_rejection(replay, transport, status):
    """An authorization failure without quota evidence remains decisive."""
    api, state = transport
    state.replies = [(status, {})]
    result = replay.wait_for_decision(None, CONTEXT, "Lint")
    assert result["decision"] == "FAIL"
    assert api.elapsed == 0
    assert len(state.calls) == state.closed == 1


@pytest.mark.parametrize("status", [429, 502, 503, 504])
def test_transport_retry_cannot_outlive_deadline(replay, transport, status):
    """Retry delays consume the same deadline as the polling loop."""
    api, state = transport
    state.replies = [(status, {"retry-after": "120"})]
    result = replay.wait_for_decision(None, CONTEXT, "Lint", timeout=45)
    assert result["decision"] == "FAIL"
    assert result["reason"] == "replay wait timed out"
    assert api.elapsed == 45
    assert len(state.calls) == state.closed == 1


def test_transport_bounds_socket_phases_and_late_reads(replay, transport):
    """Header and body latency reduce each subsequent socket timeout."""
    api, state = transport
    state.header_delay = 5
    state.read_delay = 5
    state.read_size = 1
    result = replay.wait_for_decision(None, CONTEXT, "Lint", timeout=12)
    assert result["decision"] == "FAIL"
    assert result["reason"] == "replay wait timed out"
    assert state.timeouts[:4] == [12, 12, 12, 7]
    assert state.timeouts[-1] == 2
    assert len(state.calls) == state.closed == 1


def test_transport_retries_use_the_gate_request_budget(replay, transport):
    """Pagination and retries share the allowance, never bypassing the cap."""
    api, state = transport
    api.runs[0].update(status="queued", conclusion=None)
    api.jobs[90] *= 201
    state.replies = [(503, {})]
    result = replay.wait_for_decision(None, CONTEXT, "Lint", interval=1)
    assert result["decision"] == "FAIL"
    assert result["reason"] == "replay API request budget exhausted"
    assert len(state.calls) == state.closed == 180


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf")])
@pytest.mark.parametrize("parameter", ["timeout", "interval"])
def test_invalid_wait_timing_is_rejected(replay, value, parameter):
    """Invalid timing must never permit success or an unbounded wait."""
    api = FakeAPI()
    with pytest.raises(ValueError, match="positive finite"):
        replay.wait_for_decision(api, CONTEXT, "Lint", **{parameter: value})
    assert api.calls == []


@pytest.mark.parametrize(
    "headers",
    [
        {"retry-after": "nan"},
        {"retry-after": "inf"},
        {"retry-after": "-1"},
        {"x-ratelimit-remaining": "0"},
        {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "nan"},
        {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "inf"},
        {
            "retry-after": "nan",
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": "1015",
        },
    ],
)
def test_transport_rejects_invalid_rate_limit_timing(replay, transport, headers):
    """Invalid server timing fails without accepting the following success."""
    api, state = transport
    state.replies = [(429, headers)]
    result = replay.wait_for_decision(None, CONTEXT, "Lint")
    assert result["decision"] == "FAIL"
    assert api.elapsed == 0
    assert len(state.calls) == state.closed == 1


def test_transport_waits_after_last_available_request(replay, transport):
    """A successful response with no remaining quota defers the next read."""
    api, state = transport
    state.replies = [(200, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1020"})]
    result = replay.wait_for_decision(None, CONTEXT, "Lint")
    assert result["decision"] == "PASS"
    assert api.elapsed == 20
    assert len(state.calls) == state.closed == 4


def test_transport_bounds_transient_retries(replay, transport):
    """Repeated server errors fail after six attempts with bounded backoff."""
    api, state = transport
    state.replies = [(503, {})] * 6
    result = replay.wait_for_decision(None, CONTEXT, "Lint")
    assert result["decision"] == "FAIL"
    # Five pauses: 60 + 120 + 240 + 480 + 960 = 1860 seconds.
    assert api.elapsed == 1860
    assert len(state.calls) == state.closed == 6


@pytest.mark.parametrize("truncated", [False, True])
def test_transport_accepts_connection_close_response(
    replay, transport, monkeypatch, truncated
):
    """A real HTTP response can close its socket after its last body chunk."""
    api, state = transport

    class ClosingConnection(HTTPConnection):
        def connect(self):
            self.sock, self.peer = socket.socketpair()

        def request(self, method, path, headers):
            super().request(method, path, headers=headers)
            payload = json.dumps(api(path.lstrip("/"))).encode("utf-8")
            header = (
                "HTTP/1.1 200 OK\r\nConnection: close\r\n"
                f"Content-Length: {len(payload) + int(truncated)}\r\n\r\n"
            ).encode("ascii")
            self.peer.sendall(header + payload)
            self.peer.close()

    monkeypatch.setattr(replay, "HTTPSConnection", ClosingConnection)
    result = replay.wait_for_decision(None, CONTEXT, "Lint")
    assert result["decision"] == ("FAIL" if truncated else "PASS")
    assert len(api.calls) == (1 if truncated else 4)
