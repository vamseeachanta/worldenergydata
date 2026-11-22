"""Check the importable branch rule against the production lint workflow.

Expected policy comes from issue #1353, rather than a generated ruleset:
the named lint job must be required on the default branch without bypasses.
The JSON field meanings are documented in GitHub REST API, version
2022-11-28, "Create a repository ruleset":
https://docs.github.com/en/rest/repos/rules#create-a-repository-ruleset
"""

import json
from pathlib import Path

import pytest
import yaml

ROOT = next(
    parent for parent in Path(__file__).parents if (parent / ".github").is_dir()
)
RULESET = ROOT / ".github/rulesets/required-pack-lint.json"
WORKFLOW = ROOT / ".github/workflows/pr-validation.yml"
# Issue #1353 names this check; GitHub requires the job's display name.
CONTEXT = "Lint Changed Knowledge Packs"


@pytest.fixture
def ruleset():
    return json.loads(RULESET.read_text(encoding="utf-8"))


@pytest.fixture
def workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_active_default_branch_rule_has_no_bypass(ruleset):
    """An active rule applies to the default branch with no actor exemptions."""
    assert ruleset["target"] == "branch"
    assert ruleset["enforcement"] == "active"
    assert ruleset["conditions"] == {
        "ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}
    }
    assert ruleset["bypass_actors"] == []


def test_requires_production_job_display_name(ruleset, workflow):
    """The required context is the existing job name, not its internal job ID."""
    (rule,) = ruleset["rules"]
    assert rule["type"] == "required_status_checks"
    assert rule["parameters"]["required_status_checks"] == [{"context": CONTEXT}]
    assert workflow["jobs"]["pack-lint"]["name"] == CONTEXT
    matching_jobs = [
        job for job in workflow["jobs"].values() if job.get("name") == CONTEXT
    ]
    assert matching_jobs == [workflow["jobs"]["pack-lint"]]


def test_supplement_preserves_existing_freshness_policy(ruleset):
    """Add the missing check without introducing a separate freshness change.

    The existing branch rule uses non-strict status checks. GitHub's rule
    layering applies the strictest matching policy, so false here cannot
    weaken another ruleset. Source: GitHub Docs, "About rule layering":
    https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets#about-rule-layering
    """
    (rule,) = ruleset["rules"]
    assert rule["parameters"]["strict_required_status_checks_policy"] is False
    assert rule["parameters"]["do_not_enforce_on_create"] is False


def test_required_workflow_runs_for_all_pull_requests(workflow):
    """Non-pack changes must still produce the required check's success."""
    # PyYAML's YAML 1.1 loader resolves the workflow key `on` to True.
    events = workflow.get("on", workflow.get(True))
    event = events["pull_request"]
    assert {"opened", "synchronize", "reopened"} <= set(event["types"])
    for filter_name in ("paths", "paths-ignore", "branches", "branches-ignore"):
        assert filter_name not in event


def test_required_job_cannot_skip_or_ignore_a_lint_failure(workflow):
    """A skipped job can satisfy a required check; lint must actually execute.

    Source: GitHub Docs, "Using conditions to control job execution":
    https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-jobs-with-conditions

    The existing workflow integration tests exercise SWEEP and URL failures
    through the production shell, including clean and no-pack controls.
    """
    job = workflow["jobs"]["pack-lint"]
    for execution in [job, *job["steps"]]:
        assert "if" not in execution
        assert not execution.get("continue-on-error", False)
