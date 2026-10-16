"""Fail-closed replay decisions using an in-memory API and clock."""

import importlib.util
from pathlib import Path
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
            return {"jobs": self.jobs.get(run_id, []) if page == 1 else []}
        raise AssertionError(path)

    def sleep(self, seconds):
        """Advance only the fake clock and optionally finish a source run."""
        self.elapsed += seconds
        if self.on_sleep:
            self.on_sleep()


def decide(replay, api, **kwargs):
    """Invoke the real decision engine without real sleeping or networking."""
    return replay.decide(
        api, CONTEXT, "Lint", sleep=api.sleep, monotonic=lambda: api.elapsed, **kwargs
    )


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


def test_in_progress_source_is_waited_for(replay):
    """The latest active full run wins over an older green run."""
    api = FakeAPI()
    api.runs[0].update(status="in_progress", conclusion=None)

    def finish():
        api.runs[0].update(status="completed", conclusion="success")

    api.on_sleep = finish
    assert decide(replay, api)["decision"] == "PASS"
    assert api.elapsed == 30


def test_wait_timeout(replay):
    """A full run that never completes fails at the 45-minute boundary."""
    api = FakeAPI()
    api.runs[0].update(status="queued", conclusion=None)
    result = decide(replay, api)
    assert result["decision"] == "FAIL"
    assert "timeout" in result["reason"]
    assert api.elapsed == 2700


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
    api.jobs[95] = [{"name": "Gate mode", "status": "completed"}]
    assert decide(replay, api)["decision"] == "PASS"
    assert api.elapsed == 0


@pytest.mark.parametrize(
    "conclusion", ["success", "skipped", "failure", "timed_out", "cancelled", None]
)
def test_same_named_job_conclusions(replay, conclusion):
    """Only a successful or deliberately skipped source job passes."""
    api = FakeAPI()
    api.jobs[90][0]["conclusion"] = conclusion
    result = decide(replay, api)
    assert result["decision"] == (
        "PASS" if conclusion in ("success", "skipped") else "FAIL"
    )


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
def test_duplicate_job_names_ignore_inactive_twin(replay, reverse):
    """The completed heavy job wins over its same-named skipped twin."""
    api = FakeAPI()
    api.jobs[90].append({"id": 4, "name": "Lint", "conclusion": "skipped"})
    if reverse:
        api.jobs[90].reverse()
    assert decide(replay, api)["job_id"] == 3
    next(job for job in api.jobs[90] if job["id"] == 3)["conclusion"] = "failure"
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
