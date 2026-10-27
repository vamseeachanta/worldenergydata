"""Offline runner contracts for CI, PR validation and domain workflows."""

import ast
import hashlib
import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ("ci.yml", "pr-validation.yml", "domain-matrix.yml")
RUNNER_JSON = '["self-hosted","x64"]'
RUNNER_VALUES = ("self-hosted-x64", RUNNER_JSON)
LABELS = ["self-hosted", "Linux", "X64"]
JOB_NAMES = {
    "ci.yml": {
        "mode": "Gate mode",
        "domain-tests": None,
        "test": "Test Python ${{ matrix.python-version }}",
        "lint": "Lint (full)",
        "type-check": "Type Check (full)",
        "security": "Security Scan (full)",
        "build": "Build Package",
        "docs": "Documentation (full)",
        "lint-gate": "Lint",
        "type-check-gate": "Type Check",
        "security-gate": "Security Scan",
        "docs-gate": "Documentation",
        "pr-gate": "Test (PR gate)",
    },
    "domain-matrix.yml": {
        "discover": "Discover domains",
        "test-domain": "Domain ${{ matrix.name }}",
        "aggregate": "Aggregate domain results",
    },
    "pr-validation.yml": {
        "pr-title": "Validate PR Title",
        "file-size": "Check File Sizes",
        "sensitive-files": "Check Sensitive Files",
        "changelog-check": "Changelog Check",
        "code-owners": "Code Owners Check",
        "pack-lint": "Lint Changed Knowledge Packs",
    },
}


def workflow(name):
    return yaml.safe_load((ROOT / ".github/workflows" / name).read_text())


def expression_tree(expression):
    """Parse the small Actions subset used by runner and required-job guards."""
    text = expression.removeprefix("${{").removesuffix("}}").strip()
    text = text.replace("&&", " and ").replace("||", " or ")
    text = re.sub(r"!(?!=)", " not ", text)
    return ast.parse(text.strip(), mode="eval").body


def evaluate(expression, context):
    """Evaluate the YAML expression itself, preserving short-circuit values.

    Only literals, context lookups, equality, boolean operators and the two
    functions used here are accepted. Unrecognized syntax fails the contract.
    """

    def visit(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return {"true": True, "false": False, "null": None}.get(
                node.id, context.get(node.id, "")
            )
        if isinstance(node, ast.Attribute):
            parent = visit(node.value)
            return parent.get(node.attr, "") if isinstance(parent, dict) else ""
        if isinstance(node, ast.BoolOp):
            result = visit(node.values[0])
            for child in node.values[1:]:
                if isinstance(node.op, ast.And) and not result:
                    return result
                if isinstance(node.op, ast.Or) and result:
                    return result
                result = visit(child)
            return result
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not visit(node.operand)
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left, right = visit(node.left), visit(node.comparators[0])
            if isinstance(left, str) and isinstance(right, str):
                left, right = left.casefold(), right.casefold()
            if isinstance(node.ops[0], ast.Eq):
                return left == right
            if isinstance(node.ops[0], ast.NotEq):
                return left != right
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "fromJSON" and len(node.args) == 1:
                return json.loads(visit(node.args[0]))
            if node.func.id == "cancelled" and not node.args:
                return False
        raise AssertionError(f"Unsupported expression node: {ast.dump(node)}")

    return visit(expression_tree(expression))


def context(value=None, event="pull_request", fork=False, draft=False):
    data = {
        "vars": {} if value is None else {"PR_GATE_RUNNER": value},
        "github": {
            "repository": "base/repository",
            "event_name": event,
            "event": {
                "pull_request": {
                    "head": {
                        "repo": {
                            "full_name": (
                                "fork/repository" if fork else "base/repository"
                            )
                        }
                    },
                    "draft": draft,
                }
            },
        },
    }
    if event != "pull_request":
        data["github"]["event"] = {}
    return data


@pytest.mark.parametrize("name", WORKFLOWS)
@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "{broken",
        "unknown",
        '"ubuntu-missing"',
        '["self-hosted"]',
        "self-hosted-arm64",
        '"self-hosted-x64"',
        "self-hosted-x64 ",
        " self-hosted-x64",
        "self-hosted-x64-extra",
    ],
)
def test_unrecognized_configuration_uses_hosted(name, value):
    """ARM64 and arbitrary runner configuration must retain the hosted fallback."""
    for job_id, job in workflow(name)["jobs"].items():
        if "runs-on" in job:
            assert evaluate(job["runs-on"], context(value)) == "ubuntu-latest", job_id


