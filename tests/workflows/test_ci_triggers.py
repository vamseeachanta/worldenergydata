"""Keep pull request CI available for every target branch."""

from pathlib import Path

import yaml

CI_WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml"


def _load_workflow() -> dict:
    """Read the workflow with the YAML 1.1 event-key conversion handled."""
    return yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))


def test_pull_request_has_no_branch_filters() -> None:
    """Stacked pull requests receive the same workflow as default-base PRs."""
    workflow = _load_workflow()
    events = workflow["on"] if "on" in workflow else workflow[True]
    assert "pull_request" in events
    pull_request = events["pull_request"]
    assert pull_request is None or isinstance(pull_request, dict)
    filters = pull_request or {}
    assert "branches" not in filters
    assert "branches-ignore" not in filters


def test_push_branch_filter_is_unchanged() -> None:
    """Feature pushes do not duplicate pull request runs."""
    workflow = _load_workflow()
    events = workflow["on"] if "on" in workflow else workflow[True]
    assert events["push"]["branches"] == ["main", "develop"]


def test_required_pull_request_check_name_is_unchanged() -> None:
    """The aggregate keeps the name required by branch protection."""
    assert _load_workflow()["jobs"]["pr-gate"]["name"] == "Test (PR gate)"
