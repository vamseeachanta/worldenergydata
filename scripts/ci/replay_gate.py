#!/usr/bin/env python3
"""Copy a required check from a decisive full run of the exact PR head."""

import json
import os
import re
import sys
import time
from collections.abc import Callable
from http.client import HTTPException, HTTPSConnection
from typing import Any
from urllib.parse import quote, urlencode, urlsplit

API = Callable[[str], dict[str, Any]]


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
    """Choose the newest completed decisive full run; never use older evidence."""
    root = f"repos/{context['repository']}/actions"
    query = urlencode({"event": "pull_request", "head_sha": context["head"]})
    runs = pages(api, f"{root}/workflows/ci.yml/runs?{query}", "workflow_runs")
    for run in sorted(runs, key=lambda item: item["id"], reverse=True):
        if not matching(run, context):
            continue
        if run["status"] != "completed" or run["conclusion"] not in (
            "success",
            "failure",
            "timed_out",
        ):
            continue
        artifacts = pages(api, f"{root}/runs/{run['id']}/artifacts", "artifacts")
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
        jobs = pages(
            api, f"{root}/runs/{run['id']}/attempts/{run['run_attempt']}/jobs", "jobs"
        )
        if len(tips) == 1:
            return run, tips[0], jobs
        if any(item["name"].startswith("gate-tip-") for item in artifacts):
            raise ValueError("missing current-attempt base-tip evidence")
        modes = [job for job in jobs if job["name"] == "Gate mode"]
        if not jobs or (
            len(modes) == 1
            and modes[0].get("status") == "completed"
            and modes[0].get("conclusion") == "success"
        ):
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
            "full run without base-tip evidence"
            if isinstance(error, ValueError)
            and str(error) == "full run without base-tip evidence"
            else "API evidence unavailable or malformed"
        )
        return result


def request_json(path: str) -> dict[str, Any]:
    """Use the workflow's read-only token for a bounded GitHub REST request."""
    base = urlsplit(os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    if base.scheme != "https" or base.netloc != "api.github.com" or base.path:
        raise ValueError("unsupported API endpoint")
    headers = {
        "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gate-replay",
    }
    for attempt in range(6):
        connection = HTTPSConnection(base.netloc, timeout=30)
        try:
            connection.request("GET", f"/{path}", headers=headers)
            response = connection.getresponse()
            if response.status == 200:
                return json.loads(response.read())
            retry = response.status in (502, 503, 504) and attempt < 5
            if not retry:
                raise OSError("GitHub API request failed")
        finally:
            connection.close()
        time.sleep(60)
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
        result = decide(request_json, context, sys.argv[1])
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        result = {"decision": "FAIL", "reason": "invalid replay context"}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["decision"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
