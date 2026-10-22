"""Auxiliary failure reporting policy from issue #466 (2026 update).

The expected event/result truth table is enumerated by hand: only failed full
runs on main or the scheduled default branch report. PRs, other branches,
successful runs and cancelled runs must not write issues. The embedded action
script executes with fake API clients; these tests make no network requests.
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml
from test_ci_triggers import _evaluate_expression

ROOT = Path(__file__).resolve().parents[2]


def reporter():
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    return workflow["jobs"]["auxiliary-failure"]


@pytest.mark.parametrize(
    "event,ref,result,cancelled,expected",
    [
        ("push", "refs/heads/main", "failure", False, True),
        ("schedule", "refs/heads/main", "failure", False, True),
        ("workflow_dispatch", "refs/heads/main", "failure", False, True),
        ("pull_request", "refs/pull/example/merge", "failure", False, False),
        ("push", "refs/heads/develop", "failure", False, False),
        ("workflow_dispatch", "refs/heads/feature", "failure", False, False),
        ("push", "refs/heads/main", "success", False, False),
        ("push", "refs/heads/main", "skipped", False, False),
        ("push", "refs/heads/main", "cancelled", False, False),
        ("push", "refs/heads/main", "failure", True, False),
    ],
)
def test_reporting_event_policy(event, ref, result, cancelled, expected):
    expression = reporter()["if"].strip().removeprefix("${{").removesuffix("}}")
    expression = expression.replace("!cancelled()", repr(not cancelled))
    assert (
        _evaluate_expression(
            expression,
            {
                "github.event_name": event,
                "github.ref": ref,
                "needs.test.result": result,
            },
        )
        is expected
    )


def execute_script(issues, failure=None):
    fixture = json.dumps({"issues": issues, "failure": failure})
    script = json.dumps(reporter()["steps"][0]["with"]["script"])
    harness = """
const fixture = FIXTURE;
const calls = [];
const context = {
  repo: {owner: 'fixture', repo: 'fixture'},
  serverUrl: 'https://github.com', runId: 'recorded-run',
  sha: 'recorded-revision', ref: 'refs/heads/main'
};
const github = {
  rest: {issues: {
    listForRepo: 'list-issues',
    create: async args => {
      if (fixture.failure === 'create') throw new Error('create failed');
      calls.push({method: 'create', args});
    }
  }},
  paginate: async (route, args) => {
    if (fixture.failure === 'list') throw new Error('list failed');
    calls.push({method: 'paginate', route, args});
    return fixture.issues;
  }
};
const core = {notice: message => calls.push({method: 'notice', message})};
const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
new AsyncFunction('github', 'context', 'core', SCRIPT)(github, context, core)
  .then(() => process.stdout.write(JSON.stringify({calls})))
  .catch(error => process.stdout.write(JSON.stringify({calls, error: error.message})));
""".replace(
        "FIXTURE", fixture
    ).replace(
        "SCRIPT", script
    )
    result = subprocess.run(
        ["node", "-e", harness], capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def test_failure_creates_issue_with_evidence():
    result = execute_script([])
    listing, creation = result["calls"]
    assert listing == {
        "method": "paginate",
        "route": "list-issues",
        "args": {"owner": "fixture", "repo": "fixture", "state": "open"},
    }
    assert creation["method"] == "create"
    assert creation["args"]["title"] == "Auxiliary CI test failure"
    assert "actions/runs/recorded-run" in creation["args"]["body"]
    assert "recorded-revision" in creation["args"]["body"]
    assert "refs/heads/main" in creation["args"]["body"]
    assert "error" not in result


def test_open_issue_deduplicates_but_pull_request_does_not():
    matching = {"title": "Auxiliary CI test failure", "number": "recorded-issue"}
    result = execute_script([{"title": "Unrelated"}, matching])
    assert [call["method"] for call in result["calls"]] == ["paginate", "notice"]
    result = execute_script([{**matching, "pull_request": {"url": "unused"}}])
    assert [call["method"] for call in result["calls"]] == ["paginate", "create"]


@pytest.mark.parametrize("failure", ["list", "create"])
def test_api_failure_is_visible(failure):
    assert execute_script([], failure)["error"] == f"{failure} failed"


def test_reporter_permissions_and_gate_independence():
    job = reporter()
    assert job["needs"] == ["test"]
    assert job["permissions"] == {"contents": "read", "issues": "write"}
    assert job["concurrency"] == {
        "group": "auxiliary-failure-report",
        "cancel-in-progress": False,
    }
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    for key, value in workflow["jobs"].items():
        assert "auxiliary-failure" not in value.get("needs", []), key
