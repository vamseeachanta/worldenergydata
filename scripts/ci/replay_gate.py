#!/usr/bin/env python3
"""Copy a required check from a decisive full run of the exact PR head."""

import json
import math
import os
import re
import sys
import time
from collections.abc import Callable
from http.client import HTTPException, HTTPSConnection
from typing import Any
from urllib.parse import quote, urlencode, urlsplit

API = Callable[[str], dict[str, Any]]


class ReplayBudget:
    """Share one deadline and request allowance across polling and retries.

    Five replay gates reserve 180 requests each: 5 * 180 = 900, leaving 100
    of GitHub's shared 1000 requests/hour for other repository API consumers.
    See GitHub REST API docs, "Primary rate limit for GITHUB_TOKEN".
    """

    def __init__(self, timeout, clock, sleep):
        self.clock = clock
        self.sleep = sleep
        self.deadline = clock() + timeout
        self.requests = 0
        self.resume_at = 0.0

    def remaining(self) -> float:
        """Reject expiry before another operation or acceptance of evidence."""
        remaining = self.deadline - self.clock()
        if remaining <= 0:
            raise TimeoutError("replay wait timed out")
        return remaining

    def pause(self, seconds: float) -> None:
        """Clip all sleeps to the common deadline and reject oversleep."""
        self.sleep(min(seconds, self.remaining()))
        self.remaining()

    def request(self) -> float:
        """Charge each HTTP attempt, including retries and pagination."""
        self.remaining()
        if self.resume_at > self.clock():
            self.pause(self.resume_at - self.clock())
        if self.requests >= 180:
            raise ValueError("replay API request budget exhausted")
        self.requests += 1
        return min(30, self.remaining())


def pages(api: API, path: str, key: str) -> list[dict[str, Any]]:
    """Read every page rather than treating a truncated list as evidence."""
    result = []
    separator = "&" if "?" in path else "?"
    for page in range(1, 12):
        values = api(f"{path}{separator}per_page=100&page={page}")[key]
        result.extend(values)
        if len(values) < 100:
            return result
    raise ValueError("API pagination limit reached")


def matching(run: dict[str, Any], context: dict[str, Any]) -> bool:
    """Require an earlier run for the same head, PR and base identity."""
    return (
        run["id"] < context["run_id"]
        and run["event"] == "pull_request"
        and run["head_sha"] == context["head"]
        and any(
            pr["number"] == context["pr"]
            and pr["base"]["ref"] == context["base_ref"]
            and pr["base"]["repo"]["id"] == context["base_repository_id"]
            for pr in run["pull_requests"]
        )
    )


def source(api: API, context: dict[str, Any]) -> tuple[dict, str, list] | None:
    """Choose decisive full evidence; reject a newer unfinished full run."""
    root = f"repos/{context['repository']}/actions"
    query = urlencode({"event": "pull_request", "head_sha": context["head"]})
    runs = pages(api, f"{root}/workflows/ci.yml/runs?{query}", "workflow_runs")
    for run in sorted(runs, key=lambda item: item["id"], reverse=True):
        if not matching(run, context):
            continue
        if run["status"] == "completed" and run["conclusion"] not in (
            "success",
            "failure",
            "timed_out",
        ):
            continue
        artifacts = pages(api, f"{root}/runs/{run['id']}/artifacts", "artifacts")
        jobs = pages(
            api, f"{root}/runs/{run['id']}/attempts/{run['run_attempt']}/jobs", "jobs"
        )
        modes = [job for job in jobs if job["name"] == "Gate mode"]
        is_replay = (
            len(modes) == 1
            and modes[0].get("status") == "completed"
            and modes[0].get("conclusion") == "success"
        )
        has_marker = any(item["name"].startswith("gate-tip-") for item in artifacts)
        if run["status"] != "completed":
            if is_replay and not has_marker:
                continue
            raise ValueError("newer full run in progress")
        tips = [
            item["name"][9:49]
            for item in artifacts
            if re.fullmatch(
                rf"gate-tip-[0-9a-f]{{40}}-attempt-{run['run_attempt']}", item["name"]
            )
            and not item.get("expired", True)
        ]
        if len(tips) > 1:
            raise ValueError("ambiguous base-tip evidence")
        if len(tips) == 1:
            return run, tips[0], jobs
        if has_marker:
            raise ValueError("missing current-attempt base-tip evidence")
        if not jobs or is_replay:
            continue
        raise ValueError("full run without base-tip evidence")
    return None


def copy_job(jobs: list[dict], name: str, result: dict) -> dict:
    """Require exactly one successful source job under the required name."""
    matches = [job for job in jobs if job["name"] == name]
    if len(matches) != 1:
        result["reason"] = "missing or ambiguous source job"
        return result
    job = matches[0]
    result.update(job_id=job["id"], conclusion=job.get("conclusion"))
    if job.get("conclusion") == "success":
        result.update(decision="PASS", reason="source job passed")
    else:
        result["reason"] = "source job did not pass"
    return result