@pytest.mark.parametrize("name", WORKFLOWS)
def test_checkout_credentials_are_not_persisted(name):
    for job_id, job in workflow(name)["jobs"].items():
        for step in job.get("steps", []):
            if step.get("uses", "").startswith("actions/checkout@"):
                assert step.get("with", {}).get("persist-credentials") is False, job_id


@pytest.mark.parametrize("name", WORKFLOWS)
def test_pr_code_has_read_only_permissions(name):
    data = workflow(name)
    assert data["permissions"] == {"contents": "read"}
    for job_id, job in data["jobs"].items():
        permissions = job.get("permissions", data["permissions"])
        assert isinstance(permissions, dict), job_id
        assert all(value in ("read", "none") for value in permissions.values()), job_id
        assert "secrets" not in job, job_id
        assert "secrets." not in json.dumps(job), job_id


def test_coverage_upload_has_no_repository_secret():
    job = workflow("ci.yml")["jobs"]["test"]
    upload = next(s for s in job["steps"] if s.get("uses", "").startswith("codecov/"))
    assert "secrets." not in json.dumps(job)
    assert upload["with"]["fail_ci_if_error"] is False


@pytest.mark.parametrize("name", WORKFLOWS)
@pytest.mark.parametrize(
    "event",
    [
        "pull_request",
        "push",
        "schedule",
        "workflow_dispatch",
        "pull_request_target",
        "workflow_call",
        "issues",
    ],
)
@pytest.mark.parametrize(
    "fork,draft", [(False, False), (True, False), (False, True), (True, True)]
)
def test_runner_selection_across_events(name, event, fork, draft):
    values = [
        None,
        "",
        "{broken",
        "unknown",
        '"ubuntu-missing"',
        "self-hosted-arm64",
        *RUNNER_VALUES,
    ]
    for job in workflow(name)["jobs"].values():
        if "runs-on" in job:
            for value in values:
                eligible = event in ("push", "workflow_dispatch") or (
                    event == "pull_request" and not fork
                )
                expected = (
                    LABELS if value in RUNNER_VALUES and eligible else "ubuntu-latest"
                )
                assert (
                    evaluate(job["runs-on"], context(value, event, fork, draft))
                    == expected
                )


@pytest.mark.parametrize("name", WORKFLOWS)
def test_fixed_mapping_cannot_parse_runner_configuration(name):
    for job in workflow(name)["jobs"].values():
        if "runs-on" not in job:
            continue
        expression = job["runs-on"]
        nodes = list(ast.walk(expression_tree(expression)))
        calls = [node for node in nodes if isinstance(node, ast.Call)]
        assert len(calls) == 1
        call = calls[0]
        assert isinstance(call.func, ast.Name) and call.func.id == "fromJSON"
        assert len(call.args) == 1 and isinstance(call.args[0], ast.Constant)
        assert json.loads(call.args[0].value) == LABELS
        assert not any(
            isinstance(node, ast.Name) and node.id == "false" for node in nodes
        )
        assert (
            "github.event.pull_request.head.repo.full_name == github.repository"
            in expression
        )
        for value in RUNNER_VALUES:
            assert f"vars.PR_GATE_RUNNER == '{value}'" in expression


@pytest.mark.parametrize("name", WORKFLOWS)
@pytest.mark.parametrize("missing", ["pull_request", "head"])
def test_pull_request_with_missing_head_uses_hosted(name, missing):
    event_context = context("self-hosted-x64")
    if missing == "pull_request":
        event_context["github"]["event"].clear()
    else:
        event_context["github"]["event"]["pull_request"].pop("head")
    for job in workflow(name)["jobs"].values():
        if "runs-on" in job:
            assert evaluate(job["runs-on"], event_context) == "ubuntu-latest"


