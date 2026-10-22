"""Offline expectations for issue #1353, derived independently of the auditor.

The recorded fixture is the required_status_checks projection of the branch
rules API response observed on 2026-10-22. No identifiers from source metadata
are retained. Hand inspection: its contexts omit Lint Changed Knowledge Packs,
so FAIL is expected. Adding exactly that context must give PASS. An empty
readable response has no requirement; an unreadable response is NOT_EVALUATED.
Schema source: GitHub REST API 2022-11-28, "Get rules for a branch":
https://docs.github.com/en/rest/repos/rules#get-rules-for-a-branch
"""

import copy
import json
import runpy
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/ci/audit_required_pack_check.py"
RECORDED = Path(__file__).parent / "ruleset_audit/active-branch-rules.json"
CONTEXT = "Lint Changed Knowledge Packs"


def auditor():
    return runpy.run_path(str(SCRIPT))


def recorded():
    return json.loads(RECORDED.read_text())


def test_recorded_response_does_not_require_pack_lint():
    assert auditor()["evaluate_rules"](recorded()) == "FAIL"


def test_exact_required_context_passes():
    rules = copy.deepcopy(recorded())
    rules[0]["parameters"]["required_status_checks"].append({"context": CONTEXT})
    assert auditor()["evaluate_rules"](rules) == "PASS"


@pytest.mark.parametrize("context", ["pack-lint", CONTEXT.lower(), CONTEXT + " extra"])
def test_similar_names_are_not_the_required_display_name(context):
    rules = [
        {
            "type": "required_status_checks",
            "parameters": {"required_status_checks": [{"context": context}]},
        }
    ]
    assert auditor()["evaluate_rules"](rules) == "FAIL"


@pytest.mark.parametrize("rules", [[], [{"type": "pull_request"}]])
def test_readable_rules_without_requirement_fail(rules):
    assert auditor()["evaluate_rules"](rules) == "FAIL"


@pytest.mark.parametrize(
    "rules",
    [
        None,
        {},
        [None],
        [{"type": "required_status_checks"}],
        [{"type": "required_status_checks", "parameters": {}}],
        [
            {
                "type": "required_status_checks",
                "parameters": {"required_status_checks": None},
            }
        ],
        [
            {
                "type": "required_status_checks",
                "parameters": {"required_status_checks": [{}]},
            }
        ],
    ],
)
def test_unreadable_schema_is_not_evaluated(rules):
    assert auditor()["evaluate_rules"](rules) == "NOT_EVALUATED"


def test_readonly_api_collects_all_pages():
    module = auditor()
    pages = [
        [],
        [
            {
                "type": "required_status_checks",
                "parameters": {"required_status_checks": [{"context": CONTEXT}]},
            }
        ],
    ]
    completed = subprocess.CompletedProcess(
        [], 0, "\n".join(json.dumps(page) for page in pages), ""
    )
    with patch("subprocess.run", return_value=completed) as api:
        assert (
            module["main"](["--repo", "example/repository", "--branch", "release/test"])
            == 0
        )
    command = api.call_args.args[0]
    assert command[:4] == ["gh", "api", "--method", "GET"]
    assert "--paginate" in command and "--slurp" not in command
    assert command[-1].endswith("/rules/branches/release%2Ftest")


@pytest.mark.parametrize(
    "error", [FileNotFoundError(), subprocess.CalledProcessError(1, "gh")]
)
def test_unavailable_api_is_not_evaluated(error, capsys):
    with patch("subprocess.run", side_effect=error):
        assert auditor()["main"](["--repo", "example/repository"]) == 2
    assert capsys.readouterr().out.startswith("NOT_EVALUATED:")


@pytest.mark.parametrize("contents", ["not JSON", "{}", "[[{}]]"])
def test_invalid_offline_record_is_not_evaluated(tmp_path, contents, capsys):
    source = tmp_path / "rules.json"
    source.write_text(contents)
    assert auditor()["main"](["--rules-json", str(source)]) == 2
    assert capsys.readouterr().out.startswith("NOT_EVALUATED:")


def test_offline_cli_reports_failure_without_network():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--rules-json", str(RECORDED)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert result.stdout.startswith("FAIL:")


@pytest.mark.parametrize("contents", ["", "{}", "[] broken", "[] {}"])
def test_incomplete_api_pages_are_not_evaluated(contents, capsys):
    completed = subprocess.CompletedProcess([], 0, contents, "")
    with patch("subprocess.run", return_value=completed):
        assert auditor()["main"](["--repo", "example/repository"]) == 2
    assert capsys.readouterr().out.startswith("NOT_EVALUATED:")


def test_valid_requirement_cannot_hide_malformed_evidence():
    rules = [
        {
            "type": "required_status_checks",
            "parameters": {"required_status_checks": [{"context": CONTEXT}]},
        },
        None,
    ]
    assert auditor()["evaluate_rules"](rules) == "NOT_EVALUATED"