def decide(
    api: API,
    context: dict[str, Any],
    job_name: str,
) -> dict[str, Any]:
    """Fail closed on absent, stale, failed or unverifiable full-run evidence."""
    result = dict(
        decision="FAIL",
        reason="no earlier decisive full run",
        run_id=None,
        attempt=None,
        head=context["head"],
        recorded_tip=None,
        live_tip=None,
        job_id=None,
        conclusion=None,
    )
    try:
        candidate = source(api, context)
        if candidate is None:
            return result
        run, tip, jobs = candidate
        result.update(run_id=run["id"], attempt=run["run_attempt"], recorded_tip=tip)
        result = copy_job(jobs, job_name, result)
        base = quote(context["base_ref"], safe="")
        live = api(f"repos/{context['repository']}/branches/{base}")["commit"]["sha"]
        result["live_tip"] = live
        if live != tip:
            result["decision"] = "FAIL"
            result["reason"] = (
                "the base moved since the last full run; push or re-run the gate"
            )
            return result
        return result
    except (OSError, HTTPException, ValueError, KeyError, TypeError) as error:
        result["decision"] = "FAIL"
        result["reason"] = (
            str(error)
            if isinstance(error, ValueError)
            and str(error)
            in (
                "full run without base-tip evidence",
                "newer full run in progress",
                "replay API request budget exhausted",
            )
            else "API evidence unavailable or malformed"
        )
        return result


def wait_for_decision(
    api: API | None,
    context: dict[str, Any],
    job_name: str,
    *,
    timeout: float = 3600,
    interval: float = 120,
    clock: Callable[[], float] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    """Reject evidence arriving at or after the one-hour replay deadline.

    Metadata edits can arrive before a full run completes. Re-read all evidence
    after each wait so a newer run or a changed live base cannot expose stale
    success. Decisive failures and invalid evidence still fail immediately.
    At 120 seconds, 30 three-request active polls across five gates use 450
    requests/hour, before final evidence, pagination and bounded retries.
    """
    if any(not math.isfinite(value) or value <= 0 for value in (timeout, interval)):
        raise ValueError("replay timing must be positive finite numbers")
    clock = clock or time.monotonic
    sleep = sleep or time.sleep
    budget = ReplayBudget(timeout, clock, sleep)

    def fetch(path):
        if api is None:
            return request_json(path, budget=budget)
        budget.request()
        value = api(path)
        budget.remaining()
        return value

    result = {"decision": "FAIL"}
    try:
        while True:
            budget.remaining()
            result = decide(fetch, context, job_name)
            budget.remaining()
            if result["reason"] != "newer full run in progress":
                return result
            budget.pause(interval)
    except TimeoutError:
        result.update(decision="FAIL", reason="replay wait timed out")
        return result


def retry_delay(response, attempt: int) -> float:
    """Honor server quota/reset headers; otherwise back off exponentially."""
    retry_after = response.getheader("retry-after")
    delay = float(retry_after) if retry_after is not None else 60 * 2**attempt
    if not math.isfinite(delay) or delay < 0:
        raise ValueError("invalid API retry delay")
    if response.getheader("x-ratelimit-remaining") == "0":
        reset = float(response.getheader("x-ratelimit-reset"))
        if not math.isfinite(reset) or reset < 0:
            raise ValueError("invalid API retry delay")
        delay = max(float(retry_after or 0), reset - time.time(), 0)
    return delay


def request_json(path: str, *, budget: ReplayBudget | None = None) -> dict[str, Any]:
    """Use the workflow's read-only token for a bounded GitHub REST request."""
    base = urlsplit(os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    if base.scheme != "https" or base.netloc != "api.github.com" or base.path:
        raise ValueError("unsupported API endpoint")
    budget = budget or ReplayBudget(3600, time.monotonic, time.sleep)
    headers = {
        "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gate-replay",
    }
    for attempt in range(6):
        connection = HTTPSConnection(base.netloc, timeout=budget.request())
        try:
            connection.connect()
            sock = connection.sock
            sock.settimeout(min(30, budget.remaining()))
            connection.request("GET", f"/{path}", headers=headers)
            sock.settimeout(min(30, budget.remaining()))
            response = connection.getresponse()
            if response.status == 200:
                chunks = []
                while True:
                    sock.settimeout(min(30, budget.remaining()))
                    chunk = response.read1(65536)
                    budget.remaining()
                    if not chunk:
                        if response.length not in (None, 0):
                            raise HTTPException("incomplete API response")
                        break
                    chunks.append(chunk)
                    if response.isclosed():
                        if response.length not in (None, 0):
                            raise HTTPException("incomplete API response")
                        break
                if response.getheader("x-ratelimit-remaining") == "0":
                    budget.resume_at = budget.clock() + retry_delay(response, 0)
                return json.loads(b"".join(chunks))
            rate_limited = response.status == 429 or (
                response.status == 403
                and (
                    response.getheader("x-ratelimit-remaining") == "0"
                    or response.getheader("retry-after") is not None
                )
            )
            if not (rate_limited or response.status in (502, 503, 504)) or attempt == 5:
                raise OSError("GitHub API request failed")
            delay = retry_delay(response, attempt)
        finally:
            connection.close()
        budget.pause(delay)
    raise OSError("GitHub API retries exhausted")


def main() -> int:
    """Emit one audit line and return the actual copied decision."""
    try:
        with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as stream:
            event = json.load(stream)
        pr = event["pull_request"]
        context = dict(
            repository=os.environ["GITHUB_REPOSITORY"],
            run_id=int(os.environ["GITHUB_RUN_ID"]),
            head=pr["head"]["sha"],
            pr=pr["number"],
            base_ref=pr["base"]["ref"],
            base_repository_id=pr["base"]["repo"]["id"],
        )
        result = wait_for_decision(None, context, sys.argv[1])
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        result = {"decision": "FAIL", "reason": "invalid replay context"}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["decision"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