@pytest.mark.parametrize("name", WORKFLOWS)
@pytest.mark.parametrize("draft", [False, True])
@pytest.mark.parametrize("action", ["opened", "synchronize", "reopened", "edited"])
def test_drafts_and_metadata_edits_preserve_every_gate(name, draft, action):
    data = workflow(name)
    events = data.get("on", data.get(True))
    assert "pull_request_target" not in events
    if name == "domain-matrix.yml":
        assert set(events) == {"workflow_call"}
    else:
        assert action in events["pull_request"]["types"]
        assert set(events["pull_request"]) == {"types"}
    assert {
        job_id: job.get("name") for job_id, job in data["jobs"].items()
    } == JOB_NAMES[name]
    event_context = context("self-hosted-x64", draft=draft)
    event_context["github"]["event"]["action"] = action
    for job_id, job in data["jobs"].items():
        for execution in [job, *job.get("steps", [])]:
            assert "draft" not in str(execution.get("if", "")).casefold()
        if name == "pr-validation.yml" or job_id.endswith("-gate"):
            assert evaluate(job.get("if", "true"), event_context) is True
            assert not job.get("continue-on-error", False)


def test_local_reusable_gate_preserves_required_result():
    jobs = workflow("ci.yml")["jobs"]
    reusable = jobs["domain-tests"]
    assert reusable["uses"] == "./.github/workflows/domain-matrix.yml"
    assert "runs-on" not in reusable
    assert "with" not in reusable  # No runner input exists in the inspected contract.
    assert "secrets" not in reusable
    assert jobs["pr-gate"]["needs"] == ["mode", "domain-tests"]
    full = next(
        s for s in jobs["pr-gate"]["steps"] if s.get("name") == "Gate on full result"
    )
    assert full["env"]["FULL_RESULT"] == "${{ needs.domain-tests.result }}"
    assert '"$FULL_RESULT" != success' in full["run"]
    assert "exit 1" in full["run"]


def test_domain_workflow_keeps_test_and_aggregate_contract():
    data = workflow("domain-matrix.yml")
    events = data.get("on", data.get(True))
    inputs = events["workflow_call"]["inputs"]
    assert inputs["install-cmd"]["default"] == "uv sync --frozen --all-extras"
    assert inputs["test-runner"]["default"] == "uv run --with pytest-xdist pytest"
    jobs = data["jobs"]
    assert jobs["test-domain"]["needs"] == "discover"
    assert jobs["test-domain"]["strategy"] == {
        "fail-fast": False,
        "max-parallel": "${{ inputs.max-parallel }}",
        "matrix": "${{ fromJSON(needs.discover.outputs.matrix) }}",
    }
    aggregate = jobs["aggregate"]
    assert aggregate["needs"] == ["discover", "test-domain"]
    assert aggregate["if"] == "always()"
    assert not aggregate.get("continue-on-error", False)
    for job in jobs.values():
        assert "if" not in job or job is aggregate
        assert not job.get("continue-on-error", False)
    run = aggregate["steps"][0]["run"]
    assert 'args.discover != "success" or args.test_domain != "success"' in run


@pytest.mark.parametrize("name", ("ci.yml", "pr-validation.yml"))
def test_triggers_and_conditions_match_existing_gate(name):
    """Routing must preserve triggers, dependencies, matrices and every guard."""
    data = workflow(name)
    controls = {
        "events": data.get("on", data.get(True)),
        "jobs": {
            job_id: {
                key: job.get(key)
                for key in ("if", "needs", "strategy", "continue-on-error")
            }
            | {"steps": [step.get("if") for step in job.get("steps", [])]}
            for job_id, job in data["jobs"].items()
        },
    }
    # Fingerprints of the reviewed workflows before this routing fix.
    expected = {
        "ci.yml": "931b63bf2de131a26f450ec5086dd347f84cdede290b950f4a811f023a5ef3d3",
        "pr-validation.yml": "04e9973274020af213e23fd8964a065a9249bb093286bf918f110b0bd5e0e583",
    }
    digest = hashlib.sha256(json.dumps(controls, sort_keys=True).encode()).hexdigest()
    assert digest == expected[name]


def test_domain_scaffolding_matches_shared_workflow_except_routing():
    """Pin the shared workflow's parsed content, including all test commands."""
    data = workflow("domain-matrix.yml")
    data["on"] = data.pop(True)
    for job in data["jobs"].values():
        job.pop("runs-on")
    # Shared workflow blob fetched for this copy; comments do not affect YAML.
    expected = "853c74b911a903c59153f203d6b68d58ee323dcf0f295d14f73d56693af1a680"
    assert (
        hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        == expected
    )
